# DecisionRisk Demo Guide

This guide demonstrates the capabilities currently implemented in DecisionRisk:

- Deterministic LaunchRisk replay for `ai_memory_launch`.
- Root `run_manifest.json` artifact indexing with SHA-256 hashes.
- ClaimRef provenance enforcement for verdict rationale.
- Safety gates for prompt-only, no-evidence, political persuasion, stock-advice, and prompt-injection fixtures.
- Read-only DecisionRisk artifact APIs and Vue routes inside the MiroFish app.
- Live MiroFish handoff facades for project, graph, simulation, report, and substrate artifact refs.

Live runtime orchestration is not implemented yet. The demo uses replay artifacts, while the issue #5 facade surface now gives later live modes a typed boundary into MiroFish internals.

## Prerequisites

From the repository root:

```bash
pwd
```

Expected location:

```txt
/Users/vin/Documents/Agent Projects/DecisionRisk
```

Use Python 3.11 or newer. The current replay demo uses only the Python standard library.

## 1. Generate the Replay Artifacts

Run:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay
```

Expected output:

```txt
outputs/ai_memory_launch/run_manifest.json
```

This generates the current demo artifact set:

```txt
outputs/ai_memory_launch/
  run_manifest.json
  decision_case.json
  evidence_manifest.json
  grounding_report.json
  risk_graph.json
  scenario_design.json
  scenario_runs.json
  simulation_metrics.json
  council_rounds.json
  verdict.json
  risk_docket.md
  inputs/case.yaml
```

## 2. Inspect the Root Manifest

Open:

```bash
sed -n '1,220p' outputs/ai_memory_launch/run_manifest.json
```

What to point out:

- `run_manifest.json` is the root artifact.
- Every input and output has a `path`.
- Every input and output has a `sha256`.
- `mirofish_ref` is currently `not_imported_foundation_build` for replay mode.
- Files, not runtime task state, are the source of truth for replay validation.

## 3. Validate the Artifact Contract

Run:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch
```

Expected output:

```txt
validated: outputs/ai_memory_launch
```

The validator checks:

- The root manifest exists.
- Required artifacts are present.
- Artifact hashes match the manifest.
- `scenario_runs.json` contains 36 replay runs.
- `verdict.final_verdict` is one of `RECOMMEND`, `DEFER`, or `NO_GO`.
- `verdict.primary_rationale` has at least one non-unsupported ClaimRef.
- `risk_docket.md` contains required report sections and the responsible-use notice.

## 4. Inspect ClaimRef Provenance

Open the verdict:

```bash
sed -n '1,220p' outputs/ai_memory_launch/verdict.json
```

Then open the grounding report:

```bash
sed -n '1,260p' outputs/ai_memory_launch/grounding_report.json
```

What to point out:

- `primary_rationale_claim_refs` links the verdict rationale to claim IDs.
- Claims include `status`, `source_refs`, `confidence`, and `used_in`.
- Unsupported assumptions are allowed, but they cannot be the sole support for the verdict.

Key example:

```txt
claim_0001: Users may perceive persistent memory as surveillance-like if enabled by default.
claim_0002: Opt-in launch reduces consent friction while slowing early adoption.
claim_0004: Clear deletion controls and temporary-use mode are plausible mitigations.
```

## 5. Inspect the 36-Run Scenario Ensemble

Run:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 - <<'PY'
import json
from pathlib import Path
runs = json.loads(Path("outputs/ai_memory_launch/scenario_runs.json").read_text())
print("expected_runs:", runs["expected_runs"])
print("actual_runs:", len(runs["runs"]))
print("first_run:", runs["runs"][0])
PY
```

Expected:

```txt
expected_runs: 36
actual_runs: 36
```

What to point out:

- Replay mode models `3 options x 4 scenarios x 3 seeds`.
- Each run has an option, scenario, seed, clone project ID, simulation ID, graph mode, status, and ClaimRef links.
- This is the replay artifact shape that live MiroFish runs will later populate.

## 6. Inspect Metrics and the Recommendation

Open:

```bash
sed -n '1,240p' outputs/ai_memory_launch/simulation_metrics.json
```

What to point out:

- Metrics are deterministic scores over structured signals.
- The current demo compares:
  - `default_on`
  - `opt_in_beta`
  - `enterprise_only`
- `opt_in_beta` has the lowest overall risk score in the replay fixture.

Open:

```bash
sed -n '1,220p' outputs/ai_memory_launch/risk_docket.md
```

What to point out:

- The Risk Docket is board-style Markdown.
- It includes the responsible-use boundary.
- The executive recommendation cites ClaimRefs.
- It preserves the strongest dissent.
- It includes mitigation and monitoring sections.

## 7. Run the Automated Tests

Run:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests
```

Expected:

```txt
Ran 9 tests

OK
```

The tests cover:

- Replay artifact generation.
- Replay output validation.
- Verdict ClaimRef support.
- Blocked negative fixtures.
- Prompt-injection warning behavior.
- MiroFish facade refs, trace collection, report substrate normalization, and artifact SHA-256 refs.

