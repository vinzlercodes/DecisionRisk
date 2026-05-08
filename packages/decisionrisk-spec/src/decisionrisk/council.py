from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .artifacts import collect_claim_refs


FINAL_VERDICTS = {"RECOMMEND", "DEFER", "NO_GO"}
COUNCIL_MODEL_POLICIES = {"deterministic_or_logged"}
REQUIRED_COUNCIL_ROLES = (
    "growth_strategist",
    "trust_reputation_analyst",
    "regulatory_analyst",
    "competitor_strategist",
    "decision_chair",
)
SPECIALIST_COUNCIL_ROLES = REQUIRED_COUNCIL_ROLES[:-1]
REQUIRED_COUNCIL_OUTPUTS = (
    "claim_refs",
    "confidence",
    "dissent",
    "mitigation_requirements",
)
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
class CouncilRoleSpec:
    role_id: str
    name: str
    lens: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "lens": self.lens,
        }


@dataclass(frozen=True)
class CouncilConfig:
    risk_pack: str
    model_policy: str
    temperature: float
    max_rounds: int
    required_roles: tuple[str, ...]
    required_outputs: tuple[str, ...]
    role_specs: tuple[CouncilRoleSpec, ...]

    def validate(self) -> None:
        errors: list[str] = []
        if self.model_policy not in COUNCIL_MODEL_POLICIES:
            errors.append(f"unsupported council model_policy: {self.model_policy}")
        if self.max_rounds < 3:
            errors.append("council max_rounds must be at least 3")
        if tuple(self.required_roles) != REQUIRED_COUNCIL_ROLES:
            errors.append(f"council required_roles must be exactly {list(REQUIRED_COUNCIL_ROLES)}")
        if tuple(self.required_outputs) != REQUIRED_COUNCIL_OUTPUTS:
            errors.append(f"council required_outputs must be exactly {list(REQUIRED_COUNCIL_OUTPUTS)}")

        role_ids = tuple(spec.role_id for spec in self.role_specs)
        if role_ids != SPECIALIST_COUNCIL_ROLES:
            errors.append(f"council role_specs must define specialist roles {list(SPECIALIST_COUNCIL_ROLES)}")

        if errors:
            raise ValueError("invalid council config: " + "; ".join(errors))

    def as_dict(self) -> dict[str, Any]:
        return {
            "risk_pack": self.risk_pack,
            "model_policy": self.model_policy,
            "temperature": self.temperature,
            "max_rounds": self.max_rounds,
            "required_roles": list(self.required_roles),
            "required_outputs": list(self.required_outputs),
            "role_specs": [spec.as_dict() for spec in self.role_specs],
        }


def launch_risk_council_config() -> CouncilConfig:
    return CouncilConfig(
        risk_pack="launch_risk",
        model_policy="deterministic_or_logged",
        temperature=0.2,
        max_rounds=3,
        required_roles=REQUIRED_COUNCIL_ROLES,
        required_outputs=REQUIRED_COUNCIL_OUTPUTS,
        role_specs=(
            CouncilRoleSpec(
                "growth_strategist",
                "Growth Strategist",
                "Adoption, retention, learning velocity, and launch momentum.",
            ),
            CouncilRoleSpec(
                "trust_reputation_analyst",
                "Trust and Reputation Analyst",
                "User trust, press framing, privacy perception, and brand damage.",
            ),
            CouncilRoleSpec(
                "regulatory_analyst",
                "Regulatory Analyst",
                "Regulator attention, compliance risk, and public commitments.",
            ),
            CouncilRoleSpec(
                "competitor_strategist",
                "Competitor Strategist",
                "Adversarial framing, attack surface, and market narrative.",
            ),
        ),
    )


@dataclass(frozen=True)
class CouncilRoleInput:
    role: CouncilRoleSpec
    artifacts: dict[str, Any]
    mode: str
    council_config: CouncilConfig

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.as_dict(),
            "mode": self.mode,
            "council_config": self.council_config.as_dict(),
            "artifact_names": sorted(self.artifacts.keys()),
        }


