# DecisionRisk MVP Tasks

## Foundation

- [x] Create monorepo directory skeleton.
- [x] Add audit discipline to `AGENTS.md`.
- [x] Add root project docs and licensing boundary docs.
- [x] Add `CONTEXT.md` with canonical domain language.
- [x] Add ADRs for MiroFish-first monorepo and artifact-root manifest.

## Replay MVP

- [x] Add portable spec package with CLI.
- [x] Add `run_manifest.json` root artifact contract.
- [x] Add `ClaimRef` schema enforcement.
- [x] Add LaunchRisk risk pack fixture.
- [x] Add deterministic replay output generation.
- [x] Add replay validation command.

## Tests

- [x] Add unit tests for schemas, gates, manifests, and ClaimRefs.
- [x] Add replay integration validation for `ai_memory_launch`.
- [x] Add negative fixtures for blocked cases.

## MiroFish Integration

- [x] Import MiroFish through fork/subtree.
- [x] Add DecisionRisk facade skeletons.
- [x] Add minimal backend artifact APIs.
- [x] Add minimal Vue case viewer route.

## Review

- Validation results: replay generation, replay validation, and 5 unittest tests pass.
- Remaining implementation gaps: see `audit.md`.
