# ADR 0002: Policy Guardrails Before Tool Execution

## Status
Accepted

## Context
LLM or heuristic decisions can be incorrect or unsafe for account-sensitive actions.

## Decision
Adjudicator output is advisory only. A deterministic policy layer enforces:

- authentication requirements
- risk-aware action constraints
- allowed execution paths

Tool calls execute only after policy validation.

## Consequences
- Reduced unsafe automation risk.
- Clear boundary between reasoning and control.
- Slightly more orchestration complexity.
