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
- [x] Add Replay report substrate fixtures so every runtime mode loads report substrate before final verdict.
- [x] Harden `ReportCritic`, `ClaimRefAuditor`, and `VerdictGateEngine` for issue #10.
- [x] Add validator and council tests for missing report substrate, malformed report ClaimRefs, unsupported rationale, overclaims, and missing scenario support.

## DecisionRisk Viewer

- [x] Build final case viewer tabs for issue #15.
- [x] Add artifact audit UI and backend validation summary for flat and run-specific outputs.
- [x] Add nested run route and DecisionRisk navigation links across MiroFish headers.
- [x] Verify backend tests, compile checks, and frontend build for issue #15.

## Evaluation Harness

- [x] Plan issue #20 against `CONTEXT.md`, ADRs, source-of-truth PDF section 20, and issue dependencies.
- [x] Add `decisionrisk eval` as the canonical Evaluation Harness command.
- [x] Generate `evaluation_report.json` and `evaluation_report.md`.
- [x] Cover artifact contract, ClaimRef, safety, golden replay, council quality, metric regression, UI contract, and live smoke eval checks.
- [x] Add explicit `--update-golden` workflow.
- [x] Record issue #20 caveats and remaining work in `audit.md`, `tasks/todo.md`, `demo/README.md`, and `CONTEXT.md`.

## Review

- Validation results: replay generation, replay validation, and 5 unittest tests pass.
- Remaining implementation gaps: see `audit.md`.
- Source-of-truth review: `DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf` v3 was extracted and cross-checked against `audit.md`.
- GitHub issue backlog: created 25 issues in `vinzlercodes/DecisionRisk`; see `tasks/github-issues.md` for issue numbers, labels, dependencies, acceptance criteria, and source mappings.
- GitHub creation status: verified with `gh issue list --state all --limit 40 --json number,title,url,labels`.
- Runtime mode contract: implemented issue #6 contract for CLI and backend, including reduced one-run `live_smoke` validation. Validation results: unittest suite passed with Flask route tests skipped when Flask is unavailable, compileall passed, replay generation passed in `/private/tmp`, existing replay output validation passed, and eval/golden comparison passed.
- Verdict Council pipeline: implemented issue #8 deterministic council service boundary for replay, eval, and live_smoke. Validation results: unittest suite passed with 34 tests and 5 Flask skips, compileall passed, replay generation and validation passed in `/private/tmp`, checked demo outputs were refreshed and validated, and eval/golden comparison passed.
- Verdict gates: implemented issue #10 all-mode report substrate requirements and stricter ReportCritic/ClaimRefAuditor/VerdictGateEngine behavior. Validation results are tracked in `audit.md`.
- Case viewer: implemented issue #15 final read-only workbench tabs, nested run routes, artifact audit, validation summary, and DecisionRisk navigation links. Validation results: backend route tests passed in the backend virtualenv, active-interpreter unittest suite passed with Flask skips, compileall passed, frontend build passed, and browser smoke checks covered case list, flat case view, nested run view, and Artifact Audit.
- Evaluation Harness: implemented issue #20 `decisionrisk eval`, durable reports, golden update workflow, metric regression bands, UI static contract checks, live-smoke skip behavior, and regression tests. Validation results are tracked in `audit.md`.
