"""Data loaders."""

from io import BytesIO

import pandas as pd
from utils import get_latest_snapshot
from utils.business.dilution import DilutionAssigner
from utils.business.tiers import TierAssigner
from utils.business.travel import TripBalanceCalculator
from utils.operators import Operator


class Loader(Operator):
    """Data loader."""

    def __init__(self) -> None:
        """Initialize the data loader."""
        self._data = pd.read_excel(
            BytesIO(get_latest_snapshot()),
            sheet_name="Receitas e Despesas",
            engine="openpyxl",
        )

    @property
    def data(self) -> pd.DataFrame:
        """Raw data read from the Mobills export."""
        return self._data


class PreProcessedLoader(Operator):
    """Pre-processed data loader."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the pre-processed data loader."""
        self._data = operator.data.copy()
        self._data = self._preprocess_data(self._data)

    @property
    def data(self) -> pd.DataFrame:
        """Preprocessed data: actuals only, dates parsed, Year/Month, tags as a list."""
        return self._data

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the given data."""
        data_ = data.copy()

        # Drop last two summary rows
        data_ = data_.drop(data_.tail(2).index)

        # Filter actuals only
        data_ = data_[data_["Status"] == "Paid"]

        # Convert dates to datetime
        data_["Date"] = pd.to_datetime(data_["Date"], format="%d/%m/%Y")

        # Extract year and month from date - the yearly aggregators in
        # utils/operators/aggregator.py group on this Year column
        data_["Year"] = data_["Date"].dt.year
        data_["Month"] = data_["Date"].dt.to_period("M").dt.to_timestamp()

        # Parse tags
        data_["Tags"] = (
            data_["Tags"]
            .fillna("")
            .apply(lambda x: [tag.strip() for tag in x.split(",")] if x else [])
        )

        return data_


class ProcessedLoader(Operator):
    """Processed data loader that returns the final processed loader."""

    def __init__(self) -> None:
        """Initialize the processed data loader."""
        loader = Loader()
        self._processed_loader = TripBalanceCalculator(
            TierAssigner(DilutionAssigner(PreProcessedLoader(loader)))
        )

    @property
    def data(self) -> pd.DataFrame:
        """Fully processed data: preprocessed, diluted, tiered, trip-balanced."""
        return self._processed_loader.data

    def __call__(self) -> TripBalanceCalculator:
        """Return the ProcessedLoader instance."""
        return self._processed_loader
