"""Data processing utilities for Excel and CSV file operations."""

import json
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from excelsior.schemas import SheetConfig, SplitSheetConfigSchema
from excelsior.utils.date_format_detector import (
    DateFormatDetectionError,
    DateFormatDetector,
)
from excelsior.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoadError(Exception):
    """Exception raised when data loading fails."""

    pass


class SheetConfigError(Exception):
    """Exception raised when sheet configuration processing fails."""

    pass


class DataProcessor:
    """Handles loading and basic processing of Excel and CSV files."""

    def __init__(self):
        """Initialize the data processor."""
        self.logger = get_logger(self.__class__.__module__)

    def load_file(self, file_path: Path) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Load data from a CSV or Excel file.

        Args:
            file_path: Path to the input file

        Returns:
            For CSV files: A single DataFrame
            For Excel files: A dictionary mapping sheet names to DataFrames

        Raises:
            DataLoadError: If file loading fails
        """
        self.logger.info(f"Loading file: {file_path}")

        try:
            file_extension = file_path.suffix.lower()

            if file_extension == ".csv":
                return self._load_csv(file_path)
            elif file_extension in [".xlsx", ".xls"]:
                return self._load_excel(file_path)
            else:
                raise DataLoadError(f"Unsupported file format: {file_extension}")

        except Exception as e:
            if isinstance(e, DataLoadError):
                raise
            raise DataLoadError(f"Failed to load file {file_path}: {str(e)}") from e

    def _load_csv(self, file_path: Path) -> pd.DataFrame:
        """Load a CSV file into a DataFrame.

        Args:
            file_path: Path to the CSV file

        Returns:
            DataFrame containing the CSV data

        Raises:
            DataLoadError: If CSV loading fails
        """
        try:
            self.logger.debug(f"Loading CSV file: {file_path}")
            df = pd.read_csv(file_path)

            if df.empty:
                raise DataLoadError(f"CSV file is empty: {file_path}")

            self.logger.info(
                f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns"
            )
            return df

        except pd.errors.EmptyDataError:
            raise DataLoadError(
                f"CSV file is empty or contains no data: {file_path}"
            ) from None
        except pd.errors.ParserError as e:
            raise DataLoadError(f"Failed to parse CSV file: {str(e)}") from e
        except Exception as e:
            raise DataLoadError(f"Error reading CSV file: {str(e)}") from e

    def _load_excel(self, file_path: Path) -> dict[str, pd.DataFrame]:
        """Load an Excel file into a dictionary of DataFrames.

        Args:
            file_path: Path to the Excel file

        Returns:
            Dictionary mapping sheet names to DataFrames

        Raises:
            DataLoadError: If Excel loading fails
        """
        try:
            self.logger.debug(f"Loading Excel file: {file_path}")

            # Load all sheets
            sheet_dict = pd.read_excel(file_path, sheet_name=None)

            if not sheet_dict:
                raise DataLoadError(f"Excel file contains no sheets: {file_path}")

            # Filter out empty sheets and log information
            non_empty_sheets = {}
            for sheet_name, df in sheet_dict.items():
                if not df.empty:
                    non_empty_sheets[sheet_name] = df
                    self.logger.debug(
                        f"Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns"
                    )
                else:
                    self.logger.warning(
                        f"Sheet '{sheet_name}' is empty and will be skipped"
                    )

            if not non_empty_sheets:
                raise DataLoadError(f"All sheets in Excel file are empty: {file_path}")

            self.logger.info(
                f"Loaded Excel file with {len(non_empty_sheets)} non-empty sheets"
            )
            return non_empty_sheets

        except Exception as e:
            if isinstance(e, DataLoadError):
                raise
            raise DataLoadError(f"Error reading Excel file: {str(e)}") from e

    def validate_date_column(self, data: pd.DataFrame, column_name: str) -> None:
        """Validate that a date column exists in the DataFrame.

        Args:
            data: DataFrame to check
            column_name: Name of the date column

        Raises:
            DataLoadError: If the date column doesn't exist or is invalid
        """
        if column_name not in data.columns:
            available_columns = ", ".join(data.columns.tolist())
            raise DataLoadError(
                f"Date column '{column_name}' not found. "
                f"Available columns: {available_columns}"
            )

        # Check if column has any non-null values
        non_null_count = data[column_name].notna().sum()
        if non_null_count == 0:
            raise DataLoadError(f"Date column '{column_name}' contains no valid data")

        self.logger.debug(
            f"Date column '{column_name}' validated: {non_null_count} non-null values"
        )


class SheetConfigProcessor:
    """Handles processing and validation of sheet configurations."""

    def __init__(self):
        """Initialize the sheet config processor."""
        self.logger = get_logger(self.__class__.__module__)
        self.date_format_detector = DateFormatDetector()

    def load_sheet_config(self, config_path: Path) -> SplitSheetConfigSchema:
        """Load and validate sheet configuration from JSON file.

        Args:
            config_path: Path to the JSON configuration file

        Returns:
            Validated sheet configuration schema

        Raises:
            SheetConfigError: If configuration loading or validation fails
        """
        try:
            self.logger.info(f"Loading sheet configuration: {config_path}")

            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)

            config_schema = SplitSheetConfigSchema(config_data)
            self.logger.info(
                f"Loaded configuration for {len(config_schema.keys())} sheets"
            )

            return config_schema

        except json.JSONDecodeError as e:
            raise SheetConfigError(
                f"Invalid JSON in configuration file: {str(e)}"
            ) from e
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                location = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"  {location}: {message}")

            formatted_errors = "\n".join(error_messages)
            raise SheetConfigError(
                f"Invalid sheet configuration:\n{formatted_errors}"
            ) from e
        except Exception as e:
            raise SheetConfigError(
                f"Error loading sheet configuration: {str(e)}"
            ) from e

    def process_sheet_selection(
        self,
        available_sheets: list[str],
        include_sheets: list[str] | None = None,
        exclude_sheets: list[str] | None = None,
        sheet_config: SplitSheetConfigSchema | None = None,
    ) -> list[str]:
        """Determine which sheets to process based on various selection criteria.

        Args:
            available_sheets: List of all available sheet names
            include_sheets: Explicitly included sheet names (None = all)
            exclude_sheets: Explicitly excluded sheet names (None = none)
            sheet_config: Sheet configuration with include/exclude settings

        Returns:
            List of sheet names to process

        Raises:
            SheetConfigError: If sheet selection results in no sheets or invalid names
        """
        self.logger.debug(
            f"Processing sheet selection from {len(available_sheets)} available sheets"
        )

        # Start with all available sheets
        selected_sheets = set(available_sheets)

        # Apply include filter if specified
        if include_sheets:
            self._validate_sheet_names(include_sheets, available_sheets, "include")
            selected_sheets = selected_sheets.intersection(set(include_sheets))
            self.logger.debug(
                f"Applied include filter: {len(selected_sheets)} sheets remaining"
            )

        # Apply exclude filter if specified
        if exclude_sheets:
            self._validate_sheet_names(exclude_sheets, available_sheets, "exclude")
            selected_sheets = selected_sheets.difference(set(exclude_sheets))
            self.logger.debug(
                f"Applied exclude filter: {len(selected_sheets)} sheets remaining"
            )

        # Apply sheet config include/exclude if specified
        if sheet_config:
            config_filtered = self._apply_config_filters(selected_sheets, sheet_config)
            selected_sheets = selected_sheets.intersection(set(config_filtered))
            self.logger.debug(
                f"Applied config filters: {len(selected_sheets)} sheets remaining"
            )

        final_sheets = sorted(list(selected_sheets))

        if not final_sheets:
            raise SheetConfigError(
                "No sheets selected for processing after applying filters. "
                "Check your include/exclude settings and sheet configuration."
            )

        self.logger.info(
            f"Selected {len(final_sheets)} sheets for processing: {final_sheets}"
        )
        return final_sheets

    def _validate_sheet_names(
        self, sheet_names: list[str], available_sheets: list[str], filter_type: str
    ) -> None:
        """Validate that sheet names exist in available sheets.

        Args:
            sheet_names: Sheet names to validate
            available_sheets: Available sheet names
            filter_type: Type of filter ("include" or "exclude") for error messages

        Raises:
            SheetConfigError: If any sheet names are not found
        """
        invalid_sheets = [name for name in sheet_names if name not in available_sheets]
        if invalid_sheets:
            available_str = ", ".join(available_sheets)
            raise SheetConfigError(
                f"Invalid sheet names in {filter_type} list: {invalid_sheets}. "
                f"Available sheets: {available_str}"
            )

    def _apply_config_filters(
        self, selected_sheets: set, sheet_config: SplitSheetConfigSchema
    ) -> list[str]:
        """Apply include/exclude filters from sheet configuration.

        Args:
            selected_sheets: Currently selected sheet names
            sheet_config: Sheet configuration schema

        Returns:
            List of sheet names that should be included based on config
        """
        included_sheets = []

        for sheet_name in selected_sheets:
            if sheet_name in sheet_config.root:
                config = sheet_config[sheet_name]
                if config.include:
                    included_sheets.append(sheet_name)
                else:
                    self.logger.debug(f"Sheet '{sheet_name}' excluded by configuration")
            else:
                # Sheet not in config - include by default
                included_sheets.append(sheet_name)
                self.logger.debug(f"Sheet '{sheet_name}' included (not in config)")

        return included_sheets

    def resolve_sheet_configs(
        self,
        sheet_names: list[str],
        sheet_data: dict[str, pd.DataFrame] | None = None,
        global_date_column: str | None = None,
        global_date_format: str | None = None,
        sheet_config: SplitSheetConfigSchema | None = None,
    ) -> dict[str, SheetConfig]:
        """Resolve final configuration for each sheet.

        Args:
            sheet_names: List of sheet names to process
            sheet_data: Dictionary mapping sheet names to DataFrames (for date format detection)
            global_date_column: Global date column from command line
            global_date_format: Global date format from command line
            sheet_config: Sheet-specific configurations

        Returns:
            Dictionary mapping sheet names to resolved configurations

        Raises:
            SheetConfigError: If configuration resolution fails
        """
        resolved_configs = {}

        for sheet_name in sheet_names:
            # Start with global settings
            config_dict = {}

            if global_date_column:
                config_dict["date_column"] = global_date_column
            if global_date_format:
                config_dict["date_format"] = global_date_format

            # Override with sheet-specific settings if available
            if sheet_config and sheet_name in sheet_config.root:
                sheet_specific = sheet_config[sheet_name]
                if sheet_specific.date_column:
                    config_dict["date_column"] = sheet_specific.date_column
                if sheet_specific.date_format:
                    config_dict["date_format"] = sheet_specific.date_format

            # Validate that we have a date column
            if not config_dict.get("date_column"):
                raise SheetConfigError(
                    f"No date column specified for sheet '{sheet_name}'. "
                    f"Provide either --date-column or configure it in sheet config."
                )

            # Detect date format if not provided and we have access to the data
            if (
                not config_dict.get("date_format")
                and sheet_data is not None
                and sheet_name in sheet_data
            ):
                try:
                    detected_format = self.date_format_detector.detect_date_format(
                        sheet_data[sheet_name], config_dict["date_column"]
                    )
                    if detected_format:
                        config_dict["date_format"] = detected_format
                except DateFormatDetectionError as e:
                    # Convert to SheetConfigError to maintain API compatibility
                    raise SheetConfigError(str(e)) from e

            # Create the configuration
            resolved_configs[sheet_name] = SheetConfig(**config_dict)

            self.logger.debug(
                f"Resolved config for '{sheet_name}': "
                f"date_column='{resolved_configs[sheet_name].date_column}', "
                f"date_format='{resolved_configs[sheet_name].date_format}'"
            )

        return resolved_configs
