"""Unit tests for the split command CLI interface."""

import argparse
import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from excelsior.commands.split import (
    SplitCommand,
    UnparseableDataResult,
    validate_financial_year_start,
    validate_sheet_config,
)


class TestSplitCommandRegistration:
    """Test split command registration and argument parsing."""

    def test_register_split_command(self):
        """Test that split command is properly registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        split_command = SplitCommand()
        split_command.register(subparsers)

        # Test that split command exists by checking subparsers
        assert "split" in subparsers._name_parser_map

        # Test that we can get help without causing SystemExit
        split_parser = subparsers._name_parser_map["split"]
        assert split_parser.prog.endswith("split")

    def test_split_command_required_arguments(self):
        """Test split command with missing required arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        split_command = SplitCommand()
        split_command.register(subparsers)

        # Should fail without --file
        with pytest.raises(SystemExit):
            parser.parse_args(["split"])

    def test_split_command_default_values(self):
        """Test split command default values."""
        # Create a temporary CSV file for testing
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="command")
            split_command = SplitCommand()
            split_command.register(subparsers)

            args = parser.parse_args(
                ["split", "--file", str(tmp_path), "--date-column", "Date"]
            )

            # Check default values
            assert args.interval == "month"
            assert args.financial_year_start == 4
            assert args.output_dir == Path("./out/split")
            assert args.conflict_resolution == "rename"  # Default conflict resolution
            assert args.verbose is False
            assert args.quiet is False
        finally:
            tmp_path.unlink()

    def test_split_command_all_options(self):
        """Test split command with all options specified."""
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_file_path = Path(tmp_file.name)

        config_data = {"Sheet1": {"date_column": "Date", "include": True}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_config:
            json.dump(config_data, tmp_config)
            tmp_config_path = Path(tmp_config.name)

        try:
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="command")
            split_command = SplitCommand()
            split_command.register(subparsers)

            args = parser.parse_args(
                [
                    "split",
                    "--file",
                    str(tmp_file_path),
                    "--date-column",
                    "Transaction Date",
                    "--interval",
                    "week",
                    "--financial-year-start",
                    "7",
                    "--output-dir",
                    "/tmp/output",
                    "--date-format",
                    "%Y-%m-%d",
                    "--include",
                    "Sheet1",
                    "Sheet2",
                    "--exclude",
                    "Sheet3",
                    "--sheet-config",
                    str(tmp_config_path),
                    "--verbose",
                ]
            )

            # Verify all arguments are parsed correctly
            assert args.file == tmp_file_path
            assert args.date_column == "Transaction Date"
            assert args.interval == "week"
            assert args.financial_year_start == 7
            assert args.output_dir == Path("/tmp/output")
            assert args.date_format == "%Y-%m-%d"
            assert args.include == ["Sheet1", "Sheet2"]
            assert args.exclude == ["Sheet3"]
            assert args.sheet_config == tmp_config_path
            assert args.verbose is True
            assert args.quiet is False
        finally:
            tmp_file_path.unlink()
            tmp_config_path.unlink()


class TestSplitCommandArgumentValidation:
    """Test SplitCommand-specific argument validation logic."""

    def test_validate_args_missing_date_column_and_sheet_config(self):
        """Test validation when both date_column and sheet_config are missing."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column=None,
            sheet_config=None,
            include=None,
            exclude=None,
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert error == "Either --date-column or --sheet-config must be provided"

    def test_validate_args_include_exclude_conflict(self):
        """Test validation when both --include and --exclude are used."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column="Date",
            sheet_config=None,
            include=["Sheet1"],
            exclude=["Sheet2"],
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert (
            error
            == "Cannot use multiple sheet selection flags together: --include, --exclude"
        )

    def test_validate_args_include_sheet_config_conflict(self):
        """Test validation when both --include and --sheet-config are used."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column=None,
            sheet_config="/path/to/config.json",
            include=["Sheet1"],
            exclude=None,
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert (
            error
            == "Cannot use multiple sheet selection flags together: --include, --sheet-config"
        )

    def test_validate_args_exclude_sheet_config_conflict(self):
        """Test validation when both --exclude and --sheet-config are used."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column=None,
            sheet_config="/path/to/config.json",
            include=None,
            exclude=["Sheet1"],
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert (
            error
            == "Cannot use multiple sheet selection flags together: --exclude, --sheet-config"
        )

    def test_validate_args_all_three_flags_conflict(self):
        """Test validation when all three sheet selection flags are used."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column=None,
            sheet_config="/path/to/config.json",
            include=["Sheet1"],
            exclude=["Sheet2"],
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert (
            error
            == "Cannot use multiple sheet selection flags together: --include, --exclude, --sheet-config"
        )

    def test_validate_args_valid_include_only(self):
        """Test validation with only --include flag."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column="Date",
            sheet_config=None,
            include=["Sheet1", "Sheet2"],
            exclude=None,
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert error is None

    def test_validate_args_valid_exclude_only(self):
        """Test validation with only --exclude flag."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column="Date",
            sheet_config=None,
            include=None,
            exclude=["Sheet3"],
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert error is None

    def test_validate_args_valid_sheet_config_only(self):
        """Test validation with only --sheet-config flag."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column=None,
            sheet_config="/path/to/config.json",
            include=None,
            exclude=None,
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert error is None

    def test_validate_args_valid_no_sheet_flags(self):
        """Test validation with no sheet selection flags (default behavior)."""
        command = SplitCommand()
        args = argparse.Namespace(
            date_column="Date",
            sheet_config=None,
            include=None,
            exclude=None,
            verbose=False,
            quiet=False,
        )

        error = command.validate_args(args)
        assert error is None


