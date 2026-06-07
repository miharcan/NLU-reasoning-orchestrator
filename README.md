# NLU Reasoning Orchestrator

A product-realistic conversational AI demo that shows how to safely orchestrate fast NLU, LLM-style reasoning, dialogue state, policy guardrails, and backend actions in a banking contact-centre setting.

This repository is intentionally built as a small product, not a toy chatbot. It is designed to be useful for interviews, architecture reviews, and hands-on learning about production-oriented NLU systems.

## Why this repo exists

The system answers a practical enterprise question:

> Given a customer utterance, what is the user trying to do, what information is missing, what action is allowed next, and how do we make that decision observable and safe?

Example input:

```text
I was charged twice last month and I also need to update the card on file.
```

Example output shape:

```json
{
  "primary_intent": "billing_dispute",
  "secondary_intents": ["update_payment_method"],
  "entities": {
    "time_period": "last month"
  },
  "missing_slots": ["transaction_amount", "transaction_date"],
  "risk_level": "medium",
  "next_action": "authenticate_user",
  "reasoning": "The utterance contains a billing complaint and a payment-method update. Because account-specific actions are required, authentication is needed first."
}
```

## What it demonstrates

- Fast intent detection for common traffic
- Adjudication for ambiguous and multi-intent utterances
- Structured multi-turn dialogue state
- Policy enforcement before tool execution
- Typed contracts with Pydantic validation
- Tool-calling simulation for banking workflows
- Monitoring, quality gates, and deployment discipline

## Architecture

```text
Client/UI
   |
   v
FastAPI /analyze
   |
   +--> Fast NLU ----------------------+
   |                                   |
   +--> Entity extraction              |
   |                                   v
   +--> Adjudicator (mock or HTTP LLM) ---> Structured decision
   |                                           |
   +--> Dialogue state store                   |
   |                                           v
   +--> Policy engine --------------------> Allowed next action
                                               |
                                               v
                                           Tool execution
```

## Repository layout

```text
nlu-reasoning-orchestrator/
├── app/                  # API, orchestration, state, policy, tools, schemas
├── eval/                 # Evaluation scripts and test datasets
├── tests/                # Unit tests
├── ui/                   # Streamlit demo UI
├── scripts/              # Local stack, CI, deployment, reporting
├── docs/architecture.md  # Request lifecycle and design walkthrough
├── docs/adr/             # Architecture decision records
├── .github/workflows/    # GitHub Actions CI
├── Dockerfile
├── cloudbuild.yaml
├── Makefile
└── README.md
```

## Supported intents

- `billing_dispute`
- `make_payment`
- `update_payment_method`
- `check_balance`
- `lost_card`
- `loan_status`
- `change_address`
- `speak_to_agent`

## Quick start

Python `3.11` is used in CI. Local development is also verified with Python `3.10.13`.

### Option 1: API only

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

If Python `3.11` is not installed locally, Python `3.10.13` works with the current
dependency set and quality gates:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/ci_check.sh
```

Open:

- API docs: `http://localhost:8001/docs`
- Health: `http://localhost:8001/health`

### Option 2: API + UI

Terminal 1:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

Terminal 2:

```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py
```

Open:

- UI: `http://localhost:8501`

### Option 3: Full local stack

This starts:

- local Ollama
- HTTP LLM gateway
- NLU API
- Streamlit UI

```bash
./scripts/local_stack.sh up
```

Useful commands:

```bash
./scripts/local_stack.sh status
./scripts/local_stack.sh down
```

## Configuration

Runtime settings are controlled with environment variables. A starter file is included at `.env.example`.

Key controls:

- `ADJUDICATOR_MODE=mock|http`
- `ADJUDICATOR_HTTP_URL=...`
- `STATE_BACKEND=in_memory|redis`
- `API_AUTH_ENABLED=true|false`
- `RATE_LIMIT_ENABLED=true|false`

Check the active runtime configuration:

```bash
curl -s http://localhost:8001/config | jq
```

## API example

```bash
curl -s -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session-1",
    "user_id": "user-42",
    "utterance": "I was charged twice last month and I also need to update the card on file."
  }' | jq
```

Inspect the stored session state:

```bash
curl -s http://localhost:8001/state/demo-session-1 | jq
```

## Multi-turn behavior

The service maintains structured dialogue state per `session_id`.

Typical flow:

1. User reports a billing issue.
2. System asks for authentication.
3. User provides OTP or identity confirmation.
4. Same session continues with different allowed next actions.

This demonstrates stateful orchestration rather than stateless prompting.

You can now inspect that state directly through:

- `GET /state/{session_id}` for the current structured session snapshot
- `turn_history` inside the state payload for a concise per-turn trace

### Demo walkthrough

Use these four calls with the same `session_id` to show the product behavior:

```bash
curl -s -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-state-001","user_id":"user-42","utterance":"I was charged twice last month and need to update card on file"}' | jq
```

```bash
curl -s -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-state-001","user_id":"user-42","utterance":"My OTP code is 123456, please proceed"}' | jq
```

```bash
curl -s -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-state-001","user_id":"user-42","utterance":"Please create the dispute now"}' | jq
```

```bash
curl -s http://localhost:8001/state/demo-state-001 | jq
```

What this demonstrates:

- multi-intent reasoning on turn 1
- authentication side effect on turn 2
- state-aware next action on turn 3
- inspectable state and turn trace after the flow

## Evaluation and quality gates

Run unit tests:

```bash
python -m pytest -q
```

Run lint:

```bash
python -m ruff check app eval tests scripts
```

Run evaluation:

```bash
PYTHONPATH=. python eval/evaluate.py
```

Run the full local quality gate bundle:

```bash
./scripts/ci_check.sh
```

This checks:

- code style and imports
- unit tests
- evaluation thresholds
- multi-turn conversation quality

## Security and safety controls

Optional controls included in the demo:

- API key authentication
- request rate limiting
- typed response validation
- policy gate before tool execution
- adjudicator fallback on upstream failure

## Deployment

### Docker

```bash
docker build -t nlu-reasoning-orchestrator .
docker run --rm -p 8000:8000 nlu-reasoning-orchestrator
```

### Cloud Run

```bash
./scripts/deploy_cloud_run.sh
```

The deployment defaults are tuned for low cost:

- `min-instances=0`
- `max-instances=1`
- `memory=512Mi`
- CPU always off when idle

## Architecture decisions

Architecture decision records live in [docs/adr/README.md](docs/adr/README.md).

A request-by-request system walkthrough is available in [docs/architecture.md](docs/architecture.md).

## Interview narrative

If you are using this for an interview, the strongest framing is:

> I built a small NLU reasoning orchestrator that separates fast intent detection, adjudication, dialogue state, policy validation, and tool execution. The goal is not to build a chatbot, but to show how LLM-based NLU can be productized safely inside an enterprise conversational AI platform.

## Development workflow

Common commands:

```bash
make install
make run
make ui
make test
make lint
make eval
make ci
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development guidance.

## License

This project is available under the [MIT License](LICENSE).
