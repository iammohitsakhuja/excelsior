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
        assert "--conflict-resolution" in result.stdout
        assert "--financial-year-start" in result.stdout
        assert "--include" in result.stdout
        assert "--exclude" in result.stdout
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
                    "--output-dir",
                    "out/tests/split",
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
                    "--output-dir",
                    "out/tests/split",
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
                        "--output-dir",
                        "out/tests/split",
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
                    "--output-dir",
                    "out/tests/split",
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

    def test_split_include_exclude_flag_conflict(self):
        """Test that using both --include and --exclude flags causes an error."""
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
                    "--include",
                    "Sheet1",
                    "--exclude",
                    "Sheet2",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use multiple sheet selection flags together" in result.stderr
            assert "--include" in result.stderr
            assert "--exclude" in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_include_sheet_config_flag_conflict(self):
        """Test that using both --include and --sheet-config flags causes an error."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_file_path = Path(tmp_file.name)

        # Create a temporary config file
        config_data = {"Sheet1": {"date_column": "Date", "include": True}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(config_data, tmp_config)
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
                    "--include",
                    "Sheet1",
                    "--sheet-config",
                    str(tmp_config_path),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use multiple sheet selection flags together" in result.stderr
            assert "--include" in result.stderr
            assert "--sheet-config" in result.stderr
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()

    def test_split_exclude_sheet_config_flag_conflict(self):
        """Test that using both --exclude and --sheet-config flags causes an error."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_file_path = Path(tmp_file.name)

        # Create a temporary config file
        config_data = {"Sheet1": {"date_column": "Date", "include": True}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(config_data, tmp_config)
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
                    "--exclude",
                    "Sheet2",
                    "--sheet-config",
                    str(tmp_config_path),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use multiple sheet selection flags together" in result.stderr
            assert "--exclude" in result.stderr
            assert "--sheet-config" in result.stderr
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()

    def test_split_all_three_flags_conflict(self):
        """Test that using all three sheet selection flags causes an error."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write("Date,Amount\n2024-01-01,100.00\n")
            tmp_file_path = Path(tmp_file.name)

        # Create a temporary config file
        config_data = {"Sheet1": {"date_column": "Date", "include": True}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(config_data, tmp_config)
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
                    "--include",
                    "Sheet1",
                    "--exclude",
                    "Sheet2",
                    "--sheet-config",
                    str(tmp_config_path),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 1
            assert "Cannot use multiple sheet selection flags together" in result.stderr
            assert "--include" in result.stderr
            assert "--exclude" in result.stderr
            assert "--sheet-config" in result.stderr
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()

    def test_split_valid_include_flag_only(self):
        """Test that using only --include flag works correctly."""
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
                    "--include",
                    "Sheet1",
                    "--output-dir",
                    "out/tests/split",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            assert (
                "Cannot use multiple sheet selection flags together"
                not in result.stderr
            )
            assert "Starting split command" in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_valid_exclude_flag_only(self):
        """Test that using only --exclude flag works correctly."""
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
                    "--exclude",
                    "Sheet2",
                    "--output-dir",
                    "out/tests/split",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result.returncode == 0
            assert (
                "Cannot use multiple sheet selection flags together"
                not in result.stderr
            )
            assert "Starting split command" in result.stderr
        finally:
            tmp_path.unlink()

    def test_split_conflict_resolution_overwrite(self):
        """Test split command with overwrite conflict resolution."""
        import shutil

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp_path = Path(tmp.name)

        # Create temporary output directory
        output_dir = Path(tempfile.mkdtemp())

        try:
            # First run to create initial files
            result1 = subprocess.run(
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
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )
            assert result1.returncode == 0

            # Get the created file and its modification time
            output_files = list(output_dir.glob("*.csv"))
            assert len(output_files) == 1
            original_file = output_files[0]
            original_mtime = original_file.stat().st_mtime

            # Wait a bit to ensure different modification time
            import time

            time.sleep(0.1)

            # Second run with overwrite strategy
            result2 = subprocess.run(
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
                    str(output_dir),
                    "--conflict-resolution",
                    "overwrite",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result2.returncode == 0
            assert "Split command execution completed successfully" in result2.stderr

            # Verify file was overwritten (modification time should be different)
            new_mtime = original_file.stat().st_mtime
            assert new_mtime > original_mtime

            # Should still have only one file
            output_files_after = list(output_dir.glob("*.csv"))
            assert len(output_files_after) == 1

        finally:
            tmp_path.unlink()
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_split_conflict_resolution_rename(self):
        """Test split command with rename conflict resolution."""
        import shutil

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp_path = Path(tmp.name)

        # Create temporary output directory
        output_dir = Path(tempfile.mkdtemp())

        try:
            # First run to create initial files
            result1 = subprocess.run(
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
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )
            assert result1.returncode == 0

            # Verify one file was created
            output_files = list(output_dir.glob("*.csv"))
            assert len(output_files) == 1
            original_file = output_files[0]

            # Second run with rename strategy (default behavior)
            result2 = subprocess.run(
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
                    str(output_dir),
                    "--conflict-resolution",
                    "rename",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            assert result2.returncode == 0
            assert "Split command execution completed successfully" in result2.stderr

            # Should now have two files (original + renamed)
            output_files_after = list(output_dir.glob("*.csv"))
            assert len(output_files_after) == 2

            # Original file should still exist
            assert original_file.exists()

            # New file should have _1 suffix
            renamed_files = [f for f in output_files_after if f != original_file]
            assert len(renamed_files) == 1
            assert "_1.csv" in renamed_files[0].name

        finally:
            tmp_path.unlink()
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_split_conflict_resolution_skip(self):
        """Test split command with skip conflict resolution."""
        import shutil

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-15,100.00,Payment 1\n")
            tmp_path = Path(tmp.name)

        # Create temporary output directory
        output_dir = Path(tempfile.mkdtemp())

        try:
            # First run to create initial files
            result1 = subprocess.run(
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
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )
            assert result1.returncode == 0

            # Verify one file was created
            output_files = list(output_dir.glob("*.csv"))
            assert len(output_files) == 1
            original_file = output_files[0]
            original_mtime = original_file.stat().st_mtime

            # Second run with skip strategy - should fail
            result2 = subprocess.run(
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
                    str(output_dir),
                    "--conflict-resolution",
                    "skip",
                ],
                capture_output=True,
                text=True,
                env={"PYTHONPATH": "src"},
            )

            # Should fail with error about existing file
            assert result2.returncode == 1
            assert "already exists" in result2.stderr

            # Original file should be unchanged
            assert original_file.exists()
            assert original_file.stat().st_mtime == original_mtime

            # Should still have only one file
            output_files_after = list(output_dir.glob("*.csv"))
            assert len(output_files_after) == 1

        finally:
            tmp_path.unlink()
            shutil.rmtree(output_dir, ignore_errors=True)
