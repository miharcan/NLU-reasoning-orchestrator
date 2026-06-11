#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON=.venv/bin/python
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
  else
    PYTHON=python
  fi
fi

PYTHONPATH=. "$PYTHON" -m ruff check app eval tests scripts
PYTHONPATH=. "$PYTHON" -m pytest -q
ADJUDICATOR_MODE=mock PYTHONPATH=. "$PYTHON" eval/quality_gate.py
ADJUDICATOR_MODE=mock PYTHONPATH=. "$PYTHON" eval/conversation_quality_gate.py
