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
- [x] Implement issue #5 live MiroFish handoff facade contracts.
- [x] Add manifest-ready MiroFish report artifact writes.
- [x] Add unit tests for facade refs, traces, report normalization, and artifact hashes.
- [x] Update audit, lessons, and demo docs for issue #5.

## Review

- Validation results: replay generation, replay validation, and 9 unittest tests pass.
- Issue #5 review: live handoff facades now expose project, graph, simulation, report, and artifact boundaries with manifest-ready refs; raw MiroFish reports remain substrate-only.
- Remaining implementation gaps: see `audit.md`.
- Source-of-truth review: `DecisionRisk_Project_Source_of_Truth_v3_End_to_End.pdf` v3 was extracted and cross-checked against `audit.md`.
- GitHub issue backlog: created 25 issues in `vinzlercodes/DecisionRisk`; see `tasks/github-issues.md` for issue numbers, labels, dependencies, acceptance criteria, and source mappings.
- GitHub creation status: verified with `gh issue list --state all --limit 40 --json number,title,url,labels`.
