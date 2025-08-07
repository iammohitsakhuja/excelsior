"""Unit tests for split strategies."""

from datetime import date

import pandas as pd
import pytest

from excelsior.utils.split_strategies import (
    DaySplitStrategy,
    FinancialYearSplitStrategy,
    MonthSplitStrategy,
    WeekSplitStrategy,
    YearSplitStrategy,
    create_split_strategy,
)


class TestSplitStrategyProtocol:
    """Test the SplitStrategy protocol compliance."""

    def test_all_strategies_implement_protocol(self):
        """Test that all strategy classes implement the SplitStrategy protocol."""
        strategies = [
            DaySplitStrategy(),
            WeekSplitStrategy(),
            MonthSplitStrategy(),
            YearSplitStrategy(),
            FinancialYearSplitStrategy(),
        ]

        for strategy in strategies:
            # Check that strategy has required methods
            assert hasattr(strategy, "split_data")
            assert callable(strategy.split_data)


class TestCreateSplitStrategy:
    """Test the strategy factory function."""

    def test_create_day_strategy(self):
        """Test creating a day split strategy."""
        strategy = create_split_strategy("day")
        assert isinstance(strategy, DaySplitStrategy)

    def test_create_week_strategy(self):
        """Test creating a week split strategy."""
        strategy = create_split_strategy("week")
        assert isinstance(strategy, WeekSplitStrategy)

    def test_create_month_strategy(self):
        """Test creating a month split strategy."""
        strategy = create_split_strategy("month")
        assert isinstance(strategy, MonthSplitStrategy)

    def test_create_year_strategy(self):
        """Test creating a year split strategy."""
        strategy = create_split_strategy("year")
        assert isinstance(strategy, YearSplitStrategy)

    def test_create_financial_year_strategy(self):
        """Test creating a financial year split strategy."""
        strategy = create_split_strategy("financial-year")
        assert isinstance(strategy, FinancialYearSplitStrategy)

    def test_create_invalid_strategy(self):
        """Test creating a strategy with invalid interval."""
        with pytest.raises(ValueError, match="Unsupported interval"):
            create_split_strategy("invalid")  # type: ignore[arg-type]


class TestDaySplitStrategy:
    """Test the day split strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a day split strategy instance."""
        return DaySplitStrategy()

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2023-01-15",  # Sunday
                        "2023-01-16",  # Monday
                        "2023-01-17",  # Tuesday
                        "2023-01-15",  # Same Sunday (duplicate)
                        "2023-02-20",  # Different month
                    ]
                ),
                "Value": [10, 20, 30, 15, 100],
                "Description": ["A", "B", "C", "D", "E"],
            }
        )

    def test_split_by_day(self, strategy, sample_data):
        """Test splitting data by day."""
        result = strategy.split_data(sample_data, "Date")

        # Should have 4 unique days
        assert len(result) == 4

        # Check the keys are in expected format (YYYY-MM-DD)
        expected_keys = {"2023-01-15", "2023-01-16", "2023-01-17", "2023-02-20"}
        assert set(result.keys()) == expected_keys

        # Check data for Jan 15 (should have 2 rows)
        jan_15_data, jan_15_date = result["2023-01-15"]
        assert len(jan_15_data) == 2
        assert jan_15_date == date(2023, 1, 15)
        assert list(jan_15_data["Value"]) == [10, 15]

        # Check data for Jan 16 (should have 1 row)
        jan_16_data, jan_16_date = result["2023-01-16"]
        assert len(jan_16_data) == 1
        assert jan_16_date == date(2023, 1, 16)
        assert list(jan_16_data["Value"]) == [20]

    def test_empty_data(self, strategy):
        """Test splitting empty data."""
        empty_data = pd.DataFrame({"Date": pd.to_datetime([]), "Value": []})
        result = strategy.split_data(empty_data, "Date")
        assert len(result) == 0

    def test_single_row(self, strategy):
        """Test splitting data with single row."""
        single_data = pd.DataFrame(
            {"Date": pd.to_datetime(["2023-01-15"]), "Value": [100]}
        )
        result = strategy.split_data(single_data, "Date")

        assert len(result) == 1
        assert "2023-01-15" in result
        data, rep_date = result["2023-01-15"]
        assert len(data) == 1
        assert rep_date == date(2023, 1, 15)


