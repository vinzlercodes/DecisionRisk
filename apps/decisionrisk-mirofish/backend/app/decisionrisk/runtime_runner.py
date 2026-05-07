"""Runtime execution entrypoints for DecisionRisk backend runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .facades.mirofish_artifact_facade import MiroFishArtifactFacade
from .facades.mirofish_graph_facade import MiroFishGraphFacade
from .facades.mirofish_project_facade import MiroFishProjectFacade
from .facades.mirofish_report_facade import MiroFishReportFacade
from .facades.mirofish_simulation_facade import MiroFishSimulationFacade
from .runtime_modes import assert_runtime_mode_available, parse_runtime_mode

from decisionrisk import __version__
from decisionrisk.artifacts import ArtifactStore, read_json, write_json
from decisionrisk.cli import validate_output_dir
from decisionrisk.fixtures import artifact_payloads, risk_docket_markdown
from decisionrisk.safety import assess_case


class DecisionRiskRuntimeRunner:
    def __init__(
        self,
        outputs_root: Path,
        project_facade: MiroFishProjectFacade | None = None,
        graph_facade: MiroFishGraphFacade | None = None,
        simulation_facade: MiroFishSimulationFacade | None = None,
        report_facade: MiroFishReportFacade | None = None,
        artifact_facade: MiroFishArtifactFacade | None = None,
    ) -> None:
        self.outputs_root = outputs_root
        self._project_facade = project_facade
        self._graph_facade = graph_facade
        self._simulation_facade = simulation_facade
        self._report_facade = report_facade
        self._artifact_facade = artifact_facade

    @property
    def project_facade(self) -> MiroFishProjectFacade:
        if self._project_facade is None:
            self._project_facade = MiroFishProjectFacade()
        return self._project_facade

    @property
    def graph_facade(self) -> MiroFishGraphFacade:
        if self._graph_facade is None:
            self._graph_facade = MiroFishGraphFacade()
        return self._graph_facade

    @property
    def simulation_facade(self) -> MiroFishSimulationFacade:
        if self._simulation_facade is None:
            self._simulation_facade = MiroFishSimulationFacade()
        return self._simulation_facade

    @property
    def report_facade(self) -> MiroFishReportFacade:
        if self._report_facade is None:
            self._report_facade = MiroFishReportFacade()
        return self._report_facade

    @property
    def artifact_facade(self) -> MiroFishArtifactFacade:
        if self._artifact_facade is None:
            self._artifact_facade = MiroFishArtifactFacade()
        return self._artifact_facade

    def run(self, decision_case: dict[str, Any], mode: str) -> dict[str, Any]:
        mode = parse_runtime_mode(mode)
        assessment = assess_case(decision_case)
        if not assessment.allowed:
            raise RuntimePreflightError(assessment.reason or "DecisionCase failed safety assessment.")
        try:
            assert_runtime_mode_available(mode)
        except RuntimeError as exc:
            raise RuntimePreflightError(str(exc)) from exc

        if mode in {"replay", "eval"}:
            output_dir = self._write_canonical_artifacts(decision_case, mode)
        elif mode == "live_smoke":
            output_dir = self._run_live_smoke(decision_case)
        else:
            raise RuntimeNotImplementedError(
                "live_full requires the live Verdict Council pipeline from issue #8 and is not downgraded to replay."
            )

        errors = validate_output_dir(output_dir)
        if errors:
            raise RuntimeValidationError(errors)
        manifest = read_json(output_dir / "run_manifest.json")
        return {
            "case_id": manifest["case_id"],
            "mode": manifest["mode"],
            "manifest_path": str(output_dir / "run_manifest.json"),
            "final_artifacts": {
                "verdict": manifest["artifacts"].get("verdict"),
                "risk_docket": manifest["artifacts"].get("risk_docket"),
            },
        }

    def _run_live_smoke(self, decision_case: dict[str, Any]) -> Path:
        payloads = artifact_payloads(decision_case)
        evidence_manifest = payloads["evidence_manifest"]
        base_project = self.project_facade.create_base_project(decision_case, evidence_manifest)
        graph_ref = self.graph_facade.build_graph(
            base_project.project_id,
            str(decision_case.get("risk_pack", "")),
            evidence_manifest,
        )
        if not graph_ref.graph_id:
            raise RuntimeNotImplementedError(
                "live_smoke graph construction was queued; issue #7 will add asynchronous resume/publish handling."
            )

        scenario_run = self.project_facade.clone_project_for_run(
            base_project.project_id,
            str(decision_case["case_id"]),
            str(decision_case.get("options", [{"option_id": "option"}])[0]["option_id"]),
            "live_smoke",
            1,
        )
        simulation_ref = self.simulation_facade.run_simulation(
            scenario_run,
            graph_ref,
            {
                "platform": "parallel",
                "max_rounds": 1,
                "prepare": False,
                "start_runner": False,
            },
        )
        trace = self.simulation_facade.collect_simulation_trace(simulation_ref, limit=50)
        report_ref = self.report_facade.generate_mirofish_report(
            base_project.project_id,
            [simulation_ref],
        )

        output_dir = self._write_canonical_artifacts(
            decision_case,
            "live_smoke",
            mirofish_ref=base_project.project_id,
        )
        store = ArtifactStore(output_dir)
        live_scenario_runs = {
            "expected_runs": 1,
            "runs": [
                {
                    "run_id": scenario_run.run_id,
                    "option_id": scenario_run.option_id,
                    "scenario_id": scenario_run.scenario_id,
                    "seed": scenario_run.seed,
                    "mode": "live_smoke",
                    "clone_project_id": scenario_run.clone_project_id,
                    "simulation_id": simulation_ref.simulation_id,
                    "graph_mode": "live_smoke_reduced",
                    "status": simulation_ref.status,
                    "runner_status": simulation_ref.runner_status,
                    "claim_refs": [],
                }
            ],
        }
        live_metrics = payloads["simulation_metrics"]
        live_metrics["metric_authority"] = "live_smoke_reduced_mirofish_trace_with_fixture_scores"
        live_metrics["ensemble"] = {
            **live_metrics["ensemble"],
            "runs": 1,
            "scenario_dispersion": 0.0,
        }
        substrate_refs = self.artifact_facade.write_mirofish_report_artifact(
            report_ref,
            output_dir,
            traces=[trace.to_dict()],
            graph=graph_ref.to_dict(),
        )
        manifest_path = output_dir / "run_manifest.json"
        manifest = read_json(manifest_path)
        manifest["artifacts"]["scenario_runs"] = store.write_json_artifact("scenario_runs", live_scenario_runs).as_dict()
        manifest["artifacts"]["simulation_metrics"] = store.write_json_artifact("simulation_metrics", live_metrics).as_dict()
        for name, ref in substrate_refs.items():
            manifest["artifacts"][name] = ref.as_manifest_ref()
        manifest["live_runtime"] = {
            "base_project": base_project.to_dict(),
            "graph": graph_ref.to_dict(),
            "smoke_run": scenario_run.to_dict(),
            "simulation": simulation_ref.to_dict(),
            "report": report_ref.to_dict(),
            "substrate_only_final_block": True,
        }
        write_json(manifest_path, manifest)
        return output_dir

    def _write_canonical_artifacts(
        self,
        decision_case: dict[str, Any],
        mode: str,
        mirofish_ref: str = "not_used_clean_spec_runtime",
    ) -> Path:
        output_dir = self.outputs_root / str(decision_case["case_id"])
        store = ArtifactStore(output_dir)
        case_path = output_dir / "inputs" / "case.json"
        case_path.parent.mkdir(parents=True, exist_ok=True)
        case_path.write_text(json.dumps(decision_case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        input_refs = {"case_json": store.ref(case_path).as_dict()}

        artifact_refs: dict[str, dict[str, str]] = {}
        payloads = artifact_payloads(decision_case)
        for name, payload in payloads.items():
            artifact_refs[name] = store.write_json_artifact(name, payload).as_dict()
        artifact_refs["risk_docket"] = store.write_text_artifact("risk_docket.md", risk_docket_markdown()).as_dict()
        input_refs["evidence_manifest"] = artifact_refs["evidence_manifest"]
        input_refs["scenario_design"] = artifact_refs["scenario_design"]

        manifest = {
            "case_id": decision_case["case_id"],
            "risk_pack": decision_case["risk_pack"],
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decisionrisk_version": __version__,
            "mirofish_ref": mirofish_ref,
            "inputs": input_refs,
            "artifacts": artifact_refs,
        }
        write_json(output_dir / "run_manifest.json", manifest)
        return output_dir


class RuntimePreflightError(RuntimeError):
    pass


class RuntimeNotImplementedError(RuntimeError):
    pass


class RuntimeValidationError(RuntimeError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("DecisionRisk run failed validation.")
        self.errors = errors