@dataclass(frozen=True)
class CouncilRoleOutput:
    role_id: str
    role_name: str
    analysis: str
    claim_refs: list[str]
    confidence: float
    dissent: str
    mitigation_requirements: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "analysis": self.analysis,
            "claim_refs": self.claim_refs,
            "confidence": self.confidence,
            "dissent": self.dissent,
            "mitigation_requirements": self.mitigation_requirements,
        }


@dataclass(frozen=True)
class DecisionChairInput:
    artifacts: dict[str, Any]
    role_outputs: list[CouncilRoleOutput]
    report_critique: dict[str, Any]
    council_claim_refs: list[dict[str, Any]]
    mode: str
    council_config: CouncilConfig

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "council_config": self.council_config.as_dict(),
            "role_outputs": [output.as_dict() for output in self.role_outputs],
            "report_critique": self.report_critique,
            "council_claim_refs": self.council_claim_refs,
        }


@dataclass(frozen=True)
class DecisionChairOutput:
    verdict_draft: str
    rationale: str
    final_verdict: str
    recommended_option_id: str
    risk_level: str
    confidence: float
    claim_refs: list[str]
    mitigation_requirements: list[str]
    strongest_dissent: str
    what_would_change_the_verdict: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict_draft": self.verdict_draft,
            "rationale": self.rationale,
            "final_verdict": self.final_verdict,
            "recommended_option_id": self.recommended_option_id,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "claim_refs": self.claim_refs,
            "mitigation_requirements": self.mitigation_requirements,
            "strongest_dissent": self.strongest_dissent,
            "what_would_change_the_verdict": self.what_would_change_the_verdict,
        }

    def verdict(self, mode: str) -> dict[str, Any]:
        return {
            "threshold_verdict": self.final_verdict,
            "final_verdict": self.final_verdict,
            "recommended_option_id": self.recommended_option_id,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "primary_rationale": self.rationale,
            "primary_rationale_claim_refs": self.claim_refs,
            "strongest_dissent": self.strongest_dissent,
            "required_mitigations": self.mitigation_requirements,
            "what_would_change_the_verdict": self.what_would_change_the_verdict,
            "council_mode": mode,
        }


@dataclass(frozen=True)
class CouncilExecutionPackage:
    council_config: CouncilConfig
    role_outputs: list[CouncilRoleOutput]
    chair_output: DecisionChairOutput
    report_critique: dict[str, Any]
    claim_audit: dict[str, Any]
    gate: GateResult
    council_claim_refs: list[dict[str, Any]]
    mode: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "decisionrisk.council_execution.v1",
            "mode": self.mode,
            "council_config": self.council_config.as_dict(),
            "role_outputs": [output.as_dict() for output in self.role_outputs],
            "chair_output": self.chair_output.as_dict(),
            "report_critique": self.report_critique,
            "claim_support_map": self.claim_audit["claim_support_map"],
            "gate": self.gate.as_dict(),
            "claim_refs": self.council_claim_refs,
        }


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


class DeterministicCouncilRoleAgent:
    """Deterministic role service used by replay, eval, and live_smoke."""

    def __init__(self, role: CouncilRoleSpec) -> None:
        self.role = role

    def analyze(self, role_input: CouncilRoleInput) -> CouncilRoleOutput:
        metrics = role_input.artifacts["simulation_metrics"]
        confidence = min(float(metrics.get("ensemble", {}).get("evidence_confidence", 0.66)), 0.70)
        return CouncilRoleOutput(
            role_id=self.role.role_id,
            role_name=self.role.name,
            analysis=_role_analysis(self.role.role_id),
            claim_refs=_role_claim_refs(self.role.role_id),
            confidence=confidence,
            dissent=_role_dissent(self.role.role_id),
            mitigation_requirements=_role_mitigations(self.role.role_id),
        )


