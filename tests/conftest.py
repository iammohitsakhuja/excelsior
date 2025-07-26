"""Test fixtures and utilities shared across tests."""

from pathlib import Path


# Shared mixin for test classes
class VenvPythonMixin:
    """Mixin to provide venv python path resolution for tests."""

    def _get_venv_python_path(self) -> Path:
        """Get the path to the virtual environment's Python executable."""
        import os

        if os.name == "nt":  # Windows
            return Path.cwd() / ".venv" / "Scripts" / "python.exe"
        else:  # Unix-like systems
            return Path.cwd() / ".venv" / "bin" / "python"
