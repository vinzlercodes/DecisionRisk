# DecisionRisk Spec

Clean portable schemas, risk-pack definitions, replay artifact contracts, and validation tooling for DecisionRisk.

This package intentionally avoids MiroFish-derived implementation code so it can later be extracted into a standalone permissive package if the boundary stays clean.

## Run

```bash
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay
PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch
```

Canonical runtime modes are `replay`, `live_smoke`, `live_full`, and `eval`. The clean spec CLI owns deterministic replay/eval artifact contracts. Live MiroFish execution is owned by the MiroFish backend runtime API so this package does not take a dependency on MiroFish internals.