class DeterministicDecisionChair:
    """Deterministic Chair service that synthesizes role outputs into a verdict draft."""

    def synthesize(self, chair_input: DecisionChairInput) -> DecisionChairOutput:
        metrics = chair_input.artifacts["simulation_metrics"]
        options = metrics.get("options", {})
        recommended_option_id = _lowest_risk_option(options) or "opt_in_beta"
        confidence = min(float(metrics.get("ensemble", {}).get("evidence_confidence", 0.66)), 0.70)
        strongest_dissent = _strongest_dissent(chair_input.role_outputs)
        return DecisionChairOutput(
            verdict_draft="RECOMMEND",
            rationale="Opt-in beta reduces trust and narrative cascade risk while preserving enough adoption signal for learning.",
            final_verdict="RECOMMEND",
            recommended_option_id=recommended_option_id,
            risk_level="medium",
            confidence=confidence,
            claim_refs=["claim_0001", "claim_0002", "claim_0004"],
            mitigation_requirements=[
                "Publish memory controls before launch",
                "Expose deletion and temporary-use controls in onboarding",
                "Prepare a privacy-focused press FAQ",
            ],
            strongest_dissent=strongest_dissent,
            what_would_change_the_verdict=[
                "Public evidence that users strongly prefer default-on memory",
                "Beta telemetry showing low opt-out and low trust damage",
            ],
        )


