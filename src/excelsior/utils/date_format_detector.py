"""Date format detection utilities for automatically detecting date formats in data columns."""

import re

import pandas as pd

from excelsior.utils.logger import get_logger


class DateFormatDetectionError(Exception):
    """Exception raised when date format detection fails."""

    pass


class DateFormatDetector:
    """Handles automatic detection and validation of date formats in data columns."""

    def __init__(self):
        """Initialize the date format detector."""
        self.logger = get_logger(self.__class__.__module__)

        # Common date format patterns to try (ordered by priority)
        self.format_patterns = [
            # ISO formats (most common first)
            ("%Y-%m-%d", r"^\d{4}-\d{1,2}-\d{1,2}$"),
            ("%Y-%m-%d %H:%M:%S", r"^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2}$"),
            ("%Y-%m-%d %H:%M", r"^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}$"),
            # Common Worldwide formats
            ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
            ("%d/%m/%y", r"^\d{1,2}/\d{1,2}/\d{2}$"),
            ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
            ("%d-%m-%y", r"^\d{1,2}-\d{1,2}-\d{2}$"),
            ("%d.%m.%Y", r"^\d{1,2}\.\d{1,2}\.\d{4}$"),
            ("%d.%m.%y", r"^\d{1,2}\.\d{1,2}\.\d{2}$"),
            # Common US formats
            ("%m/%d/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
            ("%m/%d/%y", r"^\d{1,2}/\d{1,2}/\d{2}$"),
            ("%m-%d-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
            ("%m-%d-%y", r"^\d{1,2}-\d{1,2}-\d{2}$"),
            # Other common formats
            ("%Y/%m/%d", r"^\d{4}/\d{1,2}/\d{1,2}$"),
            ("%Y.%m.%d", r"^\d{4}\.\d{1,2}\.\d{1,2}$"),
            ("%B %d, %Y", r"^[A-Za-z]+ \d{1,2}, \d{4}$"),
            ("%b %d, %Y", r"^[A-Za-z]+ \d{1,2}, \d{4}$"),
            ("%d %B %Y", r"^\d{1,2} [A-Za-z]+ \d{4}$"),
            ("%d %b %Y", r"^\d{1,2} [A-Za-z]+ \d{4}$"),
        ]

    def detect_date_format(self, data: pd.DataFrame, date_column: str) -> str | None:
        """Detect the date format from the first non-null value and validate consistency.

        Args:
            data: DataFrame containing the date column
            date_column: Name of the column containing date values

        Returns:
            Detected date format string, or None if detection fails

        Raises:
            DateFormatDetectionError: If the date column doesn't exist, has no valid data,
                                    or contains inconsistent date formats
        """
        if date_column not in data.columns:
            available_columns = ", ".join(data.columns.tolist())
            raise DateFormatDetectionError(
                f"Date column '{date_column}' not found. "
                f"Available columns: {available_columns}"
            )

        # Get non-null values from the date column
        date_values = data[date_column].dropna()
        if len(date_values) == 0:
            raise DateFormatDetectionError(
                f"Date column '{date_column}' contains no valid data for format detection"
            )

        # Convert to string for pattern matching
        string_values = date_values.astype(str).tolist()

        # Use the first non-null value to detect the format
        first_value = string_values[0].strip()
        detected_format = self._detect_format_from_value(first_value)

        if not detected_format:
            self.logger.warning(
                f"Could not detect date format for column '{date_column}' "
                f"from first value '{first_value}'. "
                f"Consider providing explicit format with --date-format or in sheet config."
            )
            return None

        # Validate that all values match this format
        self._validate_format_consistency(
            string_values, date_values, detected_format, date_column
        )

        self.logger.info(
            f"Detected date format '{detected_format}' for column '{date_column}' "
            f"(validated {len(string_values)} values)"
        )
        return detected_format

    def _detect_format_from_value(self, value: str) -> str | None:
        """Detect the date format from a single value.

        Args:
            value: Date string to analyze

        Returns:
            Detected date format string, or None if no format matches
        """
        # Find the format that matches the value
        for date_format, pattern in self.format_patterns:
            if re.match(pattern, value):
                # Try to actually parse it to confirm
                try:
                    pd.to_datetime(value, format=date_format, errors="raise")
                    return date_format
                except (ValueError, TypeError):
                    continue

        return None

    def _validate_format_consistency(
        self,
        string_values: list[str],
        date_values: pd.Series,
        detected_format: str,
        date_column: str,
    ) -> None:
        """Validate that all values in the column match the detected format.

        Args:
            string_values: List of string values from the date column
            date_values: Original pandas Series with date values (for index mapping)
            detected_format: The detected date format to validate against
            date_column: Name of the date column (for error messages)

        Raises:
            DateFormatDetectionError: If inconsistent formats are found
        """
        # Find the regex pattern for the detected format
        pattern = None
        for fmt, pat in self.format_patterns:
            if fmt == detected_format:
                pattern = pat
                break

        # This should not happen since we found the format above, but be safe
        if pattern is None:
            return

        # Validate all values match this format
        mismatched_values = []

        for i, value in enumerate(string_values):
            value = value.strip()

            # Check pattern match first
            if not re.match(pattern, value):
                mismatched_values.append((i, value))
            else:
                # Also try to parse it
                try:
                    pd.to_datetime(value, format=detected_format, errors="raise")
                except (ValueError, TypeError):
                    mismatched_values.append((i, value))

            # Stop collecting after 5 mismatches for error reporting
            if len(mismatched_values) >= 5:
                break

        if mismatched_values:
            self._raise_consistency_error(
                mismatched_values,
                string_values,
                date_values,
                detected_format,
                date_column,
                pattern,
            )

    def _raise_consistency_error(
        self,
        mismatched_values: list[tuple[int, str]],
        string_values: list[str],
        date_values: pd.Series,
        detected_format: str,
        date_column: str,
        pattern: str,
    ) -> None:
        """Raise a detailed error for inconsistent date formats.

        Args:
            mismatched_values: List of (index, value) tuples for mismatched values
            string_values: All string values from the column
            date_values: Original pandas Series (for row index mapping)
            detected_format: The detected format
            date_column: Name of the date column
            pattern: Regex pattern for the detected format
        """
        mismatch_details = []
        for row_idx, value in mismatched_values[:5]:
            # Convert back to original DataFrame row index
            original_row = date_values.index[row_idx]
            mismatch_details.append(f"  Row {original_row}: '{value}'")

        mismatch_summary = "\n".join(mismatch_details)
        total_mismatches = len(
            [v for v in string_values if not re.match(pattern, v.strip())]
        )

        raise DateFormatDetectionError(
            f"Inconsistent date formats detected in column '{date_column}'. "
            f"Detected format '{detected_format}' from first value, but found "
            f"{total_mismatches} values that don't match this format:\n"
            f"{mismatch_summary}"
            f"{' (showing first 5)' if total_mismatches > 5 else ''}\n"
            f"Please ensure all dates in the column use the same format, "
            f"or provide an explicit format with --date-format."
        )
