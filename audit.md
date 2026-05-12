# DecisionRisk Implementation Audit

This file is the live implementation tracker. Every task must update this file before it is considered complete.

## Current Status

- Status: Foundation MVP slice, runtime mode contract, deterministic Verdict Council pipeline, issue #10 verdict gates, and issue #15 case viewer/audit UI implemented.
- MVP target: replayable LaunchRisk `ai_memory_launch` fixture with canonical `run_manifest.json`, all-mode report substrate, ClaimRef enforcement, CLI validation, backend runtime preflight, deterministic Verdict Council finalization, documented MiroFish integration boundary, and read-only case workbench.

## Completed Work

- Added `.gitignore` entries for local editor/system/cache files before splitting work into PR branches.
- Created the planned monorepo directory skeleton for the MiroFish app, portable spec package, examples, tests, docs, and task tracking.
- Added root `audit.md`, `tasks/todo.md`, `tasks/lessons.md`, license boundary docs, responsible-use docs, `CONTEXT.md`, and initial ADRs.
- Updated `AGENTS.md` so every implementation task must update `audit.md` before it is considered complete.
- Added the portable `decisionrisk` Python package with replay/validate CLI, artifact hashing, manifest validation, safety gates, deterministic LaunchRisk fixture payload generation, and ClaimRef collection/enforcement.
- Added the `examples/launch_risk/ai_memory_launch` hybrid fixture, scorecard, synthetic/public context sources, safety negative fixtures, and CLI tests.
- Generated `outputs/ai_memory_launch/` replay artifacts with `run_manifest.json` as the root artifact and validated the manifest/artifact hashes successfully.
- Converted tests to stdlib `unittest` and verified the replay, validation, ClaimRef, and safety-gate tests pass.
- Imported upstream MiroFish into `apps/decisionrisk-mirofish/` with `git subtree add --prefix=apps/decisionrisk-mirofish https://github.com/666ghj/MiroFish.git main --squash`.
- Added DecisionRisk backend blueprint registration, read-only artifact APIs, MiroFish facade skeletons, and minimal Vue case list/viewer routes inside the MiroFish app.
- Copied the imported MiroFish AGPL-3.0 license to the root `LICENSE`, preserved Apache-2.0 in `packages/decisionrisk-spec/LICENSE`, and updated README quickstart/layout/licensing guidance.
- Added `demo/README.md` with a detailed walkthrough for replay generation, manifest inspection, validation, ClaimRef provenance, metrics, safety gates, and MiroFish artifact viewer routes.
- Added the canonical runtime mode contract for `replay`, `live_smoke`, `live_full`, and `eval` in the clean spec package.
- Updated the CLI to reject legacy `live`/`record`, keep replay deterministic, support eval/golden comparison, validate manifest mode values, and preflight live modes without executing MiroFish from the clean package.
- Added backend runtime mode discovery and run creation APIs under `/api/decisionrisk/runtime-modes` and `/api/decisionrisk/runs`.
- Added a backend runtime runner that writes replay/eval artifacts, routes a reduced one-run `live_smoke` through the existing MiroFish facade boundary when configured, writes substrate-only MiroFish report artifacts, and refuses to downgrade `live_full` before the live Verdict Council exists.
- Added the deterministic Verdict Council service boundary with `VerdictCouncilRunner`, `ReportCritic`, `ClaimRefAuditor`, `VerdictGateEngine`, and `RiskDocketGenerator`.
- Routed replay, eval, and reduced `live_smoke` final artifact generation through the Verdict Council so `council_rounds.json`, `verdict.json`, and `risk_docket.md` come from a shared service boundary.
- Added minimal publish gates that reject MiroFish report substrate without council artifacts and require verdict rationale ClaimRefs to be supported or corroborated council judgments.
- Updated domain language for Verdict Council, MiroFish report substrate, and `council_judgment`.
- Added Replay report substrate as the deterministic replay/eval form of MiroFish report substrate.
- Added ADR 0003 documenting the all-mode report substrate requirement.
- Added pure spec report substrate helpers, wired replay/eval and backend replay/eval artifact generation to write `mirofish_report.json`, `mirofish_report.md`, and `mirofish_report_claims.json`, and kept replay/eval free of MiroFish internals.
- Reused the spec report claim normalizer from the MiroFish artifact facade so live_smoke and replay-shaped runs share ClaimRef shape.
- Hardened `ReportCritic`, `ClaimRefAuditor`, and `VerdictGateEngine` for issue #10, including malformed report ClaimRefs, overclaim warnings, missing-scenario warnings, and blocking when those claims support the final rationale.
- Updated validator requirements so every mode requires the three report substrate artifacts and rejects malformed report ClaimRefs.
- Expanded the DecisionRisk artifact API for issue #15 so flat outputs and run-specific outputs under `outputs/<case_id>/runs/<execution_id>/` share manifest, artifact, risk docket, run listing, audit summary, and raw file read behavior.
- Added backend audit metadata that uses `run_status.json` when present and falls back to manifest validation for flat replay outputs.
- Replaced the minimal Vue case viewer with the final read-only workbench tabs: Executive Summary, Option Metrics, Scenario Ensemble, Evidence & ClaimRefs, Council Review, Risk Docket, and Artifact Audit.
- Added nested `/decisionrisk/:caseId/runs/:executionId` routing, a run selector, non-final run warning behavior, artifact audit table, and DecisionRisk navigation links across the MiroFish headers.

## Remaining Work

