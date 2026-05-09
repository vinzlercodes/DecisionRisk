from __future__ import annotations

import re
from typing import Any


REPORT_SUBSTRATE_ARTIFACTS = (
    "mirofish_report",
    "mirofish_report_markdown",
    "mirofish_report_claims",
)

REPORT_CLAIM_REQUIRED_FIELDS = {
    "claim_id",
    "text",
    "claim_type",
    "status",
    "source_refs",
    "confidence",
    "used_in",
}

OVERCLAIM_PATTERNS = (
    r"\bguarantee[sd]?\b",
    r"\bprove[sn]?\b",
    r"\bcertain(?:ly|ty)?\b",
    r"\beliminate[sd]?\s+(?:all\s+)?risk\b",
    r"\bno\s+(?:material\s+)?risk\b",
    r"\bwill\s+(?:definitely|always|never)\b",
)


def replay_report_payload(artifacts: dict[str, Any], mode: str) -> dict[str, Any]:
    decision_case = artifacts.get("decision_case", {})
    scenario_runs = artifacts.get("scenario_runs", {})
    metrics = artifacts.get("simulation_metrics", {})
    case_id = decision_case.get("case_id", "decision_case")
    expected_runs = scenario_runs.get("expected_runs", len(scenario_runs.get("runs", [])))
    options = metrics.get("options", {})
    lowest_risk_option = _lowest_risk_option(options) or "unknown"
    lowest_risk_score = options.get(lowest_risk_option, {}).get("overall_risk_score", "unknown")

    markdown = f"""# MiroFish Report Substrate: {decision_case.get("title", case_id)}

This replay report substrate summarizes deterministic DecisionRisk fixture artifacts in the MiroFish report handoff shape. It is not a final DecisionRisk verdict.

The decision question is: {decision_case.get("decision_question", "No decision question supplied.")}

The scenario ensemble contains {expected_runs} option x scenario x seed runs.

The lowest deterministic overall risk score belongs to {lowest_risk_option} with score {lowest_risk_score}.

Any recommendation must be produced by the Verdict Council after ClaimRef audit, not by this report substrate.
"""

    return {
        "report_id": f"replay_report_{case_id}",
        "simulation_id": f"replay_simulation_{case_id}",
        "graph_id": artifacts.get("risk_graph", {}).get("graph_id", f"replay_graph_{case_id}"),
        "status": "completed",
        "substrate_only": True,
        "markdown_content": markdown,
        "metadata": {
            "provenance": "replay_report_substrate",
            "mode": _report_substrate_mode(mode),
            "case_id": case_id,
        },
    }


def normalize_report_to_claims(
    report: dict[str, Any],
    traces: list[dict[str, Any]] | None = None,
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    markdown = report.get("markdown_content", "")
    if not isinstance(markdown, str):
        markdown = ""

    claim_refs = []
    source_refs = _substrate_source_refs(report, traces)
    for index, text in enumerate(candidate_claims(markdown), start=1):
        claim_refs.append(
            {
                "claim_id": f"mirofish_claim_{index:04d}",
                "text": text,
                "claim_type": "report_substrate",
                "status": "unsupported_assumption",
                "source_refs": source_refs,
                "confidence": 0.2,
                "used_in": ["mirofish_report_substrate"],
                "metadata": {
                    "requires_claimref_audit": True,
                    "raw_mirofish_output": True,
                    "report_id": report.get("report_id"),
                },
            }
        )

    return {
        "schema_version": "mirofish_report_claims.v1",
        "substrate_only": True,
        "report_id": report.get("report_id"),
        "simulation_id": report.get("simulation_id"),
        "trace_count": len(traces or []),
        "graph_ref": graph or {},
        "claim_refs": claim_refs,
    }


def valid_report_claim_ref(claim_ref: dict[str, Any]) -> bool:
    if not REPORT_CLAIM_REQUIRED_FIELDS.issubset(claim_ref):
        return False
    if not isinstance(claim_ref.get("source_refs"), list):
        return False
    if not isinstance(claim_ref.get("used_in"), list):
        return False
    return bool(claim_ref.get("claim_id")) and bool(claim_ref.get("text")) and bool(claim_ref.get("status"))


def overclaiming_claim_ids(claim_refs: list[dict[str, Any]]) -> list[str]:
    overclaimed: list[str] = []
    for claim_ref in claim_refs:
        text = str(claim_ref.get("text", "")).lower()
        if any(re.search(pattern, text) for pattern in OVERCLAIM_PATTERNS):
            overclaimed.append(str(claim_ref.get("claim_id", "unknown")))
    return overclaimed


def scenario_unsupported_claim_ids(claim_refs: list[dict[str, Any]]) -> list[str]:
    unsupported: list[str] = []
    for claim_ref in claim_refs:
        source_refs = _source_refs(claim_ref)
        if not any(ref.startswith(("run:", "scenario:", "simulation:", "metric:", "metrics:")) for ref in source_refs):
            unsupported.append(str(claim_ref.get("claim_id", "unknown")))
    return unsupported


def candidate_claims(markdown: str) -> list[str]:
    candidates: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        text = clean_claim_text(block)
        if not text:
            continue
        if text.startswith("#"):
            continue
        if len(text) < 24:
            continue
        candidates.append(text)
    return candidates


def clean_claim_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        stripped = stripped.lstrip(">").strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines).strip()


def _substrate_source_refs(report: dict[str, Any], traces: list[dict[str, Any]] | None) -> list[str]:
    refs = ["artifact:mirofish_report.md"]
    if report.get("metadata", {}).get("provenance") == "replay_report_substrate":
        refs.append("grounding:replay_report_substrate")
    for trace in traces or []:
        run_id = trace.get("run_id")
        if run_id:
            refs.append(f"run:{run_id}")
            break
    return refs


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


def _lowest_risk_option(options: dict[str, Any]) -> str | None:
    scored = [
        (option_id, metrics.get("overall_risk_score"))
        for option_id, metrics in options.items()
        if isinstance(metrics, dict) and isinstance(metrics.get("overall_risk_score"), (int, float))
    ]
    if not scored:
        return None
    return min(scored, key=lambda item: item[1])[0]


def _report_substrate_mode(mode: str) -> str:
    if mode in {"replay", "eval"}:
        return "deterministic_replay"
    return mode
