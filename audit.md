# DecisionRisk Implementation Audit

This file is the live implementation tracker. Every task must update this file before it is considered complete.

## Current Status

- Status: Foundation MVP slice implemented.
- MVP target: replayable LaunchRisk `ai_memory_launch` fixture with canonical `run_manifest.json`, ClaimRef enforcement, CLI validation, and documented MiroFish integration boundary.

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
- Implemented GitHub issue #5 live MiroFish handoff facades for project, graph, simulation, report, and artifact operations inside `apps/decisionrisk-mirofish/`.
- Added manifest-ready facade contract refs, substrate-only MiroFish report artifact writes, conservative `mirofish_report_claims.json` normalization, and unit tests using local doubles with no live Zep/OASIS/OpenAI dependencies.
- Made the MiroFish Flask app factory imports lazy so pure DecisionRisk facade modules can be imported by tests and tooling without requiring Flask.
- Updated `tasks/todo.md`, `tasks/lessons.md`, and `demo/README.md` for the issue #5 implementation and source-hierarchy planning lesson.

## Remaining Work

- Push stacked branches and open PRs after GitHub authentication is repaired.
- Use the created source-of-truth GitHub issues (#5 through #29) as the implementation backlog.
- Wire the issue #5 facade surface into the later live runtime orchestrator and manifest writer.
- Implement the mandatory DecisionRisk verdict evaluation layer:
  - Pipeline rule: `MiroFish run completes -> MiroFish report + traces + graph + metrics + grounding + ClaimRefs -> DecisionRisk VerdictCouncilRunner runs automatically -> verdict.json + council_rounds.json + risk_docket.md -> final user response`.
  - Architectural invariant: no MiroFish report is user-final until it passes through the DecisionRisk Verdict Council.
  - Required services: `VerdictCouncilRunner`, `ReportCritic`, `ClaimRefAuditor`, `VerdictGateEngine`, and `RiskDocketGenerator`.
  - Required gates: `run_manifest.json` must include the MiroFish report artifact; MiroFish report claims must become ClaimRefs or be marked unsupported; `simulation_metrics.json`, `scenario_runs.json`, `grounding_report.json`, and the MiroFish report must all be loaded before final verdict; `verdict.primary_rationale` cannot be generated without non-unsupported ClaimRefs; final user response must come from `verdict.json` or `risk_docket.md`, never directly from MiroFish report text.
- Wire the minimal Vue case viewer into navigation after product shell decisions.
- Add frontend build verification once MiroFish frontend dependencies are installed.
- Add full seven-step authoring UI after MVP.
- Add SQLite artifact indexing after MVP.
- Add heavier automated safety enforcement after MVP.
- Add additional risk packs after MVP.
- Add live CI smoke workflow after MVP.
- Keep `demo/README.md` updated as live MiroFish capabilities are implemented.
- Keep `llm-council` as a reusable general skill only; DecisionRisk's Verdict Council must be product code, not an optional skill-triggered workflow.
- Implement the expanded source-of-truth requirements captured as GitHub issue drafts:
  - Runtime mode contract: `replay`, `live_smoke`, `live_full`, and `eval`.
  - Long-running run orchestration with `run_status.json`, `run_events.jsonl`, `run_error.json`, retries, cancellation, idempotency, and resume.
  - Artifact schema versioning, risk pack versions, generator versions, and migration tooling.
  - File-backed LaunchRisk risk pack contract.
  - Final case viewer tabs, artifact audit UI, navigation integration, and later seven-step authoring UI.
  - Evaluation harness covering artifact contract, ClaimRefs, safety, golden replay, council quality, metrics, UI contract, and live smoke.
  - Security/privacy/access-control/export policy, evidence retention, source trust, prompt-injection visibility, and audit trail fields.
  - Observability telemetry, run logs, cost/token estimates, and validation/hash status.
  - Human review, post-decision monitoring, retrospective artifacts, SQLite metadata index, deployment docs, CI/release discipline, and future risk packs.

## Validation

- `gh auth status` failed because the stored token for `vinzlercodes` is invalid; PR creation is blocked until re-authentication.
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
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest tests.test_mirofish_facades` passed: 4 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed: 9 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed after issue #5 facade implementation.
- `gh issue close 5 --comment ...` passed and closed `vinzlercodes/DecisionRisk#5`.
- MiroFish subtree import completed successfully.
- Demo guide was added; existing validation commands remain the same.

## Known Limitations

- The MiroFish source subtree import created standard subtree merge commits automatically.
- Live MiroFish orchestration is not yet implemented; issue #5 now provides the facade surface that later live modes can call.
- MiroFish report claims are normalized as `unsupported_assumption` substrate until later ClaimRef audit and Verdict Council gates connect them to evidence, traces, graph inferences, or council judgments.
- Frontend route code was added but not build-tested because frontend dependencies were not installed in this turn.
- The source-of-truth issue backlog is now remote, but local working tree updates are not committed.

## Next Task

- Pick the next MVP blocker issue (#6, #7, #8, #10, #15, #20, #21, or #22) and implement it on a focused branch.
