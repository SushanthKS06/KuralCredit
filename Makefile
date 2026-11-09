PYTHON ?= python
NPM ?= npm

.PHONY: install install-backend install-frontend dev-backend dev-frontend check-config demo-docs test test-backend test-frontend lint typecheck smoke eval verify docker-up docker-down

install: install-backend install-frontend

install-backend:
	$(PYTHON) -m pip install -e "backend[dev]"

install-frontend:
	$(NPM) install

dev-backend:
	$(PYTHON) -m uvicorn app.main:app --reload --app-dir backend --port 8000

dev-frontend:
	$(NPM) --workspace frontend run dev

check-config:
	$(PYTHON) scripts/check_config.py

demo-docs:
	$(PYTHON) scripts/create_synthetic_documents.py

test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest backend/tests

test-frontend:
	$(NPM) --workspace frontend run test -- --run

lint:
	$(PYTHON) -m ruff check backend scripts

typecheck:
	$(NPM) --workspace frontend run typecheck

smoke:
	$(PYTHON) scripts/run_provider_smoke_tests.py

eval:
	$(PYTHON) scripts/run_evaluation.py

verify:
	$(PYTHON) scripts/verify_submission.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down
