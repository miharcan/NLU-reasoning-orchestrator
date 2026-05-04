PYTHONPATH := .

.PHONY: install run ui test lint eval ci

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --port 8001

ui:
	streamlit run ui/streamlit_app.py

test:
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q

lint:
	PYTHONPATH=$(PYTHONPATH) python -m ruff check app eval tests scripts

eval:
	ADJUDICATOR_MODE=mock PYTHONPATH=$(PYTHONPATH) python eval/evaluate.py

ci:
	./scripts/ci_check.sh
