"""Data loaders."""

import glob

import pandas as pd

from utils.data import Operator
from utils.data.rules import assign_dillution, assign_tiers, dillute_costs


class Loader(Operator):
    """Data loader."""

    def __init__(self):
        """Initialize the data loader."""
        path = self._get_latest_data_path()
        self._data = self._preprocess_data(pd.read_excel(path, engine="openpyxl"))
        self._data["Tier"] = self._data.apply(assign_tiers, axis=1)
        self._data["Dillution"] = self._data.apply(assign_dillution, axis=1)
        # fixit only apply dillute costs when a class is applied (so we can inspect both without dilluting and with dilluting)
        self._data = dillute_costs(self._data)

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

        # Convert dates to datetime
        data_["Date"] = pd.to_datetime(data_["Date"], format="%d/%m/%Y")

        # Extract month from date
        data_["Month"] = data_["Date"].dt.to_period("M").dt.to_timestamp()

        return data_
