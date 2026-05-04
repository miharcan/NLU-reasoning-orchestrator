# ADR 0004: Quality Gates and SLO-Driven Delivery

## Status
Accepted

## Context
NLU quality can regress silently without repeatable checks and operational targets.

## Decision
Adopt release gates and runtime SLO checks:

- CI gate: lint + tests + eval thresholds + conversation-transition gate
- runtime SLO endpoint tracking latency/fallback/denial/json-validity
- weekly quality report for delivery review

## Consequences
- Higher confidence in releases.
- Faster detection of regressions.
- Requires maintenance of test/eval assets.
