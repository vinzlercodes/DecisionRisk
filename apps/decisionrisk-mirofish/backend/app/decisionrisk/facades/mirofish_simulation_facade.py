"""Boundary for DecisionRisk scenario ensemble operations over MiroFish simulations."""

from __future__ import annotations

import os
from typing import Any

from .contracts import (
    MiroFishGraphRef,
    MiroFishSimulationRef,
    MiroFishSimulationTrace,
    ScenarioRunRef,
)


class MiroFishSimulationFacade:
    """Owns DecisionRisk access to MiroFish simulation execution."""

    def __init__(
        self,
        simulation_manager_factory: object | None = None,
        simulation_runner: object | None = None,
        project_manager: object | None = None,
    ) -> None:
        self.simulation_manager_factory = simulation_manager_factory or self._default_simulation_manager
        self.simulation_runner = simulation_runner or self._default_simulation_runner()
        self.project_manager = project_manager or self._default_project_manager()

    @staticmethod
    def _default_simulation_manager() -> object:
        from ...services.simulation_manager import SimulationManager

        return SimulationManager()

    @staticmethod
    def _default_simulation_runner() -> object:
        from ...services.simulation_runner import SimulationRunner

        return SimulationRunner

    @staticmethod
    def _default_project_manager() -> object:
        from ...models.project import ProjectManager

        return ProjectManager

    def run_simulation(
        self,
        scenario_run_ref: ScenarioRunRef,
        graph_ref: MiroFishGraphRef | dict[str, Any] | None = None,
        scenario_config: dict[str, Any] | None = None,
    ) -> MiroFishSimulationRef:
        """Create and optionally start a MiroFish simulation for one scenario run."""

        scenario_config = scenario_config or {}
        graph_id = _graph_id(graph_ref) or scenario_config.get("graph_id")
        if not graph_id:
            raise ValueError("run_simulation requires a graph_id from graph_ref or scenario_config.")

        manager = self.simulation_manager_factory()
        state = manager.create_simulation(
            project_id=scenario_run_ref.clone_project_id,
            graph_id=graph_id,
            enable_twitter=scenario_config.get("enable_twitter", True),
            enable_reddit=scenario_config.get("enable_reddit", True),
        )

        if scenario_config.get("prepare"):
            project = self.project_manager.get_project(scenario_run_ref.clone_project_id)
            manager.prepare_simulation(
                simulation_id=state.simulation_id,
                simulation_requirement=scenario_config.get("simulation_requirement")
                or getattr(project, "simulation_requirement", ""),
                document_text=scenario_config.get("document_text")
                or self.project_manager.get_extracted_text(scenario_run_ref.clone_project_id)
                or "",
                defined_entity_types=scenario_config.get("defined_entity_types"),
                use_llm_for_profiles=scenario_config.get("use_llm_for_profiles", True),
                parallel_profile_count=scenario_config.get("parallel_profile_count", 3),
            )
            state = manager.get_simulation(state.simulation_id) or state

        runner_status = "not_started"
        if scenario_config.get("start_runner", True):
            run_state = self.simulation_runner.start_simulation(
                simulation_id=state.simulation_id,
                platform=scenario_config.get("platform", "parallel"),
                max_rounds=scenario_config.get("max_rounds"),
                enable_graph_memory_update=scenario_config.get("enable_graph_memory_update", False),
                graph_id=graph_id,
            )
            runner_status = _status_value(getattr(run_state, "runner_status", "started"))

        return MiroFishSimulationRef(
            simulation_id=state.simulation_id,
            run_id=scenario_run_ref.run_id,
            project_id=scenario_run_ref.clone_project_id,
            graph_id=str(graph_id),
            status=_status_value(getattr(state, "status", "created")),
            runner_status=runner_status,
            platform=scenario_config.get("platform", "parallel"),
            metadata={
                "case_id": scenario_run_ref.case_id,
                "option_id": scenario_run_ref.option_id,
                "scenario_id": scenario_run_ref.scenario_id,
                "seed": scenario_run_ref.seed,
                "substrate": "mirofish_simulation",
            },
        )

    def collect_simulation_trace(
        self,
        simulation_ref: MiroFishSimulationRef | str,
        limit: int | None = None,
    ) -> MiroFishSimulationTrace:
        """Collect persisted MiroFish run state and action logs as a trace."""

        simulation_id = simulation_ref if isinstance(simulation_ref, str) else simulation_ref.simulation_id
        run_id = simulation_id if isinstance(simulation_ref, str) else simulation_ref.run_id
        run_state = self.simulation_runner.get_run_state(simulation_id)
        actions = self.simulation_runner.get_all_actions(simulation_id)
        action_dicts = [_to_dict(action) for action in actions]
        if limit is not None:
            action_dicts = action_dicts[:limit]

        runner_status = _status_value(getattr(run_state, "runner_status", "unknown")) if run_state else "unknown"
        source_paths = _trace_source_paths(self.simulation_runner, simulation_id)
        return MiroFishSimulationTrace(
            simulation_id=simulation_id,
            run_id=run_id,
            status=runner_status,
            runner_status=runner_status,
            action_count=len(actions),
            actions=action_dicts,
            source_paths=source_paths,
            metadata={
                "substrate": "mirofish_simulation_trace",
                "trace_complete": runner_status == "completed",
            },
        )

    def run_scenario(
        self,
        scenario_run_ref: ScenarioRunRef,
        graph_ref: MiroFishGraphRef | dict[str, Any] | None = None,
        scenario_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible alias returning a plain dictionary."""

        return self.run_simulation(scenario_run_ref, graph_ref, scenario_config).to_dict()


def _graph_id(graph_ref: MiroFishGraphRef | dict[str, Any] | None) -> str | None:
    if isinstance(graph_ref, MiroFishGraphRef):
        return graph_ref.graph_id
    if isinstance(graph_ref, dict):
        return graph_ref.get("graph_id")
    return None


def _status_value(status: object) -> str:
    return str(getattr(status, "value", status))


def _to_dict(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    return dict(getattr(value, "__dict__", {}))


def _trace_source_paths(simulation_runner: object, simulation_id: str) -> dict[str, str]:
    root = getattr(simulation_runner, "RUN_STATE_DIR", "")
    if not root:
        return {}
    simulation_dir = os.path.join(root, simulation_id)
    return {
        "run_state": os.path.join(simulation_dir, "run_state.json"),
        "twitter_actions": os.path.join(simulation_dir, "twitter", "actions.jsonl"),
        "reddit_actions": os.path.join(simulation_dir, "reddit", "actions.jsonl"),
        "legacy_actions": os.path.join(simulation_dir, "actions.jsonl"),
    }
