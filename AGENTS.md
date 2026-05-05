# Repository Guidelines

## Project Structure & Module Organization

DecisionRisk is currently a minimal repository. The root contains `README.md` for the project summary and `LICENSE` for licensing. No source, test, or asset directories exist yet.

When implementation begins, prefer a predictable layout:

- `src/` for application and domain code.
- `tests/` for automated tests that mirror `src/` structure.
- `docs/` for architecture notes, decision records, and product context.
- `assets/` for static images, fixtures, or sample data.

Keep generated files, editor metadata, and local environment files out of version control unless they are intentionally shared project configuration.

## Build, Test, and Development Commands

No package manager, build tool, or test runner is configured yet. Until one is added, use these basic checks:

- `git status --short` shows local changes before committing.
- `rg --files` lists tracked project files quickly.
- `sed -n '1,120p' README.md` verifies the current project description.

When adding a language stack, document the canonical commands here, such as `npm test`, `npm run build`, `cargo test`, or `make test`.

## Coding Style & Naming Conventions

Match the conventions of the language and framework introduced by the first implementation. Prefer small modules with clear domain names tied to the product purpose: decisions, risks, simulations, debates, assumptions, scenarios, and outcomes.

Use descriptive file names. For example, prefer `risk-simulation.ts` or `risk_simulation.py` over vague names like `utils` or `helpers`. Keep formatting automated once tooling exists, and commit formatter configuration with the codebase.

## Testing Guidelines

No testing framework is configured yet. New feature work should introduce tests alongside the implementation. Place tests in `tests/` or adjacent `*.test.*` / `*_test.*` files, depending on the chosen stack.

Focus early coverage on core decision-risk behavior: scenario modeling, downside quantification, debate logic, and edge cases around missing or uncertain inputs.

## Commit & Pull Request Guidelines

The current history only contains `Initial commit`, so no strong convention has emerged. Use concise, imperative commit messages such as `Add risk scoring model` or `Document simulation assumptions`.

Pull requests should include a short description, the reason for the change, validation steps run, and any relevant screenshots or sample outputs for user-facing work. Link issues or planning docs when available. Keep PRs focused; separate broad architecture changes from feature implementation.

## Workflow Orchestration

### Plan Mode Default
- Enter plan mode for any non-trivial task, defined as 3+ steps, architectural decisions, or meaningful uncertainty.
- Write detailed specs upfront to reduce ambiguity.
- Use plan mode for verification steps, not just implementation.
- If something goes sideways, stop and re-plan immediately.

### Subagent Strategy
- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to focused subagents.
- Use one task per subagent.
- For complex problems, use additional subagents rather than overloading one thread.

### Self-Improvement Loop
- After any correction from the user, update `tasks/lessons.md` with the pattern.
- Write rules that prevent the same mistake from recurring.
- Review relevant lessons at session start.
- Ruthlessly iterate on these lessons until the mistake rate drops.

### Verification Before Done
- Never mark a task complete without proving it works.
- Run tests, check logs, and demonstrate correctness where applicable.
- Diff behavior between main and the current changes when relevant.
- Ask: “Would a staff engineer approve this?”

### Demand Elegance, Balanced
- For non-trivial changes, pause and ask whether there is a more elegant approach.
- If a fix feels hacky, rework it into the simplest elegant solution.
- Skip this for simple, obvious fixes; do not over-engineer.
- Challenge the work before presenting it.

### Autonomous Bug Fixing
- When given a bug report, investigate and fix it without asking for unnecessary hand-holding.
- Use logs, errors, failing tests, and reproduction steps to identify the root cause.
- Fix failing CI tests without waiting for step-by-step instructions.
- Minimize context switching for the user.

## Task Management
- Plan first: write the plan to `tasks/todo.md` with checkable items.
- Verify the plan: check in before starting implementation when the task is substantial or ambiguous.
- Track progress: mark items complete as work proceeds.
- Keep a live root `audit.md` after every implementation task. Update completed work, remaining work, validation run or gap, known limitations, and next task before considering any task complete.
- Explain changes: provide high-level summaries at meaningful milestones.
- Document results: add a review section to `tasks/todo.md`.
- Capture lessons: update `tasks/lessons.md` after user corrections.
- Demo artifacts: for meaningful changes, create or update a `demo/` folder containing clear reproduction steps, test instructions, expected outputs, screenshots or sample data when useful, and any commands needed to verify the project behavior.

## Core Principles
- Simplicity first: make every change as simple as possible.
- Minimal impact: touch only what is necessary.
- No laziness: find root causes, avoid temporary fixes, and hold senior developer standards.
- No side effects: avoid unrelated changes that introduce new bugs.

## Security & Configuration Tips
Do not commit secrets, patient data, or environment-specific credentials. Keep the local virtual environment disposable, and do not treat `doctor/` as a source directory.


## Agent-Specific Instructions

Before editing, inspect the repository state and avoid overwriting unrelated local changes. Keep this guide updated as source directories, build tools, and test commands are added.
