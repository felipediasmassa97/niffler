"""Data filterers."""

import pandas as pd

from utils.data import Operator


class Filterer(Operator):
    """Data filterer."""

    def __init__(self, operator: Operator, filters: bool):
        """Initialize the filterer."""
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


class ExpensesFilterer(Filterer):
    """Expenses filterer."""

    def __init__(self, operator: Operator):
        super().__init__(operator, operator.data["Value"] < 0)


class IncomesFilterer(Filterer):
    """Incomes filterer."""

    def __init__(self, operator: Operator):
        super().__init__(operator, operator.data["Value"] > 0)


class DateFilterer(Filterer):
    """Date filterer."""

    def __init__(
        self, operator: Operator, start_date: pd.Timestamp, end_date: pd.Timestamp
    ):
        super().__init__(
            operator,
            (operator.data["Date"] >= start_date) & (operator.data["Date"] <= end_date),
        )


class ThisYearFilterer(Filterer):
    """This year filterer."""

    def __init__(self, operator: Operator):
        pass


class Last3MonthsFilterer(Filterer):
    """Last 3 months filterer."""

    def __init__(self, operator: Operator):
        pass


class Last12MonthsFilterer(Filterer):
    """Last 12 months filterer."""

    def __init__(self, operator: Operator):
        pass


class AllTimeFilterer(Filterer):
    """All time filterer."""

    def __init__(self, operator: Operator):
        pass