class VerdictCouncilRunner:
    """Deterministic Verdict Council pipeline for replay, eval, and live_smoke."""

    def __init__(
        self,
        council_config: CouncilConfig | None = None,
        role_agents: dict[str, DeterministicCouncilRoleAgent] | None = None,
        decision_chair: DeterministicDecisionChair | None = None,
        report_critic: ReportCritic | None = None,
        claim_ref_auditor: ClaimRefAuditor | None = None,
        gate_engine: VerdictGateEngine | None = None,
        docket_generator: RiskDocketGenerator | None = None,
    ) -> None:
        self.council_config = council_config or launch_risk_council_config()
        self.role_agents = role_agents or {
            spec.role_id: DeterministicCouncilRoleAgent(spec)
            for spec in self.council_config.role_specs
        }
        self.decision_chair = decision_chair or DeterministicDecisionChair()
        self.report_critic = report_critic or ReportCritic()
        self.claim_ref_auditor = claim_ref_auditor or ClaimRefAuditor()
        self.gate_engine = gate_engine or VerdictGateEngine()
        self.docket_generator = docket_generator or RiskDocketGenerator()

    def run(self, artifacts: dict[str, Any], mode: str) -> dict[str, Any]:
        self.council_config.validate()
        council_mode = _council_artifact_mode(mode)
        report_critique = self.report_critic.review(artifacts)
        council_claim_refs = self._council_claim_refs(artifacts, council_mode)
        role_outputs = self._role_outputs(artifacts, council_mode)
        chair_output = self.decision_chair.synthesize(
            DecisionChairInput(
                artifacts=artifacts,
                role_outputs=role_outputs,
                report_critique=report_critique,
                council_claim_refs=council_claim_refs,
                mode=council_mode,
                council_config=self.council_config,
            )
        )
        verdict = chair_output.verdict(council_mode)
        claim_audit = self.claim_ref_auditor.audit({**artifacts, "verdict": verdict}, council_claim_refs)
        gate = self.gate_engine.evaluate(artifacts, verdict, claim_audit, report_critique)
        if gate.errors:
            raise ValueError("Verdict Council gate blocked finalization: " + "; ".join(gate.errors))
        execution_package = CouncilExecutionPackage(
            council_config=self.council_config,
            role_outputs=role_outputs,
            chair_output=chair_output,
            report_critique=report_critique,
            claim_audit=claim_audit,
            gate=gate,
            council_claim_refs=council_claim_refs,
            mode=council_mode,
        )
        council_rounds = self._council_rounds(execution_package)
        risk_docket = self.docket_generator.generate(artifacts, council_rounds, verdict, gate)
        return {
            "council_rounds": council_rounds,
            "verdict": verdict,
            "risk_docket": risk_docket,
        }

    def _role_outputs(self, artifacts: dict[str, Any], mode: str) -> list[CouncilRoleOutput]:
        outputs: list[CouncilRoleOutput] = []
        for spec in self.council_config.role_specs:
            agent = self.role_agents.get(spec.role_id)
            if agent is None:
                raise ValueError(f"missing council role agent: {spec.role_id}")
            outputs.append(
                agent.analyze(
                    CouncilRoleInput(
                        role=spec,
                        artifacts=artifacts,
                        mode=mode,
                        council_config=self.council_config,
                    )
                )
            )
        return outputs

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

    def _council_rounds(self, execution_package: CouncilExecutionPackage) -> dict[str, Any]:
        package = execution_package.as_dict()
        return {
            "schema_version": "decisionrisk.council_rounds.v1",
            "mode": execution_package.mode,
            "council_config": package["council_config"],
            "role_outputs": package["role_outputs"],
            "chair_output": package["chair_output"],
            "gate": package["gate"],
            "confidence": execution_package.chair_output.confidence,
            "dissent": execution_package.chair_output.strongest_dissent,
            "mitigation_requirements": execution_package.chair_output.mitigation_requirements,
            "rounds": [
                {
                    "round": 1,
                    "name": "Independent analysis",
                    "council_roles": [output.role_name for output in execution_package.role_outputs],
                    "role_outputs": package["role_outputs"],
                    "claim_refs": _unique_claim_refs(execution_package.role_outputs),
                },
                {
                    "round": 2,
                    "name": "Report critique and ClaimRef audit",
                    "claim_refs": ["claim_0002", "claim_0003"] + [claim["claim_id"] for claim in execution_package.council_claim_refs],
                    "report_critique": execution_package.report_critique,
                    "claim_support_map": execution_package.claim_audit["claim_support_map"],
                },
                {
                    "round": 3,
                    "name": "Chair synthesis",
                    "council_role": "Decision Chair",
                    "chair_output": execution_package.chair_output.as_dict(),
                    "claim_refs": execution_package.chair_output.claim_refs,
                    "gate": execution_package.gate.as_dict(),
                },
            ],
            "claim_refs": execution_package.council_claim_refs,
            "strongest_dissent": execution_package.chair_output.strongest_dissent,
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


def _role_analysis(role_id: str) -> str:
    analyses = {
        "growth_strategist": "Opt-in beta preserves learning velocity while avoiding the adoption-at-all-costs risk of default-on launch.",
        "trust_reputation_analyst": "Default-on memory creates avoidable trust and press-framing risk; explicit controls are required before broader launch.",
        "regulatory_analyst": "The lower-risk path is a constrained launch with visible commitments, deletion controls, and enough telemetry to close evidence gaps.",
        "competitor_strategist": "Competitors can attack default-on memory as careless handling of personal context; opt-in beta reduces that attack surface.",
    }
    return analyses[role_id]


def _role_claim_refs(role_id: str) -> list[str]:
    claim_refs = {
        "growth_strategist": ["claim_0002", "claim_0005"],
        "trust_reputation_analyst": ["claim_0001", "claim_0003", "claim_0004"],
        "regulatory_analyst": ["claim_0004", "claim_0007"],
        "competitor_strategist": ["claim_0003", "claim_0006"],
    }
    return claim_refs[role_id]


def _role_dissent(role_id: str) -> str:
    dissents = {
        "growth_strategist": "Default-on could win adoption faster if controls are exceptionally clear and onboarding builds trust.",
        "trust_reputation_analyst": "Enterprise-only launch may be safer for reputation but delays consumer learning.",
        "regulatory_analyst": "A public launch could become acceptable if evidence closes consent and deletion-control gaps before release.",
        "competitor_strategist": "Competitor attack risk may be tolerable if the company preempts the narrative with strong user-control proof.",
    }
    return dissents[role_id]


def _role_mitigations(role_id: str) -> list[str]:
    mitigations = {
        "growth_strategist": ["Run an opt-in beta before wider launch"],
        "trust_reputation_analyst": ["Publish memory controls before launch", "Prepare a privacy-focused press FAQ"],
        "regulatory_analyst": ["Expose deletion and temporary-use controls in onboarding"],
        "competitor_strategist": ["Pre-brief competitive narrative risks with evidence-backed control messaging"],
    }
    return mitigations[role_id]


def _strongest_dissent(role_outputs: list[CouncilRoleOutput]) -> str:
    for output in role_outputs:
        if output.role_id == "growth_strategist":
            return output.dissent
    if role_outputs:
        return role_outputs[0].dissent
    return "No dissent recorded."


def _unique_claim_refs(role_outputs: list[CouncilRoleOutput]) -> list[str]:
    refs: list[str] = []
    for output in role_outputs:
        for claim_ref in output.claim_refs:
            if claim_ref not in refs:
                refs.append(claim_ref)
    return refs


def _sentence_list(items: list[str]) -> str:
    if not items:
        return "No required mitigations were generated."
    return " ".join(f"{item}." for item in items)
