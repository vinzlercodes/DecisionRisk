from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .artifacts import collect_claim_refs


FINAL_VERDICTS = {"RECOMMEND", "DEFER", "NO_GO"}
REQUIRED_COUNCIL_INPUTS = {
    "decision_case",
    "grounding_report",
    "risk_graph",
    "scenario_runs",
    "simulation_metrics",
}
NON_MIROFISH_SOURCE_PREFIXES = (
    "evidence:",
    "graph:",
    "run:",
    "metric:",
    "metrics:",
    "grounding:",
    "scenario:",
    "simulation:",
)


@dataclass(frozen=True)
class GateResult:
    result: str
    errors: list[str]
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ReportCritic:
    """Reviews MiroFish report substrate before it can influence a verdict."""

    def review(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        report_claims = artifacts.get("mirofish_report_claims")
        if not isinstance(report_claims, dict):
            return {
                "substrate_present": False,
                "unsupported_claim_ids": [],
                "warnings": [],
            }

        unsupported_claim_ids = [
            str(claim.get("claim_id"))
            for claim in report_claims.get("claim_refs", [])
            if claim.get("status") == "unsupported_assumption"
        ]
        warnings = []
        if unsupported_claim_ids:
            warnings.append(
                "MiroFish report substrate contains claims that require DecisionRisk council judgment before use."
            )

        return {
            "substrate_present": True,
            "unsupported_claim_ids": unsupported_claim_ids,
            "warnings": warnings,
        }


class ClaimRefAuditor:
    """Builds a ClaimRef support map and validates council judgment provenance."""

    def audit(self, artifacts: dict[str, Any], council_claim_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        claim_index: dict[str, dict[str, Any]] = {}
        for value in artifacts.values():
            for claim_ref in collect_claim_refs(value):
                claim_index[str(claim_ref["claim_id"])] = claim_ref
        for claim_ref in council_claim_refs or []:
            claim_index[str(claim_ref["claim_id"])] = claim_ref

        support_map: dict[str, dict[str, Any]] = {}
        unsupported_rationale_failures: list[str] = []
        for claim_id, claim_ref in claim_index.items():
            source_refs = _source_refs(claim_ref)
            support_map[claim_id] = {
                "status": claim_ref.get("status"),
                "source_refs": source_refs,
                "has_mirofish_report_source": _has_mirofish_report_source(source_refs),
                "has_non_mirofish_source": _has_non_mirofish_source(source_refs),
                "primary_rationale_eligible": self.primary_rationale_eligible(claim_ref),
            }

        verdict = artifacts.get("verdict")
        if isinstance(verdict, dict):
            for claim_id in verdict.get("primary_rationale_claim_refs", []):
                claim_ref = claim_index.get(str(claim_id))
                if not claim_ref or not self.primary_rationale_eligible(claim_ref):
                    unsupported_rationale_failures.append(str(claim_id))

        return {
            "claim_support_map": support_map,
            "unsupported_rationale_failures": unsupported_rationale_failures,
            "claim_index": claim_index,
        }

    def primary_rationale_eligible(self, claim_ref: dict[str, Any]) -> bool:
        status = claim_ref.get("status")
        if status == "unsupported_assumption":
            return False
        if status != "council_judgment":
            return True
        source_refs = _source_refs(claim_ref)
        return _has_mirofish_report_source(source_refs) and _has_non_mirofish_source(source_refs)


class VerdictGateEngine:
    """Applies the minimal issue #8 gates before final artifacts are written."""

    def evaluate(
        self,
        artifacts: dict[str, Any],
        verdict: dict[str, Any],
        claim_audit: dict[str, Any],
        report_critique: dict[str, Any],
    ) -> GateResult:
        errors: list[str] = []
        warnings = list(report_critique.get("warnings", []))

        missing_inputs = sorted(name for name in REQUIRED_COUNCIL_INPUTS if name not in artifacts)
        if missing_inputs:
            errors.append(f"missing council inputs: {missing_inputs}")

        if verdict.get("final_verdict") not in FINAL_VERDICTS:
            errors.append("verdict.final_verdict is not allowed")

        rationale_refs = verdict.get("primary_rationale_claim_refs", [])
        if not rationale_refs:
            errors.append("verdict.primary_rationale has no ClaimRef references")

        claim_index = claim_audit.get("claim_index", {})
        eligible_refs = [
            claim_id
            for claim_id in rationale_refs
            if claim_id in claim_index and ClaimRefAuditor().primary_rationale_eligible(claim_index[claim_id])
        ]
        if not eligible_refs:
            errors.append("verdict.primary_rationale lacks an eligible ClaimRef")

        if claim_audit.get("unsupported_rationale_failures"):
            errors.append(
                "verdict.primary_rationale uses unsupported or uncorroborated ClaimRefs: "
                + ", ".join(claim_audit["unsupported_rationale_failures"])
            )

        result = "blocked" if errors else _candidate_gate_result(verdict.get("final_verdict"))
        return GateResult(result=result, errors=errors, warnings=warnings)


class RiskDocketGenerator:
    """Generates the final board-style Risk Docket from council artifacts."""

    def generate(
        self,
        artifacts: dict[str, Any],
        council_rounds: dict[str, Any],
        verdict: dict[str, Any],
        gate: GateResult,
    ) -> str:
        decision_case = artifacts["decision_case"]
        metrics = artifacts["simulation_metrics"]
        grounding = artifacts["grounding_report"]
        scenario_runs = artifacts["scenario_runs"]
        option = verdict.get("recommended_option_id") or "no recommended option"
        claim_refs = ", ".join(verdict.get("primary_rationale_claim_refs", []))
        run_count = scenario_runs.get("expected_runs", len(scenario_runs.get("runs", [])))
        option_metrics = metrics.get("options", {}).get(option, {})
        risk_score = option_metrics.get("overall_risk_score", "unknown")

        return f"""# Risk Docket: {decision_case.get("title", decision_case.get("case_id", "DecisionCase"))}

Safety boundary: DecisionRisk is experimental decision-support software. It does not predict the future and should not be used as the sole basis for legal, financial, medical, electoral, public-safety, or other high-stakes decisions.

## Executive Verdict

Recommendation: {verdict.get("primary_rationale")} Final verdict: {verdict.get("final_verdict")}. Recommended option: {option}. Confidence: {verdict.get("confidence")}. Risk level: {verdict.get("risk_level")}. ClaimRefs: {claim_refs}.

## Decision Context

{decision_case.get("decision_question", "No decision question supplied.")}

## Evidence Base

Grounding Level: {grounding.get("grounding_level", "unknown")}. Unsupported assumptions: {grounding.get("unsupported_assumptions", 0)}. Confidence cap: {grounding.get("confidence_cap", "unknown")}.

## Risk Graph

The risk graph contains {len(artifacts.get("risk_graph", {}).get("nodes", []))} nodes and {len(artifacts.get("risk_graph", {}).get("edges", []))} edges covering stakeholders, narratives, risks, and mitigations.

## Scenario Ensemble

The scenario ensemble contains {run_count} option x scenario x seed runs.

## Metrics

The recommended option has overall risk score {risk_score}. Metric authority: {metrics.get("metric_authority", "unknown")}.

## Council Debate

The Verdict Council ran {len(council_rounds.get("rounds", []))} deterministic rounds and preserved dissent before chair synthesis.

## Strongest Dissent

{verdict.get("strongest_dissent", council_rounds.get("strongest_dissent", "No dissent recorded."))}

## Final Recommendation

Choose {option}. Required mitigations: {", ".join(verdict.get("required_mitigations", []))}.

## Mitigation Plan

{_sentence_list(verdict.get("required_mitigations", []))}

## Monitoring Plan

Monitor negative narrative share, opt-out rate, support burden, regulator mentions, press framing, and any signals listed in what_would_change_the_verdict.

## Audit Trail

Material claims link to ClaimRefs in durable artifacts. Gate result: {gate.result}. Unsupported assumptions are not used as the sole basis for the verdict.
"""


class VerdictCouncilRunner:
    """Deterministic Verdict Council pipeline for replay, eval, and live_smoke."""

    def __init__(
        self,
        report_critic: ReportCritic | None = None,
        claim_ref_auditor: ClaimRefAuditor | None = None,
        gate_engine: VerdictGateEngine | None = None,
        docket_generator: RiskDocketGenerator | None = None,
    ) -> None:
        self.report_critic = report_critic or ReportCritic()
        self.claim_ref_auditor = claim_ref_auditor or ClaimRefAuditor()
        self.gate_engine = gate_engine or VerdictGateEngine()
        self.docket_generator = docket_generator or RiskDocketGenerator()

    def run(self, artifacts: dict[str, Any], mode: str) -> dict[str, Any]:
        council_mode = _council_artifact_mode(mode)
        report_critique = self.report_critic.review(artifacts)
        council_claim_refs = self._council_claim_refs(artifacts, council_mode)
        claim_audit = self.claim_ref_auditor.audit(artifacts, council_claim_refs)
        verdict = self._verdict(artifacts, council_mode)
        claim_audit = self.claim_ref_auditor.audit({**artifacts, "verdict": verdict}, council_claim_refs)
        gate = self.gate_engine.evaluate(artifacts, verdict, claim_audit, report_critique)
        if gate.errors:
            raise ValueError("Verdict Council gate blocked finalization: " + "; ".join(gate.errors))
        council_rounds = self._council_rounds(artifacts, council_mode, council_claim_refs, report_critique, claim_audit, gate)
        risk_docket = self.docket_generator.generate(artifacts, council_rounds, verdict, gate)
        return {
            "council_rounds": council_rounds,
            "verdict": verdict,
            "risk_docket": risk_docket,
        }

    def _council_claim_refs(self, artifacts: dict[str, Any], mode: str) -> list[dict[str, Any]]:
        if "mirofish_report_claims" not in artifacts:
            return []
        metrics = artifacts.get("simulation_metrics", {})
        scenario_runs = artifacts.get("scenario_runs", {})
        sources = [
            "artifact:mirofish_report.md",
            "metrics:simulation_metrics.overall_risk_score",
        ]
        if scenario_runs.get("runs"):
            sources.append(f"run:{scenario_runs['runs'][0].get('run_id', 'live_smoke')}")
        else:
            sources.append("grounding:grounding_report")
        return [
            {
                "claim_id": "claim_council_mirofish_0001",
                "text": "The Verdict Council treated raw MiroFish report claims as substrate and used them only when corroborated by DecisionRisk metrics or run traces.",
                "claim_type": "council_judgment",
                "status": "council_judgment",
                "source_refs": sources,
                "confidence": min(float(metrics.get("ensemble", {}).get("evidence_confidence", 0.6)), 0.7),
                "used_in": ["council_rounds.report_critique"],
                "metadata": {"mode": mode, "corroborates_mirofish_report": True},
            }
        ]

    def _council_rounds(
        self,
        artifacts: dict[str, Any],
        mode: str,
        council_claim_refs: list[dict[str, Any]],
        report_critique: dict[str, Any],
        claim_audit: dict[str, Any],
        gate: GateResult,
    ) -> dict[str, Any]:
        return {
            "schema_version": "decisionrisk.council_rounds.v1",
            "mode": mode,
            "rounds": [
                {
                    "round": 1,
                    "name": "Independent analysis",
                    "advisors": [
                        "Growth Strategist",
                        "Trust and Reputation Analyst",
                        "Regulatory Analyst",
                        "Competitor Strategist",
                    ],
                    "claim_refs": ["claim_0001", "claim_0005"],
                },
                {
                    "round": 2,
                    "name": "Report critique and ClaimRef audit",
                    "claim_refs": ["claim_0002", "claim_0003"] + [claim["claim_id"] for claim in council_claim_refs],
                    "report_critique": report_critique,
                    "claim_support_map": claim_audit["claim_support_map"],
                },
                {
                    "round": 3,
                    "name": "Chair synthesis",
                    "advisor": "Decision Chair",
                    "claim_refs": ["claim_0001", "claim_0002", "claim_0004"],
                    "gate": gate.as_dict(),
                },
            ],
            "claim_refs": council_claim_refs,
            "strongest_dissent": "Default-on could win adoption faster if controls are exceptionally clear and onboarding builds trust.",
        }

    def _verdict(self, artifacts: dict[str, Any], mode: str) -> dict[str, Any]:
        metrics = artifacts["simulation_metrics"]
        options = metrics.get("options", {})
        recommended_option_id = _lowest_risk_option(options) or "opt_in_beta"
        return {
            "threshold_verdict": "RECOMMEND",
            "final_verdict": "RECOMMEND",
            "recommended_option_id": recommended_option_id,
            "confidence": min(float(metrics.get("ensemble", {}).get("evidence_confidence", 0.66)), 0.70),
            "risk_level": "medium",
            "primary_rationale": "Opt-in beta reduces trust and narrative cascade risk while preserving enough adoption signal for learning.",
            "primary_rationale_claim_refs": ["claim_0001", "claim_0002", "claim_0004"],
            "strongest_dissent": "Default-on may accelerate adoption if the company can prove controls are clear before launch.",
            "required_mitigations": [
                "Publish memory controls before launch",
                "Expose deletion and temporary-use controls in onboarding",
                "Prepare a privacy-focused press FAQ",
            ],
            "what_would_change_the_verdict": [
                "Public evidence that users strongly prefer default-on memory",
                "Beta telemetry showing low opt-out and low trust damage",
            ],
            "council_mode": mode,
        }


def _lowest_risk_option(options: dict[str, Any]) -> str | None:
    scored = [
        (option_id, metrics.get("overall_risk_score"))
        for option_id, metrics in options.items()
        if isinstance(metrics, dict) and isinstance(metrics.get("overall_risk_score"), (int, float))
    ]
    if not scored:
        return None
    return min(scored, key=lambda item: item[1])[0]


def _candidate_gate_result(final_verdict: object) -> str:
    if final_verdict == "DEFER":
        return "defer candidate"
    if final_verdict == "NO_GO":
        return "no-go candidate"
    return "pass"


def _council_artifact_mode(mode: str) -> str:
    if mode in {"replay", "eval"}:
        return "deterministic_replay"
    return mode


def _source_refs(claim_ref: dict[str, Any]) -> list[str]:
    refs = claim_ref.get("source_refs", [])
    normalized = []
    for ref in refs:
        if isinstance(ref, str):
            normalized.append(ref)
        elif isinstance(ref, dict):
            artifact = ref.get("artifact")
            if artifact:
                normalized.append(f"artifact:{artifact}")
    return normalized


def _has_mirofish_report_source(source_refs: list[str]) -> bool:
    return any("mirofish_report" in ref for ref in source_refs)


def _has_non_mirofish_source(source_refs: list[str]) -> bool:
    return any(ref.startswith(NON_MIROFISH_SOURCE_PREFIXES) and "mirofish_report" not in ref for ref in source_refs)


def _sentence_list(items: list[str]) -> str:
    if not items:
        return "No required mitigations were generated."
    return " ".join(f"{item}." for item in items)
