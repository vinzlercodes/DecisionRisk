"""Boundary for DecisionRisk case/project operations over MiroFish projects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioRunRef:
    run_id: str
    case_id: str
    option_id: str
    scenario_id: str
    seed: int
    clone_project_id: str


class MiroFishProjectFacade:
    """Owns DecisionRisk access to MiroFish project lifecycle behavior."""

    def create_base_project(self, case: dict) -> str:
        raise NotImplementedError("Live MiroFish project creation is post-foundation work.")

    def clone_project_for_run(self, base_project_id: str, case_id: str, option_id: str, scenario_id: str, seed: int) -> ScenarioRunRef:
        run_id = f"{option_id}_{scenario_id}_seed_{seed}"
        return ScenarioRunRef(
            run_id=run_id,
            case_id=case_id,
            option_id=option_id,
            scenario_id=scenario_id,
            seed=seed,
            clone_project_id=f"mf_proj_{case_id}_{run_id}",
        )
