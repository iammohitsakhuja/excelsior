"""Split command implementation for Excelsior CLI."""

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd
from pydantic import ValidationError

from excelsior.commands.base import FileProcessingCommand
from excelsior.schemas import SheetConfig, SplitSheetConfigSchema
from excelsior.utils import (
    ConflictResolution,
    DataLoadError,
    DataProcessor,
    FileOutputManager,
    SheetConfigError,
    SheetConfigProcessor,
    SplitInterval,
    create_split_strategy,
    get_logger,
)

logger = get_logger(__name__)


@dataclass
class SplitCommandArgs:
    """Dataclass to hold split command arguments with proper typing."""

    file: Path
    date_column: str | None
    date_format: str | None
    interval: SplitInterval
    financial_year_start: int
    output_dir: Path
    include: list[str] | None
    exclude: list[str] | None
    sheet_config: Path | None
    conflict_resolution: ConflictResolution


@dataclass
class SplitPeriodData:
    """Data structure to hold information about a split time period."""

    period_key: str
    representative_date: date
    sheet_data: dict[str, pd.DataFrame]  # sheet_name -> DataFrame


@dataclass
class UnparseableDataResult:
    """Data structure to hold results from date parsing operation."""

    parsed_data: pd.DataFrame
    unparseable_data: pd.DataFrame | None


def validate_financial_year_start(value: str) -> int:
    """Validate financial year start month.

    Args:
        value: String representation of the month number

    Returns:
        int: The validated month number (1-12)

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid month
    """
    try:
        month = int(value)
        if 1 <= month <= 12:
            return month
        else:
            raise argparse.ArgumentTypeError(
                f"Financial year start month must be between 1 and 12, got {month}"
            )
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Financial year start month must be an integer, got '{value}'"
        ) from e


def validate_file_path(value: str) -> Path:
    """Validate that the input file exists and is readable.

    Args:
        value: String path to the file

    Returns:
        Path: The validated file path

    Raises:
        argparse.ArgumentTypeError: If the file doesn't exist or isn't readable
    """
    return FileProcessingCommand.validate_file_path(value, [".xlsx", ".xls", ".csv"])


def validate_sheet_config(value: str) -> Path:
    """Validate that the sheet config file exists and is a valid JSON file with correct schema.

    Args:
        value: String path to the JSON config file

    Returns:
        Path: The validated config file path

    Raises:
        argparse.ArgumentTypeError: If the file doesn't exist, isn't valid JSON, or doesn't match schema
    """
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Sheet config file not found: {path}")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Sheet config path is not a file: {path}")

    # Validate JSON format and schema
    try:
        with open(path, encoding="utf-8") as f:
            config_data = json.load(f)

        # Validate using Pydantic schema
        SplitSheetConfigSchema(config_data)

    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid JSON in sheet config file: {e}"
        ) from e
    except ValidationError as e:
        # Format Pydantic validation errors for user-friendly display
        error_messages = []
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"  {location}: {message}")

        formatted_errors = "\n".join(error_messages)
        raise argparse.ArgumentTypeError(
            f"Invalid sheet configuration:\n{formatted_errors}"
        ) from e
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Error reading sheet config file: {e}") from e

    return path