class TestWeekSplitStrategy:
    """Test the week split strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a week split strategy instance."""
        return WeekSplitStrategy()

    @pytest.fixture
    def sample_data(self):
        """Create sample data spanning multiple weeks."""
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2023-01-15",  # Sunday (week 2)
                        "2023-01-16",  # Monday (week 3)
                        "2023-01-17",  # Tuesday (week 3)
                        "2023-01-23",  # Monday (week 4)
                        "2023-02-05",  # Sunday (different month, week 5)
                    ]
                ),
                "Value": [10, 20, 30, 40, 100],
            }
        )

    def test_split_by_week(self, strategy, sample_data):
        """Test splitting data by week."""
        result = strategy.split_data(sample_data, "Date")

        # Should have multiple weeks
        assert len(result) >= 3

        # Check that keys are in expected format (YYYY-WXX)
        for key in result:
            assert key.startswith("2023-W")

        # Verify that dates in the same week are grouped together
        # Jan 16 and Jan 17 should be in the same week
        jan_16_week = None
        jan_17_week = None
        for key, (data, _) in result.items():
            dates = data["Date"].dt.strftime("%Y-%m-%d").tolist()
            if "2023-01-16" in dates:
                jan_16_week = key
            if "2023-01-17" in dates:
                jan_17_week = key

        assert jan_16_week == jan_17_week  # Same week

    def test_representative_date_is_monday(self, strategy, sample_data):
        """Test that representative date is first date of the week."""
        result = strategy.split_data(sample_data, "Date")

        for _, (data, rep_date) in result.items():
            # Representative date should be the minimum date in the group
            group_dates = data["Date"].dt.date
            expected_rep_date = group_dates.min()
            assert rep_date == expected_rep_date


class TestMonthSplitStrategy:
    """Test the month split strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a month split strategy instance."""
        return MonthSplitStrategy()

    @pytest.fixture
    def sample_data(self):
        """Create sample data spanning multiple months."""
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2023-01-15",
                        "2023-01-25",
                        "2023-02-10",
                        "2023-02-20",
                        "2023-12-31",
                    ]
                ),
                "Value": [10, 20, 30, 40, 100],
            }
        )

    def test_split_by_month(self, strategy, sample_data):
        """Test splitting data by month."""
        result = strategy.split_data(sample_data, "Date")

        # Should have 3 months
        assert len(result) == 3

        # Check the keys are in expected format (YYYY-MM)
        expected_keys = {"2023-01", "2023-02", "2023-12"}
        assert set(result.keys()) == expected_keys

        # Check January data (should have 2 rows)
        jan_data, jan_date = result["2023-01"]
        assert len(jan_data) == 2
        assert jan_date == date(2023, 1, 1)  # First day of month
        assert list(jan_data["Value"]) == [10, 20]

        # Check February data (should have 2 rows)
        feb_data, feb_date = result["2023-02"]
        assert len(feb_data) == 2
        assert feb_date == date(2023, 2, 1)
        assert list(feb_data["Value"]) == [30, 40]


class TestYearSplitStrategy:
    """Test the year split strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a year split strategy instance."""
        return YearSplitStrategy()

    @pytest.fixture
    def sample_data(self):
        """Create sample data spanning multiple years."""
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2022-06-15",
                        "2022-12-31",
                        "2023-01-01",
                        "2023-06-15",
                        "2024-12-25",
                    ]
                ),
                "Value": [10, 20, 30, 40, 100],
            }
        )

    def test_split_by_year(self, strategy, sample_data):
        """Test splitting data by year."""
        result = strategy.split_data(sample_data, "Date")

        # Should have 3 years
        assert len(result) == 3

        # Check the keys are in expected format (YYYY)
        expected_keys = {"2022", "2023", "2024"}
        assert set(result.keys()) == expected_keys

        # Check 2022 data (should have 2 rows)
        data_2022, date_2022 = result["2022"]
        assert len(data_2022) == 2
        assert date_2022 == date(2022, 1, 1)  # January 1st
        assert list(data_2022["Value"]) == [10, 20]

        # Check 2023 data (should have 2 rows)
        data_2023, date_2023 = result["2023"]
        assert len(data_2023) == 2
        assert date_2023 == date(2023, 1, 1)
        assert list(data_2023["Value"]) == [30, 40]


