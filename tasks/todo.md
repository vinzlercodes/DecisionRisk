# DecisionRisk MVP Tasks

## Foundation

- [x] Create monorepo directory skeleton.
- [x] Add audit discipline to `AGENTS.md`.
- [x] Add root project docs and licensing boundary docs.
- [x] Add `CONTEXT.md` with canonical domain language.
- [x] Add ADRs for MiroFish-first monorepo and artifact-root manifest.

## Replay MVP

- [ ] Add portable spec package with CLI.
- [ ] Add `run_manifest.json` root artifact contract.
- [ ] Add `ClaimRef` schema enforcement.
- [ ] Add LaunchRisk risk pack fixture.
- [ ] Add deterministic replay output generation.
- [ ] Add replay validation command.

## Tests

- [ ] Add unit tests for schemas, gates, manifests, and ClaimRefs.
- [ ] Add replay integration validation for `ai_memory_launch`.
- [ ] Add negative fixtures for blocked cases.

## MiroFish Integration

- [x] Import MiroFish through fork/subtree.
- [ ] Add DecisionRisk facade skeletons.
- [ ] Add minimal backend artifact APIs.
- [ ] Add minimal Vue case viewer route.

## Review

- Validation results: MiroFish subtree import completed. CLI and tests are not present in this branch yet.
- Remaining implementation gaps: see `audit.md`.
