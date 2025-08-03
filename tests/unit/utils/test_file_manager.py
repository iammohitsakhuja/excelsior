"""Unit tests for FileOutputManager."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from excelsior.utils.file_manager import (
    ConflictResolution,
    FileOutputError,
    FileOutputManager,
)


class TestFileOutputManager:
    """Test FileOutputManager functionality."""

    def test_init_sets_properties(self):
        """Test FileOutputManager initialization sets correct properties."""
        output_dir = Path("/tmp/test")
        conflict_resolution = ConflictResolution.OVERWRITE

        manager = FileOutputManager(output_dir, conflict_resolution)

        assert manager.output_dir == output_dir
        assert manager.conflict_resolution == conflict_resolution

    def test_init_defaults_to_rename_conflict_resolution(self):
        """Test FileOutputManager defaults to RENAME conflict resolution."""
        output_dir = Path("/tmp/test")

        manager = FileOutputManager(output_dir)

        assert manager.conflict_resolution == ConflictResolution.RENAME


class TestEnsureOutputDirectory:
    """Test output directory creation and validation."""

    def test_creates_directory_when_not_exists(self, tmp_path):
        """Test creates directory when it doesn't exist."""
        output_dir = tmp_path / "new_dir"
        manager = FileOutputManager(output_dir)

        manager.ensure_output_directory()

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_creates_nested_directory_structure(self, tmp_path):
        """Test creates nested directory structure."""
        output_dir = tmp_path / "parent" / "child" / "grandchild"
        manager = FileOutputManager(output_dir)

        manager.ensure_output_directory()

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_succeeds_when_directory_already_exists(self, tmp_path):
        """Test succeeds when directory already exists."""
        output_dir = tmp_path / "existing_dir"
        output_dir.mkdir()
        manager = FileOutputManager(output_dir)

        manager.ensure_output_directory()

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_raises_error_when_path_not_writable(self, tmp_path):
        """Test raises error when path is not writable."""
        output_dir = tmp_path / "readonly_dir"
        output_dir.mkdir()
        # Make directory read-only
        output_dir.chmod(0o444)
        manager = FileOutputManager(output_dir)

        with pytest.raises(FileOutputError, match="not writable"):
            manager.ensure_output_directory()

        # Restore permissions for cleanup
        output_dir.chmod(0o755)


