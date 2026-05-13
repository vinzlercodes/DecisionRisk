from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import collect_claim_refs, load_case, read_json, write_json
from .cli import compare_golden_outputs, validate_output_dir, write_replay_shaped_run
from .report_substrate import OVERCLAIM_PATTERNS
from .runtime_modes import LIVE_ENABLE_ENV
from .safety import assess_case


EVAL_STATUSES = {"pass", "fail", "skip"}
DEFAULT_UI_VIEWER = Path("apps/decisionrisk-mirofish/frontend/src/views/decisionrisk/DecisionRiskCaseViewer.vue")
DEFAULT_BACKEND_ROOT = Path("apps/decisionrisk-mirofish/backend")
BLOCKED_FIXTURE_NAMES = (
    "no_evidence_case",
    "prompt_only_case",
    "disallowed_political_persuasion_case",
    "stock_buy_sell_case",
)
PROMPT_INJECTION_FIXTURE_NAME = "prompt_injection_doc_case"
UNCERTAIN_CLAIM_PATTERNS = OVERCLAIM_PATTERNS


@dataclass(frozen=True)
class EvalCheckResult:
    name: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        if self.status not in EVAL_STATUSES:
            raise ValueError(f"unsupported eval status: {self.status}")
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass(frozen=True)
class EvaluationReport:
    case_id: str
    generated_at: str
    output_dir: str
    golden_dir: str | None
    update_golden: bool
    overall_status: str
    checks: list[EvalCheckResult]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "decisionrisk.evaluation_report.v1",
            "case_id": self.case_id,
            "generated_at": self.generated_at,
            "output_dir": self.output_dir,
            "golden_dir": self.golden_dir,
            "update_golden": self.update_golden,
            "overall_status": self.overall_status,
            "checks": [check.as_dict() for check in self.checks],
        }


