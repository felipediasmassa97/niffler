"""Data filters."""

import pandas as pd

from utils.operators import Operator


class Filter(Operator):
    """Data filter."""

    def __init__(self, operator: Operator, filters: bool):
        """Initialize the filter."""
        if filters is None:
            filters = True
        self._data = self._filter_data(operator.data, filters)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _filter_data(self, data: pd.DataFrame, filters: bool) -> pd.DataFrame:
        """Filter data based on criteria."""
        data_ = data.copy()
        return data_[filters]


class ExpensesFilter(Filter):
    """Expenses filter."""

    def __init__(self, operator: Operator):
        super().__init__(operator, operator.data["Value"] < 0)


class IncomesFilter(Filter):
    """Incomes filter."""

    def __init__(self, operator: Operator):
        super().__init__(operator, operator.data["Value"] > 0)


class DateFilter(Filter):
    """Date filter."""

    def __init__(
        self,
        operator: Operator,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
    ):
        if end_date is None:
            end_date = pd.Timestamp.now()
        super().__init__(
            operator,
            (operator.data["Date"] >= start_date) & (operator.data["Date"] <= end_date),
        )


class ThisYearFilter(DateFilter):
    """This year filter."""

    def __init__(self, operator: Operator):
        super().__init__(
            operator,
            start_date=pd.Timestamp(year=pd.Timestamp.now().year, month=1, day=1),
        )


class ThisMonthFilter(DateFilter):
    """This month filter."""

    def __init__(self, operator: Operator):
        now = pd.Timestamp.now()
        super().__init__(
            operator,
            start_date=pd.Timestamp(year=now.year, month=now.month, day=1),
        )


class LastMonthFilter(DateFilter):
    """Last month filter."""

    def __init__(self, operator: Operator):
        now = pd.Timestamp.now()
        super().__init__(
            operator,
            start_date=pd.Timestamp(year=now.year, month=now.month - 1, day=1),
            end_date=pd.Timestamp(year=now.year, month=now.month, day=1)
            - pd.Timedelta(days=1),
        )


class Last3MonthsFilter(DateFilter):
    """Last 3 months filter."""

    def __init__(self, operator: Operator):
        super().__init__(
            operator,
            start_date=pd.Timestamp(
                pd.Timestamp.now() - pd.DateOffset(months=3)
            ).replace(day=1),
        )


class Last12MonthsFilter(DateFilter):
    """Last 12 months filter."""

    def __init__(self, operator: Operator):
        super().__init__(
            operator,
            start_date=pd.Timestamp(
                pd.Timestamp.now() - pd.DateOffset(months=12)
            ).replace(day=1),
        )


class LastYearFilter(DateFilter):
    """Last year filter."""

    def __init__(self, operator: Operator):
        super().__init__(
            operator,
            start_date=pd.Timestamp(year=pd.Timestamp.now().year - 1, month=1, day=1),
            end_date=pd.Timestamp(year=pd.Timestamp.now().year - 1, month=12, day=31),
        )


class AllTimeFilter(DateFilter):
    """All time filter."""

    def __init__(self, operator: Operator):
        """Initialize all time filter.

        Started using Mobills in Jan-24, but first data is from Dec-23 (main trip budget).
        """
        super().__init__(
            operator,
            start_date=pd.Timestamp(year=2023, month=12, day=31),
        )


# fixit add custom date range filter (long-term)
