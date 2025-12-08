"""Data business rules."""

import pandas as pd
from unidecode import unidecode

from utils.data import Operator


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
        data_dilute["ValueDiluted"] = data_dilute["Value"].apply(
            self._get_diluted_values
        )
        data_dilute["DateDiluted"] = data_dilute["Date"].apply(self._get_diluted_dates)
        data_dilute = data_dilute.explode(["ValueDiluted", "DateDiluted"])
        data_dilute["Value"] = data_dilute["ValueDiluted"]
        data_dilute["Date"] = data_dilute["DateDiluted"]
        data_dilute = data_dilute.drop(columns=["ValueDiluted", "DateDiluted"])

        # Combine data back
        return pd.concat([data_keep, data_dilute], ignore_index=True)

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
