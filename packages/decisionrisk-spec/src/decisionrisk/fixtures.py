from __future__ import annotations

from typing import Any


OPTIONS = [
    ("default_on", "Default-on public launch"),
    ("opt_in_beta", "Opt-in beta"),
    ("enterprise_only", "Enterprise-only launch"),
]

SCENARIOS = [
    ("base_case", "Base case"),
    ("privacy_backlash", "Privacy backlash cascade"),
    ("competitor_attack", "Competitor attack"),
    ("regulator_inquiry", "Regulator inquiry"),
]

SEEDS = [1, 2, 3]


def claim(
    claim_id: str,
    text: str,
    claim_type: str,
    status: str,
    source_refs: list[str],
    confidence: float,
    used_in: list[str],
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "text": text,
        "claim_type": claim_type,
        "status": status,
        "source_refs": source_refs,
        "confidence": confidence,
        "used_in": used_in,
    }


CLAIMS = [
    claim(
        "claim_0001",
        "Users may perceive persistent memory as surveillance-like if it is enabled by default.",
        "risk_signal",
        "source_observed",
        ["evidence:public_privacy_concerns_summary", "evidence:privacy_faq_draft"],
        0.78,
        ["simulation_metrics.trust_damage", "verdict.primary_rationale"],
    ),
    claim(
        "claim_0002",
        "Opt-in launch reduces consent friction while slowing early adoption.",
        "tradeoff",
        "graph_inferred",
        ["evidence:launch_memo", "graph:launch_risk"],
        0.71,
        ["simulation_metrics.adoption_friction", "verdict.primary_rationale"],
    ),
    claim(
        "claim_0003",
        "Journalists and privacy advocates are high-leverage amplifiers in the backlash scenario.",
        "stakeholder_signal",
        "simulation_observed",
        ["run:privacy_backlash_seed_2"],
        0.68,
        ["simulation_metrics.narrative_cascade_risk", "verdict.strongest_dissent"],
    ),
    claim(
        "claim_0004",
        "Clear deletion controls and temporary-use mode are plausible mitigations for trust damage.",
        "mitigation",
        "web_verified",
        ["evidence:openai_memory_controls_summary", "evidence:privacy_faq_draft"],
        0.74,
        ["verdict.required_mitigations", "risk_docket.mitigation_plan"],
    ),
    claim(
        "claim_0005",
        "Enterprise-only launch may reduce public backlash but delays consumer learning.",
        "tradeoff",
        "council_judgment",
        ["council:growth_strategist", "council:trust_reputation_analyst"],
        0.63,
        ["simulation_metrics.overall_risk_score", "verdict.option_comparison"],
    ),
    claim(
        "claim_0006",
        "Competitors could frame default-on memory as careless handling of sensitive personal context.",
        "risk_signal",
        "simulation_observed",
        ["run:competitor_attack_seed_1"],
        0.66,
        ["simulation_metrics.competitor_exploitability"],
    ),
    claim(
        "claim_0007",
        "The exact size of the privacy-sensitive user segment is not known from the fixture evidence.",
        "evidence_gap",
        "unsupported_assumption",
        [],
        0.38,
        ["grounding_report.unsupported_assumptions"],
    ),
]


def decision_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "title": case["title"],
        "risk_pack": "launch_risk",
        "decision_question": case["decision_question"],
        "options": [{"option_id": option_id, "label": label} for option_id, label in OPTIONS],
        "time_horizon": "30 days",
        "risk_tolerance": "low-medium",
        "success_metrics": [
            "adoption",
            "trust",
            "retention",
            "press_sentiment",
            "regulatory_attention",
        ],
        "base_mirofish_project_id": "mf_proj_ai_memory_base_replay",
        "claim_refs": [CLAIMS[0], CLAIMS[1], CLAIMS[4]],
    }


def evidence_manifest() -> dict[str, Any]:
    return {
        "grounding_level": "G1",
        "web_grounding_optional": True,
        "evidence_items": [
            {"evidence_id": "launch_memo", "source_type": "synthetic_internal", "path": "sources/synthetic/launch_memo.md"},
            {"evidence_id": "privacy_faq_draft", "source_type": "synthetic_internal", "path": "sources/synthetic/privacy_faq_draft.md"},
            {"evidence_id": "customer_interviews", "source_type": "synthetic_internal", "path": "sources/synthetic/customer_interviews.md"},
            {"evidence_id": "openai_memory_controls_summary", "source_type": "public_context_summary", "path": "sources/public/openai_memory_controls_summary.md"},
            {"evidence_id": "public_privacy_concerns_summary", "source_type": "public_context_summary", "path": "sources/public/public_privacy_concerns_summary.md"},
        ],
        "claim_refs": [CLAIMS[0], CLAIMS[3], CLAIMS[6]],
    }


