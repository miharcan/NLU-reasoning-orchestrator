# Contributing

Thanks for your interest in improving `nlu-reasoning-orchestrator`.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local development

Run the API:

```bash
uvicorn app.main:app --reload --port 8001
```

Run the UI:

```bash
streamlit run ui/streamlit_app.py
```

Or start the full local stack:

```bash
./scripts/local_stack.sh up
```

## Quality bar

Before opening a pull request, run:

```bash
./scripts/ci_check.sh
```

This repository expects:

- `ruff` to pass
- `pytest` to pass
- evaluation quality gates to stay above thresholds
- public-facing docs to stay aligned with runtime behavior

## Pull request guidance

- Keep changes focused and explain the product reason for the change.
- Add or update tests when behavior changes.
- Prefer deterministic, typed interfaces over free-form responses.
- Preserve the separation between NLU, adjudication, policy, state, and tools.