- Push stacked branches and open PRs after GitHub authentication is repaired.
- Use the created source-of-truth GitHub issues (#5 through #29) as the implementation backlog.
- Complete production live MiroFish facade behavior for project, graph, simulation, report, and artifact operations beyond the reduced `live_smoke` runner path.
- Expand the deterministic Verdict Council into live LLM role/model configuration under issue #9.
- Add full seven-step authoring UI after MVP.
- Add SQLite artifact indexing after MVP.
- Add heavier automated safety enforcement after MVP.
- Add additional risk packs after MVP.
- Add live CI smoke workflow after MVP.
- Keep `demo/README.md` updated as live MiroFish capabilities are implemented.
- Keep `llm-council` as a reusable general skill only; DecisionRisk's Verdict Council must be product code, not an optional skill-triggered workflow.
- Implement the expanded source-of-truth requirements captured as GitHub issue drafts:
  - Long-running run orchestration with `run_status.json`, `run_events.jsonl`, `run_error.json`, retries, cancellation, idempotency, and resume.
  - Artifact schema versioning, risk pack versions, generator versions, and migration tooling.
  - File-backed LaunchRisk risk pack contract.
  - Seven-step authoring UI after the read-only viewer.
  - Evaluation harness covering artifact contract, ClaimRefs, safety, golden replay, council quality, metrics, UI contract, and live smoke.
  - Security/privacy/access-control/export policy, evidence retention, source trust, prompt-injection visibility, and audit trail fields.
  - Observability telemetry, run logs, cost/token estimates, and validation/hash status.
  - Human review, post-decision monitoring, retrospective artifacts, SQLite metadata index, deployment docs, CI/release discipline, and future risk packs.

## Validation

- `PYTHONPATH=packages/decisionrisk-spec/src:apps/decisionrisk-mirofish/backend apps/decisionrisk-mirofish/backend/.venv/bin/python -m unittest tests.test_decisionrisk_backend_runtime.DecisionRiskBackendRouteTests` passed after issue #15: 9 Flask route tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed after issue #15.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed after issue #15: 49 tests, 9 Flask route tests skipped in the active interpreter because Flask is not installed there.
- `npm run build` passed in `apps/decisionrisk-mirofish/frontend` after issue #15, with existing Vite warnings about `pendingUpload.js` mixed imports and chunk size.
- Browser smoke check passed for `/decisionrisk`, `/decisionrisk/ai_memory_launch`, `/decisionrisk/ai_memory_launch/runs/<execution_id>`, and the Artifact Audit tab using a temporary `/private/tmp/decisionrisk-ui-smoke` output root.
- `gh auth status` failed during issue #10 implementation because the stored token for `vinzlercodes` is invalid; PR creation and remote issue reads remain blocked until re-authentication.
- Local issue #10 source text in `tasks/github-issues.md` was used as the implementation fallback.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_decisionrisk_council` passed after issue #10: 14 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_decisionrisk_cli` passed after issue #10: 12 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_decisionrisk_backend_runtime` passed after issue #10: 19 tests, 5 Flask route tests skipped because Flask is not installed in the active interpreter.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed after issue #10: 45 tests, 5 Flask route tests skipped because Flask is not installed in the active interpreter.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed after issue #10.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay --output-dir /private/tmp/decisionrisk-issue10-replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate /private/tmp/decisionrisk-issue10-replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay --output-dir outputs/ai_memory_launch` passed and refreshed checked replay artifacts with report substrate.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch` passed after issue #10.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode eval --output-dir /private/tmp/decisionrisk-issue10-eval --golden-dir outputs/ai_memory_launch` passed.
- `gh auth status` passed when run with GitHub network access and reported an active `vinzlercodes` login.
- Created missing labels for state, area, priority, MVP, and post-MVP tracking.
- Created 25 GitHub issues from `tasks/github-issues.md`: #5 through #29.
- `gh issue list --state all --limit 40 --json number,title,url,labels` verified the created issues and labels.
- `pdfinfo DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf` passed and reported 23 pages.
- `pdftotext -layout DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf /private/tmp/decisionrisk_source_v3.txt` passed for source-of-truth extraction.
- Cross-check completed against `audit.md`, `tasks/todo.md`, replay package code, safety gates, artifact APIs, tests, and minimal Vue viewer.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed: 5 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed after runtime mode review: 16 tests, 3 Flask route tests skipped because Flask is not installed in the active interpreter.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed after runtime mode work.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay --output-dir /private/tmp/decisionrisk-runtime-replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch` passed after runtime mode validation changes.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode eval --output-dir /private/tmp/decisionrisk-runtime-eval --golden-dir outputs/ai_memory_launch` passed.
- Focused backend runner tests passed for reduced `live_smoke` substrate artifacts and `live_full` no-downgrade behavior.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed after issue #8: 34 tests, 5 Flask route tests skipped because Flask is not installed in the active interpreter.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed after issue #8.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay --output-dir /private/tmp/decisionrisk-issue8-replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate /private/tmp/decisionrisk-issue8-replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay --output-dir outputs/ai_memory_launch` passed and refreshed the checked demo artifacts.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch` passed after refreshing the checked demo artifacts.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode eval --output-dir /private/tmp/decisionrisk-issue8-eval --golden-dir outputs/ai_memory_launch` passed.
- MiroFish subtree import completed successfully.
- Demo guide was added; existing validation commands remain the same.

## Known Limitations

- The MiroFish source subtree import created standard subtree merge commits automatically.
- Full live MiroFish/LLM execution is not yet implemented; replay and eval are implemented in the clean CLI, and backend `live_smoke` has a reduced one-run facade-backed path for configured environments/test doubles.
- `live_full` intentionally fails unless live LLM preflight passes and then remains blocked until issue #9 implements live Verdict Council role/model configuration; it does not silently fall back to replay.
- The source-of-truth issue backlog is now remote, but local working tree updates are not committed.

## Next Task

- Pick the next MVP blocker issue (#5, #7, #9, #20, #21, or #22) and implement it on a focused branch.
