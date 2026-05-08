from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_SRC = ROOT / "packages" / "decisionrisk-spec" / "src"
sys.path.insert(0, str(SPEC_SRC))

from decisionrisk.council import (  # noqa: E402
    ClaimRefAuditor,
    GateResult,
    ReportCritic,
    RiskDocketGenerator,
    VerdictCouncilRunner,
    VerdictGateEngine,
)
from decisionrisk.fixtures import artifact_payloads  # noqa: E402
from decisionrisk.artifacts import load_case  # noqa: E402


CASE_PATH = ROOT / "examples" / "launch_risk" / "ai_memory_launch" / "case.yaml"


def base_council_inputs() -> dict:
    payloads = artifact_payloads(load_case(CASE_PATH))
    return {name: payload for name, payload in payloads.items() if name not in {"council_rounds", "verdict"}}


class DecisionRiskCouncilTests(unittest.TestCase):
    def test_runner_generates_deterministic_final_artifacts(self) -> None:
        outputs = VerdictCouncilRunner().run(base_council_inputs(), mode="replay")

        self.assertEqual(outputs["verdict"]["final_verdict"], "RECOMMEND")
        self.assertEqual(outputs["verdict"]["recommended_option_id"], "opt_in_beta")
        self.assertEqual(outputs["council_rounds"]["rounds"][2]["gate"]["result"], "pass")
        self.assertIn("## Executive Verdict", outputs["risk_docket"])

    def test_report_critic_flags_mirofish_substrate_claims(self) -> None:
        artifacts = base_council_inputs()
        artifacts["mirofish_report_claims"] = {
            "claim_refs": [
                {
                    "claim_id": "mirofish_claim_0001",
                    "status": "unsupported_assumption",
                    "text": "Raw report claim.",
                }
            ]
        }

        critique = ReportCritic().review(artifacts)

        self.assertTrue(critique["substrate_present"])
        self.assertEqual(critique["unsupported_claim_ids"], ["mirofish_claim_0001"])

    def test_claim_ref_auditor_requires_corroborated_council_judgment_for_primary_rationale(self) -> None:
        auditor = ClaimRefAuditor()
        uncorroborated = {
            "claim_id": "claim_council_raw",
            "status": "council_judgment",
            "text": "Raw report judgment.",
            "source_refs": ["artifact:mirofish_report.md"],
        }
        corroborated = {
            **uncorroborated,
            "source_refs": ["artifact:mirofish_report.md", "metrics:simulation_metrics.overall_risk_score"],
        }

        self.assertFalse(auditor.primary_rationale_eligible(uncorroborated))
        self.assertTrue(auditor.primary_rationale_eligible(corroborated))

    def test_gate_blocks_unsupported_only_primary_rationale(self) -> None:
        artifacts = base_council_inputs()
        verdict = {
            "final_verdict": "RECOMMEND",
            "primary_rationale_claim_refs": ["claim_0007"],
        }
        audit = ClaimRefAuditor().audit({**artifacts, "verdict": verdict})

        gate = VerdictGateEngine().evaluate(artifacts, verdict, audit, ReportCritic().review(artifacts))

        self.assertEqual(gate.result, "blocked")
        self.assertTrue(any("unsupported" in error for error in gate.errors))

    def test_risk_docket_generator_writes_required_sections(self) -> None:
        artifacts = base_council_inputs()
        runner_outputs = VerdictCouncilRunner().run(artifacts, mode="replay")
        docket = RiskDocketGenerator().generate(
            artifacts,
            runner_outputs["council_rounds"],
            runner_outputs["verdict"],
            GateResult(result="pass", errors=[], warnings=[]),
        )

        self.assertIn("## Council Debate", docket)
        self.assertIn("DecisionRisk is experimental decision-support software", docket)


if __name__ == "__main__":
    unittest.main()
