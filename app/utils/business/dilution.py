"""Dilution business rules."""

import pandas as pd
from unidecode import unidecode

from utils.operators import Operator


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
        category = self._standardize_string(row["Category"])
        value = row["Value"]
        if value > 0:
            return self._assign_dilution_income(category, value)
        return self._assign_dilution_expense(category, abs(value))

    def _assign_dilution_income(self, category: str, value: float) -> bool:
        """Assign dilution for income entries."""

        # Specific cases
        if category == "refund" and value >= 500:
            return True

        # General per-category assignment
        return {
            "gift": False,
            "refund": False,
            "rewards": True,
            "salary": True,
        }[category]

    def _assign_dilution_expense(self, category: str, value: float) -> bool:
        """Assign dilution for expense entries."""

        # Specific cases
        if category == "car" and value >= 300:
            return True
        if category == "donation" and value >= 200:
            return True
        if category == "home" and value >= 250:
            return True
        if category == "subscriptions" and value >= 60:
            return True
        if category == "work" and value >= 300:
            return True

        # General per-category assignment
        return {
            "car": False,
            "commute": False,
            "donation": False,
            "education": False,
            "gift": False,
            "health": False,
            "high costs": True,
            "home": False,
            "maintenance": True,
            "personal felp": False,
            "personal lena": False,
            "pharmacy": False,
            "physical": False,
            "recreation": False,
            "rent": False,
            "restaurant": False,
            "services": False,
            "subscriptions": False,
            "supermarket": False,
            "transport": False,
            "travel": True,
            "unknown": False,
            "work": False,
            "work lunch": False,
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

    def _standardize_string(self, s: str) -> str:
        """Standardize a string by removing accents and converting to lowercase."""
        return unidecode(s).lower()
