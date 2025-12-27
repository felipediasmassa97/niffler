"""Tiers business rules."""

import pandas as pd
from unidecode import unidecode

from utils.operators import Operator


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
        # fixit evaluate fixed and variable differentiation for salary (long-term)

        # General per-category assignment
        return {
            "Gift": "Variable",
            "Refund": "Variable",
            "Rewards": "Variable",
            "Salary": "Fixed",
        }[category]

    def _assign_tiers_expense(self, category: str, description: str) -> bool:
        """Assign tiers for expense entries."""

        # fixit add rule for travel, when tag = Work -> category = Variable

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
