# Local development. No Docker required — SQLite, in-memory cache, eager Celery.
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help venv install migrate seed run test lint fmt typecheck check gate coverage clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtualenv
	python3 -m venv .venv && $(PIP) install --upgrade pip

install: ## Install runtime + dev dependencies
	$(PIP) install -e ".[dev]"

migrate: ## Apply database migrations
	$(PY) manage.py migrate

seed: ## Create the baseline branch, hours, settings and role groups
	$(PY) manage.py seed_initial

run: ## Start the development server
	$(PY) manage.py runserver

test: ## Run the test suite
	$(PY) -m pytest

coverage: ## Enforce the coverage gates (85% overall, 100% on every money path)
	$(PY) -m pytest --cov=apps --cov-report=term-missing --cov-fail-under=85
	$(PY) -m pytest apps/common/tests/test_money.py --cov=apps.common.money --cov-fail-under=100
	$(PY) -m pytest apps/carts apps/promotions apps/orders apps/payments \
		--cov=apps.carts.services --cov=apps.promotions.services \
		--cov=apps.orders.services --cov=apps.payments.services \
		--cov=apps.payments.tasks \
		--cov-report=term-missing --cov-fail-under=100

lint: ## Lint
	.venv/bin/ruff check .

fmt: ## Format
	.venv/bin/ruff format .

typecheck: ## Type-check application code (paths come from pyproject)
	.venv/bin/mypy

gate: ## PCI card-field gate
	./scripts/check-no-card-fields.sh

check: lint typecheck test gate ## Everything CI runs
	$(PY) manage.py check --deploy --fail-level WARNING --settings=config.settings.prod || true

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
