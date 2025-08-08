# Excelsior Makefile
# Common development tasks

.PHONY: help install format lint check test test-unit test-integration test-edge test-fast test-coverage clean run

# Default target
help:
	@echo "Available targets:"
	@echo "  install          - Install the package in development mode"
	@echo "  format           - Format code with ruff"
	@echo "  lint             - Run linting with ruff"
	@echo "  check            - Check code formatting and run linting"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-edge        - Run edge case tests only"
	@echo "  test-fast        - Run fast tests (no integration)"
	@echo "  test-coverage    - Run tests with coverage reporting"
	@echo "  clean            - Clean up build artifacts"
	@echo "  run              - Show usage and available commands"
	@echo "  help             - Show this help message"

# Install package in development mode
install:
	uv sync --extra dev

# Format code with ruff
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Run linting with ruff
lint:
	uv run ruff check src/ tests/

# Check formatting and run linting
check:
	uv run ruff format --check src/ tests/
	uv run ruff check src/ tests/

# Run tests with pytest
test:
	uv run pytest tests/ --tb=short

# Run unit tests only
test-unit:
	uv run pytest tests/unit/ -v --tb=short

# Run integration tests only
test-integration:
	uv run pytest tests/integration/ -v --tb=short

# Run edge case tests only
test-edge:
	uv run pytest tests/unit/ -k "edge and not keyboard_interrupt" -v --tb=short

# Run fast tests (no integration)
test-fast:
	uv run pytest tests/unit/ -k "not keyboard_interrupt" -v --tb=short

# Run tests with coverage reporting
test-coverage:
	COVERAGE_FILE=out/.coverage uv run pytest tests/ \
		--cov=src/excelsior \
		--cov-report=term-missing \
		--cov-report=html:out/htmlcov \
		--tb=short

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf out/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run excelsior to show usage and available commands
run:
	@echo "Running excelsior CLI..."
	@echo "Usage: uv run excelsior <command> [options]"
	@echo ""
	@echo "Available commands and help:"
	uv run excelsior --help
