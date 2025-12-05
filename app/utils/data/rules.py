"""Business rules utils."""

import pandas as pd
from unidecode import unidecode


def assign_tiers(row: pd.Series) -> str:
    """Assign tiers to the given data."""

    def assign_tiers_income(category: str, description: str) -> bool:
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

    def assign_tiers_expense(category: str, description: str) -> bool:
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
            "Donation": "Discretionary",
            "Education": "Variable",
            "Gift": "Discretionary",
            "Health": "Variable",
            "High Costs": "Variable",
            "Home": "Variable",
            "Maintenance": "Variable",
            "Personal Felp": "Discretionary",
            "Personal Lena": "Discretionary",
            "Pharmacy": "Variable",
            "Physical": "Variable",
            "Recreation": "Discretionary",
            "Rent": "Fixed",
            "Restaurant": "Discretionary",
            "Services": "Fixed",
            "Subscriptions": "Discretionary",
            "Supermarket": "Fixed",
            "Transport": "Variable",
            "Travel": "Discretionary",
            "Unknown": "Variable",
            "Work": "Variable",
            "Work Lunch": "Variable",
        }[category]

    category = row["Category"]
    description = _standardize_string(row["Description"])
    value = row["Value"]
    if value > 0:
        return assign_tiers_income(category, description)
    return assign_tiers_expense(category, description)


def assign_dillution(row: pd.Series) -> str:
    """Assign dillution to the given data."""

    def assign_dillution_income(category: str, value: float) -> bool:
        """Assign dillution for income entries."""

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

    def assign_dillution_expense(category: str, value: float) -> bool:
        """Assign dillution for expense entries."""

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

    category = row["Category"]
    value = row["Value"]
    if value > 0:
        return assign_dillution_income(category, value)
    return assign_dillution_expense(category, abs(value))


def _standardize_string(s: str) -> str:
    """Standardize a string by removing accents and converting to lowercase."""
    return unidecode(s).lower()


def dillute_costs(data: pd.DataFrame) -> pd.DataFrame:
    """Dillute costs in the given data.

    Dilluting means spreading the cost over 12 months.
    """
    data_ = data.copy()

    # Separate dillution and non-dillution entries
    data_keep = data_[~data_["Dillution"]].copy()
    data_dillute = data_[data_["Dillution"]].copy()

    # Dillute costs
    data_dillute["ValueDilluted"] = data_dillute["Value"].apply(get_dilluted_values)
    data_dillute["DateDilluted"] = data_dillute["Date"].apply(get_dilluted_dates)
    data_dillute = data_dillute.explode(["ValueDilluted", "DateDilluted"])
    data_dillute["Value"] = data_dillute["ValueDilluted"]
    data_dillute["Date"] = data_dillute["DateDilluted"]
    data_dillute = data_dillute.drop(columns=["ValueDilluted", "DateDilluted"])

    # Combine data back
    return pd.concat([data_keep, data_dillute], ignore_index=True)


def get_dilluted_values(value: float) -> list[float]:
    """Get dilluted values for a given value.

    For dillution, the cost is spread over 12 months of the same year.
    """
    return [value / 12] * 12


def get_dilluted_dates(date: pd.Timestamp) -> pd.DatetimeIndex:
    """Get dilluted dates for a given date.

    For dillution, the cost is spread over 12 months of the same year.
    For simplification, the first day of each month is used.
    """
    return [pd.Timestamp(year=date.year, month=month, day=1) for month in range(1, 13)]