def grounding_report() -> dict[str, Any]:
    return {
        "grounding_level": "G1",
        "web_grounding": "not_enabled",
        "evidence_items": 5,
        "unsupported_assumptions": 1,
        "confidence_cap": 0.70,
        "claim_refs": CLAIMS,
    }


def risk_graph() -> dict[str, Any]:
    return {
        "graph_id": "risk_graph_ai_memory_launch_replay",
        "entity_types": ["DecisionOption", "CustomerSegment", "Journalist", "Regulator", "Competitor", "Narrative", "Risk", "Mitigation"],
        "nodes": [
            {"id": "stakeholder_power_users", "type": "CustomerSegment", "name": "Privacy-conscious power users", "claim_refs": ["claim_0001"]},
            {"id": "narrative_surveillance", "type": "Narrative", "name": "Default memory as surveillance", "claim_refs": ["claim_0001", "claim_0003"]},
            {"id": "mitigation_controls", "type": "Mitigation", "name": "Explicit controls and deletion UX", "claim_refs": ["claim_0004"]},
        ],
        "edges": [
            {"from": "stakeholder_power_users", "to": "narrative_surveillance", "type": "amplifies", "claim_refs": ["claim_0003"]},
            {"from": "mitigation_controls", "to": "narrative_surveillance", "type": "mitigates", "claim_refs": ["claim_0004"]},
        ],
    }


def scenario_design() -> dict[str, Any]:
    return {
        "council": "scenario_design",
        "scenarios": [
            {"scenario_id": scenario_id, "name": name, "applies_to_options": [option_id for option_id, _ in OPTIONS]}
            for scenario_id, name in SCENARIOS
        ],
        "metrics": [
            "backlash_intensity",
            "adoption_friction",
            "narrative_cascade_risk",
            "trust_damage",
            "regulator_attention",
            "competitor_exploitability",
            "overall_risk_score",
        ],
        "claim_refs": [CLAIMS[1], CLAIMS[2], CLAIMS[3]],
    }


def scenario_runs() -> dict[str, Any]:
    runs = []
    for option_id, _ in OPTIONS:
        for scenario_id, _ in SCENARIOS:
            for seed in SEEDS:
                run_id = f"{option_id}_{scenario_id}_seed_{seed}"
                runs.append(
                    {
                        "run_id": run_id,
                        "option_id": option_id,
                        "scenario_id": scenario_id,
                        "seed": seed,
                        "mode": "replay",
                        "clone_project_id": f"mf_proj_{run_id}",
                        "simulation_id": f"mf_sim_{run_id}",
                        "graph_mode": "read_only_shared",
                        "status": "completed",
                        "claim_refs": ["claim_0002", "claim_0003"] if scenario_id == "privacy_backlash" else ["claim_0005"],
                    }
                )
    return {"expected_runs": 36, "runs": runs}


def simulation_metrics() -> dict[str, Any]:
    option_scores = {
        "default_on": {
            "backlash_intensity": 0.82,
            "adoption_friction": 0.31,
            "narrative_cascade_risk": 0.79,
            "trust_damage": 0.74,
            "regulator_attention": 0.61,
            "competitor_exploitability": 0.73,
            "overall_risk_score": 0.72,
        },
        "opt_in_beta": {
            "backlash_intensity": 0.45,
            "adoption_friction": 0.48,
            "narrative_cascade_risk": 0.39,
            "trust_damage": 0.34,
            "regulator_attention": 0.28,
            "competitor_exploitability": 0.41,
            "overall_risk_score": 0.43,
        },
        "enterprise_only": {
            "backlash_intensity": 0.28,
            "adoption_friction": 0.67,
            "narrative_cascade_risk": 0.25,
            "trust_damage": 0.24,
            "regulator_attention": 0.34,
            "competitor_exploitability": 0.38,
            "overall_risk_score": 0.47,
        },
    }
    return {
        "formula_version": "launch_risk.metrics.v1",
        "metric_authority": "deterministic_formulas_over_structured_signals",
        "options": option_scores,
        "ensemble": {"runs": 36, "scenario_dispersion": 0.24, "evidence_confidence": 0.66},
        "claim_refs": [CLAIMS[0], CLAIMS[1], CLAIMS[2], CLAIMS[5]],
    }


