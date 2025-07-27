"""Base command class for Excelsior CLI commands."""

import argparse
from abc import ABC, abstractmethod

from excelsior.utils.logger import get_logger


class BaseCommand(ABC):
    """Abstract base class for all Excelsior CLI commands.

    This class provides a consistent interface for all commands and handles
    common functionality like logging setup and argument validation.
    """

    def __init__(self) -> None:
        """Initialize the base command."""
        self.logger = get_logger(self.__class__.__module__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the command name (used for CLI registration)."""
        pass

    @property
    @abstractmethod
    def help_text(self) -> str:
        """Return the short help text for the command."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the detailed description for the command."""
        pass

    @property
    def epilog(self) -> str | None:
        """Return the epilog text (examples, additional info) for the command.

        Override this method to provide command-specific examples and usage patterns.
        """
        return None

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to the parser.

        Args:
            parser: The argument parser to add arguments to
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command with the given arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        pass

    def validate_args(self, args: argparse.Namespace) -> str | None:
        """Validate command arguments after parsing.

        Override this method to provide custom validation logic that cannot
        be handled by argparse alone.

        Args:
            args: Parsed command line arguments

        Returns:
            Optional[str]: Error message if validation fails, None if successful
        """
        return None

    def register(self, subparsers: argparse._SubParsersAction) -> None:
        """Register this command with the main CLI parser.

        Args:
            subparsers: The subparsers action from the main parser
        """
        parser = subparsers.add_parser(
            self.name,
            help=self.help_text,
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self.epilog,
        )

        # Add command-specific arguments
        self.add_arguments(parser)

        # Set the function to call when this command is used
        parser.set_defaults(func=self._execute_with_validation)

    def _execute_with_validation(self, args: argparse.Namespace) -> int:
        """Internal method that handles validation before executing the command.

        Args:
            args: Parsed command line arguments

        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        # Perform custom validation
        validation_error = self.validate_args(args)
        if validation_error:
            self.logger.error(validation_error)
            return 1

        # Execute the command
        try:
            return self.execute(args)
        except KeyboardInterrupt:
            self.logger.info("Command cancelled by user")
            return 130
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            if getattr(args, "verbose", False):
                self.logger.exception("Full traceback:")
            return 1


class FileProcessingCommand(BaseCommand):
    """Base class for commands that process files.

    This class provides common functionality for commands that work with
    input files and generate output files.
    """

    @staticmethod
    def validate_file_path(value: str, supported_extensions: list[str]):
        """Validate that a file path exists and has a supported format.

        Args:
            value: String path to the file
            supported_extensions: List of supported file extensions (e.g., ['.xlsx', '.csv'])

        Returns:
            Path: The validated file path

        Raises:
            argparse.ArgumentTypeError: If the file doesn't exist or has unsupported format
        """
        from pathlib import Path

        path = Path(value)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"File not found: {path}")
        if not path.is_file():
            raise argparse.ArgumentTypeError(f"Path is not a file: {path}")
        if path.suffix.lower() not in supported_extensions:
            raise argparse.ArgumentTypeError(
                f"Unsupported file format: {path.suffix}. "
                f"Supported formats: {', '.join(supported_extensions)}"
            )
        return path

    def add_common_file_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add common file processing arguments.

        Args:
            parser: The argument parser to add arguments to
        """
        # Logging options (common to all commands)
        logging_group = parser.add_argument_group("logging options")

        logging_group.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable detailed logging output",
        )

        logging_group.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Suppress all but error messages",
        )

    def validate_logging_args(self, args: argparse.Namespace) -> str | None:
        """Validate logging arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            Optional[str]: Error message if validation fails, None if successful
        """
        if getattr(args, "verbose", False) and getattr(args, "quiet", False):
            return "Cannot use --verbose and --quiet together"
        return None
