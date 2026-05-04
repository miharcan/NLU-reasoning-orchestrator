# ADR 0001: Hybrid NLU Orchestration (Fast NLU + Adjudicator)

## Status
Accepted

## Context
Single-model approaches are either too expensive/slow for all traffic or too brittle for ambiguous multi-intent turns.

## Decision
Use a two-layer architecture:

1. Fast NLU candidate generation for common intent routing.
2. Adjudicator layer for ambiguous/multi-intent reasoning.

## Consequences
- Better cost/latency profile for common traffic.
- Better handling of compositional user requests.
- Requires explicit evaluation and fallback strategy.
