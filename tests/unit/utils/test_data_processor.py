"""Unit tests for data processing utilities."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from excelsior.schemas.split import SplitSheetConfigSchema
from excelsior.utils.data_processor import (
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
