from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from decisionrisk.artifacts import read_json, sha256_file, write_json
from decisionrisk.cli import write_replay_shaped_run
from decisionrisk.evaluation import _claim_ref_eval, run_evaluation_harness


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "launch_risk" / "ai_memory_launch" / "case.yaml"
SCORECARD = ROOT / "examples" / "launch_risk" / "ai_memory_launch" / "scorecard.yaml"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "decisionrisk", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class DecisionRiskEvaluationTests(unittest.TestCase):
    def test_harness_writes_json_and_markdown_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden"
            output = Path(tmp) / "eval"
            write_replay_shaped_run(CASE, _case(), "replay", str(golden))

            report = run_evaluation_harness(CASE, output, golden, SCORECARD, repo_root=ROOT)

            self.assertEqual(report.overall_status, "pass")
            self.assertTrue((output / "evaluation_report.json").exists())
            self.assertTrue((output / "evaluation_report.md").exists())
            payload = read_json(output / "evaluation_report.json")
            statuses = {check["name"]: check["status"] for check in payload["checks"]}
            self.assertEqual(statuses["artifact_contract"], "pass")
            self.assertEqual(statuses["claim_ref"], "pass")
            self.assertEqual(statuses["safety"], "pass")
            self.assertEqual(statuses["golden_replay"], "pass")
            self.assertEqual(statuses["council_quality"], "pass")
            self.assertEqual(statuses["metric_regression"], "pass")
            self.assertEqual(statuses["ui_contract"], "pass")
            self.assertEqual(statuses["live_smoke"], "skip")

    def test_eval_cli_returns_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden"
            output = Path(tmp) / "eval"
            write_replay_shaped_run(CASE, _case(), "replay", str(golden))

            result = run_cli(
                "eval",
                str(CASE),
                "--golden-dir",
                str(golden),
                "--output-dir",
                str(output),
                "--scorecard",
                str(SCORECARD),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("evaluation_report.json", result.stdout)

    def test_update_golden_cli_requires_golden_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("eval", str(CASE), "--output-dir", str(Path(tmp) / "eval"), "--update-golden")

            self.assertEqual(result.returncode, 2)
            self.assertIn("--update-golden requires --golden-dir", result.stderr)

    def test_golden_drift_fails_without_update_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden"
            output = Path(tmp) / "eval"
            write_replay_shaped_run(CASE, _case(), "replay", str(golden))
            verdict_path = golden / "verdict.json"
            verdict = read_json(verdict_path)
            verdict["risk_level"] = "changed"
            write_json(verdict_path, verdict)
            manifest = read_json(golden / "run_manifest.json")
            manifest["artifacts"]["verdict"]["sha256"] = sha256_file(verdict_path)
            write_json(golden / "run_manifest.json", manifest)

            report = run_evaluation_harness(CASE, output, golden, SCORECARD, repo_root=ROOT)

            self.assertEqual(report.overall_status, "fail")
            golden_check = next(check for check in report.checks if check.name == "golden_replay")
            self.assertEqual(golden_check.status, "fail")
            self.assertTrue(any("verdict" in detail for detail in golden_check.details))

    def test_update_golden_refreshes_replay_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden"
            output = Path(tmp) / "eval"
            report = run_evaluation_harness(CASE, output, golden, SCORECARD, update_golden=True, repo_root=ROOT)

            self.assertEqual(report.overall_status, "pass")
            manifest = read_json(golden / "run_manifest.json")
            self.assertEqual(manifest["mode"], "replay")

    def test_metric_regression_fails_when_scorecard_band_is_violated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden"
            output = Path(tmp) / "eval"
            scorecard = Path(tmp) / "scorecard.json"
            write_replay_shaped_run(CASE, _case(), "replay", str(golden))
            write_json(
                scorecard,
                {
                    "metric_regression": {
                        "expected_lowest_risk_option": "default_on",
                        "overall_risk_bands": {"opt_in_beta": {"min": 0.95, "max": 1.0}},
                    }
                },
            )

            report = run_evaluation_harness(CASE, output, golden, scorecard, repo_root=ROOT)

            self.assertEqual(report.overall_status, "fail")
            metric_check = next(check for check in report.checks if check.name == "metric_regression")
            self.assertEqual(metric_check.status, "fail")

    def test_claim_ref_eval_catches_unsupported_only_primary_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "eval"
            write_replay_shaped_run(CASE, _case(), "eval", str(output))
            verdict_path = output / "verdict.json"
            verdict = read_json(verdict_path)
            verdict["primary_rationale_claim_refs"] = ["claim_0007"]
            write_json(verdict_path, verdict)
            manifest = read_json(output / "run_manifest.json")
            manifest["artifacts"]["verdict"]["sha256"] = sha256_file(verdict_path)
            write_json(output / "run_manifest.json", manifest)

            result = _claim_ref_eval(output)

            self.assertEqual(result.status, "fail")
            self.assertTrue(any("unsupported assumptions" in detail for detail in result.details))

    def test_live_smoke_is_skipped_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                report = run_evaluation_harness(CASE, Path(tmp) / "eval", None, SCORECARD, repo_root=ROOT)

            live_check = next(check for check in report.checks if check.name == "live_smoke")
            self.assertEqual(live_check.status, "skip")
            self.assertIn("DECISIONRISK_ENABLE_LIVE", live_check.summary)


def _case() -> dict:
    from decisionrisk.artifacts import load_case

    return load_case(CASE)


if __name__ == "__main__":
    unittest.main()
