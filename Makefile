.PHONY: help install install-dev test lint format clean run

PYTHON := python3
PIP := pip

help:
	@echo "MoMo-Nexus Development Commands"
	@echo "================================"
	@echo "install      Install production dependencies"
	@echo "install-dev  Install development dependencies"
	@echo "test         Run tests"
	@echo "test-cov     Run tests with coverage"
	@echo "lint         Run linter"
	@echo "format       Format code"
	@echo "clean        Clean build artifacts"
	@echo "run          Run Nexus"

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/nexus --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

run:
	$(PYTHON) -m nexus.cli run