## 8. Demo Safety Gates

These fixtures should be blocked:

```txt
tests/fixtures/no_evidence_case/case.yaml
tests/fixtures/prompt_only_case/case.yaml
tests/fixtures/disallowed_political_persuasion_case/case.yaml
tests/fixtures/stock_buy_sell_case/case.yaml
```

Run one blocked case:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run tests/fixtures/no_evidence_case/case.yaml --mode replay
```

Expected behavior:

```txt
blocked: DecisionRisk cannot produce a verdict without evidence.
```

Run the prompt-injection fixture through tests:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_decisionrisk_cli.DecisionRiskCliTests.test_prompt_injection_fixture_warns_but_stays_quoted
```

Expected behavior:

```txt
OK
```

What to point out:

- Prompt-injection-like evidence is not executed as instruction.
- It is treated as untrusted quoted evidence and surfaced as a warning.

## 9. Inspect the MiroFish Handoff Facades

The issue #5 facade surface lives under:

```txt
apps/decisionrisk-mirofish/backend/app/decisionrisk/facades/
```

The key facade calls are:

```txt
MiroFishProjectFacade.create_base_project
MiroFishProjectFacade.clone_project_for_run
MiroFishGraphFacade.build_graph
MiroFishSimulationFacade.run_simulation
MiroFishSimulationFacade.collect_simulation_trace
MiroFishReportFacade.generate_mirofish_report
MiroFishArtifactFacade.normalize_mirofish_report_to_claims
MiroFishArtifactFacade.write_mirofish_report_artifact
```

What to point out:

- Facades return structured refs that can be written into `run_manifest.json`.
- `mirofish_report.md`, `mirofish_report.json`, and `mirofish_report_claims.json` are substrate artifacts, not final recommendations.
- Normalized MiroFish report claims are marked `unsupported_assumption` until later ClaimRef audit and Verdict Council gates validate them.
- The tests use local doubles, so they do not require live Zep, OASIS, OpenAI, or MiroFish credentials.

Run the focused tests:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_mirofish_facades
```

Expected:

```txt
Ran 4 tests

OK
```

## 10. Demo the MiroFish Artifact API

The DecisionRisk API is registered inside the MiroFish Flask app under:

```txt
/api/decisionrisk
```

Key routes:

```txt
GET /api/decisionrisk/cases
GET /api/decisionrisk/cases/:case_id
GET /api/decisionrisk/cases/:case_id/artifacts
GET /api/decisionrisk/cases/:case_id/artifacts/:artifact_name
GET /api/decisionrisk/cases/:case_id/risk-docket
```

The artifact API reads from:

```txt
outputs/
```

or from:

```txt
DECISIONRISK_OUTPUTS_DIR
```

if that environment variable is set.

Backend syntax has been checked with:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk
```

## 11. Demo the Vue Route Shape

The current MiroFish frontend includes these DecisionRisk routes:

```txt
/decisionrisk
/decisionrisk/:caseId
```

Implemented files:

```txt
apps/decisionrisk-mirofish/frontend/src/api/decisionrisk.js
apps/decisionrisk-mirofish/frontend/src/views/decisionrisk/DecisionRiskCaseList.vue
apps/decisionrisk-mirofish/frontend/src/views/decisionrisk/DecisionRiskCaseViewer.vue
```

What the viewer shows:

- Verdict.
- Option comparison metrics.
- Grounding level.
- Scenario run count.
- Council dissent.
- Rendered Risk Docket text.

Known limitation: the frontend route has not been build-tested yet because frontend dependencies were not installed during the foundation implementation.

## Demo Script

Use this sequence in a live walkthrough:

1. Open `examples/launch_risk/ai_memory_launch/case.yaml` and explain the fictional AcmeAI decision.
2. Run replay generation.
3. Open `outputs/ai_memory_launch/run_manifest.json` and explain hash-indexed artifacts.
4. Run validation and show `validated: outputs/ai_memory_launch`.
5. Open `verdict.json` and `grounding_report.json` to show ClaimRefs.
6. Open `scenario_runs.json` to show 36 runs.
7. Open `simulation_metrics.json` to compare options.
8. Open `risk_docket.md` to show the final decision memo.
9. Run the unit tests.
10. Run a blocked negative fixture.
11. Show the issue #5 facade files as the typed MiroFish handoff boundary.
12. Show the MiroFish artifact API and Vue route files as the bridge to the app.

## Current Boundaries

Implemented:

- Replay-mode artifact generation.
- Artifact validation.
- ClaimRef provenance enforcement.
- Safety gates.
- MiroFish subtree import.
- Live MiroFish handoff facade contracts for project, graph, simulation, report, and substrate artifact refs.
- MiroFish artifact API skeleton.
- Vue artifact viewer route skeleton.

Not implemented yet:

- Full live runtime orchestration over the issue #5 facades.
- Runtime-mode-specific manifest writing for live runs.
- Job lifecycle, retries, cancellation, and resume.
- Live council runs.
- Frontend build verification.
- Full seven-step authoring UI.
