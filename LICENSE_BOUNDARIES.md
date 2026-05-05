# License Boundaries

DecisionRisk is planned as an AGPL app-first monorepo because the main application builds on MiroFish.

## Components

| Component | Intended license | Boundary |
| --- | --- | --- |
| Root repository | AGPL-3.0 | Main app-first monorepo. |
| `apps/decisionrisk-mirofish/` | AGPL-3.0 | MiroFish fork/subtree and DecisionRisk app integration. |
| `packages/decisionrisk-spec/` | Apache-2.0 if clean | Portable schemas, risk packs, report templates, and eval fixtures only. |
| `examples/` | AGPL-3.0 unless otherwise marked | Demo fixtures and generated replay artifacts for the app. |

## Clean Spec Rule

`packages/decisionrisk-spec/` must not contain copied MiroFish implementation code, MiroFish frontend components, MiroFish route handlers, or MiroFish prompts copied verbatim. If that boundary is violated, treat the affected files as AGPL.

## MiroFish Rule

If DecisionRisk imports, modifies, or forks MiroFish internals, the resulting app must be treated as AGPL-compatible. The planned integration boundary is:

```txt
DecisionRisk domain code -> DecisionRisk facade -> MiroFish internals
```

## Not Legal Advice

This document is engineering guidance for contributors. It is not legal advice.
