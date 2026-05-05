# 0001: Use a MiroFish-first AGPL monorepo

## Status

Accepted

## Context

DecisionRisk needs to use MiroFish capabilities as much as possible for the MVP: evidence ingestion, ontology/graph construction, simulation, reports, and interactive world exploration. MiroFish is AGPL-3.0, so a product that forks or imports MiroFish internals should be treated as AGPL-compatible.

## Decision

Use `/DecisionRisk` as an AGPL app-first monorepo. Keep the MiroFish-powered app under `apps/decisionrisk-mirofish/` and keep portable, clean-room schemas and risk-pack specifications under `packages/decisionrisk-spec/`.

## Consequences

- The MVP can deeply reuse MiroFish.
- The repository license posture is honest for a networked MiroFish-derived app.
- The spec package can later be extracted if it remains clean of MiroFish-derived implementation.
