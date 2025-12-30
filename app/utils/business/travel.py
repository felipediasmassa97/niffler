"""Travel business rules."""

from datetime import datetime
from functools import cache

import pandas as pd

from utils import get_latest_data_path
from utils.operators import Operator


TRIP_FUNDS_ACCOUNT = "Trip Funds"


class TripBalanceCalculator(Operator):
    """Data trip balance calculator.

    Main trips are handled in a particular way, through a dedicated account in Mobills called "Trip
    Funds":
    - In the year N-1, a transaction of type "Transfer" is created from account "Wallet" to account
    "Trip Funds", with the total amount intended for the trip. For visualization, this transaction
    is shown in the app as an expense executed during year N.
    - In the year N, during the trip, expenses are paid from the "Trip Funds" account. For
    visualization, the difference between the actual trip expense and the budgeted trip expense is
    shown in the app as an income or expense executed during year N.

    This operator adjusts the data to reflect this logic.
    """

    def __init__(self, operator: Operator) -> None:
        """Initialize the tier assigner."""
        self.raw_data = operator.data.copy()
        self._data = self._adjust_data(self.raw_data)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @classmethod
    @cache
    def _load_transfer_data(cls) -> pd.DataFrame:
        """Load transfer data from the Transfers sheet."""
        data = pd.read_excel(
            get_latest_data_path(), sheet_name="Transfers", engine="openpyxl"
        )
        data["Year"] = pd.to_datetime(data["Date"], format="%d/%m/%Y").dt.year
        return data

    @classmethod
    def get_budget(cls, year: int) -> float:
        """Get trip budget from year N-1.

        Trip budget for year N is defined as the sum of all transfer transactions to "Trip Funds"
        account in year N-1.
        """
        transfer_data = cls._load_transfer_data()
        return transfer_data[
            (transfer_data["Conta destino"] == TRIP_FUNDS_ACCOUNT)
            & (transfer_data["Year"] == year - 1)
        ].sum()["Value"]

    def sum_actuals(self, year: int) -> float:
        """Sum actual trip expenses from year N.

        Trip actual expenses for year N are defined as the sum of all expenses in "Travel" category paid
        from "Trip Funds" account in year N.
        """
        travel_data = self.raw_data[
            (self.raw_data["Account"] == TRIP_FUNDS_ACCOUNT)
            & (self.raw_data["Category"] == "Travel")
            & (self.raw_data["Date"].dt.year == year)
        ]
        return abs(travel_data["Value"].sum())

    def calculate_balance(self, year: int) -> float:
        """Calculate the balance between budget and actual trip expenses in year N."""
        return self.get_budget(year) - self.sum_actuals(year)

    def _adjust_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Adjust data to include trip balance.

        Remove trip funds transfer transaction (budget) from year N-1; remove actual trip expenses
        from year N; and add balance transaction to year N.
        """
        data_ = data.copy()

        # Iterate over years to adjust data
        for year in range(2024, datetime.now().year + 1):
            # Remove Trip Funds account's Travel expenses from year N
            data_ = data_[
                ~(
                    (data_["Account"] == TRIP_FUNDS_ACCOUNT)
                    & (data_["Category"] == "Travel")
                    & (data_["Date"].dt.year == year)
                )
            ]

            # Create balance transaction to be added to year N
            date = pd.Timestamp(year=year, month=12, day=31)
            balance_transaction = {
                "Date": date,
                "Description": f"Saldo Viagem {year}",
                "Value": self.calculate_balance(year),
                "Account": TRIP_FUNDS_ACCOUNT,
                "Status": "Paid",
                "Category": "Travel",
                "Subcategory": None,
                "Tags": None,
                "Month": date.to_period("M").to_timestamp(),
                "Tier": "Lifestyle",
            }

            # Add balance transaction to year N
            data_ = pd.concat(
                [data_, pd.DataFrame([balance_transaction])], ignore_index=True
            )

        return data_
