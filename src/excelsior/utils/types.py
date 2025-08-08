"""Shared type definitions for Excelsior CLI."""

from typing import Literal

# Type alias for time intervals used in the split command
SplitInterval = Literal["day", "week", "month", "year", "financial-year"]
