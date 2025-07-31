"""Unit tests for the base command classes."""

import argparse
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from excelsior.commands import BaseCommand, FileProcessingCommand


class TestBaseCommand:
    """Test the BaseCommand abstract base class."""

    @pytest.fixture
    def test_command_class(self):
        """Fixture that provides a concrete test command class."""

        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def help_text(self):
                return "A test command"

            @property
            def description(self):
                return "A test command for unit testing"

            @property
            def epilog(self):
                return "Test epilog with examples"

            def add_arguments(self, parser):
                parser.add_argument("--test-arg", help="Test argument")
                self._add_common_command_arguments(parser)

            def validate_args(self, args):
                # Call parent validation first (includes logging validation)
                parent_error = super().validate_args(args)
                if parent_error:
                    return parent_error

                # Add custom validation logic for testing
                if getattr(args, "test_invalid", False):
                    return "Test validation error"
                return None

            def execute(self, args):
                return 0

        return TestCommand

    def test_base_command_is_abstract(self):
        """Test that BaseCommand cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCommand()  # type: ignore

    def test_concrete_command_implementation(self, test_command_class):
        """Test that a concrete command implementation works correctly."""
        command = test_command_class()

        # Test that required properties are implemented
        assert command.name == "test"
        assert command.help_text == "A test command"
        assert command.description == "A test command for unit testing"
        assert command.epilog == "Test epilog with examples"

    def test_command_registration(self, test_command_class):
        """Test that a command can be registered with a parser."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        command = test_command_class()
        command.register(subparsers)

        # Test that the command was registered
        assert "test" in subparsers._name_parser_map

        # Test that we can access the test parser
        test_parser = subparsers._name_parser_map["test"]
        assert test_parser.prog.endswith("test")

    def test_validation_integration(self, test_command_class):
        """Test that validation works through the base class system."""
        command = test_command_class()

        # Test that logging validation works (from parent class)
        args = argparse.Namespace(
            verbose=True,
            quiet=True,
            test_invalid=False,
        )

        error = command.validate_args(args)
        assert error == "Cannot use --verbose and --quiet together"

        # Test with valid logging arguments but custom validation error
        args.verbose = True
        args.quiet = False
        args.test_invalid = True

        error = command.validate_args(args)
        assert error == "Test validation error"

        # Test with all valid arguments
        args.test_invalid = False
        error = command.validate_args(args)
        assert error is None

    def test_execute_with_validation_integration(self):
        """Test the _execute_with_validation method."""
        # Create a mock command for testing
        command = Mock(spec=BaseCommand)
        command.validate_args.return_value = None
        command.execute.return_value = 0
        command.logger = Mock()

        # Use the actual _execute_with_validation method
        result = BaseCommand._execute_with_validation(command, Mock())

        # Verify validation was called
        command.validate_args.assert_called_once()
        # Verify execute was called
        command.execute.assert_called_once()
        # Verify success
        assert result == 0

    def test_execute_with_validation_error(self):
        """Test _execute_with_validation with validation error."""
        # Create a mock command that fails validation
        command = Mock(spec=BaseCommand)
        command.validate_args.return_value = "Validation failed"
        command.logger = Mock()

        result = BaseCommand._execute_with_validation(command, Mock())

        # Verify validation was called
        command.validate_args.assert_called_once()
        # Verify execute was NOT called
        command.execute.assert_not_called()
        # Verify error was logged
        command.logger.error.assert_called_once_with("Validation failed")
        # Verify error code
        assert result == 1

    def test_validate_logging_args(self, test_command_class):
        """Test logging arguments validation."""
        test_command = test_command_class()

        # Test conflicting verbose/quiet
        args = argparse.Namespace(verbose=True, quiet=True)
        error = test_command._validate_logging_args(args)
        assert error == "Cannot use --verbose and --quiet together"

        # Test valid combinations
        args = argparse.Namespace(verbose=True, quiet=False)
        error = test_command._validate_logging_args(args)
        assert error is None

        args = argparse.Namespace(verbose=False, quiet=True)
        error = test_command._validate_logging_args(args)
        assert error is None


class TestFileProcessingCommand:
    """Test the FileProcessingCommand class."""

    def test_validate_file_path_success(self):
        """Test successful file path validation."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            result = FileProcessingCommand.validate_file_path(
                str(tmp_path), [".csv", ".xlsx"]
            )
            assert result == tmp_path
        finally:
            tmp_path.unlink()

    def test_validate_file_path_nonexistent(self):
        """Test file path validation with nonexistent file."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            FileProcessingCommand.validate_file_path("nonexistent.csv", [".csv"])
        assert "File not found" in str(exc_info.value)

    def test_validate_file_path_unsupported_format(self):
        """Test file path validation with unsupported format."""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(argparse.ArgumentTypeError) as exc_info:
                FileProcessingCommand.validate_file_path(
                    str(tmp_path), [".csv", ".xlsx"]
                )
            assert "Unsupported file format" in str(exc_info.value)
        finally:
            tmp_path.unlink()
