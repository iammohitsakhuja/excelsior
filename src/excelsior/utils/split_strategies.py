"""Split strategies for different time intervals."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol

import pandas as pd

from excelsior.utils.logger import get_logger
from excelsior.utils.types import SplitInterval

logger = get_logger(__name__)


class SplitStrategy(Protocol):
    """Protocol for data splitting strategies."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by time period.

        Args:
            data: DataFrame to split
            date_column: Name of the date column to split by
            financial_year_start: Month when financial year starts (1-12, default 4 for April)

        Returns:
            Dictionary mapping period names to (DataFrame, representative_date) tuples
        """
        ...


class BaseSplitStrategy(ABC):
    """Base class for split strategies with common functionality."""

    def __init__(self) -> None:
        """Initialize the strategy."""
        self.logger = logger

    @abstractmethod
    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by time period.

        Args:
            data: DataFrame to split
            date_column: Name of the date column to split by
            financial_year_start: Month when financial year starts (1-12, default 4 for April)

        Returns:
            Dictionary mapping period names to (DataFrame, representative_date) tuples
        """
        pass


class DaySplitStrategy(BaseSplitStrategy):
    """Strategy for splitting data by individual days."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by individual days."""
        groups: dict[str, tuple[pd.DataFrame, date]] = {}

        # Group by individual days
        for period_date, group_data in data.groupby(data[date_column].dt.date):
            period_key = period_date.strftime("%Y-%m-%d")
            groups[period_key] = (group_data.copy(), period_date)

        self.logger.info(f"Split data into {len(groups)} groups by day")
        return groups


class WeekSplitStrategy(BaseSplitStrategy):
    """Strategy for splitting data by ISO weeks."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by ISO weeks."""
        groups: dict[str, tuple[pd.DataFrame, date]] = {}

        # Group by ISO weeks
        for (year, week), group_data in data.groupby(
            [
                data[date_column].dt.isocalendar().year,
                data[date_column].dt.isocalendar().week,
            ]
        ):
            # Find the first date of the week as representative date
            first_date = group_data[date_column].min().date()
            period_key = f"{year}-W{week:02d}"
            groups[period_key] = (group_data.copy(), first_date)

        self.logger.info(f"Split data into {len(groups)} groups by week")
        return groups


class MonthSplitStrategy(BaseSplitStrategy):
    """Strategy for splitting data by calendar months."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by calendar months."""
        groups: dict[str, tuple[pd.DataFrame, date]] = {}

        # Group by months
        for (year, month), group_data in data.groupby(
            [data[date_column].dt.year, data[date_column].dt.month]
        ):
            # Use first day of month as representative date
            representative_date = date(year, month, 1)
            period_key = f"{year}-{month:02d}"
            groups[period_key] = (group_data.copy(), representative_date)

        self.logger.info(f"Split data into {len(groups)} groups by month")
        return groups


class YearSplitStrategy(BaseSplitStrategy):
    """Strategy for splitting data by calendar years."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by calendar years."""
        groups: dict[str, tuple[pd.DataFrame, date]] = {}

        # Group by calendar years
        for year, group_data in data.groupby(data[date_column].dt.year):
            # Use January 1st as representative date
            representative_date = date(year, 1, 1)
            period_key = str(year)
            groups[period_key] = (group_data.copy(), representative_date)

        self.logger.info(f"Split data into {len(groups)} groups by year")
        return groups


class FinancialYearSplitStrategy(BaseSplitStrategy):
    """Strategy for splitting data by financial years."""

    def split_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        financial_year_start: int = 4,
    ) -> dict[str, tuple[pd.DataFrame, date]]:
        """Split data by financial years."""
        groups: dict[str, tuple[pd.DataFrame, date]] = {}

        def get_financial_year(dt):
            """Get financial year for a date."""
            if dt.month >= financial_year_start:
                return dt.year
            else:
                return dt.year - 1

        fy_groups = data.groupby(data[date_column].apply(get_financial_year))
        for fy_start_year, group_data in fy_groups:
            # Use the start of financial year as representative date
            representative_date = date(fy_start_year, financial_year_start, 1)
            fy_end_year = fy_start_year + 1
            period_key = f"FY{fy_start_year}-{fy_end_year}"
            groups[period_key] = (group_data.copy(), representative_date)

        self.logger.info(f"Split data into {len(groups)} groups by financial year")
        return groups


def create_split_strategy(interval: SplitInterval) -> SplitStrategy:
    """Factory function to create appropriate split strategy.

    Args:
        interval: The split interval type

    Returns:
        Appropriate strategy instance for the interval

    Raises:
        ValueError: If interval is not supported
    """
    strategies = {
        "day": DaySplitStrategy(),
        "week": WeekSplitStrategy(),
        "month": MonthSplitStrategy(),
        "year": YearSplitStrategy(),
        "financial-year": FinancialYearSplitStrategy(),
    }

    if interval not in strategies:
        raise ValueError(f"Unsupported interval: {interval}")

    return strategies[interval]
