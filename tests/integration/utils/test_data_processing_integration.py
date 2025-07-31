"""Integration tests for data processing functionality."""

import json
import tempfile
from pathlib import Path

import pandas as pd

from excelsior.utils import DataProcessor, SheetConfigProcessor


class TestDataProcessingIntegration:
    """Integration tests for data processing workflows."""

    def test_csv_processing_workflow(self):
        """Test complete CSV processing workflow."""
        # Create test CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("Date,Amount,Description\n")
            tmp.write("2024-01-01,100.00,Payment 1\n")
            tmp.write("2024-01-02,200.00,Payment 2\n")
            tmp_path = Path(tmp.name)

        try:
            # Initialize processors
            data_processor = DataProcessor()
            sheet_processor = SheetConfigProcessor()

            # Load file
            file_data = data_processor.load_file(tmp_path)
            assert isinstance(file_data, pd.DataFrame)

            # Convert to sheet format for consistency
            file_data = {"CSV": file_data}
            available_sheets = ["CSV"]

            # Process sheet selection
            selected_sheets = sheet_processor.process_sheet_selection(available_sheets)
            assert selected_sheets == ["CSV"]

            # Resolve configurations
            resolved_configs = sheet_processor.resolve_sheet_configs(
                sheet_names=selected_sheets,
                sheet_data=file_data,
                global_date_column="Date",
            )

            assert "CSV" in resolved_configs
            assert resolved_configs["CSV"].date_column == "Date"

            # Validate date column
            data_processor.validate_date_column(file_data["CSV"], "Date")

        finally:
            tmp_path.unlink()

    def test_excel_processing_workflow_with_config(self):
        """Test Excel processing workflow with sheet configuration."""
        # Create test Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # Create sample data
        sheet1_data = pd.DataFrame(
            {"Date": ["2024-01-01", "2024-01-02"], "Sales": [100.00, 200.00]}
        )
        sheet2_data = pd.DataFrame(
            {
                "Transaction Date": ["2024-01-01", "2024-01-02"],
                "Expenses": [50.00, 75.00],
            }
        )

        try:
            # Write Excel file
            with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                sheet1_data.to_excel(writer, sheet_name="Sales", index=False)
                sheet2_data.to_excel(writer, sheet_name="Expenses", index=False)

            # Create sheet configuration
            config_data = {
                "Sales": {
                    "date_column": "Date",
                    "date_format": "%Y-%m-%d",
                    "include": True,
                },
                "Expenses": {"date_column": "Transaction Date", "include": True},
            }

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as config_tmp:
                json.dump(config_data, config_tmp)
                config_path = Path(config_tmp.name)

            try:
                # Initialize processors
                data_processor = DataProcessor()
                sheet_processor = SheetConfigProcessor()

                # Load sheet config
                sheet_config = sheet_processor.load_sheet_config(config_path)

                # Load Excel file
                file_data = data_processor.load_file(tmp_path)
                assert isinstance(file_data, dict)
                assert "Sales" in file_data
                assert "Expenses" in file_data

                # Process sheet selection
                available_sheets = list(file_data.keys())
                selected_sheets = sheet_processor.process_sheet_selection(
                    available_sheets=available_sheets, sheet_config=sheet_config
                )

                assert set(selected_sheets) == {"Sales", "Expenses"}

                # Resolve configurations
                resolved_configs = sheet_processor.resolve_sheet_configs(
                    sheet_names=selected_sheets,
                    sheet_data=file_data,
                    global_date_column="Date",  # Should be overridden for Expenses
                    sheet_config=sheet_config,
                )

                assert resolved_configs["Sales"].date_column == "Date"
                assert resolved_configs["Expenses"].date_column == "Transaction Date"

                # Validate date columns
                for sheet_name in selected_sheets:
                    config = resolved_configs[sheet_name]
                    assert config.date_column is not None
                    data_processor.validate_date_column(
                        file_data[sheet_name], config.date_column
                    )

            finally:
                config_path.unlink()

        finally:
            tmp_path.unlink()

    def test_excel_date_format_detection_integration(self):
        """Integration test for automatic date format detection across multiple sheets."""
        # Create test Excel file with different date formats
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # Create sample data with different date formats
        iso_data = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-02-20", "2024-03-10"],
                "Sales": [100.00, 200.00, 300.00],
            }
        )
        us_data = pd.DataFrame(
            {
                "Date": ["01/15/2024", "02/20/2024", "03/10/2024"],
                "Expenses": [50.00, 75.00, 100.00],
            }
        )
        euro_data = pd.DataFrame(
            {
                "Date": ["15/01/2024", "20/02/2024", "10/03/2024"],
                "Revenue": [1000.00, 1500.00, 2000.00],
            }
        )

        try:
            # Write Excel file with multiple sheets
            with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                iso_data.to_excel(writer, sheet_name="ISO_Format", index=False)
                us_data.to_excel(writer, sheet_name="US_Format", index=False)
                euro_data.to_excel(writer, sheet_name="Euro_Format", index=False)

            # Initialize processors
            data_processor = DataProcessor()
            sheet_processor = SheetConfigProcessor()

            # Load Excel file
            file_data = data_processor.load_file(tmp_path)
            assert isinstance(file_data, dict)
            assert len(file_data) == 3

            # Process sheet selection (all sheets)
            available_sheets = list(file_data.keys())
            selected_sheets = sheet_processor.process_sheet_selection(available_sheets)

            # Resolve configurations with date format detection
            resolved_configs = sheet_processor.resolve_sheet_configs(
                sheet_names=selected_sheets,
                sheet_data=file_data,
                global_date_column="Date",  # No global format - should auto-detect
            )

            # Verify that correct formats were detected for each sheet
            assert resolved_configs["ISO_Format"].date_format == "%Y-%m-%d"
            assert resolved_configs["US_Format"].date_format == "%m/%d/%Y"
            assert resolved_configs["Euro_Format"].date_format == "%d/%m/%Y"

            # Validate that all date columns work with detected formats
            for sheet_name in selected_sheets:
                config = resolved_configs[sheet_name]
                assert config.date_column == "Date"
                assert config.date_format is not None
                data_processor.validate_date_column(
                    file_data[sheet_name], config.date_column
                )

        finally:
            tmp_path.unlink()

    def test_csv_date_format_detection_integration(self):
        """Integration test for date format detection in CSV files."""
        # Create test CSV with datetime format
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("DateTime,Amount,Description\n")
            tmp.write("2024-01-01 14:30:00,100.00,Payment 1\n")
            tmp.write("2024-01-02 09:15:30,200.00,Payment 2\n")
            tmp.write("2024-01-03 16:45:00,300.00,Payment 3\n")
            tmp_path = Path(tmp.name)

        try:
            # Initialize processors
            data_processor = DataProcessor()
            sheet_processor = SheetConfigProcessor()

            # Load CSV file
            file_data = data_processor.load_file(tmp_path)
            assert isinstance(file_data, pd.DataFrame)

            # Convert to sheet format
            file_data = {"CSV": file_data}
            selected_sheets = ["CSV"]

            # Resolve configurations with date format detection
            resolved_configs = sheet_processor.resolve_sheet_configs(
                sheet_names=selected_sheets,
                sheet_data=file_data,
                global_date_column="DateTime",
            )

            # Should detect datetime format
            assert resolved_configs["CSV"].date_column == "DateTime"
            assert resolved_configs["CSV"].date_format == "%Y-%m-%d %H:%M:%S"

            # Validate date column
            data_processor.validate_date_column(file_data["CSV"], "DateTime")

        finally:
            tmp_path.unlink()
