"""Read-only artifact APIs for DecisionRisk replay outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import abort, jsonify, request, Response

from . import decisionrisk_bp


def outputs_root() -> Path:
    configured = os.environ.get("DECISIONRISK_OUTPUTS_DIR")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[6] / "outputs"


def case_dir(case_id: str) -> Path:
    safe_case_id = "".join(ch for ch in case_id if ch.isalnum() or ch in {"_", "-"})
    if safe_case_id != case_id:
        abort(400, description="Invalid case id.")
    root = outputs_root()
    path = (root / case_id).resolve()
    if root not in path.parents and path != root:
        abort(400, description="Invalid case path.")
    return path


def execution_dir(case_id: str, execution_id: str) -> Path:
    safe_execution_id = "".join(ch for ch in execution_id if ch.isalnum() or ch in {"_", "-"})
    if safe_execution_id != execution_id:
        abort(400, description="Invalid execution id.")
    root = case_dir(case_id)
    path = (root / "runs" / execution_id).resolve()
    if root not in path.parents:
        abort(400, description="Invalid execution path.")
    return path


def read_manifest(case_id: str, execution_id: str | None = None) -> dict:
    root = execution_dir(case_id, execution_id) if execution_id else _default_artifact_dir(case_id)
    path = root / "run_manifest.json"
    if not path.exists():
        abort(404, description="DecisionRisk run manifest not found.")
    return json.loads(path.read_text(encoding="utf-8"))


def _default_artifact_dir(case_id: str) -> Path:
    root = case_dir(case_id)
    published = _latest_published_execution_dir(root)
    if published:
        return published
    return root


def _latest_published_execution_dir(root: Path) -> Path | None:
    runs_root = root / "runs"
    if not runs_root.exists():
        return None
    published: list[tuple[str, Path]] = []
    for child in runs_root.iterdir():
        status_path = child / "run_status.json"
        if not status_path.exists():
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") == "published":
            published.append((str(status.get("updated_at", "")), child))
    if not published:
        return None
    return sorted(published, key=lambda item: item[0], reverse=True)[0][1]


@decisionrisk_bp.get("/cases")
def list_cases():
    root = outputs_root()
    cases = []
    if root.exists():
        for child in sorted(root.iterdir()):
            manifest = child / "run_manifest.json"
            if manifest.exists():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                cases.append(
                    {
                        "case_id": data.get("case_id", child.name),
                        "risk_pack": data.get("risk_pack"),
                        "mode": data.get("mode"),
                        "created_at": data.get("created_at"),
                        "execution_id": data.get("execution", {}).get("execution_id"),
                        "status": "legacy",
                    }
                )
            runs_root = child / "runs"
            if runs_root.exists():
                for execution_dir_path in sorted(runs_root.iterdir()):
                    status_path = execution_dir_path / "run_status.json"
                    manifest_path = execution_dir_path / "run_manifest.json"
                    if not status_path.exists() or not manifest_path.exists():
                        continue
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                    if status.get("status") != "published":
                        continue
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    cases.append(
                        {
                            "case_id": data.get("case_id", child.name),
                            "risk_pack": data.get("risk_pack"),
                            "mode": data.get("mode"),
                            "created_at": data.get("created_at"),
                            "execution_id": status.get("execution_id"),
                            "status": status.get("status"),
                        }
                    )
    return jsonify({"success": True, "cases": cases})


@decisionrisk_bp.get("/cases/<case_id>")
def get_case(case_id: str):
    return jsonify({"success": True, "manifest": read_manifest(case_id, request.args.get("execution_id"))})


@decisionrisk_bp.get("/cases/<case_id>/artifacts")
def list_artifacts(case_id: str):
    manifest = read_manifest(case_id, request.args.get("execution_id"))
    return jsonify({"success": True, "artifacts": manifest.get("artifacts", {})})


@decisionrisk_bp.get("/cases/<case_id>/artifacts/<artifact_name>")
def get_artifact(case_id: str, artifact_name: str):
    execution_id = request.args.get("execution_id")
    root = execution_dir(case_id, execution_id) if execution_id else _default_artifact_dir(case_id)
    manifest = read_manifest(case_id, execution_id)
    artifact = manifest.get("artifacts", {}).get(artifact_name)
    if not artifact:
        abort(404, description="Artifact not found.")
    path = (root / artifact["path"]).resolve()
    resolved_root = root.resolve()
    if resolved_root not in path.parents and path != resolved_root:
        abort(400, description="Artifact path escapes case directory.")
    if not path.exists():
        abort(404, description="Artifact file missing.")
    if path.suffix == ".json":
        return jsonify({"success": True, "artifact": json.loads(path.read_text(encoding="utf-8"))})
    return Response(path.read_text(encoding="utf-8"), mimetype="text/plain")


@decisionrisk_bp.get("/cases/<case_id>/risk-docket")
def get_risk_docket(case_id: str):
    execution_id = request.args.get("execution_id")
    root = execution_dir(case_id, execution_id) if execution_id else _default_artifact_dir(case_id)
    manifest = read_manifest(case_id, execution_id)
    artifact = manifest.get("artifacts", {}).get("risk_docket")
    if not artifact:
        abort(404, description="Risk Docket not found.")
    path = root / artifact["path"]
    return Response(path.read_text(encoding="utf-8"), mimetype="text/markdown")
