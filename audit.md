# DecisionRisk Implementation Audit

This file is the live implementation tracker. Every task must update this file before it is considered complete.

## Current Status

- Status: Repository foundation prepared for MiroFish-first MVP implementation.
- MVP target: replayable LaunchRisk `ai_memory_launch` fixture with canonical `run_manifest.json`, ClaimRef enforcement, CLI validation, and documented MiroFish integration boundary.

## Completed Work

- Imported upstream MiroFish into `apps/decisionrisk-mirofish/` with `git subtree add --prefix=apps/decisionrisk-mirofish https://github.com/666ghj/MiroFish.git main --squash`.
- Added `.gitignore` entries for local editor/system/cache files.
- Added root `audit.md`, `tasks/todo.md`, `tasks/lessons.md`, license boundary docs, responsible-use docs, `CONTEXT.md`, and initial ADRs.
- Updated `AGENTS.md` so every implementation task must update `audit.md` before it is considered complete.
- Copied the imported MiroFish AGPL-3.0 license to the root `LICENSE` and documented future Apache-only boundaries for a clean spec package.

## Remaining Work

- Add the portable `decisionrisk` Python package with replay/validate CLI.
- Add the `ai_memory_launch` fixture, generated replay artifacts, and tests.
- Add DecisionRisk backend artifact APIs, MiroFish facade skeletons, and minimal Vue viewer route.
- Push stacked branches and open PRs after GitHub authentication is repaired.
- Implement live MiroFish facade methods for project, graph, simulation, report, and artifact operations.
- Add full seven-step authoring UI after MVP.
- Add SQLite artifact indexing after MVP.
- Add heavier automated safety enforcement after MVP.
- Add additional risk packs after MVP.
- Add live CI smoke workflow after MVP.

## Validation

- `gh auth status` failed because the stored token for `vinzlercodes` is invalid; PR creation is blocked until re-authentication.
- MiroFish subtree import completed successfully.

## Known Limitations

- The MiroFish source subtree import created standard subtree merge commits automatically.
- Replay mode, ClaimRef validation, and live MiroFish facades are not yet implemented in this branch.

## Next Task

- Add replay/spec package, deterministic fixture artifacts, validation, and tests.
