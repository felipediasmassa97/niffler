"""Data aggregators."""

import pandas as pd

from utils.data import Operator


class Aggregator(Operator):
    """Data aggregator."""

    def __init__(self, operator: Operator, columns: list[str]):
        """Initialize the aggregator."""
        if columns is None:
            columns = []
        self.columns = columns
        self._data = self._aggregate_data(operator.data, columns)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _aggregate_data(self, data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Aggregate data based on columns."""
        data_ = data.copy()
        if not columns:
            return data_
        return (
            data_.groupby(columns)["Value"]
            .sum()
            .reset_index()
            .sort_values(by=["Value", *columns], ascending=False)
        )


class CombinedAggregator(Aggregator):
    """Combined aggregator."""

    def __init__(self, operator: Operator, *aggregator_classes: list[Aggregator]):
        all_columns = []

        # Collect all columns from the aggregator classes
        for cls in aggregator_classes:
            # Create a temporary instance to get the columns
            temp_instance = cls.__new__(cls)

            # Get columns from instance
            if hasattr(temp_instance, "columns"):
                all_columns.extend(temp_instance.columns)

        # Remove duplicates while preserving order
        columns_unique = list(dict.fromkeys(all_columns))

        # Initialize the base Aggregator
        super().__init__(operator, columns_unique)


class MonthlyAggregator(Aggregator):
    """Monthly aggregator."""

    columns = ["Month"]

    def __init__(self, operator: Operator):
        super().__init__(operator, self.columns)


class YearlyAggregator(Aggregator):
    """Yearly aggregator."""

    columns = ["Year"]

    def __init__(self, operator: Operator):
        super().__init__(operator, self.columns)


class CategoryAggregator(Aggregator):
    """Category aggregator."""

    columns = ["Category"]

    def __init__(self, operator: Operator):
        super().__init__(operator, self.columns)


class TierAggregator(Aggregator):
    """Tier aggregator."""

    columns = ["Tier"]

    def __init__(self, operator: Operator):
        super().__init__(operator, self.columns)


class MonthlyCategoryAggregator(CombinedAggregator):
    """Monthly-category aggregator."""

    def __init__(self, operator: Operator):
        super().__init__(operator, MonthlyAggregator, CategoryAggregator)


class MonthlyTierAggregator(CombinedAggregator):
    """Monthly-tier aggregator."""

    def __init__(self, operator: Operator):
        super().__init__(operator, MonthlyAggregator, TierAggregator)


class YearlyCategoryAggregator(CombinedAggregator):
    """Yearly-category aggregator."""

    def __init__(self, operator: Operator):
        super().__init__(operator, YearlyAggregator, CategoryAggregator)


class YearlyTierAggregator(CombinedAggregator):
    """Yearly-tier aggregator."""

    def __init__(self, operator: Operator):
        super().__init__(operator, YearlyAggregator, TierAggregator)
