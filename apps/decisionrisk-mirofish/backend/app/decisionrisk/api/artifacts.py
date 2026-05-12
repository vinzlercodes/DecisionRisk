"""Read-only artifact APIs for DecisionRisk outputs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import abort, jsonify, Response, url_for

from decisionrisk.artifacts import sha256_file
from decisionrisk.cli import validate_output_dir

from . import decisionrisk_bp


@dataclass(frozen=True)
class ArtifactContext:
    case_id: str
    directory: Path
    manifest: dict[str, Any]
    source_type: str
    execution_id: str | None = None
    run_status: dict[str, Any] | None = None
    run_error: dict[str, Any] | None = None


def outputs_root() -> Path:
    configured = os.environ.get("DECISIONRISK_OUTPUTS_DIR")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[6] / "outputs"


def case_dir(case_id: str) -> Path:
    safe_case_id = _safe_identifier(case_id)
    if safe_case_id != case_id:
        abort(400, description="Invalid case id.")
    root = outputs_root()
    path = (root / case_id).resolve()
    if root not in path.parents and path != root:
        abort(400, description="Invalid case path.")
    return path


def read_manifest(case_id: str) -> dict[str, Any]:
    return _selected_context(case_id).manifest


@decisionrisk_bp.get("/cases")
def list_cases():
    root = outputs_root()
    cases = []
    if root.exists():
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            context = _selected_context_or_none(child.name)
            if not context:
                continue
            cases.append(_case_summary(child.name, context))
    return jsonify({"success": True, "cases": cases})


@decisionrisk_bp.get("/cases/<case_id>")
def get_case(case_id: str):
    context = _selected_context(case_id)
    return jsonify(_case_payload(context))


@decisionrisk_bp.get("/cases/<case_id>/runs")
def list_case_runs(case_id: str):
    case_path = case_dir(case_id)
    runs = [_run_summary(context) for context in _run_contexts(case_path, case_id)]
    return jsonify({"success": True, "case_id": case_id, "runs": runs})


@decisionrisk_bp.get("/cases/<case_id>/runs/<execution_id>")
def get_case_run(case_id: str, execution_id: str):
    context = _run_context(case_id, execution_id)
    return jsonify(_case_payload(context))


@decisionrisk_bp.get("/cases/<case_id>/artifacts")
def list_artifacts(case_id: str):
    context = _selected_context(case_id)
    return jsonify(_artifact_listing_payload(context))


@decisionrisk_bp.get("/cases/<case_id>/runs/<execution_id>/artifacts")
def list_run_artifacts(case_id: str, execution_id: str):
    context = _run_context(case_id, execution_id)
    return jsonify(_artifact_listing_payload(context))


@decisionrisk_bp.get("/cases/<case_id>/artifacts/<artifact_name>")
def get_artifact(case_id: str, artifact_name: str):
    context = _selected_context(case_id)
    return _artifact_response(context, artifact_name)


@decisionrisk_bp.get("/cases/<case_id>/runs/<execution_id>/artifacts/<artifact_name>")
def get_run_artifact(case_id: str, execution_id: str, artifact_name: str):
    context = _run_context(case_id, execution_id)
    return _artifact_response(context, artifact_name)


@decisionrisk_bp.get("/cases/<case_id>/risk-docket")
def get_risk_docket(case_id: str):
    context = _selected_context(case_id)
    return _artifact_response(context, "risk_docket", mimetype="text/markdown")


@decisionrisk_bp.get("/cases/<case_id>/runs/<execution_id>/risk-docket")
def get_run_risk_docket(case_id: str, execution_id: str):
    context = _run_context(case_id, execution_id)
    return _artifact_response(context, "risk_docket", mimetype="text/markdown")


def _case_payload(context: ArtifactContext) -> dict[str, Any]:
    return {
        "success": True,
        "case_id": context.case_id,
        "execution_id": context.execution_id,
        "source_type": context.source_type,
        "manifest": context.manifest,
        "audit": _audit_summary(context),
        "artifacts": _artifact_metadata(context),
        "runs": [_run_summary(run_context) for run_context in _run_contexts(case_dir(context.case_id), context.case_id)],
    }


def _case_summary(case_id: str, context: ArtifactContext) -> dict[str, Any]:
    audit = _audit_summary(context)
    return {
        "case_id": context.manifest.get("case_id", case_id),
        "risk_pack": context.manifest.get("risk_pack"),
        "mode": context.manifest.get("mode"),
        "created_at": context.manifest.get("created_at"),
        "source_type": context.source_type,
        "execution_id": context.execution_id,
        "validation_status": audit["validation_status"],
        "final": audit["final"],
        "run_count": len(_run_contexts(case_dir(case_id), case_id)),
    }


def _artifact_listing_payload(context: ArtifactContext) -> dict[str, Any]:
    return {
        "success": True,
        "case_id": context.case_id,
        "execution_id": context.execution_id,
        "source_type": context.source_type,
        "artifacts": _artifact_metadata(context),
        "audit": _audit_summary(context),
    }


def _selected_context(case_id: str) -> ArtifactContext:
    context = _selected_context_or_none(case_id)
    if not context:
        abort(404, description="DecisionRisk run manifest not found.")
    return context


def _selected_context_or_none(case_id: str) -> ArtifactContext | None:
    case_path = case_dir(case_id)
    runs = _run_contexts(case_path, case_id)
    if runs:
        return runs[0]
    return _flat_context(case_path, case_id)


def _flat_context(case_path: Path, case_id: str) -> ArtifactContext | None:
    manifest_path = case_path / "run_manifest.json"
    if not manifest_path.exists():
        return None
    return ArtifactContext(
        case_id=case_id,
        directory=case_path,
        manifest=_read_json(manifest_path),
        source_type="flat",
    )


def _run_context(case_id: str, execution_id: str) -> ArtifactContext:
    execution_id = _safe_identifier(execution_id)
    case_path = case_dir(case_id)
    run_path = (case_path / "runs" / execution_id).resolve()
    runs_root = (case_path / "runs").resolve()
    if runs_root not in run_path.parents and run_path != runs_root:
        abort(400, description="Invalid run path.")
    manifest_path = run_path / "run_manifest.json"
    if not manifest_path.exists():
        abort(404, description="DecisionRisk run manifest not found.")
    return _context_from_run_dir(case_id, run_path)


def _run_contexts(case_path: Path, case_id: str) -> list[ArtifactContext]:
    runs_root = case_path / "runs"
    if not runs_root.exists():
        return []
    contexts = []
    for run_path in runs_root.iterdir():
        if not run_path.is_dir() or not (run_path / "run_manifest.json").exists():
            continue
        contexts.append(_context_from_run_dir(case_id, run_path))
    return sorted(contexts, key=_context_sort_key, reverse=True)


def _context_from_run_dir(case_id: str, run_path: Path) -> ArtifactContext:
    status_path = run_path / "run_status.json"
    error_path = run_path / "run_error.json"
    manifest = _read_json(run_path / "run_manifest.json")
    run_status = _read_json(status_path) if status_path.exists() else None
    execution_id = (
        str(run_status.get("execution_id"))
        if run_status and run_status.get("execution_id")
        else str(manifest.get("execution", {}).get("execution_id") or run_path.name)
    )
    return ArtifactContext(
        case_id=case_id,
        directory=run_path,
        manifest=manifest,
        source_type="run",
        execution_id=execution_id,
        run_status=run_status,
        run_error=_read_json(error_path) if error_path.exists() else None,
    )


def _run_summary(context: ArtifactContext) -> dict[str, Any]:
    audit = _audit_summary(context)
    return {
        "case_id": context.case_id,
        "execution_id": context.execution_id,
        "mode": context.manifest.get("mode"),
        "risk_pack": context.manifest.get("risk_pack"),
        "created_at": _run_created_at(context),
        "updated_at": context.run_status.get("updated_at") if context.run_status else None,
        "status": audit["validation_status"],
        "stage": context.run_status.get("stage") if context.run_status else None,
        "validated": audit["validated"],
        "published": context.run_status.get("published", False) if context.run_status else False,
        "final": audit["final"],
    }


def _audit_summary(context: ArtifactContext) -> dict[str, Any]:
    if context.run_status:
        status = str(context.run_status.get("status", "unknown"))
        validation_errors = []
        if context.run_error:
            details = context.run_error.get("details", {})
            validation_errors = details.get("validation_errors") or []
        return {
            "source": "run_status",
            "validation_status": status,
            "validation_result": "pass" if context.run_status.get("validated") else "non_final",
            "validated": bool(context.run_status.get("validated")),
            "final": bool(context.run_status.get("final")),
            "published": bool(context.run_status.get("published")),
            "stage": context.run_status.get("stage"),
            "errors": validation_errors,
            "run_error": context.run_error,
        }

    errors = validate_output_dir(context.directory)
    return {
        "source": "validate_output_dir",
        "validation_status": "validated" if not errors else "invalid",
        "validation_result": "pass" if not errors else "fail",
        "validated": not errors,
        "final": not errors,
        "published": False,
        "stage": "manifest_validated" if not errors else "validation_failed",
        "errors": errors,
        "run_error": None,
    }


def _artifact_metadata(context: ArtifactContext) -> dict[str, dict[str, Any]]:
    metadata = {}
    for section in ("inputs", "artifacts", "operations"):
        entries = context.manifest.get(section, {})
        if not isinstance(entries, dict):
            continue
        for name, ref in entries.items():
            if not isinstance(ref, dict) or "path" not in ref:
                continue
            metadata[name] = _artifact_ref_metadata(context, section, name, ref)
    return metadata


def _artifact_ref_metadata(
    context: ArtifactContext,
    section: str,
    name: str,
    ref: dict[str, str],
) -> dict[str, Any]:
    path = _resolve_ref_path(context, ref)
    expected_sha = ref.get("sha256")
    exists = path.exists()
    actual_sha = sha256_file(path) if exists else None
    return {
        "section": section,
        "path": ref["path"],
        "sha256": expected_sha,
        "actual_sha256": actual_sha,
        "hash_matches": bool(exists and expected_sha and actual_sha == expected_sha),
        "exists": exists,
        "content_type": _content_type(path),
        "raw_url": _raw_artifact_url(context, name),
    }


def _artifact_response(context: ArtifactContext, artifact_name: str, mimetype: str | None = None):
    section, artifact = _manifest_ref(context, artifact_name)
    if not artifact:
        abort(404, description="Artifact not found.")
    path = _resolve_ref_path(context, artifact)
    if not path.exists():
        abort(404, description="Artifact file missing.")
    if path.suffix == ".json":
        return jsonify({"success": True, "artifact": _read_json(path), "metadata": _artifact_ref_metadata(context, section, artifact_name, artifact)})
    return Response(path.read_text(encoding="utf-8"), mimetype=mimetype or "text/plain")


def _manifest_ref(context: ArtifactContext, artifact_name: str) -> tuple[str, dict[str, str] | None]:
    for section in ("artifacts", "inputs", "operations"):
        ref = context.manifest.get(section, {}).get(artifact_name)
        if isinstance(ref, dict):
            return section, ref
    return "artifacts", None


def _resolve_ref_path(context: ArtifactContext, ref: dict[str, str]) -> Path:
    path = (context.directory / ref["path"]).resolve()
    root = context.directory.resolve()
    if root not in path.parents and path != root:
        abort(400, description="Artifact path escapes case directory.")
    return path


def _raw_artifact_url(context: ArtifactContext, artifact_name: str) -> str:
    if context.execution_id:
        return url_for(
            "decisionrisk.get_run_artifact",
            case_id=context.case_id,
            execution_id=context.execution_id,
            artifact_name=artifact_name,
        )
    return url_for("decisionrisk.get_artifact", case_id=context.case_id, artifact_name=artifact_name)


def _content_type(path: Path) -> str:
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".md":
        return "text/markdown"
    return "text/plain"


def _context_sort_key(context: ArtifactContext) -> tuple[str, str]:
    return (_run_created_at(context), context.execution_id or "")


def _run_created_at(context: ArtifactContext) -> str:
    if context.run_status and context.run_status.get("created_at"):
        return str(context.run_status["created_at"])
    return str(context.manifest.get("created_at", ""))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_identifier(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-"})
    if safe != value:
        abort(400, description="Invalid identifier.")
    return value
