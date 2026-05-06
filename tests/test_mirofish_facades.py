from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "decisionrisk-mirofish" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.decisionrisk.facades import (  # noqa: E402
    MiroFishArtifactFacade,
    MiroFishGraphFacade,
    MiroFishProjectFacade,
    MiroFishReportFacade,
    MiroFishSimulationFacade,
)


@dataclass
class FakeProject:
    project_id: str
    name: str
    status: str = "created"
    files: list[dict] = field(default_factory=list)
    total_text_length: int = 0
    ontology: dict | None = None
    analysis_summary: str | None = None
    graph_id: str | None = None
    graph_build_task_id: str | None = None
    simulation_requirement: str | None = None
    chunk_size: int = 500
    chunk_overlap: int = 50


class FakeProjectManager:
    def __init__(self) -> None:
        self.projects: dict[str, FakeProject] = {}
        self.text: dict[str, str] = {}
        self.counter = 0

    def create_project(self, name: str) -> FakeProject:
        self.counter += 1
        project = FakeProject(project_id=f"proj_{self.counter:04d}", name=name)
        self.projects[project.project_id] = project
        return project

    def save_project(self, project: FakeProject) -> None:
        self.projects[project.project_id] = project

    def get_project(self, project_id: str) -> FakeProject | None:
        return self.projects.get(project_id)

    def save_extracted_text(self, project_id: str, text: str) -> None:
        self.text[project_id] = text

    def get_extracted_text(self, project_id: str) -> str | None:
        return self.text.get(project_id)


