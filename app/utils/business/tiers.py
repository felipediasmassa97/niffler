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
        category = self._standardize_string(row["Category"])
        description = self._standardize_string(row["Description"])
        tags = [self._standardize_string(tag) for tag in row["Tags"]]
        value = row["Value"]

        if value > 0:
            return self._assign_tiers_income(category, description, tags)
        return self._assign_tiers_expense(category, description, tags)

    def _assign_tiers_income(
        self, category: str, description: str, tags: list[str]
    ) -> bool:
        """Assign tiers for income entries."""

        # Specific cases
        # fixit long-term evaluate fixed and variable differentiation for salary

        # General per-category assignment
        return {
            "gift": "Variable",
            "refund": "Variable",
            "rewards": "Variable",
            "salary": "Fixed",
        }[category]

    def _assign_tiers_expense(
        self, category: str, description: str, tags: list[str]
    ) -> bool:
        """Assign tiers for expense entries."""

        # Specific cases
        if category == "education" and "medcurso" in description:
            return "Fixed"
        if category == "education" and "pos graduacao" in description:
            return "Fixed"
        if category == "health" and "bradesco saude" in description:
            return "Fixed"
        if category == "travel" and "work" in tags:
            return "Variable"
        if category == "work" and "crea" in description:
            return "Fixed"
        if category == "work" and "crm" in description:
            return "Fixed"
        if category == "work" and "chatgpt" in description:
            return "Fixed"
        if category == "work" and "contabileasy mensalidade" in description:
            return "Fixed"
        if category == "work" and "darf" in description:
            return "Fixed"
        if category == "work" and "whitebook" in description:
            return "Fixed"

        # General per-category assignment
        return {
            "car": "Fixed",
            "commute": "Fixed",
            "donation": "Lifestyle",
            "education": "Variable",
            "gift": "Lifestyle",
            "health": "Variable",
            "high costs": "Variable",
            "home": "Variable",
            "maintenance": "Variable",
            "personal felp": "Lifestyle",
            "personal lena": "Lifestyle",
            "pharmacy": "Variable",
            "physical": "Variable",
            "recreation": "Lifestyle",
            "rent": "Fixed",
            "restaurant": "Lifestyle",
            "services": "Fixed",
            "subscriptions": "Lifestyle",
            "supermarket": "Fixed",
            "transport": "Variable",
            "travel": "Lifestyle",
            "unknown": "Variable",
            "work": "Variable",
            "work lunch": "Variable",
        }[category]

    def _standardize_string(self, s: str) -> str:
        """Standardize a string by removing accents and converting to lowercase."""
        return unidecode(s).lower()
