from __future__ import annotations

import json
import os
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

    def test_legacy_runtime_modes_are_rejected(self) -> None:
        for legacy_mode in ("live", "record"):
            result = run_cli("run", str(CASE), "--mode", legacy_mode)
            self.assertEqual(result.returncode, 2, legacy_mode)
            self.assertIn("invalid choice", result.stderr)

    def test_eval_run_writes_replay_shaped_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "eval_ai_memory_launch"
            result = run_cli("run", str(CASE), "--mode", "eval", "--output-dir", str(output_dir))
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = read_json(output_dir / "run_manifest.json")
            self.assertEqual(manifest["mode"], "eval")
            self.assertIn("verdict", manifest["artifacts"])
            self.assertIn("risk_docket", manifest["artifacts"])

            validate_result = run_cli("validate", str(output_dir))
            self.assertEqual(validate_result.returncode, 0, validate_result.stderr)
            mismatch_result = run_cli("validate", str(output_dir), "--mode", "replay")
            self.assertEqual(mismatch_result.returncode, 1)
            self.assertIn("does not match requested mode replay", mismatch_result.stderr)

    def test_eval_can_compare_against_golden_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden_dir = Path(tmp) / "golden"
            eval_dir = Path(tmp) / "eval"
            replay_result = run_cli("run", str(CASE), "--mode", "replay", "--output-dir", str(golden_dir))
            self.assertEqual(replay_result.returncode, 0, replay_result.stderr)

            eval_result = run_cli(
                "run",
                str(CASE),
                "--mode",
                "eval",
                "--output-dir",
                str(eval_dir),
                "--golden-dir",
                str(golden_dir),
            )
            self.assertEqual(eval_result.returncode, 0, eval_result.stderr)

    def test_live_modes_fail_preflight_without_live_config(self) -> None:
        env = os.environ.copy()
        env.pop("DECISIONRISK_ENABLE_LIVE", None)
        for mode in ("live_smoke", "live_full"):
            result = subprocess.run(
                [sys.executable, "-m", "decisionrisk", "run", str(CASE), "--mode", mode],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 2, mode)
            self.assertIn("runtime mode preflight failed", result.stderr)

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