class FakeGraphBuilder:
    def __init__(self) -> None:
        self.calls = []

    def build_graph_async(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return "task_graph_001"


class FakeSimulationManager:
    def __init__(self) -> None:
        self.states = {}

    def create_simulation(self, **kwargs):
        state = SimpleNamespace(
            simulation_id="sim_001",
            project_id=kwargs["project_id"],
            graph_id=kwargs["graph_id"],
            status="created",
        )
        self.states[state.simulation_id] = state
        return state

    def get_simulation(self, simulation_id: str):
        return self.states.get(simulation_id)


class FakeRunner:
    RUN_STATE_DIR = "/tmp/fake-simulations"

    def start_simulation(self, **kwargs):
        return SimpleNamespace(runner_status="running")

    def get_run_state(self, simulation_id: str):
        return SimpleNamespace(runner_status="completed")

    def get_all_actions(self, simulation_id: str):
        return [
            SimpleNamespace(to_dict=lambda: {"round_num": 1, "agent_name": "A", "action_type": "CREATE_POST"}),
            {"round_num": 1, "agent_name": "B", "action_type": "LIKE_POST"},
        ]


@dataclass
class FakeReport:
    report_id: str = "report_001"
    simulation_id: str = "sim_001"
    graph_id: str = "graph_001"
    simulation_requirement: str = "Should we launch?"
    status: str = "completed"
    markdown_content: str = (
        "# Raw Report\n\n"
        "Users may react cautiously to default-on memory.\n\n"
        "- Regulators may ask for clearer controls.\n"
    )

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class FakeReportManager:
    def __init__(self) -> None:
        self.reports: dict[str, FakeReport] = {}

    def get_report_by_simulation(self, simulation_id: str):
        return None

    def save_report(self, report: FakeReport) -> None:
        self.reports[report.report_id] = report

    def get_report(self, report_id: str):
        return self.reports.get(report_id)


class FakeReportAgent:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def generate_report(self, report_id: str | None = None):
        return FakeReport(report_id=report_id or "report_001")


class MiroFishFacadeTests(unittest.TestCase):
    def test_project_facade_creates_base_project_and_clone_ref(self) -> None:
        project_manager = FakeProjectManager()
        facade = MiroFishProjectFacade(project_manager=project_manager)

        project_ref = facade.create_base_project(
            {
                "case_id": "ai_memory_launch",
                "title": "Launch Risk",
                "risk_pack": "launch_risk",
                "decision_question": "Should AcmeAI launch memory?",
                "options": [{"option_id": "opt_in_beta"}],
                "evidence_items": ["memo.md"],
                "ontology": {"entity_types": ["users"], "edge_types": ["reacts_to"]},
            },
            {"combined_text": "Evidence text."},
        )

        self.assertEqual(project_ref.case_id, "ai_memory_launch")
        self.assertEqual(project_ref.status, "ontology_generated")
        self.assertEqual(project_manager.text[project_ref.project_id], "Evidence text.")

        clone_ref = facade.clone_project_for_run(
            project_ref.project_id,
            "ai_memory_launch",
            "opt_in_beta",
            "privacy_backlash",
            7,
        )

        self.assertEqual(clone_ref.run_id, "opt_in_beta_privacy_backlash_seed_7")
        self.assertEqual(clone_ref.base_project_id, project_ref.project_id)
        self.assertNotEqual(clone_ref.clone_project_id, project_ref.project_id)
        self.assertEqual(project_manager.text[clone_ref.clone_project_id], "Evidence text.")

    def test_graph_facade_starts_async_graph_build_and_returns_ref(self) -> None:
        project_manager = FakeProjectManager()
        project = project_manager.create_project("Launch Risk")
        project.ontology = {"entity_types": ["users"], "edge_types": ["reacts_to"]}
        project_manager.save_extracted_text(project.project_id, "Evidence text.")
        builder = FakeGraphBuilder()
        facade = MiroFishGraphFacade(
            project_manager=project_manager,
            graph_builder_factory=lambda: builder,
        )

        graph_ref = facade.build_graph(project.project_id, "launch_risk")

        self.assertEqual(graph_ref.graph_task_id, "task_graph_001")
        self.assertEqual(graph_ref.status, "graph_building")
        self.assertEqual(project_manager.get_project(project.project_id).graph_build_task_id, "task_graph_001")
        self.assertEqual(builder.calls[0]["text"], "Evidence text.")

    def test_simulation_facade_runs_and_collects_trace(self) -> None:
        project_manager = FakeProjectManager()
        manager = FakeSimulationManager()
        runner = FakeRunner()
        facade = MiroFishSimulationFacade(
            simulation_manager_factory=lambda: manager,
            simulation_runner=runner,
            project_manager=project_manager,
        )
        scenario_ref = MiroFishProjectFacade(project_manager=project_manager).clone_project_for_run(
            MiroFishProjectFacade(project_manager=project_manager)
            .create_base_project(
                {
                    "case_id": "ai_memory_launch",
                    "title": "Launch Risk",
                    "decision_question": "Should we launch?",
                }
            )
            .project_id,
            "ai_memory_launch",
            "opt_in_beta",
            "privacy_backlash",
            1,
        )

        simulation_ref = facade.run_simulation(
            scenario_ref,
            {"graph_id": "graph_001"},
            {"start_runner": True, "platform": "parallel"},
        )
        trace = facade.collect_simulation_trace(simulation_ref)

        self.assertEqual(simulation_ref.simulation_id, "sim_001")
        self.assertEqual(simulation_ref.runner_status, "running")
        self.assertEqual(trace.action_count, 2)
        self.assertEqual(trace.runner_status, "completed")
        self.assertIn("twitter_actions", trace.source_paths)

    def test_report_and_artifact_facades_write_substrate_claim_refs(self) -> None:
        project_manager = FakeProjectManager()
        project = project_manager.create_project("Launch Risk")
        project.graph_id = "graph_001"
        project.simulation_requirement = "Should we launch?"
        simulation_manager = FakeSimulationManager()
        simulation_manager.states["sim_001"] = SimpleNamespace(simulation_id="sim_001", graph_id="graph_001")
        report_manager = FakeReportManager()
        report_facade = MiroFishReportFacade(
            report_agent_factory=FakeReportAgent,
            report_manager=report_manager,
            simulation_manager_factory=lambda: simulation_manager,
            project_manager=project_manager,
        )

        report_ref = report_facade.generate_mirofish_report(
            project.project_id,
            [{"simulation_id": "sim_001"}],
            report_id="report_live_001",
        )

        with tempfile.TemporaryDirectory() as tmp:
            artifacts = MiroFishArtifactFacade(report_manager=report_manager).write_mirofish_report_artifact(
                report_ref,
                tmp,
            )
            output_dir = Path(tmp)
            claims = json.loads((output_dir / artifacts["mirofish_report_claims"].path).read_text())

            self.assertTrue(report_ref.substrate_only)
            self.assertEqual(artifacts["mirofish_report"].as_manifest_ref()["path"], "mirofish_report.json")
            self.assertEqual(claims["schema_version"], "mirofish_report_claims.v1")
            self.assertGreaterEqual(len(claims["claim_refs"]), 2)
            self.assertTrue(all(c["status"] == "unsupported_assumption" for c in claims["claim_refs"]))
            self.assertEqual(
                artifacts["mirofish_report_markdown"].sha256,
                _sha256(output_dir / "mirofish_report.md"),
            )


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
