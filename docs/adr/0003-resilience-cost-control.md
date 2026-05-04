# ADR 0003: Resilience and Cost Control for HTTP Adjudication

## Status
Accepted

## Context
Remote adjudication (HTTP/Ollama) can be slow or unavailable due to cold starts or upstream issues.

## Decision
Implement fail-fast + fallback:

- short HTTP timeout threshold
- cooldown circuit for repeated upstream errors
- deterministic mock fallback for continuity

Deploy with low-cost Cloud Run defaults (`min-instances=0`, bounded max instances).

## Consequences
- Predictable latency under failure.
- Cheap baseline operations.
- Possible quality reduction during fallback windows.
