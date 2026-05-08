from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from flask import Flask
except ImportError:  # pragma: no cover - exercised when backend deps are not installed.
    Flask = None


ROOT = Path(__file__).resolve().parents[1]
SPEC_SRC = ROOT / "packages" / "decisionrisk-spec" / "src"
BACKEND_ROOT = ROOT / "apps" / "decisionrisk-mirofish" / "backend"
sys.path.insert(0, str(SPEC_SRC))
sys.path.insert(0, str(BACKEND_ROOT))

if Flask is not None:
    from app.decisionrisk.api import decisionrisk_bp  # noqa: E402
from app.decisionrisk.facades.contracts import (  # noqa: E402
    MiroFishGraphRef,
    MiroFishProjectRef,
    MiroFishReportRef,
    MiroFishSimulationRef,
    MiroFishSimulationTrace,
    ScenarioRunRef,
)
from app.decisionrisk.execution_orchestrator import FileBackedExecutionQueue  # noqa: E402
from app.decisionrisk.runtime_runner import DecisionRiskRuntimeRunner  # noqa: E402
from app.decisionrisk.runtime_runner import RuntimeValidationError  # noqa: E402
from decisionrisk.artifacts import load_case, read_json, write_json  # noqa: E402


CASE_PATH = ROOT / "examples" / "launch_risk" / "ai_memory_launch" / "case.yaml"


def make_app(outputs_dir: Path) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(decisionrisk_bp, url_prefix="/api/decisionrisk")
    app.config["TESTING"] = True
    os.environ["DECISIONRISK_OUTPUTS_DIR"] = str(outputs_dir)
    os.environ["DECISIONRISK_EXECUTION_AUTO_START"] = "0"
    return app


