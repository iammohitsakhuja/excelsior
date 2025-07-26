"""Version information for Excelsior."""

import importlib.metadata
import pathlib
from contextlib import suppress

import tomllib


def get_version():
    """
    Retrieve the version of the 'excelsior' package.

    This function attempts to determine the current version of the 'excelsior' package
    using the following strategies, in order:
    1. Try to obtain the version from the installed package metadata.
    2. If that fails, attempt to read the version from the 'pyproject.toml' file,
        supporting both PEP 621 ('project.version') and Poetry ('tool.poetry.version') formats.
    3. If neither method succeeds, return "unknown".

    Returns:
         str: The version string if found, otherwise "unknown".
    """
    # First try to get version from installed package
    with suppress(Exception):
        return importlib.metadata.version("excelsior")

    # Fallback to reading from pyproject.toml
    source_location = pathlib.Path(__file__).parent.parent
    pyproject_path = source_location.parent / "pyproject.toml"

    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        if "project" in data and "version" in data["project"]:
            return data["project"]["version"]
        elif (
            "tool" in data
            and "poetry" in data["tool"]
            and "version" in data["tool"]["poetry"]
        ):
            return data["tool"]["poetry"]["version"]

    return "unknown"


__version__ = get_version()