def council_rounds() -> dict[str, Any]:
    return {
        "rounds": [
            {"round": 1, "name": "Independent analysis", "advisors": ["Growth Strategist", "Trust and Reputation Analyst", "Regulatory Analyst", "Competitor Strategist"], "claim_refs": ["claim_0001", "claim_0005"]},
            {"round": 2, "name": "Anonymous peer review", "claim_refs": ["claim_0002", "claim_0003"]},
            {"round": 3, "name": "Chair synthesis", "advisor": "Decision Chair", "claim_refs": ["claim_0001", "claim_0002", "claim_0004"]},
        ],
        "strongest_dissent": "Default-on could win adoption faster if controls are exceptionally clear and onboarding builds trust.",
    }


def verdict() -> dict[str, Any]:
    return {
        "threshold_verdict": "RECOMMEND",
        "final_verdict": "RECOMMEND",
        "recommended_option_id": "opt_in_beta",
        "confidence": 0.66,
        "risk_level": "medium",
        "primary_rationale": "Opt-in beta reduces trust and narrative cascade risk while preserving enough adoption signal for learning.",
        "primary_rationale_claim_refs": ["claim_0001", "claim_0002", "claim_0004"],
        "strongest_dissent": "Default-on may accelerate adoption if the company can prove controls are clear before launch.",
        "required_mitigations": ["Publish memory controls before launch", "Expose deletion and temporary-use controls in onboarding", "Prepare a privacy-focused press FAQ"],
        "what_would_change_the_verdict": ["Public evidence that users strongly prefer default-on memory", "Beta telemetry showing low opt-out and low trust damage"],
    }


def risk_docket_markdown() -> str:
    return """# Risk Docket: AcmeAI Memory Launch

Safety boundary: DecisionRisk is experimental decision-support software. It does not predict the future and should not be used as the sole basis for legal, financial, medical, electoral, or public-safety decisions.

## Executive Verdict

Recommendation: launch as an opt-in beta. Confidence: 0.66. Risk level: medium. ClaimRefs: claim_0001, claim_0002, claim_0004.

## Decision Context

AcmeAI is deciding whether to launch long-term assistant memory as default-on, opt-in beta, or enterprise-only over a 30 day horizon.

## Evidence Base

Grounding Level: G1 - User Evidence Only. The company, internal memo, and interview snippets are fictional synthetic evidence. Public context summaries ground the memory/privacy control category. Unsupported assumptions are tracked in claim_0007.

## Risk Graph

The graph highlights privacy-conscious power users, journalists, competitors, regulators, the surveillance narrative, and explicit control mitigations.

## Scenario Ensemble

Replay fixture includes 36 runs: 3 options x 4 scenarios x 3 seeds.

## Metrics

Opt-in beta has lower backlash intensity, trust damage, narrative cascade risk, regulator attention, and overall risk score than default-on.

## Council Debate

The council preserved dissent that default-on may accelerate adoption if controls are unusually clear and trusted.

## Strongest Dissent

Default-on could win faster adoption if onboarding makes memory behavior obvious and users value personalization more than control.

## Final Recommendation

Choose opt-in beta. Do not launch default-on until controls, deletion, and temporary-use behavior are visible and tested.

## Mitigation Plan

Publish memory controls before launch, expose deletion controls in onboarding, prepare a privacy-focused press FAQ, and run a staged beta.

## Monitoring Plan

Monitor negative narrative share, opt-out rate, support burden, regulator mentions, and press framing in the first 72 hours.

## Audit Trail

Material claims link to ClaimRefs in the durable artifacts. Unsupported assumptions are not used as the sole basis for the verdict.
"""


def artifact_payloads(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_case": decision_case(case),
        "evidence_manifest": evidence_manifest(),
        "grounding_report": grounding_report(),
        "risk_graph": risk_graph(),
        "scenario_design": scenario_design(),
        "scenario_runs": scenario_runs(),
        "simulation_metrics": simulation_metrics(),
        "council_rounds": council_rounds(),
        "verdict": verdict(),
    }
