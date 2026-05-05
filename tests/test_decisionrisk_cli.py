from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from decisionrisk.artifacts import load_case, read_json
from decisionrisk.safety import assess_case


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "launch_risk" / "ai_memory_launch" / "case.yaml"


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "decisionrisk", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


class DecisionRiskCliTests(unittest.TestCase):
    def test_replay_run_writes_manifest_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "ai_memory_launch"
            result = run_cli("run", str(CASE), "--mode", "replay", "--output-dir", str(output_dir))
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = read_json(output_dir / "run_manifest.json")
            self.assertEqual(manifest["case_id"], "ai_memory_launch")
            self.assertEqual(manifest["mode"], "replay")
            self.assertIn("sha256", manifest["artifacts"]["verdict"])
            self.assertTrue((output_dir / manifest["artifacts"]["risk_docket"]["path"]).exists())

    def test_validate_replay_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "ai_memory_launch"
            run_result = run_cli("run", str(CASE), "--mode", "replay", "--output-dir", str(output_dir))
            self.assertEqual(run_result.returncode, 0, run_result.stderr)

            validate_result = run_cli("validate", str(output_dir))
            self.assertEqual(validate_result.returncode, 0, validate_result.stderr)
            self.assertIn("validated", validate_result.stdout)

    def test_verdict_primary_rationale_has_supported_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "ai_memory_launch"
            result = run_cli("run", str(CASE), "--mode", "replay", "--output-dir", str(output_dir))
            self.assertEqual(result.returncode, 0, result.stderr)

            verdict = read_json(output_dir / "verdict.json")
            grounding = read_json(output_dir / "grounding_report.json")
            claims = {claim["claim_id"]: claim for claim in grounding["claim_refs"]}
            statuses = [claims[claim_id]["status"] for claim_id in verdict["primary_rationale_claim_refs"]]
            self.assertTrue(any(status != "unsupported_assumption" for status in statuses))

    def test_safety_blocks_negative_fixtures(self) -> None:
        blocked = [
            "no_evidence_case",
            "prompt_only_case",
            "disallowed_political_persuasion_case",
            "stock_buy_sell_case",
        ]
        for name in blocked:
            case = load_case(ROOT / "tests" / "fixtures" / name / "case.yaml")
            assessment = assess_case(case)
            self.assertFalse(assessment.allowed, name)

    def test_prompt_injection_fixture_warns_but_stays_quoted(self) -> None:
        case = load_case(ROOT / "tests" / "fixtures" / "prompt_injection_doc_case" / "case.yaml")
        assessment = assess_case(case)
        self.assertTrue(assessment.allowed)
        self.assertTrue(assessment.warnings)


if __name__ == "__main__":
    unittest.main()
