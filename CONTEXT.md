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

### run_manifest.json

`run_manifest.json` is the root artifact for a DecisionRisk run. It is the canonical index that points to every input and output artifact with paths and SHA-256 hashes.

### ClaimRef

A ClaimRef is the shared provenance primitive for assertions in durable artifacts. It links a claim to evidence, simulation runs, graph inference, council judgment, confidence, and downstream usage.

### Project Audit

`audit.md` is the live project implementation tracker. It is process state, not a generated product artifact.
