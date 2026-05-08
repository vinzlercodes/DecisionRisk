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

## Runtime Mode Contract

- [x] Add shared runtime mode contract for `replay`, `live_smoke`, `live_full`, and `eval`.
- [x] Update CLI parsing, preflight checks, eval mode, and validation behavior.
- [x] Add backend runtime mode discovery and run creation endpoints.
- [x] Add CLI and backend tests for canonical modes and live preflight behavior.
- [x] Update README, demo guide, and audit tracker for issue #6.

## Verdict Council Pipeline

- [x] Add deterministic Verdict Council service boundary.
- [x] Route replay, eval, and live_smoke final artifacts through `VerdictCouncilRunner`.
- [x] Enforce minimal publish gates for MiroFish substrate and council artifacts.
- [x] Add council, validator, and backend runtime tests for issue #8.
- [x] Update context, demo, and audit documentation for the Verdict Council pipeline.

## Council Role Contracts

- [x] Add LaunchRisk default Verdict Council config.
- [x] Define council role, chair, and execution package contracts.
- [x] Refactor `VerdictCouncilRunner` to use injectable config, role agents, and chair synthesis.
- [x] Expose config, role outputs, chair output, gate result, ClaimRefs, confidence, dissent, and mitigations in `council_rounds.json`.
- [x] Update runtime wording, context language, tests, replay artifacts, and audit notes for issue #9.

## Review

- Validation results: replay generation, replay validation, and 5 unittest tests pass.
- Remaining implementation gaps: see `audit.md`.
- Source-of-truth review: `DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf` v3 was extracted and cross-checked against `audit.md`.
- GitHub issue backlog: created 25 issues in `vinzlercodes/DecisionRisk`; see `tasks/github-issues.md` for issue numbers, labels, dependencies, acceptance criteria, and source mappings.
- GitHub creation status: verified with `gh issue list --state all --limit 40 --json number,title,url,labels`.
- Runtime mode contract: implemented issue #6 contract for CLI and backend, including reduced one-run `live_smoke` validation. Validation results: unittest suite passed with Flask route tests skipped when Flask is unavailable, compileall passed, replay generation passed in `/private/tmp`, existing replay output validation passed, and eval/golden comparison passed.
- Verdict Council pipeline: implemented issue #8 deterministic council service boundary for replay, eval, and live_smoke. Validation results: unittest suite passed with 34 tests and 5 Flask skips, compileall passed, replay generation and validation passed in `/private/tmp`, checked demo outputs were refreshed and validated, and eval/golden comparison passed.
- Council role contracts: implemented issue #9 contracts-first slice with LaunchRisk config, injectable role agents and chair synthesis, refreshed replay artifacts, and updated domain language. Validation results: council-focused tests passed, full unittest suite passed with 38 tests and 5 Flask skips, compileall passed, replay generation passed, and replay validation passed.
