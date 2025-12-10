"""Data loaders."""

import glob

import pandas as pd

from utils.data import Operator
from utils.data.rules import TierAssigner


class Loader(Operator):
    """Data loader."""

    def __init__(self):
        """Initialize the data loader."""
        path = self._get_latest_data_path()
        self._data = pd.read_excel(path, engine="openpyxl")

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _get_latest_data_path(self) -> str:
        """Get the latest data path."""
        files = glob.glob("data/????????.xlsx")
        if not files:
            raise FileNotFoundError("No data files found in 'data/' directory.")
        return max(files)


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
        self._processed_loader = TierAssigner(PreProcessedLoader(loader))

    @property
    def data(self) -> pd.DataFrame:
        return self._processed_loader.data

    def __call__(self):
        """Return the ProcessedLoader instance."""
        return self._processed_loader