class TestGenerateFilename:
    """Test filename generation based on naming conventions."""

    def test_generate_filename_day_interval(self):
        """Test filename generation for day interval."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        filename = manager.generate_filename("sales_data.xlsx", "day", test_date)

        assert filename == "sales_data_2023-05-15.xlsx"

    def test_generate_filename_week_interval(self):
        """Test filename generation for week interval."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)  # Week 20 of 2023

        filename = manager.generate_filename("sales_data.xlsx", "week", test_date)

        assert filename == "sales_data_2023-W20.xlsx"

    def test_generate_filename_month_interval(self):
        """Test filename generation for month interval."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        filename = manager.generate_filename("sales_data.xlsx", "month", test_date)

        assert filename == "sales_data_2023-05.xlsx"

    def test_generate_filename_year_interval(self):
        """Test filename generation for year interval."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        filename = manager.generate_filename("sales_data.xlsx", "year", test_date)

        assert filename == "sales_data_2023.xlsx"

    def test_generate_filename_financial_year_interval(self):
        """Test filename generation for financial year interval."""
        manager = FileOutputManager(Path("/tmp"))

        # Test date in April (FY 2023-2024 with April start)
        test_date = date(2023, 6, 15)
        filename = manager.generate_filename(
            "sales_data.xlsx", "financial-year", test_date, 4
        )

        assert filename == "sales_data_FY2023-2024.xlsx"

    def test_generate_filename_financial_year_before_start_month(self):
        """Test financial year filename when date is before start month."""
        manager = FileOutputManager(Path("/tmp"))

        # Test date in January (FY 2022-2023 with April start)
        test_date = date(2023, 1, 15)
        filename = manager.generate_filename(
            "sales_data.xlsx", "financial-year", test_date, 4
        )

        assert filename == "sales_data_FY2022-2023.xlsx"

    def test_generate_filename_with_extension_preserved(self):
        """Test filename generation preserves original extension."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        # Test with Excel extension
        excel_filename = manager.generate_filename("data.xlsx", "month", test_date)
        assert excel_filename == "data_2023-05.xlsx"

        # Test with CSV extension
        csv_filename = manager.generate_filename("data.csv", "month", test_date)
        assert csv_filename == "data_2023-05.csv"

    def test_generate_filename_csv_format(self):
        """Test filename generation with CSV file."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        filename = manager.generate_filename("data.csv", "month", test_date)

        assert filename == "data_2023-05.csv"

    def test_generate_filename_unsupported_interval_raises_error(self):
        """Test unsupported interval raises FileOutputError."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        with pytest.raises(FileOutputError, match="Unsupported interval"):
            manager.generate_filename("data.xlsx", "invalid", test_date)  # type: ignore


class TestResolveOutputPath:
    """Test output path resolution and conflict handling."""

    def test_returns_path_when_file_not_exists(self, tmp_path):
        """Test returns original path when file doesn't exist."""
        manager = FileOutputManager(tmp_path)
        filename = "new_file.xlsx"

        result_path = manager.resolve_output_path(filename)

        assert result_path == tmp_path / filename

    def test_overwrite_strategy_returns_existing_path(self, tmp_path):
        """Test OVERWRITE strategy returns existing path."""
        manager = FileOutputManager(tmp_path, ConflictResolution.OVERWRITE)
        filename = "existing_file.xlsx"
        existing_file = tmp_path / filename
        existing_file.touch()

        result_path = manager.resolve_output_path(filename)

        assert result_path == existing_file

    def test_skip_strategy_raises_error_for_existing_file(self, tmp_path):
        """Test SKIP strategy raises error for existing file."""
        manager = FileOutputManager(tmp_path, ConflictResolution.SKIP)
        filename = "existing_file.xlsx"
        existing_file = tmp_path / filename
        existing_file.touch()

        with pytest.raises(FileOutputError, match="already exists"):
            manager.resolve_output_path(filename)

    def test_rename_strategy_generates_unique_name(self, tmp_path):
        """Test RENAME strategy generates unique filename."""
        manager = FileOutputManager(tmp_path, ConflictResolution.RENAME)
        filename = "existing_file.xlsx"
        existing_file = tmp_path / filename
        existing_file.touch()

        result_path = manager.resolve_output_path(filename)

        assert result_path == tmp_path / "existing_file_1.xlsx"
        assert not result_path.exists()

    def test_rename_strategy_handles_multiple_conflicts(self, tmp_path):
        """Test RENAME strategy handles multiple existing files."""
        manager = FileOutputManager(tmp_path, ConflictResolution.RENAME)
        filename = "file.xlsx"

        # Create multiple existing files
        (tmp_path / "file.xlsx").touch()
        (tmp_path / "file_1.xlsx").touch()
        (tmp_path / "file_2.xlsx").touch()

        result_path = manager.resolve_output_path(filename)

        assert result_path == tmp_path / "file_3.xlsx"


