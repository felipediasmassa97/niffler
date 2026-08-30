"""Data operators utils."""

from abc import ABC, abstractmethod

import pandas as pd


class Operator(ABC):
    """Data operators."""

    @property
    @abstractmethod
    def data(self) -> pd.DataFrame:
        """Data."""
