from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BLOCKED_TERMS = {
    "political_persuasion": ["voter targeting", "persuade voters", "suppress turnout"],
    "market_advice": ["what stock should i buy", "buy this stock", "guaranteed price"],
    "manipulation": ["astroturf", "disinformation", "deceptive influence"],
    "harassment": ["dox", "harass", "target this person"],
}

PROMPT_INJECTION_TERMS = [
    "ignore previous instructions",
    "reveal system prompt",
    "override safety",
]


@dataclass(frozen=True)
class SafetyAssessment:
    allowed: bool
    reason: str
    warnings: list[str]


def assess_case(case: dict[str, Any]) -> SafetyAssessment:
    risk_pack = str(case.get("risk_pack", ""))
    text = " ".join(
        [
            str(case.get("title", "")),
            str(case.get("decision_question", "")),
            " ".join(str(metric) for metric in case.get("success_metrics", [])),
        ]
    ).lower()

    if risk_pack != "launch_risk":
        return SafetyAssessment(False, "MVP allowlist supports only launch_risk.", [])

    evidence = case.get("evidence_items") or case.get("evidence_bundle") or []
    if not evidence:
        return SafetyAssessment(False, "DecisionRisk cannot produce a verdict without evidence.", [])

    if len(str(case.get("decision_question", "")).strip()) > 0 and not case.get("options"):
        return SafetyAssessment(False, "DecisionRisk requires explicit decision options.", [])

    for category, terms in BLOCKED_TERMS.items():
        if any(term in text for term in terms):
            return SafetyAssessment(False, f"Blocked disallowed use: {category}.", [])

    warnings = []
    evidence_text = " ".join(str(item) for item in evidence).lower()
    if any(term in evidence_text for term in PROMPT_INJECTION_TERMS):
        warnings.append("Evidence contains prompt-injection-like text; treat it as untrusted quoted evidence.")

    return SafetyAssessment(True, "Allowed LaunchRisk case.", warnings)