class TestWriteDataFrame:
    """Test DataFrame writing functionality."""

    def test_write_csv_creates_file(self, tmp_path):
        """Test writing DataFrame to CSV creates file."""
        manager = FileOutputManager(tmp_path)
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        filename = "test.csv"

        result_path = manager.write_dataframe(df, filename)

        assert result_path.exists()
        assert result_path.suffix == ".csv"

        # Verify content
        written_df = pd.read_csv(result_path)
        pd.testing.assert_frame_equal(df, written_df)

    def test_write_excel_creates_file(self, tmp_path):
        """Test writing DataFrame to Excel creates file."""
        manager = FileOutputManager(tmp_path)
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        filename = "test.xlsx"

        result_path = manager.write_dataframe(df, filename)

        assert result_path.exists()
        assert result_path.suffix == ".xlsx"

        # Verify content
        written_df = pd.read_excel(result_path)
        pd.testing.assert_frame_equal(df, written_df)

    def test_write_excel_with_custom_sheet_name(self, tmp_path):
        """Test writing Excel file with custom sheet name."""
        manager = FileOutputManager(tmp_path)
        df = pd.DataFrame({"A": [1, 2, 3]})
        filename = "test.xlsx"
        sheet_name = "CustomSheet"

        result_path = manager.write_dataframe(df, filename, sheet_name)

        # Verify sheet name
        excel_file = pd.ExcelFile(result_path)
        assert sheet_name in excel_file.sheet_names

    def test_write_unsupported_format_raises_error(self, tmp_path):
        """Test writing unsupported format raises error."""
        manager = FileOutputManager(tmp_path)
        df = pd.DataFrame({"A": [1, 2, 3]})

        with pytest.raises(FileOutputError, match="Unsupported file format"):
            manager.write_dataframe(df, "test.txt")


class TestWriteMultipleSheets:
    """Test multi-sheet writing functionality."""

    def test_write_single_sheet_as_csv(self, tmp_path):
        """Test writing single sheet data as CSV."""
        manager = FileOutputManager(tmp_path)
        sheet_data = {"Sheet1": pd.DataFrame({"A": [1, 2, 3]})}
        filename = "test.csv"

        result_path = manager.write_multiple_sheets(sheet_data, filename)

        assert result_path.exists()
        assert result_path.suffix == ".csv"

    def test_write_multiple_sheets_as_excel(self, tmp_path):
        """Test writing multiple sheets as Excel."""
        manager = FileOutputManager(tmp_path)
        sheet_data = {
            "Sales": pd.DataFrame({"A": [1, 2, 3]}),
            "Expenses": pd.DataFrame({"B": [4, 5, 6]}),
        }
        filename = "test.xlsx"

        result_path = manager.write_multiple_sheets(sheet_data, filename)

        assert result_path.exists()
        assert result_path.suffix == ".xlsx"

        # Verify both sheets exist
        excel_file = pd.ExcelFile(result_path)
        assert "Sales" in excel_file.sheet_names
        assert "Expenses" in excel_file.sheet_names

    def test_write_multiple_sheets_to_csv_raises_error(self, tmp_path):
        """Test writing multiple sheets to CSV raises error."""
        manager = FileOutputManager(tmp_path)
        sheet_data = {
            "Sheet1": pd.DataFrame({"A": [1, 2, 3]}),
            "Sheet2": pd.DataFrame({"B": [4, 5, 6]}),
        }

        with pytest.raises(
            FileOutputError, match="Cannot write multiple sheets to CSV"
        ):
            manager.write_multiple_sheets(sheet_data, "test.csv")


