"""Unit tests for data processing utilities."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from excelsior.schemas import SplitSheetConfigSchema
from excelsior.utils import (
    DataLoadError,
    DataProcessor,
    SheetConfigError,
    SheetConfigProcessor,
)


class TestDataProcessor:
    """Test the DataProcessor class."""

    def test_load_csv_success(self):
        """Test successful CSV loading."""
        processor = DataProcessor()

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-01,100.00,Payment 1\n")
            tmp.write("2024-01-02,200.00,Payment 2\n")
            tmp_path = Path(tmp.name)

        try:
            result = processor.load_file(tmp_path)

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2
            assert list(result.columns) == ["Date", "Amount", "Description"]
            assert result.iloc[0]["Amount"] == 100.00
        finally:
            tmp_path.unlink()

    def test_load_csv_empty_file(self):
        """Test loading an empty CSV file."""
        processor = DataProcessor()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(DataLoadError) as exc_info:
                processor.load_file(tmp_path)
            assert "empty" in str(exc_info.value).lower()
        finally:
            tmp_path.unlink()

    def test_load_csv_invalid_format(self):
        """Test loading a malformed CSV file."""
        processor = DataProcessor()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount\n")
            tmp.write("2024-01-01,100.00\n")
            tmp.write("malformed line without proper separator\n")
            tmp_path = Path(tmp.name)

        try:
            # This should still work as pandas is quite forgiving
            result = processor.load_file(tmp_path)
            assert isinstance(result, pd.DataFrame)
        finally:
            tmp_path.unlink()

    def test_validate_date_column_success(self):
        """Test successful date column validation."""
        processor = DataProcessor()
        df = pd.DataFrame(
            {"Date": ["2024-01-01", "2024-01-02"], "Amount": [100.00, 200.00]}
        )

        # Should not raise an exception
        processor.validate_date_column(df, "Date")

    def test_validate_date_column_missing(self):
        """Test validation with missing date column."""
        processor = DataProcessor()
        df = pd.DataFrame(
            {"Amount": [100.00, 200.00], "Description": ["Payment 1", "Payment 2"]}
        )

        with pytest.raises(DataLoadError) as exc_info:
            processor.validate_date_column(df, "Date")

        assert "Date column 'Date' not found" in str(exc_info.value)
        assert "Available columns: Amount, Description" in str(exc_info.value)

    def test_validate_date_column_empty(self):
        """Test validation with empty date column."""
        processor = DataProcessor()
        df = pd.DataFrame({"Date": [None, None], "Amount": [100.00, 200.00]})

        with pytest.raises(DataLoadError) as exc_info:
            processor.validate_date_column(df, "Date")

        assert "contains no valid data" in str(exc_info.value)

    def test_unsupported_file_format(self):
        """Test loading unsupported file format."""
        processor = DataProcessor()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("some content")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(DataLoadError) as exc_info:
                processor.load_file(tmp_path)
            assert "Unsupported file format: .txt" in str(exc_info.value)
        finally:
            tmp_path.unlink()


class TestSheetConfigProcessor:
    """Test the SheetConfigProcessor class."""

    def test_load_sheet_config_success(self):
        """Test successful sheet config loading."""
        processor = SheetConfigProcessor()

        config_data = {
            "Sheet1": {
                "date_column": "Date",
                "date_format": "%Y-%m-%d",
                "include": True,
            },
            "Sheet2": {"date_column": "Transaction Date", "include": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(config_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            result = processor.load_sheet_config(tmp_path)

            assert isinstance(result, SplitSheetConfigSchema)
            assert "Sheet1" in result.root
            assert "Sheet2" in result.root
            assert result["Sheet1"].date_column == "Date"
            assert result["Sheet1"].include is True
            assert result["Sheet2"].include is False
        finally:
            tmp_path.unlink()

    def test_load_sheet_config_invalid_json(self):
        """Test loading invalid JSON."""
        processor = SheetConfigProcessor()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write("{ invalid json }")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(SheetConfigError) as exc_info:
                processor.load_sheet_config(tmp_path)
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            tmp_path.unlink()

    def test_load_sheet_config_invalid_schema(self):
        """Test loading JSON with invalid schema."""
        processor = SheetConfigProcessor()

        config_data = {"Sheet1": {"invalid_field": "value"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(config_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(SheetConfigError) as exc_info:
                processor.load_sheet_config(tmp_path)
            assert "Invalid sheet configuration" in str(exc_info.value)
        finally:
            tmp_path.unlink()

    def test_process_sheet_selection_all_sheets(self):
        """Test sheet selection with no filters."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2", "Sheet3"]

        result = processor.process_sheet_selection(available_sheets)

        assert result == ["Sheet1", "Sheet2", "Sheet3"]

    def test_process_sheet_selection_include_filter(self):
        """Test sheet selection with include filter."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2", "Sheet3"]
        include_sheets = ["Sheet1", "Sheet3"]

        result = processor.process_sheet_selection(
            available_sheets, include_sheets=include_sheets
        )

        assert result == ["Sheet1", "Sheet3"]

    def test_process_sheet_selection_exclude_filter(self):
        """Test sheet selection with exclude filter."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2", "Sheet3"]
        exclude_sheets = ["Sheet2"]

        result = processor.process_sheet_selection(
            available_sheets, exclude_sheets=exclude_sheets
        )

        assert result == ["Sheet1", "Sheet3"]

    def test_process_sheet_selection_invalid_include(self):
        """Test sheet selection with invalid include sheets."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2"]
        include_sheets = ["Sheet1", "NonExistent"]

        with pytest.raises(SheetConfigError) as exc_info:
            processor.process_sheet_selection(
                available_sheets, include_sheets=include_sheets
            )

        assert "Invalid sheet names in include list" in str(exc_info.value)
        assert "NonExistent" in str(exc_info.value)

    def test_process_sheet_selection_config_filter(self):
        """Test sheet selection with config include/exclude."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2", "Sheet3"]

        config_data = {
            "Sheet1": {"include": True},
            "Sheet2": {"include": False},
            # Sheet3 not in config - should be included by default
        }
        sheet_config = SplitSheetConfigSchema(config_data)  # type: ignore

        result = processor.process_sheet_selection(
            available_sheets, sheet_config=sheet_config
        )

        assert result == ["Sheet1", "Sheet3"]

    def test_process_sheet_selection_no_sheets_result(self):
        """Test sheet selection that results in no sheets."""
        processor = SheetConfigProcessor()
        available_sheets = ["Sheet1", "Sheet2"]
        exclude_sheets = ["Sheet1", "Sheet2"]

        with pytest.raises(SheetConfigError) as exc_info:
            processor.process_sheet_selection(
                available_sheets, exclude_sheets=exclude_sheets
            )

        assert "No sheets selected for processing" in str(exc_info.value)

    def test_resolve_sheet_configs_global_only(self):
        """Test config resolution with only global settings."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1", "Sheet2"]

        result = processor.resolve_sheet_configs(
            sheet_names, global_date_column="Date", global_date_format="%Y-%m-%d"
        )

        assert len(result) == 2
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%Y-%m-%d"
        assert result["Sheet2"].date_column == "Date"
        assert result["Sheet2"].date_format == "%Y-%m-%d"

    def test_resolve_sheet_configs_with_overrides(self):
        """Test config resolution with sheet-specific overrides."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1", "Sheet2"]

        config_data = {
            "Sheet2": {"date_column": "Transaction Date", "date_format": "%d/%m/%Y"}
        }
        sheet_config = SplitSheetConfigSchema(config_data)  # type: ignore

        result = processor.resolve_sheet_configs(
            sheet_names,
            global_date_column="Date",
            global_date_format="%Y-%m-%d",
            sheet_config=sheet_config,
        )

        # Sheet1 should use global settings
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%Y-%m-%d"

        # Sheet2 should use overrides
        assert result["Sheet2"].date_column == "Transaction Date"
        assert result["Sheet2"].date_format == "%d/%m/%Y"

    def test_resolve_sheet_configs_missing_date_column(self):
        """Test config resolution when no date column is specified."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        with pytest.raises(SheetConfigError) as exc_info:
            processor.resolve_sheet_configs(sheet_names)

        assert "No date column specified for sheet 'Sheet1'" in str(exc_info.value)

    def test_resolve_sheet_configs_with_date_format_detection(self):
        """Test config resolution with automatic date format detection."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with ISO date format
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["2024-01-15", "2024-02-20", "2024-03-10"],
                    "Amount": [100, 200, 300],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="Date",
        )

        # Should detect ISO format
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%Y-%m-%d"

    def test_resolve_sheet_configs_date_detection_us_format(self):
        """Test date format detection for US format (MM/DD/YYYY)."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with US date format
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["01/15/2024", "02/20/2024", "03/10/2024"],
                    "Amount": [100, 200, 300],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="Date",
        )

        # Should detect US format
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%m/%d/%Y"

    def test_resolve_sheet_configs_date_detection_european_format(self):
        """Test date format detection for European format (DD/MM/YYYY)."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with European date format (using dates that are unambiguous)
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["15/01/2024", "20/02/2024", "25/03/2024"],
                    "Amount": [100, 200, 300],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="Date",
        )

        # Should detect European format
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%d/%m/%Y"

    def test_resolve_sheet_configs_date_detection_with_datetime(self):
        """Test date format detection for datetime format."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with datetime format
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "DateTime": [
                        "2024-01-15 14:30:00",
                        "2024-02-20 09:15:30",
                        "2024-03-10 16:45:00",
                    ],
                    "Amount": [100, 200, 300],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="DateTime",
        )

        # Should detect datetime format
        assert result["Sheet1"].date_column == "DateTime"
        assert result["Sheet1"].date_format == "%Y-%m-%d %H:%M:%S"

    def test_resolve_sheet_configs_date_detection_mixed_formats_fails(self):
        """Test that mixed date formats result in detection failure with helpful error."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with mixed date formats
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["2024-01-15", "02/20/2024", "25.03.2024"],
                    "Amount": [100, 200, 300],
                }
            )
        }

        # Should raise an error due to mixed formats
        with pytest.raises(SheetConfigError) as exc_info:
            processor.resolve_sheet_configs(
                sheet_names,
                sheet_data=sheet_data,
                global_date_column="Date",
            )

        error_message = str(exc_info.value)
        assert "Inconsistent date formats detected" in error_message
        assert "Detected format '%Y-%m-%d'" in error_message
        assert "02/20/2024" in error_message
        assert "25.03.2024" in error_message

    def test_resolve_sheet_configs_explicit_format_overrides_detection(self):
        """Test that explicit format specification overrides auto-detection."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        # Create test data with ISO format
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["2024-01-15", "2024-02-20", "2024-03-10"],
                    "Amount": [100, 200, 300],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="Date",
            global_date_format="%Y-%m-%d",  # Explicit format
        )

        # Should use explicit format, not detected format
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format == "%Y-%m-%d"

    def test_resolve_sheet_configs_detection_without_data(self):
        """Test that detection is skipped when no sheet data is provided."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1"]

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=None,  # No data provided
            global_date_column="Date",
        )

        # Should not have detected format
        assert result["Sheet1"].date_column == "Date"
        assert result["Sheet1"].date_format is None

    def test_resolve_sheet_configs_detection_missing_sheet_data(self):
        """Test behavior when sheet data is missing for specific sheet."""
        processor = SheetConfigProcessor()
        sheet_names = ["Sheet1", "Sheet2"]

        # Provide data only for Sheet1
        sheet_data = {
            "Sheet1": pd.DataFrame(
                {
                    "Date": ["2024-01-15", "2024-02-20"],
                    "Amount": [100, 200],
                }
            )
        }

        result = processor.resolve_sheet_configs(
            sheet_names,
            sheet_data=sheet_data,
            global_date_column="Date",
        )

        # Sheet1 should have detected format
        assert result["Sheet1"].date_format == "%Y-%m-%d"
        # Sheet2 should not have format (no data provided)
        assert result["Sheet2"].date_format is None
