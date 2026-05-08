from __future__ import annotations

import argparse
import json
import sys
import filecmp
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .artifacts import ArtifactStore, artifact_paths, collect_claim_refs, load_case, read_json, sha256_file, write_json
from .council import ClaimRefAuditor, VerdictCouncilRunner
from .fixtures import artifact_payloads
from .runtime_modes import CANONICAL_RUNTIME_MODES, assert_runtime_mode_available, parse_runtime_mode
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

COUNCIL_OUTPUT_ARTIFACTS = {"council_rounds", "verdict"}


def run_case(args: argparse.Namespace) -> int:
    case_path = Path(args.case_yaml)
    case = load_case(case_path)
    assessment = assess_case(case)
    if not assessment.allowed:
        print(f"blocked: {assessment.reason}", file=sys.stderr)
        return 2

    try:
        mode = parse_runtime_mode(args.mode)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        assert_runtime_mode_available(mode)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if mode in {"live_smoke", "live_full"}:
        print(
            f"{mode} is a MiroFish backend runtime mode; use POST /api/decisionrisk/runs for live execution.",
            file=sys.stderr,
        )
        return 2

    output_dir = write_replay_shaped_run(case_path=case_path, case=case, mode=mode, output_dir_arg=args.output_dir)
    if mode == "eval":
        errors = validate_output_dir(output_dir)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        if args.golden_dir:
            diff_errors = compare_golden_outputs(output_dir, Path(args.golden_dir))
            if diff_errors:
                for error in diff_errors:
                    print(f"error: {error}", file=sys.stderr)
                return 1
    print(output_dir / "run_manifest.json")
    return 0


def write_replay_shaped_run(
    case_path: Path,
    case: dict[str, Any],
    mode: str,
    output_dir_arg: str | None = None,
) -> Path:
    output_dir = Path(output_dir_arg or Path("outputs") / case["case_id"])
    store = ArtifactStore(output_dir)
    input_refs = {
        "case_yaml": store.copy_input(case_path).as_dict(),
    }

    artifact_refs: dict[str, dict[str, str]] = {}
    payloads = artifact_payloads(case)
    council_inputs = {name: payload for name, payload in payloads.items() if name not in COUNCIL_OUTPUT_ARTIFACTS}
    for name, payload in council_inputs.items():
        artifact_refs[name] = store.write_json_artifact(name, payload).as_dict()

    council_outputs = VerdictCouncilRunner().run(council_inputs, mode=mode)
    artifact_refs["council_rounds"] = store.write_json_artifact(
        "council_rounds",
        council_outputs["council_rounds"],
    ).as_dict()
    artifact_refs["verdict"] = store.write_json_artifact("verdict", council_outputs["verdict"]).as_dict()
    artifact_refs["risk_docket"] = store.write_text_artifact("risk_docket.md", council_outputs["risk_docket"]).as_dict()
    input_refs["evidence_manifest"] = artifact_refs["evidence_manifest"]
    input_refs["scenario_design"] = artifact_refs["scenario_design"]

    manifest = {
        "case_id": case["case_id"],
        "risk_pack": case["risk_pack"],
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decisionrisk_version": __version__,
        "mirofish_ref": "not_used_clean_spec_runtime",
        "inputs": input_refs,
        "artifacts": artifact_refs,
    }
    write_json(output_dir / "run_manifest.json", manifest)
    return output_dir


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

    errors = validate_output_dir(output_dir, expected_mode=args.mode)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"validated: {output_dir}")
    return 0


