---
applyTo: "tests/**/*.py"
---

# Copilot Testing Instructions for Excelsior

**Project Overview**

Excelsior is a Python CLI application for working with Excel and CSV files.

**Tools & Configuration**

* Python 3.13+
* `uv` for package management and virtual environment
* `pytest` with comprehensive configuration in `pyproject.toml`
* `ruff` for formatting and linting
* `argparse` for CLI, `dataclasses` for structured data
* `make` commands for development tasks (formatting, linting, testing)

**Testing Standards and Conventions**

* Follow AAA pattern: Arrange, Act, Assert
* Clear, descriptive test names (e.g., `test_cli_fails_on_empty_vault()`)
* Prefer real data and subprocess in integration tests
* Minimize mocks — only mock I/O, subprocess, or system dependencies
* Group related tests in classes with short docstrings
* Use shared fixtures via `conftest.py`
* **Do not include full project structure** in documentation as it's evolving

**Integration Test Practices**

* Test actual CLI behavior using subprocess
* Use real file I/O for input and output validation
* Avoid mocking in integration tests unless external system behavior must be isolated
* Cover multiple CLI argument combinations and output formats (CSV, JSON, table)

**Maintenance Guidelines**

* Keep tests self-explanatory and in sync with core application structure
* Maintain test documentation in `docs/test-suite.md`
* Do not auto-generate summary files — keep documentation minimal and focused
