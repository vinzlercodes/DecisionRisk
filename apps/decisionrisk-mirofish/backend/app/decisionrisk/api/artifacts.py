"""Read-only artifact APIs for DecisionRisk replay outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import abort, jsonify, Response

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


def read_manifest(case_id: str) -> dict:
    path = case_dir(case_id) / "run_manifest.json"
    if not path.exists():
        abort(404, description="DecisionRisk run manifest not found.")
    return json.loads(path.read_text(encoding="utf-8"))


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
                    }
                )
    return jsonify({"success": True, "cases": cases})


@decisionrisk_bp.get("/cases/<case_id>")
def get_case(case_id: str):
    return jsonify({"success": True, "manifest": read_manifest(case_id)})


@decisionrisk_bp.get("/cases/<case_id>/artifacts")
def list_artifacts(case_id: str):
    manifest = read_manifest(case_id)
    return jsonify({"success": True, "artifacts": manifest.get("artifacts", {})})


@decisionrisk_bp.get("/cases/<case_id>/artifacts/<artifact_name>")
def get_artifact(case_id: str, artifact_name: str):
    manifest = read_manifest(case_id)
    artifact = manifest.get("artifacts", {}).get(artifact_name)
    if not artifact:
        abort(404, description="Artifact not found.")
    path = (case_dir(case_id) / artifact["path"]).resolve()
    root = case_dir(case_id).resolve()
    if root not in path.parents and path != root:
        abort(400, description="Artifact path escapes case directory.")
    if not path.exists():
        abort(404, description="Artifact file missing.")
    if path.suffix == ".json":
        return jsonify({"success": True, "artifact": json.loads(path.read_text(encoding="utf-8"))})
    return Response(path.read_text(encoding="utf-8"), mimetype="text/plain")


@decisionrisk_bp.get("/cases/<case_id>/risk-docket")
def get_risk_docket(case_id: str):
    manifest = read_manifest(case_id)
    artifact = manifest.get("artifacts", {}).get("risk_docket")
    if not artifact:
        abort(404, description="Risk Docket not found.")
    path = case_dir(case_id) / artifact["path"]
    return Response(path.read_text(encoding="utf-8"), mimetype="text/markdown")
