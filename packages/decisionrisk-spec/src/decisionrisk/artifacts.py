from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ArtifactMap = dict[str, dict[str, str]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_case(case_path: Path) -> dict[str, Any]:
    text = case_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{case_path} must be JSON-compatible YAML for the MVP replay CLI."
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"{case_path} must contain a mapping.")
    return data


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}


class ArtifactStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_json_artifact(self, name: str, data: Any) -> ArtifactRef:
        path = self.output_dir / f"{name}.json"
        write_json(path, data)
        return self.ref(path)

    def write_text_artifact(self, filename: str, text: str) -> ArtifactRef:
        path = self.output_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return self.ref(path)

    def copy_input(self, source: Path, filename: str | None = None) -> ArtifactRef:
        target = self.output_dir / "inputs" / (filename or source.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return self.ref(target)

    def ref(self, path: Path) -> ArtifactRef:
        return ArtifactRef(path=path.relative_to(self.output_dir).as_posix(), sha256=sha256_file(path))

    def resolve(self, ref: dict[str, str]) -> Path:
        path = self.output_dir / ref["path"]
        resolved = path.resolve()
        root = self.output_dir.resolve()
        if root not in resolved.parents and resolved != root:
            raise ValueError(f"Artifact path escapes output directory: {ref['path']}")
        return path


def collect_claim_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if {"claim_id", "status", "text"}.issubset(value.keys()):
            refs.append(value)
        for child in value.values():
            refs.extend(collect_claim_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(collect_claim_refs(child))
    return refs


def artifact_paths(manifest: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for section in ("inputs", "artifacts"):
        entries = manifest.get(section, {})
        if not isinstance(entries, dict):
            continue
        for ref in entries.values():
            if isinstance(ref, dict) and "path" in ref and "sha256" in ref:
                refs.append(ref)
    return refs
