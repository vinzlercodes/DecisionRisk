"""Runtime mode and run creation APIs for DecisionRisk."""

from __future__ import annotations

from flask import jsonify, request

from ..execution_orchestrator import execution_url, get_execution_queue
from ..runtime_modes import parse_runtime_mode, runtime_mode_contracts
from . import decisionrisk_bp
from .artifacts import outputs_root


@decisionrisk_bp.get("/runtime-modes")
def get_runtime_modes():
    return jsonify({"success": True, "modes": runtime_mode_contracts()})


@decisionrisk_bp.post("/runs")
def create_run():
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "replay")
    decision_case = payload.get("decision_case")
    if not isinstance(decision_case, dict):
        return jsonify({"success": False, "error": "decision_case must be an object."}), 400
    try:
        parse_runtime_mode(str(mode))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    try:
        execution = get_execution_queue(outputs_root()).enqueue(
            decision_case,
            str(mode),
            execution_id=payload.get("execution_id"),
            overwrite=bool(payload.get("overwrite", False)),
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify(
        {
            "success": True,
            "execution_id": execution["execution_id"],
            "case_id": execution["case_id"],
            "mode": execution["mode"],
            "status": execution["status"],
            "stage": execution["stage"],
            "status_url": execution_url(execution["execution_id"]),
            "execution": execution,
        }
    )


@decisionrisk_bp.get("/runs/<execution_id>/status")
def get_execution_status(execution_id: str):
    try:
        status = get_execution_queue(outputs_root()).status(execution_id)
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    return jsonify({"success": True, "execution": status})


@decisionrisk_bp.get("/runs/<execution_id>/events")
def get_execution_events(execution_id: str):
    try:
        events = get_execution_queue(outputs_root()).events(execution_id)
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    return jsonify({"success": True, "events": events})


@decisionrisk_bp.post("/runs/<execution_id>/cancel")
def cancel_execution(execution_id: str):
    try:
        status = get_execution_queue(outputs_root()).cancel(execution_id)
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    return jsonify({"success": True, "execution": status})


@decisionrisk_bp.post("/runs/<execution_id>/resume")
def resume_execution(execution_id: str):
    try:
        status = get_execution_queue(outputs_root()).resume(execution_id)
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    return jsonify({"success": True, "execution": status})


@decisionrisk_bp.post("/runs/<execution_id>/publish")
def publish_execution(execution_id: str):
    try:
        status = get_execution_queue(outputs_root()).publish(execution_id)
    except FileNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "execution": status})


@decisionrisk_bp.post("/runs/<execution_id>/scenario-runs/<scenario_run_id>/retry")
def retry_scenario_run(execution_id: str, scenario_run_id: str):
    try:
        status = get_execution_queue(outputs_root()).retry_scenario_run(execution_id, scenario_run_id)
    except FileNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "execution": status})


@decisionrisk_bp.post("/runs/<execution_id>/scenario-runs/retry-failed")
def retry_failed_scenario_runs(execution_id: str):
    try:
        status = get_execution_queue(outputs_root()).retry_failed_scenario_runs(execution_id)
    except FileNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "execution": status})