def run_evaluation_harness(
    case_path: Path,
    output_dir: Path,
    golden_dir: Path | None,
    scorecard_path: Path | None = None,
    update_golden: bool = False,
    repo_root: Path | None = None,
) -> EvaluationReport:
    repo_root = repo_root or _repo_root_from(case_path)
    case = load_case(case_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_output_dir = write_replay_shaped_run(
        case_path=case_path,
        case=case,
        mode="eval",
        output_dir_arg=str(output_dir),
    )
    scorecard = _load_scorecard(scorecard_path)

    checks = [
        _artifact_contract_eval(run_output_dir),
        _claim_ref_eval(run_output_dir),
        _safety_eval(repo_root),
        _golden_replay_eval(case_path, case, run_output_dir, golden_dir, update_golden),
        _council_quality_eval(run_output_dir),
        _metric_regression_eval(run_output_dir, scorecard),
        _ui_contract_eval(repo_root),
        _live_smoke_eval(case, output_dir, repo_root),
    ]
    overall_status = "fail" if any(check.status == "fail" for check in checks) else "pass"
    report = EvaluationReport(
        case_id=str(case.get("case_id", case_path.stem)),
        generated_at=datetime.now(timezone.utc).isoformat(),
        output_dir=str(output_dir),
        golden_dir=str(golden_dir) if golden_dir else None,
        update_golden=update_golden,
        overall_status=overall_status,
        checks=checks,
    )
    _write_reports(output_dir, report)
    return report


def _artifact_contract_eval(output_dir: Path) -> EvalCheckResult:
    errors = validate_output_dir(output_dir, expected_mode="eval")
    if errors:
        return EvalCheckResult(
            "artifact_contract",
            "fail",
            "Eval artifacts failed manifest validation.",
            errors,
        )
    return EvalCheckResult(
        "artifact_contract",
        "pass",
        "Required artifacts exist, validate, and hash-match.",
        [str(output_dir / "run_manifest.json")],
    )


def _claim_ref_eval(output_dir: Path) -> EvalCheckResult:
    manifest = read_json(output_dir / "run_manifest.json")
    verdict = _artifact_json(output_dir, manifest, "verdict")
    claim_refs = _claim_index(output_dir, manifest)
    errors: list[str] = []
    rationale_refs = verdict.get("primary_rationale_claim_refs", [])
    if not rationale_refs:
        errors.append("verdict.primary_rationale_claim_refs is empty")
    if rationale_refs and not any(
        claim_refs.get(claim_id, {}).get("status") != "unsupported_assumption"
        for claim_id in rationale_refs
    ):
        errors.append("verdict.primary_rationale is supported only by unsupported assumptions")
    for claim_id in rationale_refs:
        if claim_id not in claim_refs:
            errors.append(f"verdict references missing ClaimRef: {claim_id}")
    if errors:
        return EvalCheckResult("claim_ref", "fail", "ClaimRef provenance checks failed.", errors)
    return EvalCheckResult("claim_ref", "pass", "Primary rationale uses existing non-unsupported ClaimRefs.")


def _safety_eval(repo_root: Path) -> EvalCheckResult:
    fixture_root = repo_root / "tests" / "fixtures"
    errors: list[str] = []
    for name in BLOCKED_FIXTURE_NAMES:
        case_path = fixture_root / name / "case.yaml"
        assessment = assess_case(load_case(case_path))
        if assessment.allowed:
            errors.append(f"{name} should be blocked")
    prompt_case = load_case(fixture_root / PROMPT_INJECTION_FIXTURE_NAME / "case.yaml")
    prompt_assessment = assess_case(prompt_case)
    if not prompt_assessment.allowed:
        errors.append("prompt_injection_doc_case should remain allowed as quoted evidence")
    if not prompt_assessment.warnings:
        errors.append("prompt_injection_doc_case should produce a warning")
    if errors:
        return EvalCheckResult("safety", "fail", "Safety fixture checks failed.", errors)
    return EvalCheckResult("safety", "pass", "Blocked fixtures fail and prompt injection stays warned.")


def _golden_replay_eval(
    case_path: Path,
    case: dict[str, Any],
    output_dir: Path,
    golden_dir: Path | None,
    update_golden: bool,
) -> EvalCheckResult:
    if not golden_dir:
        return EvalCheckResult("golden_replay", "skip", "No golden directory was provided.")
    if update_golden:
        write_replay_shaped_run(
            case_path=case_path,
            case=case,
            mode="replay",
            output_dir_arg=str(golden_dir),
        )
        return EvalCheckResult("golden_replay", "pass", f"Golden artifacts refreshed at {golden_dir}.")
    errors = compare_golden_outputs(output_dir, golden_dir)
    if errors:
        return EvalCheckResult("golden_replay", "fail", "Generated artifacts differ from golden outputs.", errors)
    return EvalCheckResult("golden_replay", "pass", "Generated artifacts match golden outputs.")


def _council_quality_eval(output_dir: Path) -> EvalCheckResult:
    manifest = read_json(output_dir / "run_manifest.json")
    council = _artifact_json(output_dir, manifest, "council_rounds")
    verdict = _artifact_json(output_dir, manifest, "verdict")
    errors: list[str] = []
    role_outputs = council.get("role_outputs", [])
    if not role_outputs:
        errors.append("council_rounds.role_outputs is empty")
    for output in role_outputs:
        role_id = output.get("role_id", "unknown")
        if not output.get("claim_refs"):
            errors.append(f"{role_id} has no ClaimRefs")
        if not isinstance(output.get("confidence"), (int, float)):
            errors.append(f"{role_id} has no numeric confidence")
        if not output.get("dissent"):
            errors.append(f"{role_id} has no dissent")
    if not verdict.get("strongest_dissent"):
        errors.append("verdict.strongest_dissent is missing")
    rationale = str(verdict.get("primary_rationale", "")).lower()
    if any(re.search(pattern, rationale) for pattern in UNCERTAIN_CLAIM_PATTERNS):
        errors.append("verdict.primary_rationale uses unsupported certainty language")
    gate = council.get("gate", {})
    if gate.get("result") != "pass":
        errors.append(f"council gate did not pass: {gate.get('result')}")
    if errors:
        return EvalCheckResult("council_quality", "fail", "Council quality checks failed.", errors)
    return EvalCheckResult("council_quality", "pass", "Council preserves dissent, ClaimRefs, confidence, and gate result.")


def _metric_regression_eval(output_dir: Path, scorecard: dict[str, Any]) -> EvalCheckResult:
    manifest = read_json(output_dir / "run_manifest.json")
    metrics = _artifact_json(output_dir, manifest, "simulation_metrics")
    options = metrics.get("options", {})
    regression = scorecard.get("metric_regression", {})
    errors: list[str] = []
    expected_lowest = regression.get("expected_lowest_risk_option")
    if expected_lowest:
        scored = [
            (option_id, values.get("overall_risk_score"))
            for option_id, values in options.items()
            if isinstance(values, dict) and isinstance(values.get("overall_risk_score"), (int, float))
        ]
        if not scored:
            errors.append("simulation_metrics has no numeric overall_risk_score values")
        else:
            actual_lowest = min(scored, key=lambda item: item[1])[0]
            if actual_lowest != expected_lowest:
                errors.append(f"lowest risk option drifted from {expected_lowest} to {actual_lowest}")
    for option_id, band in regression.get("overall_risk_bands", {}).items():
        score = options.get(option_id, {}).get("overall_risk_score")
        if not isinstance(score, (int, float)):
            errors.append(f"{option_id} has no numeric overall_risk_score")
            continue
        minimum = band.get("min")
        maximum = band.get("max")
        if minimum is not None and score < minimum:
            errors.append(f"{option_id} overall_risk_score {score} is below minimum {minimum}")
        if maximum is not None and score > maximum:
            errors.append(f"{option_id} overall_risk_score {score} is above maximum {maximum}")
    for lower, higher in regression.get("risk_order_before", []):
        lower_score = options.get(lower, {}).get("overall_risk_score")
        higher_score = options.get(higher, {}).get("overall_risk_score")
        if not isinstance(lower_score, (int, float)) or not isinstance(higher_score, (int, float)):
            errors.append(f"cannot compare risk order for {lower} and {higher}")
        elif lower_score >= higher_score:
            errors.append(f"expected {lower} risk {lower_score} to stay below {higher} risk {higher_score}")
    if errors:
        return EvalCheckResult("metric_regression", "fail", "Metric regression checks failed.", errors)
    return EvalCheckResult("metric_regression", "pass", "Metric bands and option ranking remain within scorecard expectations.")


def _ui_contract_eval(repo_root: Path) -> EvalCheckResult:
    viewer_path = repo_root / DEFAULT_UI_VIEWER
    if not viewer_path.exists():
        return EvalCheckResult("ui_contract", "fail", "DecisionRisk case viewer file is missing.", [str(viewer_path)])
    text = viewer_path.read_text(encoding="utf-8")
    required_fragments = [
        "Executive Summary",
        "Option Metrics",
        "Scenario Ensemble",
        "Evidence & ClaimRefs",
        "Council Review",
        "Risk Docket",
        "Artifact Audit",
        "finalVerdictLabel",
        "recommended_option_id",
        "manifest?.risk_pack",
        "manifest?.mode",
        "audit?.validation_status",
        "grounding?.grounding_level",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        return EvalCheckResult("ui_contract", "fail", "Viewer is missing required contract fields.", missing)
    return EvalCheckResult("ui_contract", "pass", "Viewer exposes required tabs and summary fields.")


def _live_smoke_eval(case: dict[str, Any], output_dir: Path, repo_root: Path) -> EvalCheckResult:
    if os.environ.get(LIVE_ENABLE_ENV) != "1":
        return EvalCheckResult("live_smoke", "skip", f"{LIVE_ENABLE_ENV}=1 is not set.")
    backend_root = repo_root / DEFAULT_BACKEND_ROOT
    if not backend_root.exists():
        return EvalCheckResult("live_smoke", "fail", "Backend root is missing.", [str(backend_root)])
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    try:
        from app.decisionrisk.runtime_runner import DecisionRiskRuntimeRunner
    except Exception as exc:  # pragma: no cover - depends on optional backend environment.
        return EvalCheckResult("live_smoke", "fail", "Could not import backend live smoke runner.", [str(exc)])
    try:
        live_output_dir = output_dir / "live_smoke"
        result = DecisionRiskRuntimeRunner(output_dir).run(case, "live_smoke", output_dir=live_output_dir)
    except Exception as exc:  # pragma: no cover - depends on optional live environment.
        return EvalCheckResult("live_smoke", "fail", "Live smoke execution failed.", [str(exc)])
    errors = validate_output_dir(Path(result["manifest_path"]).parent, expected_mode="live_smoke")
    if errors:
        return EvalCheckResult("live_smoke", "fail", "Live smoke artifacts failed validation.", errors)
    return EvalCheckResult("live_smoke", "pass", "One small live MiroFish-backed path validated.")


def _write_reports(output_dir: Path, report: EvaluationReport) -> None:
    write_json(output_dir / "evaluation_report.json", report.as_dict())
    (output_dir / "evaluation_report.md").write_text(_report_markdown(report), encoding="utf-8")


def _report_markdown(report: EvaluationReport) -> str:
    lines = [
        f"# DecisionRisk Evaluation Report: {report.case_id}",
        "",
        f"Generated: {report.generated_at}",
        f"Overall status: {report.overall_status}",
        f"Output directory: {report.output_dir}",
        f"Golden directory: {report.golden_dir or 'not provided'}",
        f"Golden update: {'yes' if report.update_golden else 'no'}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.extend(["", f"### {check.name}: {check.status}", "", check.summary])
        for detail in check.details:
            lines.append(f"- {detail}")
    lines.append("")
    return "\n".join(lines)


def _load_scorecard(scorecard_path: Path | None) -> dict[str, Any]:
    if not scorecard_path:
        return {}
    return json.loads(scorecard_path.read_text(encoding="utf-8"))


def _artifact_json(output_dir: Path, manifest: dict[str, Any], artifact_name: str) -> dict[str, Any]:
    ref = manifest["artifacts"][artifact_name]
    return read_json(output_dir / ref["path"])


def _claim_index(output_dir: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for ref in manifest.get("artifacts", {}).values():
        path = output_dir / ref["path"]
        if path.suffix != ".json" or not path.exists():
            continue
        for claim_ref in collect_claim_refs(read_json(path)):
            refs[claim_ref["claim_id"]] = claim_ref
    return refs


def _repo_root_from(case_path: Path) -> Path:
    for parent in [case_path.resolve(), *case_path.resolve().parents]:
        if (parent / "CONTEXT.md").exists() and (parent / "packages").exists():
            return parent
    return Path.cwd()
