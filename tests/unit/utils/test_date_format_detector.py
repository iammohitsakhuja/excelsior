"""Unit tests for date format detection utilities."""

import pandas as pd
import pytest

from excelsior.utils import (
    DateFormatDetectionError,
    DateFormatDetector,
)


class TestDateFormatDetector:
    """Test the DateFormatDetector class."""

    def test_detect_date_format_missing_column(self):
        """Test date format detection with missing column."""
        detector = DateFormatDetector()

        data = pd.DataFrame({"Amount": [100, 200, 300], "Description": ["A", "B", "C"]})

        with pytest.raises(DateFormatDetectionError) as exc_info:
            detector.detect_date_format(data, "Date")

        assert "Date column 'Date' not found" in str(exc_info.value)
        assert "Available columns: Amount, Description" in str(exc_info.value)

    def test_detect_date_format_empty_column(self):
        """Test date format detection with empty date column."""
        detector = DateFormatDetector()

        data = pd.DataFrame(
            {
                "Date": [None, None, None],
                "Amount": [100, 200, 300],
            }
        )

        with pytest.raises(DateFormatDetectionError) as exc_info:
            detector.detect_date_format(data, "Date")

        assert "Date column 'Date' contains no valid data for format detection" in str(
            exc_info.value
        )

    def test_detect_date_format_various_patterns(self):
        """Test detection of various date format patterns."""
        detector = DateFormatDetector()

        test_cases = [
            # Format, Sample data, Expected format
            (["2024-01-15", "2024-02-20"], "%Y-%m-%d"),
            (["01/15/2024", "02/20/2024"], "%m/%d/%Y"),
            (["15/01/2024", "20/02/2024"], "%d/%m/%Y"),
            (["2024/01/15", "2024/02/20"], "%Y/%m/%d"),
            (["15.01.2024", "20.02.2024"], "%d.%m.%Y"),
            (["2024.01.15", "2024.02.20"], "%Y.%m.%d"),
            (["01-15-2024", "02-20-2024"], "%m-%d-%Y"),
            (["15-01-2024", "20-02-2024"], "%d-%m-%Y"),
            (["January 15, 2024", "February 20, 2024"], "%B %d, %Y"),
            (["Jan 15, 2024", "Feb 20, 2024"], "%b %d, %Y"),
            (["15 January 2024", "20 February 2024"], "%d %B %Y"),
            (["15 Jan 2024", "20 Feb 2024"], "%d %b %Y"),
        ]

        for sample_data, expected_format in test_cases:
            data = pd.DataFrame({"Date": sample_data})
            detected_format = detector.detect_date_format(data, "Date")
            assert detected_format == expected_format, (
                f"Failed for {sample_data}: expected {expected_format}, got {detected_format}"
            )

    def test_detect_date_format_unrecognized_pattern(self):
        """Test date format detection with unrecognized pattern."""
        detector = DateFormatDetector()

        # Data that doesn't match any known pattern
        data = pd.DataFrame(
            {
                "Date": ["invalid", "also invalid", "not a date"],
            }
        )

        result = detector.detect_date_format(data, "Date")
        # Should return None due to unrecognized pattern
        assert result is None

    def test_detect_date_format_large_sample(self):
        """Test date format detection with a large dataset (performance test)."""
        detector = DateFormatDetector()

        # Create a large dataset (100 dates)
        large_date_list = [f"2024-{i:02d}-15" for i in range(1, 13)]  # 12 months
        large_date_list = large_date_list * 10  # Repeat to get 120 dates

        data = pd.DataFrame({"Date": large_date_list})
        detected_format = detector.detect_date_format(data, "Date")

        # Should still detect the ISO format correctly
        assert detected_format == "%Y-%m-%d"

    def test_detect_date_format_inconsistent_formats(self):
        """Test that inconsistent date formats raise detailed error."""
        detector = DateFormatDetector()

        # Data with inconsistent formats
        data = pd.DataFrame(
            {
                "Date": [
                    "2024-01-15",
                    "02/20/2024",
                    "25.03.2024",
                    "not-a-date",
                    "2024-05-10",
                ],
            }
        )

        with pytest.raises(DateFormatDetectionError) as exc_info:
            detector.detect_date_format(data, "Date")

        error_message = str(exc_info.value)
        assert "Inconsistent date formats detected" in error_message
        assert "Detected format '%Y-%m-%d'" in error_message
        assert "02/20/2024" in error_message
        assert "25.03.2024" in error_message
        assert "not-a-date" in error_message
        assert "Row 1:" in error_message  # Should show row numbers

    def test_detect_date_format_consistent_formats(self):
        """Test that consistent formats are detected successfully."""
        detector = DateFormatDetector()

        # Data with consistent ISO format
        data = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05"],
            }
        )

        detected_format = detector.detect_date_format(data, "Date")
        assert detected_format == "%Y-%m-%d"

    def test_detect_format_from_value_iso(self):
        """Test detecting format from a single ISO date value."""
        detector = DateFormatDetector()

        result = detector._detect_format_from_value("2024-01-15")
        assert result == "%Y-%m-%d"

    def test_detect_format_from_value_us(self):
        """Test detecting format from a single US date value."""
        detector = DateFormatDetector()

        result = detector._detect_format_from_value("01/15/2024")
        assert result == "%m/%d/%Y"

    def test_detect_format_from_value_european(self):
        """Test detecting format from a single European date value."""
        detector = DateFormatDetector()

        result = detector._detect_format_from_value("15/01/2024")
        assert result == "%d/%m/%Y"

    def test_detect_format_from_value_invalid(self):
        """Test detecting format from an invalid date value."""
        detector = DateFormatDetector()

        result = detector._detect_format_from_value("not-a-date")
        assert result is None

    def test_detect_date_format_with_datetime(self):
        """Test date format detection for datetime format."""
        detector = DateFormatDetector()

        # Create test data with datetime format
        data = pd.DataFrame(
            {
                "DateTime": [
                    "2024-01-15 14:30:00",
                    "2024-02-20 09:15:30",
                    "2024-03-10 16:45:00",
                ],
            }
        )

        detected_format = detector.detect_date_format(data, "DateTime")
        # Should detect datetime format
        assert detected_format == "%Y-%m-%d %H:%M:%S"

    def test_detect_date_format_with_datetime_no_seconds(self):
        """Test date format detection for datetime format without seconds."""
        detector = DateFormatDetector()

        # Create test data with datetime format (no seconds)
        data = pd.DataFrame(
            {
                "DateTime": [
                    "2024-01-15 14:30",
                    "2024-02-20 09:15",
                    "2024-03-10 16:45",
                ],
            }
        )

        detected_format = detector.detect_date_format(data, "DateTime")
        # Should detect datetime format without seconds
        assert detected_format == "%Y-%m-%d %H:%M"
