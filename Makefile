# Clarion - TrustSec Policy Copilot
# Common development commands

.PHONY: help install dev test lint format typecheck clean api notebook

PYTHON := python3
PIP := pip

help:
	@echo "Clarion - TrustSec Policy Copilot"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install    Install production dependencies"
	@echo "  dev        Install all dependencies (including dev)"
	@echo "  test       Run test suite"
	@echo "  lint       Run linter (ruff)"
	@echo "  format     Format code (black + ruff)"
	@echo "  typecheck  Run type checker (mypy)"
	@echo "  clean      Remove generated files"
	@echo "  api        Start API server (development)"
	@echo "  notebook   Start Jupyter notebook server"
	@echo "  load       Load sample data"
	@echo "  analyze    Run analysis on loaded data"

install:
	$(PIP) install -r requirements.txt

dev:
	$(PIP) install -e ".[dev,viz]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src/clarion --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf src/clarion/__pycache__
	rm -rf data/processed/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

api:
	python scripts/run_api.py --port 8000

notebook:
	jupyter notebook notebooks/

load:
	$(PYTHON) -m src.scripts.load_data

analyze:
	$(PYTHON) -m src.scripts.analyze

# Quick check before commit
check: format lint typecheck test
	@echo "All checks passed!"

