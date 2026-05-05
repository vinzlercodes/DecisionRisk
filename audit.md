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

## Remaining Work

- Push stacked branches and open PRs after GitHub authentication is repaired.
- Implement live MiroFish facade methods for project, graph, simulation, report, and artifact operations.
- Wire the minimal Vue case viewer into navigation after product shell decisions.
- Add frontend build verification once MiroFish frontend dependencies are installed.
- Add full seven-step authoring UI after MVP.
- Add SQLite artifact indexing after MVP.
- Add heavier automated safety enforcement after MVP.
- Add additional risk packs after MVP.
- Add live CI smoke workflow after MVP.
- Keep `demo/README.md` updated as live MiroFish capabilities are implemented.

## Validation

- `gh auth status` failed because the stored token for `vinzlercodes` is invalid; PR creation is blocked until re-authentication.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk run examples/launch_risk/ai_memory_launch/case.yaml --mode replay` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m decisionrisk validate outputs/ai_memory_launch` passed.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m unittest discover -s tests` passed: 5 tests.
- `PYTHONPATH=packages/decisionrisk-spec/src python3 -m compileall packages/decisionrisk-spec/src/decisionrisk apps/decisionrisk-mirofish/backend/app/decisionrisk` passed.
- MiroFish subtree import completed successfully.
- Demo guide was added; existing validation commands remain the same.

## Known Limitations

- The MiroFish source subtree import created standard subtree merge commits automatically.
- Live MiroFish/LLM execution is not yet implemented; replay mode is implemented.
- Frontend route code was added but not build-tested because frontend dependencies were not installed in this turn.

## Next Task

- Commit and push the demo guide on a focused branch/PR.
