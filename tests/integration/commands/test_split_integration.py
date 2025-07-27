"""Integration tests for the split command."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


class TestSplitCommandIntegration:
    """Integration tests for the split command using subprocess."""

    def test_split_help_output(self):
        """Test that split --help produces expected output."""
        result = subprocess.run(
            [sys.executable, "-m", "excelsior.cli", "split", "--help"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": "src"},
        )

        assert result.returncode == 0
        assert "Split Excel or CSV files" in result.stdout
        assert "--file" in result.stdout
        assert "--date-column" in result.stdout
        assert "--interval" in result.stdout
        assert "--output-dir" in result.stdout
        assert "--financial-year-start" in result.stdout
        assert "--sheet-config" in result.stdout

    def test_split_missing_date_column(self):
        """Test split command without date column or sheet config."""
        # Create a temporary CSV file
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
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert (
                "Either --date-column or --sheet-config must be provided"
                in result.stderr
            )
        finally:
            tmp_path.unlink()

    def test_split_invalid_financial_year(self):
        """Test split command with invalid financial year start."""
        # Create a temporary CSV file
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
                    "--financial-year-start",
                    "15",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 2  # argparse error exit code
            assert "must be between 1 and 12" in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_valid_financial_year(self):
        """Test split command with valid financial year start values."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_path = Path(tmp.name)

        try:
            # Test with valid financial year start (April = 4)
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
                    "--financial-year-start",
                    "4",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            assert "must be between 1 and 12" not in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_successful_execution(self):
        """Test successful split command execution (stub implementation)."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp.write("2024-02-20,250.50,Payment 2\n")
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
            assert "Starting split command" in result.stderr
            assert "Split command execution completed successfully" in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_with_different_intervals(self):
        """Test split command with different interval options."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp.write("2024-02-20,250.50,Payment 2\n")
            tmp_path = Path(tmp.name)

        intervals = ["day", "week", "month", "year", "financial-year"]

        for interval in intervals:
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
                        "--interval",
                        interval,
                        "--verbose",
                    ],
                    capture_output=True,
                    text=True,
                    env={"PYTHONPATH": "src"},
                )

                assert result.returncode == 0, f"Failed for interval: {interval}"
                assert "Starting split command" in result.stderr
            finally:
                # Clean up is handled after the loop
                pass

        # Clean up after all intervals tested
        tmp_path.unlink()

    def test_split_sheet_config_validation(self):
        """Test split command with invalid sheet config."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_file_path = Path(tmp_file.name)

        # Create invalid sheet config
        invalid_config = {"Sheet1": {"invalid_key": "value"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(invalid_config, tmp_config)
            tmp_config_path = Path(tmp_config.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_file_path),
                    "--sheet-config",
                    str(tmp_config_path),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 2  # argparse error exit code
            assert "Extra inputs are not permitted" in result.stderr
            assert "invalid_key" in result.stderr
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()

    def test_split_valid_sheet_config(self):
        """Test split command with valid sheet config."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_file_path = Path(tmp_file.name)

        # Create valid sheet config
        valid_config = {
            "Sheet1": {
                "date_column": "Date",
                "date_format": "%Y-%m-%d",
                "include": True,
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(valid_config, tmp_config)
            tmp_config_path = Path(tmp_config.name)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excelsior.cli",
                    "split",
                    "--file",
                    str(tmp_file_path),
                    "--sheet-config",
                    str(tmp_config_path),
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            assert "Invalid keys" not in result.stderr
            assert "Starting split command" in result.stderr
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()

    def test_split_with_output_directory(self):
        """Test split command with custom output directory."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp_path = Path(tmp.name)

        # Create a temporary output directory
        with tempfile.TemporaryDirectory() as output_dir:
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
                        "--output-dir",
                        output_dir,
                        "--verbose",
                    ],
                    capture_output=True,
                    text=True,
                    env={"PYTHONPATH": "src"},
                )

                assert result.returncode == 0
                assert "Starting split command" in result.stderr
            finally:
                tmp_path.unlink()
