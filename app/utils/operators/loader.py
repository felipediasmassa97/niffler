"""Data loaders."""

import pandas as pd

from utils import get_latest_data_path
from utils.business.rules import TierAssigner, TripBalanceCalculator
from utils.operators import Operator


class Loader(Operator):
    """Data loader."""

    def __init__(self):
        """Initialize the data loader."""
        self._data = pd.read_excel(
            get_latest_data_path(), sheet_name="Receitas e Despesas", engine="openpyxl"
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data


class PreProcessedLoader(Operator):
    """Pre-processed data loader."""

    def __init__(self, operator: Operator):
        """Initialize the pre-processed data loader."""
        self._data = operator.data.copy()
        self._data = self._preprocess_data(self._data)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the given data."""
        data_ = data.copy()

        # Drop last two summary rows
        data_.drop(data_.tail(2).index, inplace=True)

        # Filter actuals only
        data_ = data_[data_["Status"] == "Paid"]

        # Convert dates to datetime
        data_["Date"] = pd.to_datetime(data_["Date"], format="%d/%m/%Y")

        # Extract month from date
        data_["Month"] = data_["Date"].dt.to_period("M").dt.to_timestamp()

        return data_


class ProcessedLoader(Operator):
    """Processed data loader that returns the final processed loader."""

    def __init__(self):
        """Initialize the processed data loader."""
        loader = Loader()
        self._processed_loader = TripBalanceCalculator(
            TierAssigner(PreProcessedLoader(loader))
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._processed_loader.data

    def __call__(self):
        """Return the ProcessedLoader instance."""
        return self._processed_loader