def validate_output_dir(output_dir: Path, expected_mode: str | None = None) -> list[str]:
    errors: list[str] = []
    manifest_path = output_dir / "run_manifest.json"
    if not manifest_path.exists():
        return [f"missing root artifact: {manifest_path}"]
    manifest = read_json(manifest_path)
    status_path = output_dir / "run_status.json"
    if status_path.exists():
        run_status = read_json(status_path)
        if run_status.get("status") in {"partially_failed", "failed", "cancelled"}:
            errors.append(f"run_status.json marks output non-final: {run_status.get('status')}")

    for key in ("case_id", "risk_pack", "mode", "created_at", "decisionrisk_version", "mirofish_ref", "inputs", "artifacts"):
        if key not in manifest:
            errors.append(f"run_manifest.json missing {key}")

    mode = manifest.get("mode")
    try:
        parse_runtime_mode(str(mode))
    except ValueError:
        errors.append(f"run_manifest.json has unsupported mode: {mode}")
    if expected_mode and mode != expected_mode:
        errors.append(f"run_manifest.json mode {mode} does not match requested mode {expected_mode}")

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
        auditor = ClaimRefAuditor()
        supported = [claim_index.get(ref) for ref in refs if auditor.primary_rationale_eligible(claim_index.get(ref, {}))]
        if not supported:
            errors.append("verdict.primary_rationale lacks a non-unsupported ClaimRef")
        if verdict.get("final_verdict") not in {"RECOMMEND", "DEFER", "NO_GO"}:
            errors.append("verdict.final_verdict is not allowed")

    if any(name.startswith("mirofish_report") for name in artifacts):
        missing_council = {"council_rounds", "verdict", "risk_docket"} - set(artifacts)
        if missing_council:
            errors.append(f"MiroFish report substrate is not final without council artifacts: {sorted(missing_council)}")

    scenario_ref = artifacts.get("scenario_runs")
    if scenario_ref:
        scenario_runs = read_json(store.resolve(scenario_ref))
        runs = scenario_runs.get("runs", [])
        expected_runs = scenario_runs.get("expected_runs")
        if isinstance(expected_runs, int):
            if len(runs) != expected_runs:
                errors.append(f"scenario_runs must contain expected_runs entries: {expected_runs}")
            if mode == "replay" and expected_runs != 36:
                errors.append("replay scenario_runs must declare expected_runs=36")
        elif mode == "replay" and len(runs) != 36:
            errors.append("replay scenario_runs must contain 36 runs")

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


def compare_golden_outputs(output_dir: Path, golden_dir: Path) -> list[str]:
    if not golden_dir.exists():
        return [f"golden output directory does not exist: {golden_dir}"]
    errors: list[str] = []
    generated_manifest = read_json(output_dir / "run_manifest.json")
    golden_manifest = read_json(golden_dir / "run_manifest.json")
    generated_artifacts = generated_manifest.get("artifacts", {})
    golden_artifacts = golden_manifest.get("artifacts", {})
    missing = set(golden_artifacts) - set(generated_artifacts)
    extra = set(generated_artifacts) - set(golden_artifacts)
    if missing:
        errors.append(f"eval output missing golden artifacts: {sorted(missing)}")
    if extra:
        errors.append(f"eval output has extra artifacts not in golden: {sorted(extra)}")
    for name in sorted(set(generated_artifacts) & set(golden_artifacts)):
        generated_path = output_dir / generated_artifacts[name]["path"]
        golden_path = golden_dir / golden_artifacts[name]["path"]
        if not golden_path.exists():
            errors.append(f"golden artifact file missing: {golden_artifacts[name]['path']}")
            continue
        if not filecmp.cmp(generated_path, golden_path, shallow=False):
            errors.append(f"eval artifact differs from golden: {name}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decisionrisk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("case_yaml")
    run_parser.add_argument("--mode", default="replay", choices=CANONICAL_RUNTIME_MODES)
    run_parser.add_argument("--output-dir")
    run_parser.add_argument("--golden-dir")
    run_parser.set_defaults(func=run_case)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("case_dir")
    validate_parser.add_argument("--mode", choices=CANONICAL_RUNTIME_MODES)
    validate_parser.add_argument("--scorecard")
    validate_parser.add_argument("--output-dir")
    validate_parser.set_defaults(func=validate_case)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
