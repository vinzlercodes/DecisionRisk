# 0002: Make run_manifest.json the root artifact

## Status

Accepted

## Context

DecisionRisk replay, validation, provenance, regression tests, and future SQLite indexing need one canonical artifact index. Storing outputs only as loose files makes verification brittle.

## Decision

Every run writes `run_manifest.json` as the canonical root artifact. It records case ID, risk pack, run mode, versions, MiroFish reference, inputs, output artifacts, paths, and SHA-256 hashes.

## Consequences

- Replay validation can hash-check every artifact.
- UI and future database indexes can load the manifest first.
- Regression tests can compare artifact contracts without depending on MiroFish runtime state.
