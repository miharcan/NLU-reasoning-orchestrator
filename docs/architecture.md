# Architecture Walkthrough

This document explains the request lifecycle and the design choices behind the repository.

## Request sequence

```text
User/UI
  -> POST /analyze
  -> FastAPI middleware
     -> auth check
     -> rate limit check
     -> latency logging
  -> Orchestrator
     -> load or create session state
     -> detect intents with fast NLU
     -> extract entities
     -> adjudicate ambiguity with mock or HTTP LLM
     -> validate next action with policy engine
     -> execute tool if allowed
     -> persist updated state and turn history
  -> typed JSON response
```

## Runtime layers

### 1. API layer

The FastAPI app exposes product-facing endpoints such as:

- `/analyze`
- `/state/{session_id}`
- `/config`
- `/stats`
- `/slo`
- `/metrics`

The API layer owns request validation, security middleware, and operational visibility.

### 2. Fast NLU

The `FastNLU` component gives a low-cost first-pass intent ranking. The system does not need an LLM call for every utterance.

### 3. Adjudicator

The adjudicator resolves ambiguity, multi-intent cases, and next-step reasoning. It can run in:

- `mock` mode for deterministic demos and tests
- `http` mode for remote LLM-backed reasoning

### 4. State manager

Dialogue state is structured rather than prompt-only. The stored state includes:

- authentication status
- current intent
- collected slots
- missing slots
- risk level
- turn count
- turn history

This design makes multi-turn behavior inspectable and testable.

### 5. Policy engine

The policy layer is the safety boundary between reasoning and execution. The LLM or mock adjudicator can suggest actions, but policy decides whether those actions are permitted.

### 6. Tool layer

Backend tools are intentionally mocked. The point of the product is not tool realism; it is orchestration discipline.

## Design principles

- Typed interfaces before execution
- Clear separation of concerns
- Cheap fast-path for common requests
- Graceful fallback when adjudication fails
- Observable runtime behavior
- Multi-turn state stored outside prompts

## Why this is a good interview repo

It demonstrates not only NLU and LLM concepts, but also product engineering maturity:

- architecture boundaries
- quality gates
- runtime controls
- deployment discipline
- stateful orchestration
- operational metrics
