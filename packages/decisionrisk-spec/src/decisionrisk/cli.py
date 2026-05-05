from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .artifacts import ArtifactStore, artifact_paths, collect_claim_refs, load_case, read_json, sha256_file, write_json
from .fixtures import artifact_payloads, risk_docket_markdown
from .safety import assess_case


REQUIRED_ARTIFACTS = {
    "decision_case",
    "grounding_report",
    "risk_graph",
    "scenario_runs",
    "simulation_metrics",
    "council_rounds",
    "verdict",
    "risk_docket",
}

REQUIRED_DOCKET_SECTIONS = [
    "Executive Verdict",
    "Decision Context",
    "Evidence Base",
    "Scenario Ensemble",
    "Metrics",
    "Council Debate",
    "Strongest Dissent",
    "Mitigation Plan",
    "Monitoring Plan",
    "Audit Trail",
]


def run_case(args: argparse.Namespace) -> int:
    case_path = Path(args.case_yaml)
    case = load_case(case_path)
    assessment = assess_case(case)
    if not assessment.allowed:
        print(f"blocked: {assessment.reason}", file=sys.stderr)
        return 2

    if args.mode not in {"replay", "live", "record"}:
        print(f"unsupported mode: {args.mode}", file=sys.stderr)
        return 2
    if args.mode != "replay":
        print("live and record modes are planned but not implemented in this foundation build.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir or Path("outputs") / case["case_id"])
    store = ArtifactStore(output_dir)
    input_refs = {
        "case_yaml": store.copy_input(case_path).as_dict(),
    }

    artifact_refs: dict[str, dict[str, str]] = {}
    payloads = artifact_payloads(case)
    for name, payload in payloads.items():
        artifact_refs[name] = store.write_json_artifact(name, payload).as_dict()

    artifact_refs["risk_docket"] = store.write_text_artifact("risk_docket.md", risk_docket_markdown()).as_dict()
    input_refs["evidence_manifest"] = artifact_refs["evidence_manifest"]
    input_refs["scenario_design"] = artifact_refs["scenario_design"]

    manifest = {
        "case_id": case["case_id"],
        "risk_pack": case["risk_pack"],
        "mode": args.mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decisionrisk_version": __version__,
        "mirofish_ref": "not_imported_foundation_build",
        "inputs": input_refs,
        "artifacts": artifact_refs,
    }
    write_json(output_dir / "run_manifest.json", manifest)
    print(output_dir / "run_manifest.json")
    return 0


def validate_case(args: argparse.Namespace) -> int:
    case_dir = Path(args.case_dir)
    case_path = case_dir / "case.yaml"
    if case_path.exists():
        try:
            case = load_case(case_path)
        except ValueError as exc:
            print(f"invalid case: {exc}", file=sys.stderr)
            return 1
        assessment = assess_case(case)
        if not assessment.allowed:
            print(f"blocked: {assessment.reason}")
            return 0
        output_dir = Path(args.output_dir or Path("outputs") / case["case_id"])
    else:
        output_dir = case_dir

    errors = validate_output_dir(output_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"validated: {output_dir}")
    return 0


def validate_output_dir(output_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = output_dir / "run_manifest.json"
    if not manifest_path.exists():
        return [f"missing root artifact: {manifest_path}"]
    manifest = read_json(manifest_path)

    for key in ("case_id", "risk_pack", "mode", "created_at", "decisionrisk_version", "mirofish_ref", "inputs", "artifacts"):
        if key not in manifest:
            errors.append(f"run_manifest.json missing {key}")

    artifacts = manifest.get("artifacts", {})
    missing = REQUIRED_ARTIFACTS - set(artifacts.keys())
    if missing:
        errors.append(f"run_manifest.json missing artifacts: {sorted(missing)}")

    store = ArtifactStore(output_dir)
    for ref in artifact_paths(manifest):
        try:
            path = store.resolve(ref)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.exists():
            errors.append(f"missing artifact file: {ref['path']}")
            continue
        actual = sha256_file(path)
        if actual != ref["sha256"]:
            errors.append(f"sha256 mismatch for {ref['path']}")

    claim_index: dict[str, dict[str, Any]] = {}
    for name, ref in artifacts.items():
        path = store.resolve(ref)
        if not path.exists() or path.suffix not in {".json"}:
            continue
        data = read_json(path)
        for claim_ref in collect_claim_refs(data):
            claim_index[claim_ref["claim_id"]] = claim_ref

    verdict_ref = artifacts.get("verdict")
    if verdict_ref:
        verdict = read_json(store.resolve(verdict_ref))
        refs = verdict.get("primary_rationale_claim_refs", [])
        if not refs:
            errors.append("verdict.primary_rationale has no ClaimRef references")
        supported = [claim_index.get(ref) for ref in refs if claim_index.get(ref, {}).get("status") != "unsupported_assumption"]
        if not supported:
            errors.append("verdict.primary_rationale lacks a non-unsupported ClaimRef")
        if verdict.get("final_verdict") not in {"RECOMMEND", "DEFER", "NO_GO"}:
            errors.append("verdict.final_verdict is not allowed")

    scenario_ref = artifacts.get("scenario_runs")
    if scenario_ref:
        scenario_runs = read_json(store.resolve(scenario_ref))
        if len(scenario_runs.get("runs", [])) != 36:
            errors.append("scenario_runs must contain 36 replay runs")

    docket_ref = artifacts.get("risk_docket")
    if docket_ref:
        docket = store.resolve(docket_ref).read_text(encoding="utf-8")
        for section in REQUIRED_DOCKET_SECTIONS:
            if f"## {section}" not in docket:
                errors.append(f"risk_docket missing section: {section}")
        if "DecisionRisk is experimental decision-support software" not in docket:
            errors.append("risk_docket missing responsible-use notice")
        for line in docket.splitlines():
            if line.startswith("Recommendation:") and "claim_" not in line:
                errors.append("material docket recommendation lacks ClaimRef")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decisionrisk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("case_yaml")
    run_parser.add_argument("--mode", default="replay", choices=["replay", "live", "record"])
    run_parser.add_argument("--output-dir")
    run_parser.set_defaults(func=run_case)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("case_dir")
    validate_parser.add_argument("--mode", default="replay")
    validate_parser.add_argument("--scorecard")
    validate_parser.add_argument("--output-dir")
    validate_parser.set_defaults(func=validate_case)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
