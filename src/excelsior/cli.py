"""Main CLI interface for Excelsior."""

import argparse
import sys

from excelsior._version import __version__
from excelsior.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the main argument parser.

    Returns:
        argparse.ArgumentParser: The configured main parser
    """
    parser = argparse.ArgumentParser(
        prog="excelsior",
        description="A powerful CLI tool for Excel and CSV file operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  excelsior split --file data.xlsx --date-column "Date" --interval month
  excelsior --help

For more information about a specific command, use:
  excelsior <command> --help
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"excelsior {__version__}",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND",
    )

    # Automatically discover and register all commands
    _register_all_commands(subparsers)

    return parser


def _register_all_commands(subparsers: argparse._SubParsersAction) -> None:
    """Discover and register all available commands.

    This function automatically finds all command classes that inherit from
    BaseCommand and registers them with the CLI parser.

    Args:
        subparsers: The subparsers action from the main parser
    """
    import inspect

    # Import all command modules here
    # This ensures they are loaded and their classes are available
    from excelsior.commands import split  # noqa: F401
    from excelsior.commands.base import BaseCommand

    # Get all concrete subclasses of BaseCommand
    command_classes = _get_all_command_classes(BaseCommand)

    # Instantiate and register each concrete command
    for command_class in command_classes:
        # Skip abstract classes
        if inspect.isabstract(command_class):
            logger.debug(f"Skipping abstract command class: {command_class.__name__}")
            continue

        try:
            command = command_class()
            command.register(subparsers)
            logger.debug(f"Registered command: {command.name}")
        except Exception as e:
            logger.warning(f"Failed to register command {command_class.__name__}: {e}")


def _get_all_command_classes(base_class: type) -> list[type]:
    """Recursively get all subclasses of a base class.

    Args:
        base_class: The base class to find subclasses for

    Returns:
        list: List of all subclasses
    """
    subclasses = []
    for subclass in base_class.__subclasses__():
        subclasses.append(subclass)
        subclasses.extend(_get_all_command_classes(subclass))
    return subclasses


def main() -> int:
    """Main entry point for the CLI application.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    args = parser.parse_args()

    # Set up logging based on verbosity flags
    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)
    setup_logging(verbose=verbose, quiet=quiet)

    # Validate mutually exclusive options
    if verbose and quiet:
        logger.error("Cannot use --verbose and --quiet together")
        return 1

    # Execute the appropriate command
    try:
        if hasattr(args, "func"):
            return args.func(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
