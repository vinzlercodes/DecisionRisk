"""Typed handoff contracts between DecisionRisk and MiroFish internals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class MiroFishProjectRef:
    """Manifest-ready reference to a MiroFish project substrate."""

    project_id: str
    case_id: str
    name: str
    status: str
    simulation_requirement: str
    project_role: str = "base"
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "project_id": self.project_id,
            "case_id": self.case_id,
            "name": self.name,
            "status": self.status,
            "simulation_requirement": self.simulation_requirement,
            "project_role": self.project_role,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ScenarioRunRef:
    """Reference for one option x scenario x seed MiroFish run."""

    run_id: str
    case_id: str
    option_id: str
    scenario_id: str
    seed: int
    base_project_id: str
    clone_project_id: str
    status: str = "created"
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "option_id": self.option_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "base_project_id": self.base_project_id,
            "clone_project_id": self.clone_project_id,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class MiroFishGraphRef:
    """Reference to a graph/world build started or completed by MiroFish."""

    project_id: str
    risk_pack: str
    status: str
    graph_id: str | None = None
    graph_task_id: str | None = None
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "project_id": self.project_id,
            "risk_pack": self.risk_pack,
            "status": self.status,
            "graph_id": self.graph_id,
            "graph_task_id": self.graph_task_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class MiroFishSimulationRef:
    """Reference to a MiroFish simulation run."""

    simulation_id: str
    run_id: str
    project_id: str
    graph_id: str
    status: str
    runner_status: str
    platform: str = "parallel"
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "simulation_id": self.simulation_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status,
            "runner_status": self.runner_status,
            "platform": self.platform,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class MiroFishSimulationTrace:
    """Structured trace collected from persisted MiroFish simulation state."""

    simulation_id: str
    run_id: str
    status: str
    runner_status: str
    action_count: int
    actions: list[JsonDict]
    source_paths: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "simulation_id": self.simulation_id,
            "run_id": self.run_id,
            "status": self.status,
            "runner_status": self.runner_status,
            "action_count": self.action_count,
            "actions": self.actions,
            "source_paths": self.source_paths,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class MiroFishReportRef:
    """Reference to raw MiroFish report substrate, not a final verdict."""

    report_id: str
    simulation_id: str
    graph_id: str
    status: str
    task_id: str | None = None
    substrate_only: bool = True
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "status": self.status,
            "task_id": self.task_id,
            "substrate_only": self.substrate_only,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class MiroFishArtifactRef:
    """File artifact reference compatible with run_manifest.json entries."""

    artifact_name: str
    path: str
    sha256: str
    content_type: str
    substrate_only: bool = True
    metadata: JsonDict = field(default_factory=dict)

    def as_manifest_ref(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}

    def to_dict(self) -> JsonDict:
        return {
            "artifact_name": self.artifact_name,
            "path": self.path,
            "sha256": self.sha256,
            "content_type": self.content_type,
            "substrate_only": self.substrate_only,
            "metadata": self.metadata,
        }


def stable_run_id(option_id: str, scenario_id: str, seed: int) -> str:
    """Return the stable run identifier used across facade handoffs."""

    return f"{option_id}_{scenario_id}_seed_{seed}"
