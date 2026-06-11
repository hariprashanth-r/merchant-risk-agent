# Friendly shortcuts. Run `make help` to see them.

.PHONY: help install web serve test ofac

help:
	@echo "make install   - install dependencies"
	@echo "make web        - open the ADK dev playground (no frontend needed)"
	@echo "make serve      - run the full-stack app at http://localhost:8000"
	@echo "make test       - run the tool tests"
	@echo "make ofac       - download the real OFAC sanctions list"

install:
	pip install -r requirements.txt

web:
	adk web

serve:
	uvicorn server.main:app --reload

test:
	pytest -q

ofac:
	python scripts/download_ofac.py
