# 0003: Require report substrate for every final verdict

## Status

Accepted

## Context

DecisionRisk's core invariant is that raw MiroFish-style report material is substrate, not the final answer. Requiring report substrate in every runtime mode keeps the Verdict Council, ClaimRef audit, and manifest validation paths consistent, but replay and eval still need to remain deterministic and API-key-free.

## Decision

Every final DecisionRisk verdict requires `mirofish_report.json`, `mirofish_report.md`, and `mirofish_report_claims.json` before council finalization. Live modes populate these from MiroFish execution; replay and eval populate them as deterministic Replay report substrate fixtures inside the clean spec package.

## Consequences

- The gate contract is the same across replay, eval, and live modes.
- Replay and eval do not import MiroFish internals or require API keys.
- Report substrate claims remain unsupported until corroborated by ClaimRef audit and Verdict Council judgment.
