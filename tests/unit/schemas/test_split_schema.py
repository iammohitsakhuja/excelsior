"""Unit tests for Pydantic schemas used in split command."""

import pytest
from pydantic import ValidationError

from excelsior.schemas.split import SheetConfig, SplitSheetConfigSchema


class TestSheetConfig:
    """Test individual sheet configuration validation."""

    def test_sheet_config_default_values(self):
        """Test SheetConfig with default values."""
        config = SheetConfig()  # type: ignore
        assert config.date_column is None
        assert config.date_format is None
        assert config.include is True

    def test_sheet_config_valid_data(self):
        """Test SheetConfig with all valid fields."""
        config = SheetConfig(
            date_column="Purchase Date", date_format="%Y-%m-%d", include=False
        )
        assert config.date_column == "Purchase Date"
        assert config.date_format == "%Y-%m-%d"
        assert config.include is False

    def test_sheet_config_date_column_validation(self):
        """Test date column validation - strips whitespace and rejects empty strings."""
        # Valid with whitespace (should be stripped)
        config = SheetConfig(date_column="  Date Column  ")  # type: ignore
        assert config.date_column == "Date Column"

        # Invalid - empty string
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(date_column="")  # type: ignore
        assert "Date column name cannot be empty or whitespace only" in str(
            exc_info.value
        )

        # Invalid - whitespace only
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(date_column="   ")  # type: ignore
        assert "Date column name cannot be empty or whitespace only" in str(
            exc_info.value
        )

    def test_sheet_config_date_format_validation(self):
        """Test date format validation - requires datetime format specifiers."""
        # Valid formats
        valid_formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%B %d, %Y"]
        for fmt in valid_formats:
            config = SheetConfig(date_format=fmt)  # type: ignore
            assert config.date_format == fmt

        # Valid with whitespace (should be stripped)
        config = SheetConfig(date_format="  %Y-%m-%d  ")  # type: ignore
        assert config.date_format == "%Y-%m-%d"

        # Invalid - no format specifiers
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(date_format="invalid format")  # type: ignore
        assert "Date format must contain datetime format specifiers" in str(
            exc_info.value
        )

        # Invalid - empty string
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(date_format="")  # type: ignore
        assert "Date format cannot be empty or whitespace only" in str(exc_info.value)

        # Invalid - whitespace only
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(date_format="   ")  # type: ignore
        assert "Date format cannot be empty or whitespace only" in str(exc_info.value)

    def test_sheet_config_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(extra_field="not allowed")  # type: ignore
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_sheet_config_include_type_validation(self):
        """Test include field type validation."""
        # Valid boolean values
        config_true = SheetConfig(include=True)  # type: ignore
        assert config_true.include is True

        config_false = SheetConfig(include=False)  # type: ignore
        assert config_false.include is False

        # Note: Pydantic allows string-to-bool conversion for common strings
        # like "true", "false", "1", "0", etc. To test actual type validation,
        # we need to use a string that cannot be converted to boolean
        with pytest.raises(ValidationError) as exc_info:
            SheetConfig(include="not a boolean")  # type: ignore
        assert "Input should be a valid boolean" in str(exc_info.value)


class TestSplitSheetConfigSchema:
    """Test complete sheet configuration validation."""

    def test_valid_configuration(self):
        """Test valid complete sheet configuration."""
        config_data = {
            "Sales": {
                "date_column": "Sale Date",
                "date_format": "%Y-%m-%d",
                "include": True,
            },
            "Expenses": {"date_column": "Expense Date", "include": False},
            "Inventory": {
                "date_column": "Last Updated"
                # include defaults to True
            },
        }

        schema = SplitSheetConfigSchema(config_data)

        # Test dictionary-like access
        assert schema["Sales"].date_column == "Sale Date"
        assert schema["Sales"].date_format == "%Y-%m-%d"
        assert schema["Sales"].include is True

        assert schema["Expenses"].date_column == "Expense Date"
        assert schema["Expenses"].date_format is None
        assert schema["Expenses"].include is False

        assert schema["Inventory"].date_column == "Last Updated"
        assert schema["Inventory"].include is True

        # Test iteration methods
        sheet_names = list(schema.keys())
        assert "Sales" in sheet_names
        assert "Expenses" in sheet_names
        assert "Inventory" in sheet_names

    def test_empty_configuration(self):
        """Test that empty configuration is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema({})
        assert "Sheet configuration cannot be empty" in str(exc_info.value)

    def test_no_included_sheets(self):
        """Test that at least one sheet must be included."""
        config_data = {"Sheet1": {"include": False}, "Sheet2": {"include": False}}

        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema(config_data)  # type: ignore
        assert "At least one sheet must be included" in str(exc_info.value)

    def test_empty_sheet_names(self):
        """Test that empty sheet names are rejected."""
        config_data = {"": {"date_column": "Date"}, "   ": {"date_column": "Date"}}

        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema(config_data)  # type: ignore
        assert "Sheet names cannot be empty or whitespace only" in str(exc_info.value)

    def test_invalid_sheet_config_structure(self):
        """Test rejection of invalid sheet configuration structures."""
        # Non-dict sheet configuration
        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema({"Sheet1": "invalid"})  # type: ignore
        assert "Input should be a valid dictionary or instance of SheetConfig" in str(
            exc_info.value
        )

        # Invalid field in sheet config
        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema(
                {"Sheet1": {"date_column": "Date", "invalid_field": "value"}}  # type: ignore
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_nested_validation_errors(self):
        """Test that validation errors from nested SheetConfig are properly reported."""
        config_data = {
            "Sheet1": {
                "date_column": "",  # Invalid: empty
                "date_format": "invalid",  # Invalid: no format specifiers
                "include": "not a boolean",  # Invalid: wrong type
            }
        }

        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema(config_data)  # type: ignore

        error_str = str(exc_info.value)
        assert "Date column name cannot be empty" in error_str
        assert "Date format must contain datetime format specifiers" in error_str
        assert "Input should be a valid boolean" in error_str

    def test_mixed_valid_invalid_sheets(self):
        """Test configuration with mix of valid and invalid sheets."""
        config_data = {
            "ValidSheet": {"date_column": "Date", "date_format": "%Y-%m-%d"},
            "InvalidSheet": {
                "date_column": "",  # Invalid
                "extra_field": "value",  # Invalid
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            SplitSheetConfigSchema(config_data)  # type: ignore

        error_str = str(exc_info.value)
        # Should show errors for InvalidSheet only
        assert "Date column name cannot be empty" in error_str
        assert "Extra inputs are not permitted" in error_str
