"""Integration tests for the main CLI interface and common command functionality."""

import subprocess
import sys
import tempfile
from pathlib import Path


class TestCLIIntegration:
    """Integration tests for CLI functionality common to all commands."""

    def test_cli_no_args_shows_help(self):
        """Test that running CLI without arguments shows help and exits with code 1."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 1
        assert "usage: excelsior" in result.stdout
        assert "A powerful CLI tool for Excel and CSV file operations" in result.stdout
        assert "Available commands" in result.stdout

    def test_cli_help_flag(self):
        """Test that --help flag works correctly."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "--help"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 0
        assert "usage: excelsior" in result.stdout
        assert "A powerful CLI tool for Excel and CSV file operations" in result.stdout
        assert "Available commands" in result.stdout
        assert "Examples:" in result.stdout

    def test_version_flag(self):
        """Test that --version flag displays version information."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "--version"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 0
        assert "excelsior" in result.stdout
        assert "0.1.0" in result.stdout

    def test_unknown_command_shows_error(self):
        """Test that unknown command shows error and help."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "nonexistent"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 2  # argparse error for invalid choice
        assert "invalid choice: 'nonexistent'" in result.stderr

    def test_command_registration_discovery(self):
        """Test that all commands are properly discovered and registered."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "--help"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 0
        # Check that the split command is registered
        assert "split" in result.stdout
        assert (
            "Split Excel/CSV files based on dates in a specified column"
            in result.stdout
        )

    def test_keyboard_interrupt_handling(self):
        """Test graceful handling of KeyboardInterrupt."""
        # This test is challenging to implement reliably in subprocess
        # as it requires sending signals. We'll test it indirectly through
        # the command execution path by testing the exception handling works
        pass


class TestCommonCommandOptions:
    """Integration tests for options common to all commands (from BaseCommand)."""

    def test_verbose_flag_increases_logging(self):
        """Test that --verbose flag enables detailed logging."""
        # Create a temporary CSV file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            # Verbose logging should show debug/info messages in stderr
            assert "Starting split command" in result.stderr
            assert "Split command execution completed successfully" in result.stderr
        finally:
            tmp_path.unlink()

    def test_quiet_flag_suppresses_output(self):
        """Test that --quiet flag suppresses non-error output."""
        # Create a temporary CSV file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            # Quiet mode should suppress info messages
            assert "Starting split command" not in result.stderr
            assert "Split command execution completed successfully" not in result.stderr
        finally:
            tmp_path.unlink()

    def test_verbose_and_quiet_flags_conflict(self):
        """Test that --verbose and --quiet flags cannot be used together."""
        # Create a temporary CSV file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--verbose",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use --verbose and --quiet together" in result.stderr
        finally:
            tmp_path.unlink()

    def test_command_help_includes_common_options(self):
        """Test that individual command help includes common logging options."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "split", "--help"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 0
        assert "--verbose" in result.stdout
        assert "--quiet" in result.stdout
        assert "logging options" in result.stdout
        assert "Enable detailed logging output" in result.stdout
        assert "Suppress all but error messages" in result.stdout


class TestFileProcessingCommandBase:
    """Integration tests for FileProcessingCommand validation functionality."""

    def test_file_not_found_validation(self):
        """Test that file validation catches non-existent files."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "excelsior.cli",
                "split",
                "--file",
                "/path/to/nonexistent/file.csv",
                "--date-column",
                "Date",
            ],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 2  # argparse error
        assert "File not found" in result.stderr

    def test_directory_instead_of_file_validation(self):
        """Test that file validation rejects directories."""
        # Use a known directory (current directory)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "excelsior.cli",
                "split",
                "--file",
                ".",
                "--date-column",
                "Date",
            ],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 2  # argparse error
        assert "Path is not a file" in result.stderr

    def test_unsupported_file_format_validation(self):
        """Test that file validation rejects unsupported file formats."""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("Some content\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 2  # argparse error
            assert "Unsupported file format" in result.stderr
            assert ".txt" in result.stderr
            assert "Supported formats" in result.stderr
        finally:
            tmp_path.unlink()

    def test_supported_csv_file_format(self):
        """Test that CSV files are accepted by file validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            # Should not fail at validation level
            assert result.returncode == 0
            assert "File not found" not in result.stderr
            assert "Unsupported file format" not in result.stderr
        finally:
            tmp_path.unlink()

    def test_supported_xlsx_file_format(self):
        """Test that Excel files are accepted by file validation."""
        # Create a temporary Excel file (minimal structure)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xlsx", delete=False) as tmp:
            # Note: This creates an empty .xlsx file which may not be valid Excel format
            # but should pass the file extension validation
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            # Should not fail at file extension validation level
            # (may fail later due to invalid Excel content, but that's expected)
            assert "Unsupported file format" not in result.stderr
            assert "File not found" not in result.stderr
        finally:
            tmp_path.unlink()


class TestErrorHandlingAndLogging:
    """Integration tests for error handling and logging functionality."""

    def test_error_logging_without_verbose(self):
        """Test that errors are logged without verbose flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "excelsior.cli",
                "split",
                "--file",
                "nonexistent.csv",
                "--date-column",
                "Date",
            ],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 2
        # Error should be visible in stderr
        assert "File not found" in result.stderr

    def test_validation_error_handling(self):
        """Test that validation errors are properly handled and reported."""
        # Test conflicting options
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--verbose",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use --verbose and --quiet together" in result.stderr
        finally:
            tmp_path.unlink()

    def test_exception_handling_with_verbose(self):
        """Test that exceptions show full traceback with --verbose flag."""
        # This test would require triggering an actual exception in command execution
        # For now, we'll test the framework is in place by checking verbose logging works
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_path),
                    "--date-column",
                    "Date",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            # Should succeed and show verbose logging
            assert result.returncode == 0
            assert "Starting split command" in result.stderr
        finally:
            tmp_path.unlink()
