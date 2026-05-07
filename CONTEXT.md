# DecisionRisk Context

## Ubiquitous Language

### DecisionCase

A DecisionCase is the primary DecisionRisk aggregate. It represents one consequential decision under uncertainty, including the question, options, time horizon, risk pack, evidence, scenario ensemble, metrics, council verdict, and Risk Docket.

### MiroFish Project

A MiroFish Project is the execution substrate used by a DecisionCase for evidence ingestion, graph construction, simulation, and report substrate behavior. Product-facing DecisionRisk workflows should speak in DecisionCase terms.

### Risk Pack

A Risk Pack is a reusable decision-risk template containing ontology, metrics, council roles, scenario patterns, report structure, and validation expectations for a category of decisions.

### LaunchRisk

LaunchRisk is the MVP Risk Pack. It stress-tests product, pricing, policy, public-announcement, and AI-feature launches across adoption, reputation, narrative, stakeholder, regulatory, competitor, and mitigation dimensions.

### Risk Docket

A Risk Docket is the final board-style decision memo. It summarizes verdict, evidence, graph findings, scenarios, metrics, council debate, dissent, mitigations, monitoring signals, and audit trail.

### Execution

An Execution is one long-running attempt to run a DecisionCase and produce operational status, event, error, and artifact records.

### run_manifest.json

`run_manifest.json` is the root artifact for a DecisionRisk Execution. It is the canonical index that points to every input and output artifact with paths and SHA-256 hashes.

### ClaimRef

A ClaimRef is the shared provenance primitive for assertions in durable artifacts. It links a claim to evidence, simulation runs, graph inference, council judgment, confidence, and downstream usage.

### Project Audit

`audit.md` is the live project implementation tracker. It is process state, not a generated product artifact.

## Relationships

- A **DecisionCase** can have many **Executions**.
- An **Execution** belongs to exactly one **DecisionCase**.
- An **Execution** produces one `run_manifest.json`.
- A **MiroFish Project** is substrate state used by an **Execution**, not the product-facing aggregate.

## Flagged Ambiguities

- GitHub issue #7 uses `run_id` for the whole long-running job, while earlier MiroFish handoff code uses `run_id` for one option x scenario x seed simulation. Resolved: DecisionRisk uses **Execution** and `execution_id` for the whole job; per-seed MiroFish work remains nested scenario run state.
