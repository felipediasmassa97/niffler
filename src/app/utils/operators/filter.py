"""Data filters."""

from abc import ABC, abstractmethod

import pandas as pd
from utils.operators import Operator

MONTHS_IN_YEAR = 12


class Filter(Operator):
    """Data filter."""

    def __init__(self, operator: Operator, mask: pd.Series) -> None:
        """Initialize the filter with a boolean row mask."""
        self._data = self._filter_data(operator.data, mask)

    @property
    def data(self) -> pd.DataFrame:
        """Data restricted to rows where `mask` is `True`."""
        return self._data

    def _filter_data(self, data: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
        """Filter data based on criteria."""
        data_ = data.copy()
        return data_[mask]


class ExpensesFilter(Filter):
    """Expenses filter."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the expenses filter."""
        super().__init__(operator, operator.data["Value"] < 0)


class IncomesFilter(Filter):
    """Incomes filter."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the incomes filter."""
        super().__init__(operator, operator.data["Value"] > 0)


class DateFilter(Filter, ABC):
    """Date filter."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the date filter over [`start_date`, `end_date`]."""
        self.now = pd.Timestamp.now()
        super().__init__(
            operator,
            (operator.data["Date"] >= self.start_date)
            & (operator.data["Date"] <= self.end_date),
        )

    @property
    @abstractmethod
    def start_date(self) -> pd.Timestamp:
        """Start date."""

    @property
    @abstractmethod
    def end_date(self) -> pd.Timestamp:
        """End date."""


class ThisYearFilter(DateFilter):
    """Current year filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(year=self.year, month=1, day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(year=self.year, month=12, day=31)

    @property
    def year(self) -> int:
        """Current year."""
        return self.now.year


class ThisMonthFilter(DateFilter):
    """Current month filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(year=self.now.year, month=self.now.month, day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        next_month = self.now.month + 1 if self.now.month < MONTHS_IN_YEAR else 1
        next_month_year = (
            self.now.year if self.now.month < MONTHS_IN_YEAR else self.now.year + 1
        )
        return pd.Timestamp(
            year=next_month_year, month=next_month, day=1
        ) - pd.Timedelta(days=1)


class LastMonthFilter(DateFilter):
    """Last month filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=1)).replace(day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(
            year=self.now.year, month=self.now.month, day=1
        ) - pd.Timedelta(days=1)


class Last3MonthsFilter(DateFilter):
    """Last 3 months filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=3)).replace(day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(
            year=self.now.year, month=self.now.month, day=1
        ) - pd.Timedelta(days=1)


class Last6MonthsFilter(DateFilter):
    """Last 6 months filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=6)).replace(day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(
            year=self.now.year, month=self.now.month, day=1
        ) - pd.Timedelta(days=1)


class Last12MonthsFilter(DateFilter):
    """Last 12 months filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=12)).replace(day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(
            year=self.now.year, month=self.now.month, day=1
        ) - pd.Timedelta(days=1)


class LastYearFilter(DateFilter):
    """Last year filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=12)).replace(month=1, day=1)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return pd.Timestamp(self.now - pd.DateOffset(months=12)).replace(
            month=12, day=31
        )

    @property
    def year(self) -> int:
        """Previous year."""
        return self.now.year - 1


class AllTimeFilter(DateFilter):
    """All time filter."""

    @property
    def start_date(self) -> pd.Timestamp:
        """Start date.

        Started using Mobills in Jan-24, but first data is from Dec-23 (main trip
        budget).
        """
        return pd.Timestamp(year=2023, month=12, day=31)

    @property
    def end_date(self) -> pd.Timestamp:
        """End date."""
        return self.now


# fixit long-term add custom date range filter