class SplitCommand(FileProcessingCommand):
    """Command to split Excel/CSV files based on dates in a specified column."""

    @property
    def name(self) -> str:
        """Return the command name."""
        return "split"

    @property
    def help_text(self) -> str:
        """Return the short help text."""
        return "Split Excel/CSV files based on dates in a specified column"

    @property
    def description(self) -> str:
        """Return the detailed description."""
        return (
            "Split Excel or CSV files into separate files based on dates contained "
            "in a specified column. The data will be partitioned according to the "
            "chosen time interval (day, week, month, year, or financial year)."
        )

    @property
    def epilog(self) -> str | None:
        """Return the epilog with examples and usage patterns."""
        return """
Examples:
  # Split an Excel file by month using default settings
  excelsior split --file sales_data.xlsx --date-column "Purchase Date"

  # Split a CSV file by week with custom output directory
  excelsior split -f transactions.csv -d TransactionDate -i week -o ./weekly_data

  # Split with custom date format and verbose logging
  excelsior split -f events.xlsx -d EventDate -df "%%d/%%m/%%Y" -v

  # Split by financial year starting in July
  excelsior split -f financial_data.xlsx -d "Transaction Date" -i financial-year -fys 7

  # Split specific sheets in an Excel file
  excelsior split -f multi_sheet_data.xlsx -d "Date" --include "Sales" "Expenses"

  # Split with sheet-specific configuration
  excelsior split -f complex_data.xlsx -sc sheet_config.json

  # Split with conflict resolution (overwrite existing files)
  excelsior split -f data.xlsx -d "Date" --conflict-resolution overwrite

Output File Naming:
  day:           original_YYYY-MM-DD.ext
  week:          original_YYYY-Www.ext (ISO week format)
  month:         original_YYYY-MM.ext
  year:          original_YYYY.ext
  financial-year: original_FY{YYYY}-{YYYY+1}.ext
        """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add split command-specific arguments.

        Args:
            parser: The argument parser to add arguments to
        """
        # Required arguments group
        required_group = parser.add_argument_group("required arguments")

        required_group.add_argument(
            "--file",
            "-f",
            type=validate_file_path,
            required=True,
            help="Path to the input Excel (.xlsx, .xls) or CSV file",
            metavar="PATH",
        )

        # Date column configuration
        date_group = parser.add_argument_group("date column configuration")

        date_group.add_argument(
            "--date-column",
            "-d",
            type=str,
            help=(
                "Name of the column containing date values. "
                "Required unless using --sheet-config"
            ),
            metavar="COLUMN",
        )

        date_group.add_argument(
            "--date-format",
            "-df",
            type=str,
            help=(
                "Custom date format string (e.g., '%%Y-%%m-%%d', '%%d/%%m/%%Y'). "
                "If not specified, common date formats will be automatically detected"
            ),
            metavar="FORMAT",
        )

        # Splitting configuration
        split_group = parser.add_argument_group("splitting configuration")

        split_group.add_argument(
            "--interval",
            "-i",
            choices=["day", "week", "month", "year", "financial-year"],
            default="month",
            help="Time interval for splitting data (default: %(default)s)",
            metavar="INTERVAL",
        )

        split_group.add_argument(
            "--financial-year-start",
            "-fys",
            type=validate_financial_year_start,
            default=4,
            help="Start month of financial year (1-12, default: %(default)s for April)",
            metavar="MONTH",
        )

        # Output configuration
        output_group = parser.add_argument_group("output configuration")

        output_group.add_argument(
            "--output-dir",
            "-o",
            type=Path,
            default=Path("./out/split"),
            help="Directory for output files (default: %(default)s)",
            metavar="PATH",
        )

        output_group.add_argument(
            "--conflict-resolution",
            "-cr",
            choices=["overwrite", "skip", "rename"],
            default="rename",
            help=(
                "How to handle existing output files: "
                "overwrite (replace existing), skip (keep existing), "
                "rename (add suffix to new files) (default: %(default)s)"
            ),
            metavar="STRATEGY",
        )

        # Excel-specific options
        excel_group = parser.add_argument_group("Excel-specific options")

        excel_group.add_argument(
            "--include",
            "-inc",
            nargs="+",
            help=(
                "List of sheet names to process (Excel only). "
                "Cannot be used with --exclude or --sheet-config"
            ),
            metavar="SHEET",
        )

        excel_group.add_argument(
            "--exclude",
            "-exc",
            nargs="+",
            help=(
                "List of sheet names to exclude from processing (Excel only). "
                "Cannot be used with --include or --sheet-config"
            ),
            metavar="SHEET",
        )

        excel_group.add_argument(
            "--sheet-config",
            "-sc",
            type=validate_sheet_config,
            help=(
                "Path to JSON file with per-sheet configuration. "
                "When used, --date-column becomes optional as each sheet "
                "can specify its own date column"
            ),
            metavar="PATH",
        )

        # Add common command arguments (verbose, quiet)
        self._add_common_command_arguments(parser)

    def validate_args(self, args: argparse.Namespace) -> str | None:
        """Validate split command arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            Optional[str]: Error message if validation fails, None if successful
        """
        parent_validation = super().validate_args(args)
        if parent_validation:
            return parent_validation

        # Validate argument combinations
        if not args.date_column and not args.sheet_config:
            return "Either --date-column or --sheet-config must be provided"

        # Check mutual exclusivity of sheet selection flags
        active_flags = []
        if args.include:
            active_flags.append("--include")
        if args.exclude:
            active_flags.append("--exclude")
        if args.sheet_config:
            active_flags.append("--sheet-config")

        if len(active_flags) > 1:
            return f"Cannot use multiple sheet selection flags together: {', '.join(active_flags)}"

        return None

    def _convert_args(self, args: argparse.Namespace) -> SplitCommandArgs:
        """Convert argparse.Namespace to typed SplitCommandArgs.

        Args:
            args: Parsed command line arguments

        Returns:
            SplitCommandArgs: Typed arguments dataclass
        """
        return SplitCommandArgs(
            file=args.file,
            date_column=args.date_column,
            date_format=args.date_format,
            interval=cast(SplitInterval, args.interval),
            financial_year_start=args.financial_year_start,
            output_dir=args.output_dir,
            include=args.include,
            exclude=args.exclude,
            sheet_config=args.sheet_config,
            conflict_resolution=ConflictResolution(args.conflict_resolution),
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute the split command.

        Args:
            args: Parsed command line arguments

        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        self.logger.info("Starting split command")

        try:
            # Convert to typed arguments
            typed_args = self._convert_args(args)

            self._log_execution_info(typed_args)

            # Load file data and process sheet configuration
            file_data, selected_sheets, resolved_configs = (
                self._load_and_process_sheets(typed_args)
            )

            # Initialize file output manager
            file_manager = FileOutputManager(
                typed_args.output_dir, typed_args.conflict_resolution
            )

            # Process splitting for all sheets
            period_data_map, unparseable_data_map = self._process_sheet_splitting(
                file_data, selected_sheets, resolved_configs, typed_args
            )

            # Write output files (one per time period)
            all_output_files = self._write_combined_split_files(
                period_data_map,
                file_manager,
                typed_args.file.name,
                typed_args.interval,
                typed_args.financial_year_start,
                selected_sheets,
                file_data,
            )

            # Write unparseable data file if there are any unparseable rows
            unparseable_file = None
            if unparseable_data_map:
                unparseable_file = self._write_unparseable_data_file(
                    unparseable_data_map,
                    file_manager,
                    typed_args.file.name,
                    selected_sheets,
                    file_data,
                )
                all_output_files.append(unparseable_file)

            # Log summary of all output files
            self.logger.info("Split command execution completed successfully")
            self.logger.info(f"Generated {len(all_output_files)} output files:")
            for output_file in all_output_files:
                stats = file_manager.get_file_stats(output_file)
                self.logger.info(f"  {output_file} ({stats['size_human']})")

            if unparseable_file:
                total_unparseable_rows = sum(
                    len(df) for df in unparseable_data_map.values()
                )
                self.logger.info(
                    f"Preserved {total_unparseable_rows} rows with unparseable dates in: {unparseable_file}"
                )

            return 0

        except (DataLoadError, SheetConfigError) as e:
            self.logger.error(f"Split command failed: {str(e)}")
            return 1
        except Exception as e:
            self.logger.error(f"Unexpected error in split command: {str(e)}")
            return 1

    def _log_execution_info(self, args: SplitCommandArgs) -> None:
        """Log execution information and warnings.

        Args:
            args: Split command arguments
        """
        # Check if file is CSV and Excel-specific options are used
        if args.file.suffix.lower() == ".csv":
            excel_options = []
            if args.include:
                excel_options.append("--include")
            if args.exclude:
                excel_options.append("--exclude")
            if args.sheet_config:
                excel_options.append("--sheet-config")

            if excel_options:
                self.logger.warning(
                    f"Excel-specific options {excel_options} will be ignored for CSV file"
                )

        self.logger.info(f"Input file: {args.file}")
        self.logger.info(f"Date column: {args.date_column}")
        self.logger.info(f"Split interval: {args.interval}")
        self.logger.info(f"Output directory: {args.output_dir}")

        if args.interval == "financial-year":
            self.logger.info(
                f"Financial year starts in month: {args.financial_year_start}"
            )

    def _load_and_process_sheets(
        self, args: SplitCommandArgs
    ) -> tuple[dict[str, pd.DataFrame], list[str], dict[str, SheetConfig]]:
        """Load file data and process sheet configuration.

        Args:
            args: Split command arguments

        Returns:
            Tuple of (file_data, selected_sheets, resolved_configs)
        """
        # Initialize processors
        data_processor = DataProcessor()
        sheet_config_processor = SheetConfigProcessor()

        # Load sheet configuration if provided
        sheet_config = None
        if args.sheet_config:
            self.logger.info("Loading sheet configuration")
            sheet_config = sheet_config_processor.load_sheet_config(args.sheet_config)

        # Load the input file
        self.logger.info("Loading input file")
        file_data = data_processor.load_file(args.file)

        # Determine which sheets to process
        if isinstance(file_data, dict):
            # Excel file - multiple sheets
            available_sheets = list(file_data.keys())
            self.logger.info(f"Excel file contains sheets: {available_sheets}")

            selected_sheets = sheet_config_processor.process_sheet_selection(
                available_sheets=available_sheets,
                include_sheets=args.include,
                exclude_sheets=args.exclude,
                sheet_config=sheet_config,
            )
        else:
            # CSV file - single "sheet"
            # For CSV files with sheet config, use the first configured sheet name if only one exists
            if sheet_config and len(sheet_config.keys()) == 1:
                csv_sheet_name = list(sheet_config.keys())[0]
                self.logger.info(
                    f"Using sheet config name '{csv_sheet_name}' for CSV file"
                )
            else:
                csv_sheet_name = "CSV"
                self.logger.info("Processing CSV file as single sheet")

            selected_sheets = [csv_sheet_name]
            file_data = {csv_sheet_name: file_data}

        # Resolve configurations for each sheet
        resolved_configs = sheet_config_processor.resolve_sheet_configs(
            sheet_names=selected_sheets,
            sheet_dataframes_map=file_data,
            global_date_column=args.date_column,
            global_date_format=args.date_format,
            sheet_config=sheet_config,
        )

        # Validate date columns in each sheet
        for sheet_name in selected_sheets:
            sheet_data = file_data[sheet_name]
            current_sheet_config = resolved_configs[sheet_name]

            self.logger.info(f"Validating date column for sheet '{sheet_name}'")
            # Ensure date_column is properly configured
            if current_sheet_config.date_column is None:
                raise SheetConfigError(
                    f"No date column configured for sheet '{sheet_name}'. "
                    f"This indicates a configuration error."
                )
            data_processor.validate_date_column(
                sheet_data, current_sheet_config.date_column
            )

        self.logger.info(
            "File loading and configuration processing completed successfully"
        )

        return file_data, selected_sheets, resolved_configs

    def _process_sheet_splitting(
        self,
        file_data: dict[str, pd.DataFrame],
        selected_sheets: list[str],
        resolved_configs: dict[str, SheetConfig],
        args: SplitCommandArgs,
    ) -> tuple[dict[str, SplitPeriodData], dict[str, pd.DataFrame]]:
        """Process splitting for all sheets.

        Args:
            file_data: Dictionary of sheet data
            selected_sheets: List of sheet names to process
            resolved_configs: Resolved configurations for each sheet
            args: Split command arguments

        Returns:
            Tuple of (period_data_map, unparseable_data_map)
        """
        self.logger.info("Starting date parsing and splitting process")

        # Collect all split data by time period
        period_data_map: dict[str, SplitPeriodData] = {}
        # Collect unparseable data by sheet name
        unparseable_data_map: dict[str, pd.DataFrame] = {}

        for sheet_name in selected_sheets:
            sheet_data = file_data[sheet_name]
            config = resolved_configs[sheet_name]

            self.logger.info(f"Processing sheet '{sheet_name}' for splitting")

            # Ensure date_column is properly configured
            if config.date_column is None:
                raise SheetConfigError(
                    f"No date column configured for sheet '{sheet_name}'. "
                    f"This indicates a configuration error."
                )

            # Parse dates in the sheet
            parse_result = self._parse_dates_in_sheet(
                sheet_data, config.date_column, config.date_format
            )

            # Store unparseable data if any exists
            if parse_result.unparseable_data is not None:
                unparseable_data_map[sheet_name] = parse_result.unparseable_data

            # Split data by the specified interval
            split_groups = self._split_data_by_interval(
                parse_result.parsed_data,
                config.date_column,
                args.interval,
                args.financial_year_start,
            )

            # Collect split data by time period
            for period_key, (
                period_data,
                representative_date,
            ) in split_groups.items():
                if period_key not in period_data_map:
                    period_data_map[period_key] = SplitPeriodData(
                        period_key=period_key,
                        representative_date=representative_date,
                        sheet_data={},
                    )

                period_data_map[period_key].sheet_data[sheet_name] = period_data

            self.logger.info(
                f"Sheet '{sheet_name}' prepared for {len(split_groups)} time periods"
            )

        return period_data_map, unparseable_data_map

    def _parse_dates_in_sheet(
        self, data: pd.DataFrame, date_column: str, date_format: str | None
    ) -> UnparseableDataResult:
        """Parse dates in a sheet and return both parsed and unparseable data.

        Args:
            data: Input DataFrame
            date_column: Name of the column containing date values
            date_format: Optional date format string

        Returns:
            UnparseableDataResult with parsed data and any unparseable rows

        Raises:
            DataLoadError: If date parsing fails completely
        """
        try:
            # Create a copy to avoid modifying original data
            parsed_data = data.copy()

            # TODO: Preserve original date/datetime format.
            # Parse dates using pandas
            if date_format:
                # Use explicit format if provided
                parsed_data[date_column] = pd.to_datetime(
                    parsed_data[date_column], format=date_format, errors="coerce"
                )
            else:
                # Let pandas infer the format
                parsed_data[date_column] = pd.to_datetime(
                    parsed_data[date_column], errors="coerce"
                )

            # Separate parsed and unparseable data
            date_mask = parsed_data[date_column].notna()
            valid_data = parsed_data[date_mask].copy()
            unparseable_data = data[~date_mask].copy() if (~date_mask).any() else None

            # Check for parsing failures
            null_dates = (~date_mask).sum()
            total_dates = len(parsed_data)

            if null_dates == total_dates:
                raise DataLoadError(
                    f"Failed to parse any dates in column '{date_column}'. "
                    f"Check the date format or provide explicit format with --date-format"
                )

            if null_dates > 0:
                self.logger.warning(
                    f"Failed to parse {null_dates} out of {total_dates} dates in column '{date_column}'. "
                    f"These rows will be saved to a separate file."
                )

            self.logger.info(
                f"Successfully parsed {len(valid_data)} dates in column '{date_column}'"
            )

            return UnparseableDataResult(
                parsed_data=valid_data, unparseable_data=unparseable_data
            )

        except Exception as e:
            raise DataLoadError(
                f"Date parsing failed for column '{date_column}': {str(e)}"
            ) from e

    def _split_data_by_interval(
        self,
        data: pd.DataFrame,
        date_column: str,
        interval: SplitInterval,
        financial_year_start: int,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by time interval using strategy pattern.

        Args:
            data: DataFrame with parsed dates
            date_column: Name of the date column
            interval: Time interval for splitting
            financial_year_start: Start month of financial year

        Returns:
            Dictionary mapping period names to (DataFrame, representative_date) tuples
        """
        # Create appropriate strategy for the interval
        strategy = create_split_strategy(interval)

        # Use strategy to split the data
        return strategy.split_data(data, date_column, financial_year_start)

    def _write_combined_split_files(
        self,
        period_data_map: dict[str, SplitPeriodData],
        file_manager: FileOutputManager,
        original_filename: str,
        interval: SplitInterval,
        financial_year_start: int,
        selected_sheets: list[str],
        all_file_data: dict[str, pd.DataFrame],
    ) -> list[Path]:
        """Write combined split data to output files (one file per time period).

        Args:
            period_data_map: Dictionary mapping period_key to SplitPeriodData objects
            file_manager: FileOutputManager instance
            original_filename: Name of the original file
            interval: Time interval used for splitting
            financial_year_start: Start month of financial year
            selected_sheets: List of all sheets being processed
            all_file_data: All sheet data from the original file

        Returns:
            List of paths to written files
        """
        output_files: list[Path] = []

        for period_key in sorted(period_data_map.keys()):
            period_data = period_data_map[period_key]
            sheet_name_data_map = period_data.sheet_data
            representative_date = period_data.representative_date

            # Generate filename for this period
            filename = file_manager.generate_filename(
                original_filename, interval, representative_date, financial_year_start
            )

            # Determine file format and content
            original_path = Path(original_filename)
            file_extension = original_path.suffix.lower()

            if file_extension == ".csv" or len(selected_sheets) == 1:
                # Write single sheet (CSV or single-sheet Excel)
                # For CSV, use the only sheet's data
                # For single-sheet Excel, use that sheet's data
                sheet_name = next(iter(sheet_name_data_map.keys()))
                period_data_df = sheet_name_data_map[sheet_name]

                output_path = file_manager.write_dataframe(
                    period_data_df, filename, sheet_name
                )
            else:
                # Write multi-sheet Excel file
                # Combine split data with any non-split sheets while preserving original sheet order
                sheet_data_for_period = {}

                # Iterate through all sheets in original order and use split data where available
                for sheet_name, original_sheet_data in all_file_data.items():
                    if sheet_name in selected_sheets:
                        if sheet_name in sheet_name_data_map:
                            # Use split data for this time period
                            sheet_data_for_period[sheet_name] = sheet_name_data_map[
                                sheet_name
                            ]
                        else:
                            # Create empty DataFrame with same columns for sheets with no data in this period
                            empty_df = pd.DataFrame(columns=original_sheet_data.columns)
                            sheet_data_for_period[sheet_name] = empty_df
                    else:
                        # Use original data for non-selected sheets
                        sheet_data_for_period[sheet_name] = original_sheet_data

                output_path = file_manager.write_multiple_sheets(
                    sheet_data_for_period, filename
                )

            output_files.append(output_path)

            # Log details about this period's file
            total_rows = sum(len(df) for df in sheet_name_data_map.values())
            self.logger.debug(
                f"Written {total_rows} total rows for period {period_key} to {output_path}"
            )

        return output_files

    def _generate_unparseable_filename(self, original_filename: str) -> str:
        """Generate filename for unparseable data.

        Args:
            original_filename: Name of the original file

        Returns:
            Generated filename for unparseable data
        """
        original_path = Path(original_filename)
        base_name = original_path.stem
        extension = original_path.suffix

        return f"{base_name}_unparseable_dates{extension}"

    def _write_unparseable_data_file(
        self,
        unparseable_data_map: dict[str, pd.DataFrame],
        file_manager: FileOutputManager,
        original_filename: str,
        selected_sheets: list[str],
        all_file_data: dict[str, pd.DataFrame],
    ) -> Path:
        """Write unparseable data to a separate output file.

        Args:
            unparseable_data_map: Dictionary mapping sheet names to unparseable DataFrames
            file_manager: FileOutputManager instance
            original_filename: Name of the original file
            selected_sheets: List of all sheets being processed
            all_file_data: All sheet data from the original file

        Returns:
            Path to the written unparseable data file
        """
        # Generate filename for unparseable data
        filename = self._generate_unparseable_filename(original_filename)

        # Determine file format and content
        original_path = Path(original_filename)
        file_extension = original_path.suffix.lower()

        if file_extension == ".csv" or len(selected_sheets) == 1:
            # Write single sheet (CSV or single-sheet Excel)
            sheet_name = next(iter(unparseable_data_map.keys()))
            unparseable_df = unparseable_data_map[sheet_name]

            output_path = file_manager.write_dataframe(
                unparseable_df, filename, sheet_name
            )
            self.logger.info(
                f"Written unparseable data for sheet '{sheet_name}': {len(unparseable_df)} rows"
            )
        else:
            # Write multi-sheet Excel file
            # Combine unparseable data with empty sheets for non-processed sheets
            # while preserving original sheet order
            sheet_data_for_unparseable = {}

            # Iterate through all sheets in original order
            for sheet_name, original_sheet_data in all_file_data.items():
                if sheet_name in selected_sheets:
                    if sheet_name in unparseable_data_map:
                        # Use unparseable data for this sheet
                        sheet_data_for_unparseable[sheet_name] = unparseable_data_map[
                            sheet_name
                        ]
                    else:
                        # Create empty DataFrame with same columns for sheets with no unparseable data
                        empty_df = pd.DataFrame(columns=original_sheet_data.columns)
                        sheet_data_for_unparseable[sheet_name] = empty_df
                else:
                    # Create empty DataFrame for non-selected sheets to maintain structure
                    empty_df = pd.DataFrame(columns=original_sheet_data.columns)
                    sheet_data_for_unparseable[sheet_name] = empty_df

            output_path = file_manager.write_multiple_sheets(
                sheet_data_for_unparseable, filename
            )

            # Log details about unparseable data by sheet
            for sheet_name, df in unparseable_data_map.items():
                self.logger.info(
                    f"Written unparseable data for sheet '{sheet_name}': {len(df)} rows"
                )

        return output_path
