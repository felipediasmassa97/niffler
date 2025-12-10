"""Data business rules."""

from datetime import datetime
from functools import cache

import pandas as pd
from unidecode import unidecode

from utils import get_latest_data_path
from utils.data import Operator


TRIP_FUNDS_ACCOUNT = "Trip Funds"


class TierAssigner(Operator):
    """Data tier assigner."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the tier assigner."""
        self._data = operator.data.copy()
        self._data["Tier"] = self._data.apply(self._assign_tiers, axis=1)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _assign_tiers(self, row: pd.Series) -> str:
        """Assign tiers to the given data."""
        category = row["Category"]
        description = self._standardize_string(row["Description"])
        value = row["Value"]
        if value > 0:
            return self._assign_tiers_income(category, description)
        return self._assign_tiers_expense(category, description)

    def _assign_tiers_income(self, category: str, description: str) -> bool:
        """Assign tiers for income entries."""

        # Specific cases
        # fixit evaluate fixed and variable differentiation for salary

        # General per-category assignment
        return {
            "Gift": "Variable",
            "Refund": "Variable",
            "Rewards": "Variable",
            "Salary": "Fixed",
        }[category]

    def _assign_tiers_expense(self, category: str, description: str) -> bool:
        """Assign tiers for expense entries."""

        # Specific cases
        if category == "Education" and "medcurso" in description:
            return "Fixed"
        if category == "Education" and "pos graduacao" in description:
            return "Fixed"
        if category == "Health" and "bradesco saude" in description:
            return "Fixed"
        if category == "Work" and "crea" in description:
            return "Fixed"
        if category == "Work" and "crm" in description:
            return "Fixed"
        if category == "Work" and "chatgpt" in description:
            return "Fixed"
        if category == "Work" and "contabileasy mensalidade" in description:
            return "Fixed"
        if category == "Work" and "darf" in description:
            return "Fixed"
        if category == "Work" and "whitebook" in description:
            return "Fixed"

        # General per-category assignment
        return {
            "Car": "Fixed",
            "Commute": "Fixed",
            "Donation": "Lifestyle",
            "Education": "Variable",
            "Gift": "Lifestyle",
            "Health": "Variable",
            "High Costs": "Variable",
            "Home": "Variable",
            "Maintenance": "Variable",
            "Personal Felp": "Lifestyle",
            "Personal Lena": "Lifestyle",
            "Pharmacy": "Variable",
            "Physical": "Variable",
            "Recreation": "Lifestyle",
            "Rent": "Fixed",
            "Restaurant": "Lifestyle",
            "Services": "Fixed",
            "Subscriptions": "Lifestyle",
            "Supermarket": "Fixed",
            "Transport": "Variable",
            "Travel": "Lifestyle",
            "Unknown": "Variable",
            "Work": "Variable",
            "Work Lunch": "Variable",
        }[category]

    def _standardize_string(self, s: str) -> str:
        """Standardize a string by removing accents and converting to lowercase."""
        return unidecode(s).lower()


