"""Boundary for DecisionRisk risk graph operations over MiroFish graph services."""

from __future__ import annotations

from typing import Any

from .contracts import MiroFishGraphRef


class MiroFishGraphFacade:
    """Owns DecisionRisk access to MiroFish graph/world construction."""

    def __init__(
        self,
        project_manager: object | None = None,
        graph_builder_factory: object | None = None,
    ) -> None:
        self.project_manager = project_manager or self._default_project_manager()
        self.graph_builder_factory = graph_builder_factory or self._default_graph_builder_factory()

    @staticmethod
    def _default_project_manager() -> object:
        from ...models.project import ProjectManager

        return ProjectManager

    @staticmethod
    def _default_graph_builder_factory() -> object:
        from ...services.graph_builder import GraphBuilderService

        return GraphBuilderService

    def build_graph(
        self,
        project_id: str,
        risk_pack: str,
        evidence_bundle: dict[str, Any] | None = None,
    ) -> MiroFishGraphRef:
        """Start or reference MiroFish graph construction for a DecisionRisk case."""

        project = self.project_manager.get_project(project_id)
        if not project:
            raise ValueError(f"MiroFish project not found: {project_id}")

        if getattr(project, "graph_id", None):
            return MiroFishGraphRef(
                project_id=project_id,
                risk_pack=risk_pack,
                status="completed",
                graph_id=project.graph_id,
                graph_task_id=getattr(project, "graph_build_task_id", None),
                metadata={"substrate": "mirofish_graph"},
            )

        text = self.project_manager.get_extracted_text(project_id) or _extract_evidence_text(evidence_bundle)
        if not text:
            raise ValueError("MiroFish graph build requires extracted evidence text.")

        ontology = getattr(project, "ontology", None) or _extract_ontology(evidence_bundle)
        if not ontology:
            raise ValueError("MiroFish graph build requires ontology from the project or risk pack.")

        builder = self.graph_builder_factory()
        task_id = builder.build_graph_async(
            text=text,
            ontology=ontology,
            graph_name=getattr(project, "name", None) or f"DecisionRisk {project_id}",
            chunk_size=getattr(project, "chunk_size", 500),
            chunk_overlap=getattr(project, "chunk_overlap", 50),
        )

        project.status = "graph_building"
        project.graph_build_task_id = task_id
        self.project_manager.save_project(project)
        return MiroFishGraphRef(
            project_id=project_id,
            risk_pack=risk_pack,
            status="graph_building",
            graph_id=getattr(project, "graph_id", None),
            graph_task_id=task_id,
            metadata={"substrate": "mirofish_graph", "async": True},
        )

    def build_risk_graph(
        self,
        base_project_id: str,
        risk_pack: str,
        evidence_bundle: dict[str, Any] | None = None,
    ) -> MiroFishGraphRef:
        """Backward-compatible alias for earlier foundation naming."""

        return self.build_graph(base_project_id, risk_pack, evidence_bundle)


def _extract_evidence_text(source: dict[str, Any] | None) -> str:
    if not source:
        return ""
    text_parts: list[str] = []
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


def _extract_ontology(source: dict[str, Any] | None) -> dict[str, Any] | None:
    if not source:
        return None
    ontology = source.get("ontology") or source.get("risk_pack_ontology")
    if isinstance(ontology, dict):
        return ontology
    risk_pack = source.get("risk_pack")
    if isinstance(risk_pack, dict) and isinstance(risk_pack.get("ontology"), dict):
        return risk_pack["ontology"]
    return None
