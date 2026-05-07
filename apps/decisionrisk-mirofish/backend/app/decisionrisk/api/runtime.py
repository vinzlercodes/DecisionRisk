"""Runtime mode and run creation APIs for DecisionRisk."""

from __future__ import annotations

from flask import jsonify, request

from ..runtime_modes import parse_runtime_mode, runtime_mode_contracts
from ..runtime_runner import (
    DecisionRiskRuntimeRunner,
    RuntimeNotImplementedError,
    RuntimePreflightError,
    RuntimeValidationError,
)
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

    runner = DecisionRiskRuntimeRunner(outputs_root())
    try:
        result = runner.run(decision_case, str(mode))
    except RuntimePreflightError as exc:
        return jsonify({"success": False, "error": str(exc), "stage": "preflight"}), 400
    except RuntimeNotImplementedError as exc:
        return jsonify({"success": False, "error": str(exc), "stage": "runtime"}), 501
    except RuntimeValidationError as exc:
        return jsonify({"success": False, "error": str(exc), "validation_errors": exc.errors}), 500
    except RuntimeError as exc:
        return jsonify({"success": False, "error": str(exc), "stage": "runtime"}), 500

    return jsonify({"success": True, "run": result})