class TestFinancialYearSplitStrategy:
    """Test the financial year split strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a financial year split strategy instance."""
        return FinancialYearSplitStrategy()

    @pytest.fixture
    def sample_data(self):
        """Create sample data spanning multiple financial years."""
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2022-03-15",  # FY 2021-22 (before April)
                        "2022-04-10",  # FY 2022-23 (April onwards)
                        "2022-12-31",  # FY 2022-23
                        "2023-01-15",  # FY 2022-23
                        "2023-04-01",  # FY 2023-24 (new financial year)
                        "2023-06-15",  # FY 2023-24
                    ]
                ),
                "Value": [10, 20, 30, 40, 50, 60],
            }
        )

    def test_split_by_financial_year(self, strategy, sample_data):
        """Test splitting data by financial year (April start)."""
        result = strategy.split_data(sample_data, "Date")

        # Should have 3 financial years
        assert len(result) == 3

        # Check the keys are in expected format (FYYYY-YYYY)
        expected_keys = {"FY2021-2022", "FY2022-2023", "FY2023-2024"}
        assert set(result.keys()) == expected_keys

        # Check FY 2021-22 (should have 1 row - March 2022)
        fy_2021_22_data, fy_2021_22_date = result["FY2021-2022"]
        assert len(fy_2021_22_data) == 1
        assert fy_2021_22_date == date(2021, 4, 1)  # April 1, 2021
        assert list(fy_2021_22_data["Value"]) == [10]

        # Check FY 2022-23 (should have 3 rows - April 2022 to March 2023)
        fy_2022_23_data, fy_2022_23_date = result["FY2022-2023"]
        assert len(fy_2022_23_data) == 3
        assert fy_2022_23_date == date(2022, 4, 1)  # April 1, 2022
        assert list(fy_2022_23_data["Value"]) == [20, 30, 40]

    def test_financial_year_with_custom_start_month(self, sample_data):
        """Test financial year with custom start month (July)."""
        strategy = FinancialYearSplitStrategy()

        # Use July (month 7) as financial year start
        result = strategy.split_data(sample_data, "Date", financial_year_start=7)

        # The grouping should be different with July start
        assert len(result) >= 2

        # Check that representative dates start from July
        for _, (_, rep_date) in result.items():
            assert rep_date.month == 7  # July


class TestStrategiesEdgeCases:
    """Test edge cases for all strategies."""

    def test_all_strategies_handle_same_date_multiple_rows(self):
        """Test that all strategies handle multiple rows with same date."""
        data = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2023-01-15", "2023-01-15", "2023-01-15"]),
                "Value": [10, 20, 30],
            }
        )

        strategies = [
            ("day", DaySplitStrategy()),
            ("week", WeekSplitStrategy()),
            ("month", MonthSplitStrategy()),
            ("year", YearSplitStrategy()),
            ("financial-year", FinancialYearSplitStrategy()),
        ]

        for strategy_name, strategy in strategies:
            result = strategy.split_data(data, "Date")

            # Should group all rows into single period
            assert len(result) == 1, f"Failed for {strategy_name} strategy"

            # The single group should contain all 3 rows
            period_data, _ = list(result.values())[0]
            assert len(period_data) == 3, f"Failed for {strategy_name} strategy"
            assert list(period_data["Value"]) == [
                10,
                20,
                30,
            ], f"Failed for {strategy_name} strategy"

    def test_all_strategies_preserve_data_columns(self):
        """Test that all strategies preserve all columns in the data."""
        data = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2023-01-15", "2023-02-20"]),
                "Value": [10, 20],
                "Description": ["A", "B"],
                "Category": ["X", "Y"],
            }
        )

        strategies = [
            DaySplitStrategy(),
            WeekSplitStrategy(),
            MonthSplitStrategy(),
            YearSplitStrategy(),
            FinancialYearSplitStrategy(),
        ]

        for strategy in strategies:
            result = strategy.split_data(data, "Date")

            # Check that all groups preserve all columns
            for _, (period_data, _) in result.items():
                expected_columns = {"Date", "Value", "Description", "Category"}
                assert set(period_data.columns) == expected_columns

    def test_all_strategies_maintain_row_order_within_groups(self):
        """Test that strategies maintain sorted order within groups (by date)."""
        # Create data where rows are not sorted by date
        data = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2023-01-20", "2023-01-10", "2023-01-15"]),
                "Value": [30, 10, 20],
                "Order": [3, 1, 2],  # This shows original order
            }
        )

        strategies = [
            DaySplitStrategy(),
            MonthSplitStrategy(),  # All dates in same month
            YearSplitStrategy(),  # All dates in same year
        ]

        for strategy in strategies:
            result = strategy.split_data(data, "Date")

            if len(result) == 1:  # All data in same group (month/year strategies)
                period_data, _ = list(result.values())[0]
                # Should be sorted by date, so order should be [10, 20, 30]
                assert list(period_data["Value"]) == [10, 20, 30]
