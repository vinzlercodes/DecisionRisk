"""Boundary for DecisionRisk case/project operations over MiroFish projects."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .contracts import MiroFishProjectRef, ScenarioRunRef, stable_run_id


class MiroFishProjectFacade:
    """Owns DecisionRisk access to MiroFish project lifecycle behavior."""

    def __init__(self, project_manager: object | None = None) -> None:
        self.project_manager = project_manager or self._default_project_manager()

    @staticmethod
    def _default_project_manager() -> object:
        from ...models.project import ProjectManager

        return ProjectManager

    def create_base_project(
        self,
        decision_case: dict[str, Any],
        evidence_manifest: dict[str, Any] | None = None,
    ) -> MiroFishProjectRef:
        """Create a MiroFish project substrate for a DecisionCase.

        DecisionRisk stays in DecisionCase terms; the returned project reference is
        the explicit handoff into MiroFish execution state.
        """

        case_id = _required_text(decision_case, "case_id")
        simulation_requirement = (
            decision_case.get("decision_question")
            or decision_case.get("simulation_requirement")
            or decision_case.get("question")
        )
        if not simulation_requirement:
            raise ValueError("DecisionCase must include decision_question or simulation_requirement.")

        project = self.project_manager.create_project(
            name=decision_case.get("title") or f"DecisionRisk {case_id}"
        )
        project.simulation_requirement = str(simulation_requirement)

        ontology = _extract_ontology(decision_case, evidence_manifest)
        if ontology:
            project.ontology = ontology
            project.status = "ontology_generated"

        analysis_summary = decision_case.get("analysis_summary")
        if not analysis_summary and evidence_manifest:
            analysis_summary = evidence_manifest.get("analysis_summary")
        if analysis_summary:
            project.analysis_summary = str(analysis_summary)

        evidence_text = _extract_evidence_text(decision_case, evidence_manifest)
        if evidence_text:
            self.project_manager.save_extracted_text(project.project_id, evidence_text)
            project.total_text_length = len(evidence_text)

        evidence_files = _extract_evidence_files(decision_case, evidence_manifest)
        if evidence_files:
            project.files = evidence_files

        self.project_manager.save_project(project)
        return MiroFishProjectRef(
            project_id=project.project_id,
            case_id=case_id,
            name=project.name,
            status=_status_value(project.status),
            simulation_requirement=str(simulation_requirement),
            project_role="base",
            metadata={
                "risk_pack": decision_case.get("risk_pack"),
                "options_count": len(decision_case.get("options", [])),
                "evidence_items_count": len(decision_case.get("evidence_items", [])),
                "substrate": "mirofish_project",
            },
        )

    def clone_project_for_run(
        self,
        base_project_id: str,
        case_id: str,
        option_id: str,
        scenario_id: str,
        seed: int,
    ) -> ScenarioRunRef:
        """Create a lightweight per-scenario MiroFish project clone."""

        base_project = self.project_manager.get_project(base_project_id)
        if not base_project:
            raise ValueError(f"MiroFish base project not found: {base_project_id}")

        run_id = stable_run_id(option_id, scenario_id, seed)
        clone = self.project_manager.create_project(name=f"{base_project.name} / {run_id}")
        clone.status = base_project.status
        clone.files = deepcopy(getattr(base_project, "files", []))
        clone.total_text_length = getattr(base_project, "total_text_length", 0)
        clone.ontology = deepcopy(getattr(base_project, "ontology", None))
        clone.analysis_summary = getattr(base_project, "analysis_summary", None)
        clone.graph_id = getattr(base_project, "graph_id", None)
        clone.simulation_requirement = getattr(base_project, "simulation_requirement", None)
        clone.chunk_size = getattr(base_project, "chunk_size", 500)
        clone.chunk_overlap = getattr(base_project, "chunk_overlap", 50)
        self.project_manager.save_project(clone)

        text = self.project_manager.get_extracted_text(base_project_id)
        if text:
            self.project_manager.save_extracted_text(clone.project_id, text)

        return ScenarioRunRef(
            run_id=run_id,
            case_id=case_id,
            option_id=option_id,
            scenario_id=scenario_id,
            seed=seed,
            base_project_id=base_project_id,
            clone_project_id=clone.project_id,
            metadata={"substrate": "mirofish_project_clone"},
        )


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not value:
        raise ValueError(f"DecisionCase must include {key}.")
    return str(value)


def _status_value(status: object) -> str:
    return str(getattr(status, "value", status))


def _extract_ontology(*sources: dict[str, Any] | None) -> dict[str, Any] | None:
    for source in sources:
        if not source:
            continue
        ontology = source.get("ontology") or source.get("risk_pack_ontology")
        if isinstance(ontology, dict):
            return ontology
        risk_pack = source.get("risk_pack")
        if isinstance(risk_pack, dict) and isinstance(risk_pack.get("ontology"), dict):
            return risk_pack["ontology"]
    return None


def _extract_evidence_text(*sources: dict[str, Any] | None) -> str:
    text_parts: list[str] = []
    for source in sources:
        if not source:
            continue
        for key in ("combined_text", "evidence_text", "extracted_text", "document_text", "text"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())
        for item in source.get("evidence_items", []):
            if isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if isinstance(value, str) and value.strip():
                    text_parts.append(value.strip())
    return "\n\n".join(text_parts)


def _extract_evidence_files(
    decision_case: dict[str, Any],
    evidence_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for item in decision_case.get("evidence_items", []):
        if isinstance(item, str):
            files.append({"filename": item, "source": "decision_case"})
        elif isinstance(item, dict):
            filename = item.get("filename") or item.get("path") or item.get("uri")
            if filename:
                files.append({"filename": filename, "source": "decision_case"})
    if evidence_manifest:
        for item in evidence_manifest.get("evidence_items", []):
            if isinstance(item, dict):
                filename = item.get("filename") or item.get("path") or item.get("uri")
                if filename:
                    files.append({"filename": filename, "source": "evidence_manifest"})
    return files
