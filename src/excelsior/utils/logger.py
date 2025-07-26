"""Logging utilities for Excelsior."""

import logging


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Set up logging configuration based on verbosity level.

    Args:
        verbose: If True, enable debug-level logging
        quiet: If True, suppress all but error messages
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress verbose logs from third-party libraries unless in debug mode
    if not verbose:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: The name for the logger (usually __name__)

    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