class Diluter(Operator):
    """Data expenses diluter.

    Dilutes specific incomes and expenses over a 12-month period.

    Transactions to be diluted depend on business rules associated to their category and value.
    """

    def __init__(self, operator: Operator) -> None:
        """Initialize the tier assigner."""

        self._data = operator.data.copy()

        self._data["Dilution"] = self._data.apply(self._assign_dilution, axis=1)
        self._data = self._dilute_costs(self._data)

        # Update Month column after dilution
        self._data["Month"] = self._data["Date"].dt.to_period("M").dt.to_timestamp()

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def _assign_dilution(self, row: pd.Series) -> str:
        """Assign dilution to the given data."""
        category = row["Category"]
        value = row["Value"]
        if value > 0:
            return self._assign_dilution_income(category, value)
        return self._assign_dilution_expense(category, abs(value))

    def _assign_dilution_income(self, category: str, value: float) -> bool:
        """Assign dilution for income entries."""

        # Specific cases
        if category == "Refund" and value >= 500:
            return True

        # General per-category assignment
        return {
            "Gift": False,
            "Refund": False,
            "Rewards": True,
            "Salary": True,
        }[category]

    def _assign_dilution_expense(self, category: str, value: float) -> bool:
        """Assign dilution for expense entries."""

        # Specific cases
        if category == "Car" and value >= 300:
            return True
        if category == "Donation" and value >= 200:
            return True
        if category == "Home" and value >= 250:
            return True
        if category == "Subscriptions" and value >= 60:
            return True
        if category == "Work" and value >= 300:
            return True

        # General per-category assignment
        return {
            "Car": False,
            "Commute": False,
            "Donation": False,
            "Education": False,
            "Gift": False,
            "Health": False,
            "High Costs": True,
            "Home": False,
            "Maintenance": True,
            "Personal Felp": False,
            "Personal Lena": False,
            "Pharmacy": False,
            "Physical": False,
            "Recreation": False,
            "Rent": False,
            "Restaurant": False,
            "Services": False,
            "Subscriptions": False,
            "Supermarket": False,
            "Transport": False,
            "Travel": True,
            "Unknown": False,
            "Work": False,
            "Work Lunch": False,
        }[category]

    def _dilute_costs(self, data: pd.DataFrame) -> pd.DataFrame:
        """Dilute costs in the given data.

        Diluting means spreading the cost over 12 months.
        """
        data_ = data.copy()

        # Separate dilution and non-dilution entries
        data_keep = data_[~data_["Dilution"]].copy()
        data_dilute = data_[data_["Dilution"]].copy()

        # Dilute costs
        data_dilute["DescriptionDiluted"] = data_dilute["Description"].apply(
            self._get_diluted_descriptions
        )
        data_dilute["ValueDiluted"] = data_dilute["Value"].apply(
            self._get_diluted_values
        )
        data_dilute["DateDiluted"] = data_dilute["Date"].apply(self._get_diluted_dates)
        data_dilute = data_dilute.explode(
            ["ValueDiluted", "DateDiluted", "DescriptionDiluted"]
        )
        data_dilute["Value"] = data_dilute["ValueDiluted"]
        data_dilute["Date"] = data_dilute["DateDiluted"]
        data_dilute["Description"] = data_dilute["DescriptionDiluted"]
        data_dilute = data_dilute.drop(
            columns=["ValueDiluted", "DateDiluted", "DescriptionDiluted"]
        )

        # Combine data back
        return pd.concat([data_keep, data_dilute], ignore_index=True)

    def _get_diluted_descriptions(self, description: str) -> list[str]:
        """Get diluted descriptions for a given description."""
        return [f"{description} ({i}/12)" for i in range(1, 13)]

    def _get_diluted_values(self, value: float) -> list[float]:
        """Get diluted values for a given value.

        For dilution, the cost is spread over 12 months of the same year.
        """
        return [value / 12] * 12

    def _get_diluted_dates(self, date: pd.Timestamp) -> pd.DatetimeIndex:
        """Get diluted dates for a given date.

        For dilution, the cost is spread over 12 months of the same year.
        For simplification, the first day of each month is used.
        """
        return [
            pd.Timestamp(year=date.year, month=month, day=1) for month in range(1, 13)
        ]


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
        self.years = range(2024, datetime.now().year + 1)
        self._data = self._adjust_data(self.raw_data)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @cache
    def _load_transfer_data(self) -> pd.DataFrame:
        """Load transfer data from the Transfers sheet."""
        data = pd.read_excel(
            get_latest_data_path(), sheet_name="Transfers", engine="openpyxl"
        )
        data["Year"] = pd.to_datetime(data["Date"], format="%d/%m/%Y").dt.year
        return data

    def _get_budget(self, year: int) -> float:
        """Get trip budget from year N-1.

        Trip budget for year N is defined as the sum of all transfer transactions to "Trip Funds"
        account in year N-1.
        """
        transfer_data = self._load_transfer_data()
        return transfer_data[
            (transfer_data["Conta destino"] == TRIP_FUNDS_ACCOUNT)
            & (transfer_data["Year"] == year - 1)
        ].sum()["Value"]

    def _sum_actuals(self, year: int) -> float:
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

    def _calculate_balance(self, year: int) -> float:
        """Calculate the balance between budget and actual trip expenses in year N."""
        return self._get_budget(year) - self._sum_actuals(year)

    def _adjust_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Adjust data to include trip balance.

        Remove trip funds transfer transaction (budget) from year N-1; remove actual trip expenses
        from year N; and add balance transaction to year N.
        """
        data_ = data.copy()

        # Iterate over years to adjust data
        for year in self.years:
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
                "Value": self._calculate_balance(year),
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
