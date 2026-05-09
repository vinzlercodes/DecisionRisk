"""Normalize raw MiroFish outputs into DecisionRisk artifact files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from decisionrisk.report_substrate import normalize_report_to_claims

from .contracts import MiroFishArtifactRef, MiroFishReportRef


class MiroFishArtifactFacade:
    """Writes manifest-ready substrate artifacts from MiroFish outputs."""

    def __init__(self, report_manager: object | None = None) -> None:
        self.report_manager = report_manager

    def write_mirofish_report_artifact(
        self,
        report: MiroFishReportRef | dict[str, Any] | object,
        output_dir: str | Path,
        traces: list[dict[str, Any]] | None = None,
        graph: dict[str, Any] | None = None,
    ) -> dict[str, MiroFishArtifactRef]:
        """Write raw report substrate and normalized claims with SHA-256 refs."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        report_payload = self._report_payload(report)
        markdown = report_payload.get("markdown_content", "")
        if not isinstance(markdown, str):
            markdown = ""

        report_md_path = output_path / "mirofish_report.md"
        report_json_path = output_path / "mirofish_report.json"
        claims_path = output_path / "mirofish_report_claims.json"

        report_md_path.write_text(markdown, encoding="utf-8")
        _write_json(report_json_path, report_payload)
        _write_json(
            claims_path,
            self.normalize_mirofish_report_to_claims(report_payload, traces=traces, graph=graph),
        )

        return {
            "mirofish_report_markdown": _artifact_ref(
                "mirofish_report_markdown",
                report_md_path,
                output_path,
                "text/markdown",
            ),
            "mirofish_report": _artifact_ref(
                "mirofish_report",
                report_json_path,
                output_path,
                "application/json",
            ),
            "mirofish_report_claims": _artifact_ref(
                "mirofish_report_claims",
                claims_path,
                output_path,
                "application/json",
            ),
        }

    def normalize_mirofish_report_to_claims(
        self,
        report: MiroFishReportRef | dict[str, Any] | object,
        traces: list[dict[str, Any]] | None = None,
        graph: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert report text into conservative ClaimRef-shaped records."""

        return normalize_report_to_claims(self._report_payload(report), traces=traces, graph=graph)

    def _report_payload(self, report: MiroFishReportRef | dict[str, Any] | object) -> dict[str, Any]:
        if isinstance(report, MiroFishReportRef):
            loaded = self._load_report(report.report_id)
            if loaded:
                return loaded
            payload = report.to_dict()
            payload["markdown_content"] = ""
            return payload
        if isinstance(report, dict):
            return dict(report)
        if hasattr(report, "to_dict"):
            return report.to_dict()
        return dict(getattr(report, "__dict__", {}))

    def _load_report(self, report_id: str) -> dict[str, Any] | None:
        if not self.report_manager:
            return None
        report = self.report_manager.get_report(report_id)
        if not report:
            return None
        if hasattr(report, "to_dict"):
            return report.to_dict()
        return dict(getattr(report, "__dict__", {}))

def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_ref(
    name: str,
    path: Path,
    output_dir: Path,
    content_type: str,
) -> MiroFishArtifactRef:
    return MiroFishArtifactRef(
        artifact_name=name,
        path=path.relative_to(output_dir).as_posix(),
        sha256=_sha256_file(path),
        content_type=content_type,
        substrate_only=True,
        metadata={"substrate": "mirofish_report"},
    )
