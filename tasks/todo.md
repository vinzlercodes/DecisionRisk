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

## Issue #7 Execution Orchestration

- [x] Add a hybrid `ExecutionQueue` boundary with a file-backed single-worker MVP implementation.
- [x] Store executions under `outputs/<case_id>/runs/<execution_id>/` with status, event, error, and manifest artifacts.
- [x] Wire asynchronous backend run, status, events, cancel, resume, retry, and publish APIs.
- [x] Preserve legacy case artifact reads while allowing published executions to drive the viewer.
- [x] Add tests for enqueue, rerun IDs, overwrite, cancellation, partial failure, retry, resume, publish, and validator semantics.
- [x] Update domain docs, README/demo guidance, task review notes, and `audit.md`.

## Review

- Validation results: replay generation, replay validation, and 5 unittest tests pass.
- Remaining implementation gaps: see `audit.md`.
- Source-of-truth review: `DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf` v3 was extracted and cross-checked against `audit.md`.
- GitHub issue backlog: created 25 issues in `vinzlercodes/DecisionRisk`; see `tasks/github-issues.md` for issue numbers, labels, dependencies, acceptance criteria, and source mappings.
- GitHub creation status: verified with `gh issue list --state all --limit 40 --json number,title,url,labels`.
- Runtime mode contract: implemented issue #6 contract for CLI and backend, including reduced one-run `live_smoke` validation. Validation results: unittest suite passed with Flask route tests skipped when Flask is unavailable, compileall passed, replay generation passed in `/private/tmp`, existing replay output validation passed, and eval/golden comparison passed.
- Execution orchestration: implemented issue #7 file-backed Execution queue, run APIs, operational artifacts, explicit publish, retry/resume/cancel semantics, and minimal published-execution viewer wiring. Validation results: compileall passed, unittest discovery passed with 28 tests and 5 Flask route skips because Flask is not installed, replay generation passed in `/private/tmp`, existing replay output validation passed, and eval/golden comparison passed.