class TestSplitCommandValidation:
    """Test validation functions for split command arguments."""

    def test_validate_financial_year_start_valid_months(self):
        """Test financial year start validation with valid months."""
        for month in range(1, 13):
            result = validate_financial_year_start(str(month))
            assert result == month

    def test_validate_financial_year_start_invalid_months(self):
        """Test financial year start validation with invalid months."""
        invalid_months = [0, 13, -1, 25]
        for month in invalid_months:
            with pytest.raises(argparse.ArgumentTypeError) as exc_info:
                validate_financial_year_start(str(month))
            assert "must be between 1 and 12" in str(exc_info.value)

    def test_validate_financial_year_start_non_integer(self):
        """Test financial year start validation with non-integer values."""
        invalid_values = ["abc", "12.5", "january", ""]
        for value in invalid_values:
            with pytest.raises(argparse.ArgumentTypeError) as exc_info:
                validate_financial_year_start(value)
            assert "must be an integer" in str(exc_info.value)

    def test_validate_sheet_config_valid_json(self):
        """Test sheet config validation with valid JSON."""
        config_data = {
            "Sheet1": {
                "date_column": "Date",
                "date_format": "%Y-%m-%d",
                "include": True,
            },
            "Sheet2": {"date_column": "Order Date", "include": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(config_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            result = validate_sheet_config(str(tmp_path))
            assert result == tmp_path
        finally:
            tmp_path.unlink()

    def test_validate_sheet_config_invalid_json(self):
        """Test sheet config validation with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write("{ invalid json }")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(argparse.ArgumentTypeError) as exc_info:
                validate_sheet_config(str(tmp_path))
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            tmp_path.unlink()

    def test_validate_sheet_config_invalid_structure(self):
        """Test sheet config validation with invalid structure."""
        invalid_configs = [
            # Non-dict root
            ["not", "a", "dict"],
            # Invalid sheet config structure
            {"Sheet1": "not a dict"},
            # Invalid keys
            {"Sheet1": {"invalid_key": "value", "include": True}},
            # Invalid include type
            {"Sheet1": {"include": "not a boolean"}},
        ]

        for config_data in invalid_configs:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as tmp:
                json.dump(config_data, tmp)
                tmp_path = Path(tmp.name)

            try:
                with pytest.raises(argparse.ArgumentTypeError):
                    validate_sheet_config(str(tmp_path))
            finally:
                tmp_path.unlink()


class TestUnparseableDataHandling:
    """Test handling of unparseable date data."""

    def test_generate_unparseable_filename(self):
        """Test generation of unparseable data filename."""
        command = SplitCommand()

        # Test Excel file
        excel_filename = command._generate_unparseable_filename("data.xlsx")
        assert excel_filename == "data_unparseable_dates.xlsx"

        # Test CSV file
        csv_filename = command._generate_unparseable_filename("sales.csv")
        assert csv_filename == "sales_unparseable_dates.csv"

        # Test file with complex name
        complex_filename = command._generate_unparseable_filename("my-data_file.xlsx")
        assert complex_filename == "my-data_file_unparseable_dates.xlsx"

    def test_parse_dates_returns_unparseable_data(self):
        """Test that _parse_dates_in_sheet returns unparseable data."""

        command = SplitCommand()

        # Create test data with some unparseable dates
        test_data = pd.DataFrame(
            {
                "date_col": ["2023-01-01", "invalid_date", "2023-02-01", "not_a_date"],
                "value": [10, 20, 30, 40],
            }
        )

        result = command._parse_dates_in_sheet(test_data, "date_col", None)

        # Verify the result is an UnparseableDataResult
        assert isinstance(result, UnparseableDataResult)

        # Should have 2 valid rows
        assert len(result.parsed_data) == 2
        assert result.parsed_data["date_col"].notna().all()

        # Should have 2 unparseable rows
        assert result.unparseable_data is not None
        assert len(result.unparseable_data) == 2
        assert list(result.unparseable_data["date_col"]) == [
            "invalid_date",
            "not_a_date",
        ]
        assert list(result.unparseable_data["value"]) == [20, 40]

    def test_parse_dates_no_unparseable_data(self):
        """Test parsing when all dates are valid."""
        command = SplitCommand()

        # Create test data with all valid dates
        test_data = pd.DataFrame(
            {
                "date_col": ["2023-01-01", "2023-02-01", "2023-03-01"],
                "value": [10, 20, 30],
            }
        )

        result = command._parse_dates_in_sheet(test_data, "date_col", None)

        # Verify the result is an UnparseableDataResult
        assert isinstance(result, UnparseableDataResult)

        # Should have all 3 valid rows
        assert len(result.parsed_data) == 3
        assert result.parsed_data["date_col"].notna().all()

        # Should have no unparseable data
        assert result.unparseable_data is None
