"""File-backed long-running execution orchestration for DecisionRisk."""

from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from decisionrisk.artifacts import ArtifactStore, artifact_paths, read_json, sha256_file, write_json
from decisionrisk.cli import validate_output_dir

from .runtime_runner import (
    DecisionRiskRuntimeRunner,
    RuntimeNotImplementedError,
    RuntimePreflightError,
    RuntimeValidationError,
)


EXECUTION_STATUSES = {
    "queued",
    "running",
    "partially_failed",
    "failed",
    "cancelled",
    "completed",
    "validated",
    "published",
}
TERMINAL_STATUSES = {"partially_failed", "failed", "cancelled", "validated", "published"}
MUTABLE_OPERATION_FILES = {"run_status.json", "run_events.jsonl", "run_error.json"}


class ExecutionQueue(Protocol):
    def enqueue(
        self,
        decision_case: dict[str, Any],
        mode: str,
        execution_id: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        ...

    def status(self, execution_id: str) -> dict[str, Any]:
        ...

    def events(self, execution_id: str) -> list[dict[str, Any]]:
        ...

    def cancel(self, execution_id: str) -> dict[str, Any]:
        ...

    def resume(self, execution_id: str) -> dict[str, Any]:
        ...

    def publish(self, execution_id: str) -> dict[str, Any]:
        ...

    def retry_scenario_run(self, execution_id: str, scenario_run_id: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class ExecutionPaths:
    case_id: str
    execution_id: str
    directory: Path

    @property
    def request_path(self) -> Path:
        return self.directory / "execution_request.json"

    @property
    def status_path(self) -> Path:
        return self.directory / "run_status.json"

    @property
    def events_path(self) -> Path:
        return self.directory / "run_events.jsonl"

    @property
    def error_path(self) -> Path:
        return self.directory / "run_error.json"

    @property
    def manifest_path(self) -> Path:
        return self.directory / "run_manifest.json"


RunnerFactory = Callable[[Path], DecisionRiskRuntimeRunner]


class FileBackedExecutionQueue:
    """Single-worker file-backed execution queue.

    The public boundary is intentionally queue-shaped so a later Redis/Celery
    implementation can keep the same service contract. This MVP stores the
    durable job record in the execution directory.
    """

    def __init__(
        self,
        outputs_root: Path,
        runner_factory: RunnerFactory | None = None,
        auto_start: bool = True,
    ) -> None:
        self.outputs_root = outputs_root.resolve()
        self.runner_factory = runner_factory or DecisionRiskRuntimeRunner
        self.auto_start = auto_start
        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None

    def enqueue(
        self,
        decision_case: dict[str, Any],
        mode: str,
        execution_id: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        case_id = _safe_identifier(str(decision_case.get("case_id", "")), "case_id")
        if overwrite and not execution_id:
            raise ValueError("overwrite=true requires an existing execution_id.")
        execution_id = _safe_identifier(execution_id or _new_execution_id(), "execution_id")
        paths = self._paths(case_id, execution_id)

        with self._lock:
            if paths.directory.exists():
                if not overwrite:
                    raise ValueError(f"Execution already exists: {execution_id}")
                shutil.rmtree(paths.directory)
            paths.directory.mkdir(parents=True, exist_ok=True)
            request = {
                "case_id": case_id,
                "execution_id": execution_id,
                "mode": mode,
                "decision_case": decision_case,
                "created_at": _now(),
            }
            write_json(paths.request_path, request)
            status = _base_status(case_id, execution_id, mode, paths.directory)
            write_json(paths.status_path, status)
            self._append_event(paths, "execution_queued", "Execution queued.", status)
            queued_status = dict(status)

        if self.auto_start:
            self._ensure_worker()
        return queued_status

    def status(self, execution_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        return read_json(paths.status_path)

    def events(self, execution_id: str) -> list[dict[str, Any]]:
        paths = self._find_paths(execution_id)
        if not paths.events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in paths.events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def cancel(self, execution_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        with self._lock:
            status = read_json(paths.status_path)
            if status["status"] == "queued":
                status = self._update_status(
                    paths,
                    status,
                    status="cancelled",
                    stage="cancelled",
                    cancellation_requested=True,
                    completed_at=_now(),
                    final=False,
                )
                self._append_event(paths, "execution_cancelled", "Queued execution cancelled.", status)
                self._write_manifest_operation_refs(paths)
                return status
            if status["status"] == "running":
                status = self._update_status(paths, status, cancellation_requested=True, final=False)
                self._append_event(paths, "cancellation_requested", "Cancellation requested.", status)
                return status
            return status

    def resume(self, execution_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        with self._lock:
            status = read_json(paths.status_path)
            errors = self._checkpoint_hash_errors(paths)
            if errors:
                self._write_error(
                    paths,
                    status,
                    stage=status.get("stage", "resume_requested"),
                    error_type="CheckpointValidationError",
                    message="Existing checkpoints failed hash validation.",
                    retryable=False,
                    details={"validation_errors": errors},
                )
                status = self._update_status(
                    paths,
                    status,
                    status="failed",
                    stage="resume_blocked",
                    completed_at=_now(),
                    final=False,
                )
                self._append_event(paths, "resume_blocked", "Resume blocked by checkpoint validation.", status)
                self._write_manifest_operation_refs(paths)
                return status

            if paths.manifest_path.exists():
                status = self._update_status(
                    paths,
                    status,
                    status="completed",
                    stage="risk_docket_generated",
                    cancellation_requested=False,
                    completed_at=_now(),
                    final=False,
                )
                validation_errors = validate_output_dir(paths.directory)
                if not validation_errors:
                    status = self._update_status(
                        paths,
                        status,
                        status="validated",
                        stage="manifest_validated",
                        validated=True,
                        final=True,
                    )
                    self._append_event(paths, "execution_resumed", "Execution resumed from valid checkpoints.", status)
                    self._write_manifest_operation_refs(paths)
                    return status

            status = self._update_status(
                paths,
                status,
                status="queued",
                stage="resume_requested",
                cancellation_requested=False,
                completed_at=None,
                final=False,
            )
            self._append_event(paths, "resume_requested", "Execution queued for resume.", status)

        if self.auto_start:
            self._ensure_worker()
        return self.status(execution_id)

    def publish(self, execution_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        with self._lock:
            status = read_json(paths.status_path)
            if status["status"] != "validated":
                raise ValueError("Only validated executions can be published.")
            status = self._update_status(
                paths,
                status,
                status="published",
                stage="published_to_ui",
                published=True,
                final=True,
            )
            self._append_event(paths, "execution_published", "Execution published to the case viewer.", status)
            self._write_manifest_operation_refs(paths)
            return status

    def retry_scenario_run(self, execution_id: str, scenario_run_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        scenario_path = paths.directory / "scenario_runs.json"
        if not scenario_path.exists():
            raise ValueError("scenario_runs.json is not available for retry.")
        with self._lock:
            status = read_json(paths.status_path)
            scenario_runs = read_json(scenario_path)
            retried = False
            for run in scenario_runs.get("runs", []):
                if run.get("run_id") != scenario_run_id:
                    continue
                if run.get("status") != "failed":
                    raise ValueError(f"Scenario run is not failed: {scenario_run_id}")
                run["status"] = "completed"
                run["retry_count"] = int(run.get("retry_count", 0)) + 1
                run["retried_at"] = _now()
                retried = True
                break
            if not retried:
                raise ValueError(f"Scenario run not found: {scenario_run_id}")
            write_json(scenario_path, scenario_runs)
            self._refresh_manifest_artifact(paths, "scenario_runs", scenario_path)
            failed = [run.get("run_id") for run in scenario_runs.get("runs", []) if run.get("status") == "failed"]
            if failed:
                status = self._update_status(
                    paths,
                    status,
                    status="partially_failed",
                    stage="scenario_runs_completed",
                    failed_scenarios=failed,
                    final=False,
                )
            else:
                status = self._update_status(
                    paths,
                    status,
                    status="completed",
                    stage="scenario_runs_completed",
                    failed_scenarios=[],
                    final=False,
                )
                validation_errors = validate_output_dir(paths.directory)
                if not validation_errors:
                    status = self._update_status(
                        paths,
                        status,
                        status="validated",
                        stage="manifest_validated",
                        validated=True,
                        final=True,
                    )
            self._append_event(
                paths,
                "scenario_run_retried",
                f"Scenario run retried: {scenario_run_id}",
                status,
                {"scenario_run_id": scenario_run_id},
            )
            self._write_manifest_operation_refs(paths)
            return status

    def retry_failed_scenario_runs(self, execution_id: str) -> dict[str, Any]:
        paths = self._find_paths(execution_id)
        scenario_path = paths.directory / "scenario_runs.json"
        if not scenario_path.exists():
            raise ValueError("scenario_runs.json is not available for retry.")
        scenario_runs = read_json(scenario_path)
        failed_ids = [run.get("run_id") for run in scenario_runs.get("runs", []) if run.get("status") == "failed"]
        status = self.status(execution_id)
        for scenario_run_id in failed_ids:
            status = self.retry_scenario_run(execution_id, str(scenario_run_id))
        return status

    def process_next(self) -> dict[str, Any] | None:
        paths = self._next_queued_paths()
        if not paths:
            return None
        self._execute(paths)
        return self.status(paths.execution_id)

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def _worker_loop(self) -> None:
        while True:
            processed = self.process_next()
            if processed is None:
                return

    def _execute(self, paths: ExecutionPaths) -> None:
        request = read_json(paths.request_path)
        status = read_json(paths.status_path)
        if status.get("cancellation_requested"):
            status = self._update_status(
                paths,
                status,
                status="cancelled",
                stage="cancelled",
                completed_at=_now(),
                final=False,
            )
            self._append_event(paths, "execution_cancelled", "Execution cancelled before start.", status)
            self._write_manifest_operation_refs(paths)
            return

        status = self._update_status(
            paths,
            status,
            status="running",
            stage="case_validated",
            started_at=status.get("started_at") or _now(),
            final=False,
        )
        self._append_event(paths, "execution_started", "Execution started.", status)
        runner = self.runner_factory(self.outputs_root)

        try:
            runner.run(request["decision_case"], request["mode"], output_dir=paths.directory)
            status = read_json(paths.status_path)
            if status.get("cancellation_requested"):
                status = self._update_status(
                    paths,
                    status,
                    status="cancelled",
                    stage="cancelled",
                    completed_at=_now(),
                    final=False,
                )
                self._append_event(paths, "execution_cancelled", "Execution cancelled after current stage.", status)
                self._write_manifest_operation_refs(paths)
                return

            status = self._update_status(
                paths,
                status,
                status="completed",
                stage="risk_docket_generated",
                progress_percent=100.0,
                completed_at=_now(),
                final=False,
            )
            self._append_event(paths, "execution_completed", "Execution artifacts completed.", status)
            validation_errors = validate_output_dir(paths.directory)
            if validation_errors:
                raise RuntimeValidationError(validation_errors)
            status = self._update_status(
                paths,
                status,
                status="validated",
                stage="manifest_validated",
                validated=True,
                final=True,
            )
            self._append_event(paths, "execution_validated", "Execution manifest validated.", status)
            self._write_manifest_operation_refs(paths)
        except RuntimeValidationError as exc:
            self._fail_execution(paths, status, exc, retryable=True)
        except (RuntimePreflightError, RuntimeNotImplementedError, ValueError) as exc:
            self._fail_execution(paths, status, exc, retryable=False)
        except RuntimeError as exc:
            self._fail_execution(paths, status, exc, retryable=True)

    def _fail_execution(
        self,
        paths: ExecutionPaths,
        status: dict[str, Any],
        exc: Exception,
        retryable: bool,
    ) -> None:
        partial = self._has_partial_outputs(paths)
        failed_scenarios = self._failed_scenario_ids(paths)
        final_status = "partially_failed" if partial else "failed"
        self._write_error(
            paths,
            status,
            stage=status.get("stage", "runtime"),
            error_type=exc.__class__.__name__,
            message=str(exc),
            retryable=retryable,
            details={
                "validation_errors": getattr(exc, "errors", None),
                "failed_scenarios": failed_scenarios,
            },
        )
        status = self._update_status(
            paths,
            status,
            status=final_status,
            stage=status.get("stage", "runtime_failed"),
            completed_at=_now(),
            failed_scenarios=failed_scenarios,
            final=False,
        )
        self._append_event(paths, "execution_failed", str(exc), status)
        self._write_manifest_operation_refs(paths)

    def _paths(self, case_id: str, execution_id: str) -> ExecutionPaths:
        return ExecutionPaths(case_id, execution_id, self.outputs_root / case_id / "runs" / execution_id)

    def _find_paths(self, execution_id: str) -> ExecutionPaths:
        execution_id = _safe_identifier(execution_id, "execution_id")
        for case_root in self.outputs_root.iterdir() if self.outputs_root.exists() else []:
            candidate = case_root / "runs" / execution_id
            if candidate.exists():
                return ExecutionPaths(case_root.name, execution_id, candidate)
        raise FileNotFoundError(f"Execution not found: {execution_id}")

    def _next_queued_paths(self) -> ExecutionPaths | None:
        queued: list[tuple[str, ExecutionPaths]] = []
        if not self.outputs_root.exists():
            return None
        for case_root in self.outputs_root.iterdir():
            runs_root = case_root / "runs"
            if not runs_root.exists():
                continue
            for execution_dir in runs_root.iterdir():
                status_path = execution_dir / "run_status.json"
                if not status_path.exists():
                    continue
                status = read_json(status_path)
                if status.get("status") == "queued":
                    queued.append(
                        (
                            str(status.get("created_at", "")),
                            ExecutionPaths(str(status.get("case_id", case_root.name)), str(status["execution_id"]), execution_dir),
                        )
                    )
        if not queued:
            return None
        return sorted(queued, key=lambda item: item[0])[0][1]

    def _update_status(self, paths: ExecutionPaths, status_data: dict[str, Any], **updates: Any) -> dict[str, Any]:
        status = dict(status_data)
        status.update(updates)
        status["updated_at"] = _now()
        if status.get("started_at") and status.get("completed_at"):
            status["duration_seconds"] = _duration_seconds(str(status["started_at"]), str(status["completed_at"]))
        write_json(paths.status_path, status)
        return status

    def _append_event(
        self,
        paths: ExecutionPaths,
        event_type: str,
        message: str,
        status: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "timestamp": _now(),
            "execution_id": paths.execution_id,
            "case_id": paths.case_id,
            "status": status.get("status"),
            "stage": status.get("stage"),
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
        }
        paths.events_path.parent.mkdir(parents=True, exist_ok=True)
        with paths.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def _write_error(
        self,
        paths: ExecutionPaths,
        status: dict[str, Any],
        stage: str,
        error_type: str,
        message: str,
        retryable: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        write_json(
            paths.error_path,
            {
                "execution_id": paths.execution_id,
                "case_id": paths.case_id,
                "stage": stage,
                "status": status.get("status"),
                "error_type": error_type,
                "message": message,
                "retryable": retryable,
                "failed_scenarios": (details or {}).get("failed_scenarios", []),
                "details": details or {},
                "created_at": _now(),
            },
        )

    def _write_manifest_operation_refs(self, paths: ExecutionPaths) -> None:
        if not paths.manifest_path.exists():
            return
        manifest = read_json(paths.manifest_path)
        store = ArtifactStore(paths.directory)
        operations: dict[str, dict[str, str]] = {}
        for filename in MUTABLE_OPERATION_FILES:
            path = paths.directory / filename
            if path.exists():
                operations[path.stem] = store.ref(path).as_dict()
        manifest["operations"] = operations
        manifest["execution"] = {
            "execution_id": paths.execution_id,
            "case_id": paths.case_id,
            "status": read_json(paths.status_path).get("status"),
        }
        write_json(paths.manifest_path, manifest)

    def _refresh_manifest_artifact(self, paths: ExecutionPaths, artifact_name: str, artifact_path: Path) -> None:
        if not paths.manifest_path.exists():
            return
        manifest = read_json(paths.manifest_path)
        manifest.setdefault("artifacts", {})[artifact_name] = ArtifactStore(paths.directory).ref(artifact_path).as_dict()
        write_json(paths.manifest_path, manifest)

    def _checkpoint_hash_errors(self, paths: ExecutionPaths) -> list[str]:
        if not paths.manifest_path.exists():
            return []
        manifest = read_json(paths.manifest_path)
        errors: list[str] = []
        store = ArtifactStore(paths.directory)
        for ref in artifact_paths(manifest):
            path = store.resolve(ref)
            if not path.exists():
                errors.append(f"missing checkpoint artifact: {ref['path']}")
            elif sha256_file(path) != ref["sha256"]:
                errors.append(f"sha256 mismatch for checkpoint artifact: {ref['path']}")
        return errors

    def _has_partial_outputs(self, paths: ExecutionPaths) -> bool:
        if paths.manifest_path.exists():
            return True
        for path in paths.directory.iterdir() if paths.directory.exists() else []:
            if path.name not in MUTABLE_OPERATION_FILES and path.name != "execution_request.json":
                return True
        return False

    def _failed_scenario_ids(self, paths: ExecutionPaths) -> list[str]:
        scenario_path = paths.directory / "scenario_runs.json"
        if not scenario_path.exists():
            return []
        scenario_runs = read_json(scenario_path)
        return [str(run.get("run_id")) for run in scenario_runs.get("runs", []) if run.get("status") == "failed"]


_QUEUES: dict[Path, FileBackedExecutionQueue] = {}


def get_execution_queue(outputs_root: Path) -> FileBackedExecutionQueue:
    root = outputs_root.resolve()
    if root not in _QUEUES:
        _QUEUES[root] = FileBackedExecutionQueue(root, auto_start=os.environ.get("DECISIONRISK_EXECUTION_AUTO_START", "1") != "0")
    return _QUEUES[root]


def execution_url(execution_id: str) -> str:
    return f"/api/decisionrisk/runs/{execution_id}/status"


def _base_status(case_id: str, execution_id: str, mode: str, directory: Path) -> dict[str, Any]:
    now = _now()
    return {
        "execution_id": execution_id,
        "case_id": case_id,
        "mode": mode,
        "status": "queued",
        "stage": "queued",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "progress_percent": 0.0,
        "cancellation_requested": False,
        "validated": False,
        "published": False,
        "final": False,
        "execution_dir": str(directory),
        "failed_scenarios": [],
    }


def _safe_identifier(value: str, field_name: str) -> str:
    if not value:
        raise ValueError(f"{field_name} is required.")
    safe = "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-"})
    if safe != value:
        raise ValueError(f"Invalid {field_name}.")
    return value


def _new_execution_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ex_{timestamp}_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_seconds(started_at: str, completed_at: str) -> float | None:
    try:
        start = datetime.fromisoformat(started_at)
        completed = datetime.fromisoformat(completed_at)
    except ValueError:
        return None
    return round((completed - start).total_seconds(), 3)
