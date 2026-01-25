"""Data transformers."""

from abc import ABC, abstractmethod
from typing import Any, Callable

import pandas as pd

from utils.operators import Operator


class Transformer(Operator, ABC):
    """Data transformer."""

    def __init__(self, *operators: Operator) -> None:
        """Initialize the transformer."""
        self._data = self._transform_data(*[op.data for op in operators])

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @abstractmethod
    def _transform_data(self, *data_list: list[pd.DataFrame]) -> pd.DataFrame:
        """Transform data."""


class Inverter(Transformer):
    """Data inverter."""

    def _transform_data(self, *data_list: list[pd.DataFrame]) -> pd.DataFrame:
        """Invert the values in the data."""
        if len(data_list) != 1:
            raise ValueError("Inverter expects a single DataFrame as input.")
        data = data_list[0]
        data_ = data.copy()
        data_["Value"] = -data_["Value"]
        return data_


class Merger(Transformer):
    """Data merger."""

    def _transform_data(self, *data_list: list[pd.DataFrame]) -> pd.DataFrame:
        """Merge data from multiple operators."""
        return pd.concat(data_list, axis=0, ignore_index=True)


class LabelAssigner(Transformer):
    """Label assigner."""

    def __init__(self, operator: Operator, label_col: str, label_val: Any) -> None:
        """Initialize the label assigner."""
        self._label_col = label_col
        self._label_val = label_val
        super().__init__(operator)

    def _transform_data(self, *data_list: list[pd.DataFrame]) -> pd.DataFrame:
        """Assign label to data."""
        if len(data_list) != 1:
            raise ValueError("LabelAssigner expects a single DataFrame as input.")
        data = data_list[0]
        data_ = data.copy()
        data_[self._label_col] = self._label_val
        return data_


class Remover(Transformer):
    """Data remover."""

    def __init__(
        self, operator: Operator, criterion: Callable[[pd.Series], bool]
    ) -> None:
        """Initialize the remover."""
        self._criterion = criterion
        super().__init__(operator)

    def _transform_data(self, *data_list: list[pd.DataFrame]) -> pd.DataFrame:
        """Remove data that does not meet the criterion."""
        if len(data_list) != 1:
            raise ValueError("Inverter expects a single DataFrame as input.")
        data = data_list[0]
        data_ = data.copy()
        return data_[~data_.apply(self._criterion, axis=1)]