@unittest.skipIf(Flask is None, "Flask backend dependencies are not installed.")
class DecisionRiskBackendRouteTests(unittest.TestCase):
    def test_runtime_modes_endpoint_reports_canonical_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            response = app.test_client().get("/api/decisionrisk/runtime-modes")
            self.assertEqual(response.status_code, 200)
            names = [item["name"] for item in response.get_json()["modes"]]
            self.assertEqual(names, ["replay", "live_smoke", "live_full", "eval"])

    def test_run_endpoint_enqueues_replay_execution(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            response = app.test_client().post(
                "/api/decisionrisk/runs",
                json={"mode": "replay", "decision_case": case},
            )
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            body = response.get_json()
            self.assertTrue(body["success"])
            self.assertEqual(body["mode"], "replay")
            self.assertEqual(body["status"], "queued")
            self.assertIn("execution_id", body)

            status_response = app.test_client().get(body["status_url"])
            self.assertEqual(status_response.status_code, 200)
            self.assertEqual(status_response.get_json()["execution"]["execution_id"], body["execution_id"])

    def test_execution_publish_endpoint_requires_validation(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            response = app.test_client().post(
                "/api/decisionrisk/runs",
                json={"mode": "replay", "decision_case": case},
            )
            execution_id = response.get_json()["execution_id"]
            publish_response = app.test_client().post(f"/api/decisionrisk/runs/{execution_id}/publish")
            self.assertEqual(publish_response.status_code, 400)

    def test_execution_events_endpoint_reports_queue_event(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            response = app.test_client().post(
                "/api/decisionrisk/runs",
                json={"mode": "replay", "decision_case": case},
            )
            execution_id = response.get_json()["execution_id"]
            events_response = app.test_client().get(f"/api/decisionrisk/runs/{execution_id}/events")
            self.assertEqual(events_response.status_code, 200)
            self.assertEqual(events_response.get_json()["events"][0]["event_type"], "execution_queued")

    def test_execution_cancel_endpoint_marks_queued_execution_cancelled(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            response = app.test_client().post(
                "/api/decisionrisk/runs",
                json={"mode": "replay", "decision_case": case},
            )
            execution_id = response.get_json()["execution_id"]
            cancel_response = app.test_client().post(f"/api/decisionrisk/runs/{execution_id}/cancel")
            self.assertEqual(cancel_response.status_code, 200)
            self.assertEqual(cancel_response.get_json()["execution"]["status"], "cancelled")


class DecisionRiskExecutionQueueTests(unittest.TestCase):
    def test_enqueue_writes_queued_status_and_event(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            status = queue.enqueue(case, "replay")
            self.assertEqual(status["status"], "queued")
            self.assertEqual(status["stage"], "queued")
            events = queue.events(status["execution_id"])
            self.assertEqual(events[0]["event_type"], "execution_queued")

    def test_replay_and_eval_execute_through_same_contract(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            replay = queue.enqueue(case, "replay")
            eval_run = queue.enqueue(case, "eval")
            self.assertEqual(queue.process_next()["status"], "validated")
            self.assertEqual(queue.process_next()["status"], "validated")
            replay_manifest = read_json(
                Path(tmp) / case["case_id"] / "runs" / replay["execution_id"] / "run_manifest.json"
            )
            eval_manifest = read_json(
                Path(tmp) / case["case_id"] / "runs" / eval_run["execution_id"] / "run_manifest.json"
            )
            self.assertEqual(replay_manifest["mode"], "replay")
            self.assertEqual(eval_manifest["mode"], "eval")

    def test_same_case_rerun_creates_new_execution_id(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            first = queue.enqueue(case, "replay")
            second = queue.enqueue(case, "replay")
            self.assertNotEqual(first["execution_id"], second["execution_id"])

    def test_named_overwrite_replaces_existing_execution(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            queue.enqueue(case, "replay", execution_id="ex_named")
            marker = Path(tmp) / case["case_id"] / "runs" / "ex_named" / "marker.txt"
            marker.write_text("old", encoding="utf-8")
            overwritten = queue.enqueue(case, "eval", execution_id="ex_named", overwrite=True)
            self.assertEqual(overwritten["execution_id"], "ex_named")
            self.assertFalse(marker.exists())
            self.assertEqual(overwritten["mode"], "eval")

    def test_running_cancellation_preserves_artifacts_and_marks_non_final(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue: FileBackedExecutionQueue

            class CancellingRunner:
                def __init__(self, outputs_root: Path) -> None:
                    self.outputs_root = outputs_root

                def run(self, decision_case, mode, output_dir=None):
                    queue.cancel(output_dir.name)
                    return DecisionRiskRuntimeRunner(self.outputs_root).run(decision_case, mode, output_dir=output_dir)

            queue = FileBackedExecutionQueue(Path(tmp), runner_factory=CancellingRunner, auto_start=False)
            status = queue.enqueue(case, "replay")
            processed = queue.process_next()
            self.assertEqual(processed["status"], "cancelled")
            self.assertFalse(processed["final"])
            manifest = Path(tmp) / case["case_id"] / "runs" / status["execution_id"] / "run_manifest.json"
            self.assertTrue(manifest.exists())

    def test_partial_failure_writes_run_error_and_non_final_status(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:

            class PartialFailingRunner:
                def __init__(self, outputs_root: Path) -> None:
                    self.outputs_root = outputs_root

                def run(self, decision_case, mode, output_dir=None):
                    DecisionRiskRuntimeRunner(self.outputs_root).run(decision_case, mode, output_dir=output_dir)
                    scenario_path = output_dir / "scenario_runs.json"
                    scenario_runs = read_json(scenario_path)
                    scenario_runs["runs"][0]["status"] = "failed"
                    write_json(scenario_path, scenario_runs)
                    raise RuntimeValidationError(["simulated partial failure"])

            queue = FileBackedExecutionQueue(Path(tmp), runner_factory=PartialFailingRunner, auto_start=False)
            status = queue.enqueue(case, "replay")
            processed = queue.process_next()
            run_dir = Path(tmp) / case["case_id"] / "runs" / status["execution_id"]
            self.assertEqual(processed["status"], "partially_failed")
            self.assertFalse(processed["final"])
            self.assertTrue((run_dir / "run_error.json").exists())

    def test_failed_scenario_retry_updates_only_failed_seed(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:

            class PartialFailingRunner:
                def __init__(self, outputs_root: Path) -> None:
                    self.outputs_root = outputs_root

                def run(self, decision_case, mode, output_dir=None):
                    DecisionRiskRuntimeRunner(self.outputs_root).run(decision_case, mode, output_dir=output_dir)
                    scenario_path = output_dir / "scenario_runs.json"
                    scenario_runs = read_json(scenario_path)
                    scenario_runs["runs"][0]["status"] = "failed"
                    write_json(scenario_path, scenario_runs)
                    raise RuntimeValidationError(["simulated partial failure"])

            queue = FileBackedExecutionQueue(Path(tmp), runner_factory=PartialFailingRunner, auto_start=False)
            status = queue.enqueue(case, "replay")
            queue.process_next()
            run_dir = Path(tmp) / case["case_id"] / "runs" / status["execution_id"]
            failed_id = read_json(run_dir / "scenario_runs.json")["runs"][0]["run_id"]
            retried = queue.retry_scenario_run(status["execution_id"], failed_id)
            scenario_runs = read_json(run_dir / "scenario_runs.json")
            self.assertEqual(retried["status"], "validated")
            self.assertEqual(scenario_runs["runs"][0]["retry_count"], 1)
            self.assertNotIn("retry_count", scenario_runs["runs"][1])

    def test_resume_blocks_when_checkpoint_hashes_changed(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            status = queue.enqueue(case, "replay")
            queue.process_next()
            run_dir = Path(tmp) / case["case_id"] / "runs" / status["execution_id"]
            (run_dir / "verdict.json").write_text("{}", encoding="utf-8")
            resumed = queue.resume(status["execution_id"])
            self.assertEqual(resumed["status"], "failed")
            self.assertEqual(resumed["stage"], "resume_blocked")

    def test_publish_requires_validated_execution(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileBackedExecutionQueue(Path(tmp), auto_start=False)
            status = queue.enqueue(case, "replay")
            with self.assertRaises(ValueError):
                queue.publish(status["execution_id"])
            queue.process_next()
            published = queue.publish(status["execution_id"])
            self.assertEqual(published["status"], "published")
            self.assertTrue(published["published"])

    def test_validator_rejects_partial_execution_outputs(self) -> None:
        from decisionrisk.cli import validate_output_dir

        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:

            class PartialFailingRunner:
                def __init__(self, outputs_root: Path) -> None:
                    self.outputs_root = outputs_root

                def run(self, decision_case, mode, output_dir=None):
                    DecisionRiskRuntimeRunner(self.outputs_root).run(decision_case, mode, output_dir=output_dir)
                    raise RuntimeValidationError(["simulated partial failure"])

            queue = FileBackedExecutionQueue(Path(tmp), runner_factory=PartialFailingRunner, auto_start=False)
            status = queue.enqueue(case, "replay")
            queue.process_next()
            run_dir = Path(tmp) / case["case_id"] / "runs" / status["execution_id"]
            errors = validate_output_dir(run_dir)
            self.assertIn("run_status.json marks output non-final: partially_failed", errors)


class DecisionRiskBackendRunnerTests(unittest.TestCase):
    def test_live_smoke_runner_fails_preflight_without_live_config(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            runner = DecisionRiskRuntimeRunner(Path(tmp))
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(RuntimeError) as raised:
                    runner.run(case, "live_smoke")
            self.assertIn("DECISIONRISK_ENABLE_LIVE=1", str(raised.exception))

    def test_live_smoke_runner_writes_substrate_only_mirofish_artifacts(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            runner = DecisionRiskRuntimeRunner(
                Path(tmp),
                project_facade=FakeProjectFacade(),
                graph_facade=FakeGraphFacade(),
                simulation_facade=FakeSimulationFacade(),
                report_facade=FakeReportFacade(),
            )
            with patch.dict(os.environ, {"DECISIONRISK_ENABLE_LIVE": "1"}):
                result = runner.run(case, "live_smoke")

            self.assertEqual(result["mode"], "live_smoke")
            self.assertEqual(sorted(result["final_artifacts"]), ["risk_docket", "verdict"])
            self.assertNotIn("manifest", result)
            manifest = read_json(Path(tmp) / case["case_id"] / "run_manifest.json")
            self.assertEqual(manifest["mode"], "live_smoke")
            self.assertIn("mirofish_report", manifest["artifacts"])
            self.assertIn("mirofish_report_markdown", manifest["artifacts"])
            self.assertIn("council_rounds", manifest["artifacts"])
            self.assertIn("verdict", manifest["artifacts"])
            self.assertIn("risk_docket", manifest["artifacts"])
            scenario_runs = read_json(Path(tmp) / case["case_id"] / "scenario_runs.json")
            self.assertEqual(scenario_runs["expected_runs"], 1)
            self.assertEqual(scenario_runs["runs"][0]["mode"], "live_smoke")
            substrate = read_json(Path(tmp) / case["case_id"] / "mirofish_report_claims.json")
            self.assertTrue(substrate["substrate_only"])
            council_rounds = read_json(Path(tmp) / case["case_id"] / "council_rounds.json")
            self.assertEqual(council_rounds["mode"], "live_smoke")
            self.assertTrue(council_rounds["rounds"][1]["report_critique"]["substrate_present"])
            self.assertEqual(council_rounds["claim_refs"][0]["status"], "council_judgment")

    def test_live_full_requires_llm_config_and_does_not_downgrade(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            runner = DecisionRiskRuntimeRunner(Path(tmp))
            with patch.dict(os.environ, {"DECISIONRISK_ENABLE_LIVE": "1"}, clear=True):
                with self.assertRaises(RuntimeError) as raised:
                    runner.run(case, "live_full")
            self.assertIn("DECISIONRISK_ENABLE_LIVE_LLM=1", str(raised.exception))
            self.assertFalse((Path(tmp) / case["case_id"] / "run_manifest.json").exists())

    def test_live_full_is_not_implemented_after_preflight_and_does_not_downgrade(self) -> None:
        case = load_case(CASE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            runner = DecisionRiskRuntimeRunner(Path(tmp))
            env = {
                "DECISIONRISK_ENABLE_LIVE": "1",
                "DECISIONRISK_ENABLE_LIVE_LLM": "1",
                "DECISIONRISK_LLM_API_KEY": "test-key",
            }
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(RuntimeError) as raised:
                    runner.run(case, "live_full")
            self.assertIn("live_full requires live Verdict Council role and model configuration", str(raised.exception))
            self.assertFalse((Path(tmp) / case["case_id"] / "run_manifest.json").exists())


class FakeProjectFacade:
    def create_base_project(self, decision_case, evidence_manifest):
        return MiroFishProjectRef(
            project_id="mf_live_base",
            case_id=decision_case["case_id"],
            name=decision_case["title"],
            status="completed",
            simulation_requirement=decision_case["decision_question"],
        )

    def clone_project_for_run(self, base_project_id, case_id, option_id, scenario_id, seed):
        return ScenarioRunRef(
            run_id=f"{option_id}_{scenario_id}_seed_{seed}",
            case_id=case_id,
            option_id=option_id,
            scenario_id=scenario_id,
            seed=seed,
            base_project_id=base_project_id,
            clone_project_id="mf_live_clone",
        )


class FakeGraphFacade:
    def build_graph(self, project_id, risk_pack, evidence_manifest):
        return MiroFishGraphRef(
            project_id=project_id,
            risk_pack=risk_pack,
            status="completed",
            graph_id="mf_graph_live",
        )


class FakeSimulationFacade:
    def run_simulation(self, scenario_run_ref, graph_ref, scenario_config):
        return MiroFishSimulationRef(
            simulation_id="mf_sim_live",
            run_id=scenario_run_ref.run_id,
            project_id=scenario_run_ref.clone_project_id,
            graph_id=graph_ref.graph_id,
            status="completed",
            runner_status="completed",
        )

    def collect_simulation_trace(self, simulation_ref, limit=None):
        return MiroFishSimulationTrace(
            simulation_id=simulation_ref.simulation_id,
            run_id=simulation_ref.run_id,
            status="completed",
            runner_status="completed",
            action_count=0,
            actions=[],
        )


class FakeReportFacade:
    def generate_mirofish_report(self, project_id, completed_runs):
        return MiroFishReportRef(
            report_id="mf_report_live",
            simulation_id=completed_runs[0].simulation_id,
            graph_id=completed_runs[0].graph_id,
            status="completed",
        )


if __name__ == "__main__":
    unittest.main()
