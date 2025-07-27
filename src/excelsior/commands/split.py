"""Split command implementation for Excelsior CLI."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from excelsior.commands.base import FileProcessingCommand
from excelsior.schemas.split import SplitSheetConfigSchema
from excelsior.utils.logger import get_logger

logger = get_logger(__name__)


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
  excelsior split -f multi_sheet_data.xlsx -d "Date" -s "Sales" "Expenses"

  # Split with sheet-specific configuration
  excelsior split -f complex_data.xlsx -sc sheet_config.json

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
            default=Path("./split_output"),
            help="Directory for output files (default: %(default)s)",
            metavar="PATH",
        )

        # Excel-specific options
        excel_group = parser.add_argument_group("Excel-specific options")

        excel_group.add_argument(
            "--sheets",
            "-s",
            nargs="+",
            help=(
                "List of sheet names to process (Excel only). "
                "If not specified, all sheets will be processed"
            ),
            metavar="SHEET",
        )

        excel_group.add_argument(
            "--exclude-sheets",
            "-xs",
            nargs="+",
            help="List of sheet names to exclude from processing (Excel only)",
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

        if args.sheets and args.exclude_sheets:
            # Check for overlap between sheets and exclude_sheets
            include_set = set(args.sheets)
            exclude_set = set(args.exclude_sheets)
            overlap = include_set & exclude_set
            if overlap:
                return f"Cannot both include and exclude the same sheets: {overlap}"

        return None

    def execute(self, args: argparse.Namespace) -> int:
        """Execute the split command.

        Args:
            args: Parsed command line arguments

        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        self.logger.info("Starting split command")

        # Check if file is CSV and Excel-specific options are used
        if args.file.suffix.lower() == ".csv":
            excel_options = []
            if args.sheets:
                excel_options.append("--sheets")
            if args.exclude_sheets:
                excel_options.append("--exclude-sheets")
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

        # TODO: Implement the actual splitting logic
        self.logger.info("Split command execution completed successfully")

        return 0
