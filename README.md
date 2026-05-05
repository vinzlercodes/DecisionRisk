# DecisionRisk

DecisionRisk is an AGPL-3.0 MiroFish-powered risk decision engine.

It helps teams rehearse consequential decisions with evidence graphs, scenario ensembles, adversarial council review, transparent risk metrics, and auditable Risk Dockets. It is not a future oracle and should not be used as the sole basis for legal, financial, medical, electoral, public-safety, or other high-stakes decisions.

## MVP Status

The current implementation establishes the MiroFish-first monorepo, imports MiroFish under `apps/decisionrisk-mirofish/`, and ships a deterministic replay foundation for the LaunchRisk `ai_memory_launch` demo.

The replay path produces a root `run_manifest.json` with SHA-256 references to every artifact, then validates the manifest, ClaimRefs, verdict provenance, scenario count, and Risk Docket sections.

## Quickstart

Run the deterministic demo without API keys:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch
```

Run tests:

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests
```

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

## Claim Provenance

Durable artifacts use ClaimRefs to identify assertions and their provenance. The validator rejects a verdict whose primary rationale lacks a non-unsupported ClaimRef.

## License

The root app-first monorepo is AGPL-3.0 because it builds on MiroFish. The clean spec package under `packages/decisionrisk-spec/` preserves Apache-2.0 only while it remains free of MiroFish-derived implementation code.
