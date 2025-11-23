"""Data loaders."""

import glob

import pandas as pd

from utils.data import Operator


class Loader(Operator):
    """Data loader."""

    def __init__(self):
        """Initialize the data loader."""
        path = self._get_latest_data_path()
        self._data = self._preprocess_data(pd.read_excel(path, engine="openpyxl"))

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _get_latest_data_path(self) -> str:
        """Get the latest data path."""
        files = glob.glob("data/????????.xlsx")
        if not files:
            raise FileNotFoundError("No data files found in 'data/' directory.")
        return max(files)

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the given data."""
        data_ = data.copy()

        # Drop last two summary rows
        data_.drop(data_.tail(2).index, inplace=True)

        # Filter actuals only
        data_ = data_[data_["Status"] == "Paid"]

        data_["Date"] = pd.to_datetime(data_["Date"], format="%d/%m/%Y")
        data_["Month"] = data_["Date"].dt.to_period("M")
        data_["Month"] = data_["Month"].dt.to_timestamp()

        return data_
