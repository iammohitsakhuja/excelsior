"""File output management utilities for Excelsior CLI."""

import os
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from excelsior.utils.logger import get_logger
from excelsior.utils.types import SplitInterval

logger = get_logger(__name__)


class FileOutputError(Exception):
    """Exception raised when file output operations fail."""

    pass


class ConflictResolution(Enum):
    """Strategies for handling existing files."""

    OVERWRITE = "overwrite"
    SKIP = "skip"
    RENAME = "rename"


class FileOutputManager:
    """Manages output file operations for the split command.

    This class handles:
    - Output directory creation and management
    - File naming conventions based on time intervals
    - Conflict resolution for existing files
    - Writing data to output files
    """

    def __init__(
        self,
        output_dir: Path,
        conflict_resolution: ConflictResolution = ConflictResolution.RENAME,
    ):
        """Initialize the file output manager.

        Args:
            output_dir: Directory where output files will be created
            conflict_resolution: Strategy for handling existing files
        """
        self.output_dir = output_dir
        self.conflict_resolution = conflict_resolution
        self.logger = get_logger(self.__class__.__module__)

    def ensure_output_directory(self) -> None:
        """Create the output directory if it doesn't exist.

        Raises:
            FileOutputError: If directory creation fails or path is not writable
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Check if directory is writable
            if not os.access(self.output_dir, os.W_OK):
                raise FileOutputError(
                    f"Output directory is not writable: {self.output_dir}"
                )

            self.logger.debug(f"Output directory ensured: {self.output_dir}")

        except OSError as e:
            raise FileOutputError(
                f"Failed to create output directory {self.output_dir}: {e}"
            ) from e

    def generate_filename(
        self,
        original_filename: str,
        interval: SplitInterval,
        period_date: date,
        financial_year_start: int = 4,
    ) -> str:
        """Generate output filename based on naming conventions.

        Args:
            original_filename: Name of the original file (including extension)
            interval: Time interval for splitting
            period_date: Representative date for the time period
            financial_year_start: Start month of financial year (1-12)

        Returns:
            Generated filename following the naming convention

        Raises:
            FileOutputError: If interval is not supported
        """
        # Extract original name without extension
        original_path = Path(original_filename)
        base_name = original_path.stem
        extension = original_path.suffix

        # Generate period suffix based on interval
        period_suffix = self._generate_period_suffix(
            interval, period_date, financial_year_start
        )

        # Combine components (no sheet name included)
        filename = f"{base_name}_{period_suffix}{extension}"

        self.logger.debug(
            f"Generated filename: {filename} for period {period_date} with interval {interval}"
        )

        return filename

    def _generate_period_suffix(
        self, interval: SplitInterval, period_date: date, financial_year_start: int
    ) -> str:
        """Generate period suffix for filename based on interval.

        Args:
            interval: Time interval for splitting
            period_date: Representative date for the time period
            financial_year_start: Start month of financial year (1-12)

        Returns:
            Period suffix string

        Raises:
            FileOutputError: If interval is not supported
        """
        if interval == "day":
            return period_date.strftime("%Y-%m-%d")

        elif interval == "week":
            # ISO week format: YYYY-Www (e.g., 2023-W15)
            year, week, _ = period_date.isocalendar()
            return f"{year}-W{week:02d}"

        elif interval == "month":
            return period_date.strftime("%Y-%m")

        elif interval == "year":
            return period_date.strftime("%Y")

        elif interval == "financial-year":
            # Calculate financial year based on start month
            fy_start_year = period_date.year
            if period_date.month < financial_year_start:
                fy_start_year -= 1
            fy_end_year = fy_start_year + 1
            return f"FY{fy_start_year}-{fy_end_year}"

        else:
            raise FileOutputError(f"Unsupported interval: {interval}")

    def resolve_output_path(self, filename: str) -> Path:
        """Resolve the final output path, handling conflicts if necessary.

        Args:
            filename: Base filename to use

        Returns:
            Final path to use for output

        Raises:
            FileOutputError: If conflict resolution fails
        """
        base_path = self.output_dir / filename

        if not base_path.exists():
            return base_path

        # Handle existing file based on conflict resolution strategy
        if self.conflict_resolution == ConflictResolution.OVERWRITE:
            self.logger.warning(f"Will overwrite existing file: {base_path}")
            return base_path

        elif self.conflict_resolution == ConflictResolution.SKIP:
            self.logger.warning(f"Skipping existing file: {base_path}")
            raise FileOutputError(
                f"File already exists and conflict resolution is set to skip: {base_path}"
            )

        elif self.conflict_resolution == ConflictResolution.RENAME:
            return self._generate_unique_path(base_path)

        else:
            raise FileOutputError(
                f"Unknown conflict resolution strategy: {self.conflict_resolution}"
            )

    def _generate_unique_path(self, base_path: Path) -> Path:
        """Generate a unique path by appending a counter.

        Args:
            base_path: Original path that conflicts

        Returns:
            Unique path with counter suffix
        """
        counter = 1
        stem = base_path.stem
        suffix = base_path.suffix

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = base_path.parent / new_name
            if not new_path.exists():
                self.logger.info(f"Resolved conflict by renaming to: {new_path}")
                return new_path
            counter += 1

            # Safety check to prevent infinite loop
            if counter > 9999:
                raise FileOutputError(
                    f"Unable to generate unique filename after {counter} attempts"
                )

    def write_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_name: str = "Sheet1",
    ) -> Path:
        """Write DataFrame to output file.

        Args:
            df: DataFrame to write
            filename: Filename to use
            sheet_name: Sheet name for Excel files

        Returns:
            Path to the written file

        Raises:
            FileOutputError: If writing fails
        """
        try:
            self.ensure_output_directory()
            output_path = self.resolve_output_path(filename)

            # Determine file format from extension
            file_extension = Path(filename).suffix.lower()

            if file_extension == ".csv":
                df.to_csv(output_path, index=False)
                self.logger.info(f"Written CSV file: {output_path} ({len(df)} rows)")

            elif file_extension in [".xlsx", ".xls"]:
                df.to_excel(output_path, sheet_name=sheet_name, index=False)
                self.logger.info(
                    f"Written Excel file: {output_path} ({len(df)} rows, sheet: {sheet_name})"
                )

            else:
                raise FileOutputError(f"Unsupported file format: {file_extension}")

            return output_path

        except Exception as e:
            raise FileOutputError(f"Failed to write file {filename}: {e}") from e

    def write_multiple_sheets(
        self,
        sheet_data: dict[str, pd.DataFrame],
        filename: str,
    ) -> Path:
        """Write multiple DataFrames to a single file preserving all sheets.

        Args:
            sheet_data: Dictionary mapping sheet names to DataFrames
            filename: Filename to use

        Returns:
            Path to the written file

        Raises:
            FileOutputError: If writing fails or format is incompatible
        """
        file_extension = Path(filename).suffix.lower()

        if file_extension == ".csv" and len(sheet_data) > 1:
            raise FileOutputError("Cannot write multiple sheets to CSV format")

        try:
            self.ensure_output_directory()
            output_path = self.resolve_output_path(filename)

            if file_extension == ".csv" or len(sheet_data) == 1:
                # Write single sheet as CSV or single-sheet Excel
                sheet_name, df = next(iter(sheet_data.items()))
                return self.write_dataframe(df, filename, sheet_name)

            else:
                # Write multiple sheets to Excel file
                with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                    total_rows = 0
                    for sheet_name, df in sheet_data.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        total_rows += len(df)

                self.logger.info(
                    f"Written Excel file: {output_path} ({total_rows} total rows across {len(sheet_data)} sheets)"
                )
                return output_path

        except Exception as e:
            raise FileOutputError(
                f"Failed to write multi-sheet file {filename}: {e}"
            ) from e

    def get_file_stats(self, file_path: Path) -> dict[str, str | int | datetime]:
        """Get statistics about a written file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file statistics

        Raises:
            FileOutputError: If file doesn't exist or reading fails
        """
        if not file_path.exists():
            raise FileOutputError(f"File not found: {file_path}")

        try:
            stats = file_path.stat()
            return {
                "path": str(file_path),
                "size_bytes": stats.st_size,
                "size_human": self._format_file_size(stats.st_size),
                "created": datetime.fromtimestamp(stats.st_ctime),
                "modified": datetime.fromtimestamp(stats.st_mtime),
            }

        except OSError as e:
            raise FileOutputError(
                f"Failed to get file statistics for {file_path}: {e}"
            ) from e

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted size string
        """
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def cleanup_empty_directory(self) -> bool:
        """Remove output directory if it's empty.

        Returns:
            True if directory was removed, False if it wasn't empty or doesn't exist
        """
        try:
            if self.output_dir.exists() and self.output_dir.is_dir():
                # Check if directory is empty
                if not any(self.output_dir.iterdir()):
                    self.output_dir.rmdir()
                    self.logger.debug(
                        f"Removed empty output directory: {self.output_dir}"
                    )
                    return True
                else:
                    self.logger.debug(
                        f"Output directory not empty, keeping: {self.output_dir}"
                    )
                    return False
            return False

        except OSError as e:
            self.logger.warning(
                f"Failed to remove empty directory {self.output_dir}: {e}"
            )
            return False