class TestMergeSheetData:
    """Test sheet data merging functionality."""

    def test_merge_sheet_data_with_split_sheets(self):
        """Test merging original and split sheet data."""
        # Original sheet data
        all_sheet_data = {
            "Sales": pd.DataFrame(
                {"Date": ["2023-01-01", "2023-02-01"], "Amount": [100, 200]}
            ),
            "Expenses": pd.DataFrame(
                {"Category": ["Office", "Travel"], "Cost": [50, 75]}
            ),
            "Reports": pd.DataFrame(
                {"Month": ["Jan", "Feb"], "Summary": ["Good", "Better"]}
            ),
        }

        # Split data for only "Sales" sheet
        split_sheet_data = {
            "Sales": pd.DataFrame({"Date": ["2023-01-01"], "Amount": [100]})
        }

        split_sheets = ["Sales"]

        result = FileOutputManager.merge_sheet_data(
            all_sheet_data, split_sheet_data, split_sheets
        )

        # Verify all sheets exist in result
        assert "Sales" in result
        assert "Expenses" in result
        assert "Reports" in result

        # Verify split sheet uses new data
        pd.testing.assert_frame_equal(result["Sales"], split_sheet_data["Sales"])

        # Verify non-split sheets use original data
        pd.testing.assert_frame_equal(result["Expenses"], all_sheet_data["Expenses"])
        pd.testing.assert_frame_equal(result["Reports"], all_sheet_data["Reports"])

    def test_merge_sheet_data_no_splits(self):
        """Test merging when no sheets are split."""
        all_sheet_data = {
            "Sheet1": pd.DataFrame({"A": [1, 2]}),
            "Sheet2": pd.DataFrame({"B": [3, 4]}),
        }

        split_sheet_data = {}
        split_sheets = []

        result = FileOutputManager.merge_sheet_data(
            all_sheet_data, split_sheet_data, split_sheets
        )

        # All sheets should be original data
        for sheet_name, df in all_sheet_data.items():
            pd.testing.assert_frame_equal(result[sheet_name], df)

    def test_merge_sheet_data_split_sheet_not_in_split_data(self):
        """Test merging when split sheet is missing from split data."""
        all_sheet_data = {
            "ToSplit": pd.DataFrame({"Date": ["2023-01-01"], "Value": [10]}),
            "Preserve": pd.DataFrame({"Info": ["Data"], "Status": ["Active"]}),
        }

        split_sheet_data = {}  # No split data provided
        split_sheets = ["ToSplit"]

        result = FileOutputManager.merge_sheet_data(
            all_sheet_data, split_sheet_data, split_sheets
        )

        # Should fall back to original data when split data is missing
        pd.testing.assert_frame_equal(result["ToSplit"], all_sheet_data["ToSplit"])
        pd.testing.assert_frame_equal(result["Preserve"], all_sheet_data["Preserve"])

    def test_merge_sheet_data_multiple_split_sheets(self):
        """Test merging with multiple sheets being split."""
        all_sheet_data = {
            "Sales": pd.DataFrame(
                {"Date": ["2023-01-01", "2023-02-01"], "Amount": [100, 200]}
            ),
            "Purchases": pd.DataFrame(
                {"Date": ["2023-01-01", "2023-02-01"], "Cost": [50, 75]}
            ),
            "Config": pd.DataFrame({"Setting": ["A", "B"], "Value": [1, 2]}),
        }

        split_sheet_data = {
            "Sales": pd.DataFrame({"Date": ["2023-01-01"], "Amount": [100]}),
            "Purchases": pd.DataFrame({"Date": ["2023-02-01"], "Cost": [75]}),
        }

        split_sheets = ["Sales", "Purchases"]

        result = FileOutputManager.merge_sheet_data(
            all_sheet_data, split_sheet_data, split_sheets
        )

        # Verify split sheets use new data
        pd.testing.assert_frame_equal(result["Sales"], split_sheet_data["Sales"])
        pd.testing.assert_frame_equal(
            result["Purchases"], split_sheet_data["Purchases"]
        )

        # Verify non-split sheet uses original data
        pd.testing.assert_frame_equal(result["Config"], all_sheet_data["Config"])


class TestGetFileStats:
    """Test file statistics functionality."""

    def test_get_stats_for_existing_file(self, tmp_path):
        """Test getting statistics for existing file."""
        manager = FileOutputManager(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        stats = manager.get_file_stats(test_file)

        assert stats["path"] == str(test_file)
        assert stats["size_bytes"] == 11  # "Hello World" is 11 bytes
        assert isinstance(stats["size_human"], str) and "B" in stats["size_human"]
        assert "created" in stats
        assert "modified" in stats

    def test_get_stats_for_nonexistent_file_raises_error(self, tmp_path):
        """Test getting stats for nonexistent file raises error."""
        manager = FileOutputManager(tmp_path)
        nonexistent_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileOutputError, match="File not found"):
            manager.get_file_stats(nonexistent_file)


