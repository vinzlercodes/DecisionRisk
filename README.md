# DecisionRisk

DecisionRisk is an AGPL-3.0 MiroFish-powered risk decision engine.

It helps teams rehearse consequential decisions with evidence graphs, scenario ensembles, adversarial council review, transparent risk metrics, and auditable Risk Dockets. It is not a future oracle and should not be used as the sole basis for legal, financial, medical, electoral, public-safety, or other high-stakes decisions.

## MVP Status

The current implementation establishes the MiroFish-first monorepo, imports MiroFish under `apps/decisionrisk-mirofish/`, and ships a deterministic replay foundation for the LaunchRisk `ai_memory_launch` demo.

The runtime contract now recognizes `replay`, `live_smoke`, `live_full`, and `eval`. Replay remains deterministic and API-key-free by using Replay report substrate fixtures instead of live MiroFish execution. Live modes are backend-owned MiroFish runtimes with explicit preflight checks. Replay, eval, and reduced `live_smoke` runs finalize through the deterministic Verdict Council, and raw report substrate is never a final answer.

## Quickstart

Run the deterministic demo without API keys:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch
```

Run an eval-shaped artifact generation and compare it with golden replay outputs:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode eval --output-dir /private/tmp/decisionrisk-eval --golden-dir outputs/ai_memory_launch
```

Run tests:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests
```

For a detailed walkthrough of the current demo capabilities, see [demo/README.md](demo/README.md).

## Repository Layout

```txt
apps/decisionrisk-mirofish/       MiroFish subtree plus DecisionRisk app integration
packages/decisionrisk-spec/       Clean schemas, replay CLI, fixture generation, validation logic
examples/launch_risk/             Hybrid LaunchRisk demo fixture
outputs/                          Generated replay artifacts
docs/adr/                         Architecture decision records
tasks/                            Task and lesson tracking
audit.md                          Live implementation audit
```

## Artifact Contract

`run_manifest.json` is the root artifact. It points to every input and output artifact with a path and SHA-256 hash. Files are the source of truth for replay and validation.

Every final run includes report substrate artifacts: `mirofish_report.json`, `mirofish_report.md`, and `mirofish_report_claims.json`. Replay and eval generate deterministic Replay report substrate; live modes generate MiroFish report substrate through the backend.

The manifest `mode` must be one of the canonical runtime modes. `live_smoke` and `live_full` require `DECISIONRISK_ENABLE_LIVE=1`; `live_full` also requires live LLM council enablement and an API key. The clean CLI accepts those modes for contract validation but does not execute MiroFish directly; use `POST /api/decisionrisk/runs` in the backend for live runs.

## Claim Provenance

Durable artifacts use ClaimRefs to identify assertions and their provenance. The validator rejects malformed report ClaimRefs, missing report substrate, and any verdict whose primary rationale lacks an eligible non-unsupported ClaimRef.

## License

The root app-first monorepo is AGPL-3.0 because it builds on MiroFish. The clean spec package under `packages/decisionrisk-spec/` preserves Apache-2.0 only while it remains free of MiroFish-derived implementation code.
