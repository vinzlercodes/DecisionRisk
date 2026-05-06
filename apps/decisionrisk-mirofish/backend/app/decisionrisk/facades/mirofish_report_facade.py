"""Boundary for DecisionRisk report operations over MiroFish report generation."""

from __future__ import annotations

from typing import Any

from .contracts import MiroFishReportRef, MiroFishSimulationRef


class MiroFishReportFacade:
    """Owns DecisionRisk access to raw MiroFish report substrate generation."""

    def __init__(
        self,
        report_agent_factory: object | None = None,
        report_manager: object | None = None,
        simulation_manager_factory: object | None = None,
        project_manager: object | None = None,
    ) -> None:
        self.report_agent_factory = report_agent_factory or self._default_report_agent_factory()
        self.report_manager = report_manager or self._default_report_manager()
        self.simulation_manager_factory = simulation_manager_factory or self._default_simulation_manager
        self.project_manager = project_manager or self._default_project_manager()

    @staticmethod
    def _default_report_agent_factory() -> object:
        from ...services.report_agent import ReportAgent

        return ReportAgent

    @staticmethod
    def _default_report_manager() -> object:
        from ...services.report_agent import ReportManager

        return ReportManager

    @staticmethod
    def _default_simulation_manager() -> object:
        from ...services.simulation_manager import SimulationManager

        return SimulationManager()

    @staticmethod
    def _default_project_manager() -> object:
        from ...models.project import ProjectManager

        return ProjectManager

    def generate_mirofish_report(
        self,
        project_id: str,
        completed_runs: list[MiroFishSimulationRef | dict[str, Any] | str],
        force_regenerate: bool = False,
        report_id: str | None = None,
    ) -> MiroFishReportRef:
        """Generate or retrieve a raw MiroFish report substrate.

        The report is deliberately marked substrate-only. DecisionRisk verdict
        and Risk Docket generation are owned by later council/gate work.
        """

        if not completed_runs:
            raise ValueError("generate_mirofish_report requires at least one completed simulation run.")

        simulation_id = _simulation_id(completed_runs[0])
        manager = self.simulation_manager_factory()
        simulation_state = manager.get_simulation(simulation_id)
        if not simulation_state:
            raise ValueError(f"MiroFish simulation not found: {simulation_id}")

        existing = None if force_regenerate else self.report_manager.get_report_by_simulation(simulation_id)
        if existing:
            return _report_ref(existing, task_id=None, metadata={"already_generated": True})

        project = self.project_manager.get_project(project_id)
        if not project:
            raise ValueError(f"MiroFish project not found: {project_id}")

        graph_id = getattr(simulation_state, "graph_id", None) or getattr(project, "graph_id", None)
        if not graph_id:
            raise ValueError("MiroFish report generation requires graph_id.")

        simulation_requirement = getattr(project, "simulation_requirement", None)
        if not simulation_requirement:
            raise ValueError("MiroFish report generation requires project.simulation_requirement.")

        agent = self.report_agent_factory(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
        )
        report = agent.generate_report(report_id=report_id)
        self.report_manager.save_report(report)
        return _report_ref(
            report,
            task_id=None,
            metadata={
                "completed_run_count": len(completed_runs),
                "substrate": "mirofish_report",
            },
        )

    def summarize_report(self, report_id: str) -> dict[str, Any]:
        """Return substrate metadata for an existing MiroFish report."""

        report = self.report_manager.get_report(report_id)
        if not report:
            raise ValueError(f"MiroFish report not found: {report_id}")
        ref = _report_ref(report, task_id=None, metadata={"substrate": "mirofish_report"})
        return ref.to_dict()


def _simulation_id(run: MiroFishSimulationRef | dict[str, Any] | str) -> str:
    if isinstance(run, MiroFishSimulationRef):
        return run.simulation_id
    if isinstance(run, dict):
        value = run.get("simulation_id")
        if value:
            return str(value)
    if isinstance(run, str):
        return run
    raise ValueError("Completed run must include simulation_id.")


def _status_value(status: object) -> str:
    return str(getattr(status, "value", status))


def _report_ref(report: object, task_id: str | None, metadata: dict[str, Any]) -> MiroFishReportRef:
    return MiroFishReportRef(
        report_id=str(getattr(report, "report_id")),
        simulation_id=str(getattr(report, "simulation_id")),
        graph_id=str(getattr(report, "graph_id")),
        status=_status_value(getattr(report, "status", "unknown")),
        task_id=task_id,
        substrate_only=True,
        metadata=metadata,
    )