class TestFormatFileSize:
    """Test file size formatting."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        manager = FileOutputManager(Path("/tmp"))

        result = manager._format_file_size(512)

        assert result == "512.0 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        manager = FileOutputManager(Path("/tmp"))

        result = manager._format_file_size(1536)  # 1.5 KB

        assert result == "1.5 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        manager = FileOutputManager(Path("/tmp"))

        result = manager._format_file_size(1572864)  # 1.5 MB

        assert result == "1.5 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        manager = FileOutputManager(Path("/tmp"))

        result = manager._format_file_size(1610612736)  # 1.5 GB

        assert result == "1.5 GB"


class TestCleanupEmptyDirectory:
    """Test empty directory cleanup."""

    def test_removes_empty_directory(self, tmp_path):
        """Test removes empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        manager = FileOutputManager(empty_dir)

        result = manager.cleanup_empty_directory()

        assert result is True
        assert not empty_dir.exists()

    def test_keeps_directory_with_files(self, tmp_path):
        """Test keeps directory that contains files."""
        non_empty_dir = tmp_path / "nonempty"
        non_empty_dir.mkdir()
        (non_empty_dir / "file.txt").touch()
        manager = FileOutputManager(non_empty_dir)

        result = manager.cleanup_empty_directory()

        assert result is False
        assert non_empty_dir.exists()

    def test_handles_nonexistent_directory(self, tmp_path):
        """Test handles nonexistent directory gracefully."""
        nonexistent_dir = tmp_path / "nonexistent"
        manager = FileOutputManager(nonexistent_dir)

        result = manager.cleanup_empty_directory()

        assert result is False


class TestPeriodSuffixGeneration:
    """Test period suffix generation for different intervals."""

    def test_day_suffix(self):
        """Test day period suffix generation."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        suffix = manager._generate_period_suffix("day", test_date, 4)

        assert suffix == "2023-05-15"

    def test_week_suffix(self):
        """Test week period suffix generation."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)  # Week 20

        suffix = manager._generate_period_suffix("week", test_date, 4)

        assert suffix == "2023-W20"

    def test_month_suffix(self):
        """Test month period suffix generation."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        suffix = manager._generate_period_suffix("month", test_date, 4)

        assert suffix == "2023-05"

    def test_year_suffix(self):
        """Test year period suffix generation."""
        manager = FileOutputManager(Path("/tmp"))
        test_date = date(2023, 5, 15)

        suffix = manager._generate_period_suffix("year", test_date, 4)

        assert suffix == "2023"

    def test_financial_year_suffix_april_start(self):
        """Test financial year suffix with April start."""
        manager = FileOutputManager(Path("/tmp"))

        # Date in June (FY 2023-2024)
        test_date = date(2023, 6, 15)
        suffix = manager._generate_period_suffix("financial-year", test_date, 4)
        assert suffix == "FY2023-2024"

        # Date in February (FY 2022-2023)
        test_date = date(2023, 2, 15)
        suffix = manager._generate_period_suffix("financial-year", test_date, 4)
        assert suffix == "FY2022-2023"

    def test_financial_year_suffix_july_start(self):
        """Test financial year suffix with July start."""
        manager = FileOutputManager(Path("/tmp"))

        # Date in September (FY 2023-2024)
        test_date = date(2023, 9, 15)
        suffix = manager._generate_period_suffix("financial-year", test_date, 7)
        assert suffix == "FY2023-2024"

        # Date in May (FY 2022-2023)
        test_date = date(2023, 5, 15)
        suffix = manager._generate_period_suffix("financial-year", test_date, 7)
        assert suffix == "FY2022-2023"
