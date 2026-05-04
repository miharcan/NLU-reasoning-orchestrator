#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=. python -m ruff check app eval tests scripts
PYTHONPATH=. python -m pytest -q
ADJUDICATOR_MODE=mock PYTHONPATH=. python eval/quality_gate.py
ADJUDICATOR_MODE=mock PYTHONPATH=. python eval/conversation_quality_gate.py
