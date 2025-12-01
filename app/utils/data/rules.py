"""Business rules utils."""

import pandas as pd
from unidecode import unidecode


def assign_tiers(row: pd.Series) -> str:
    """Assign tiers to the given data."""

    category = row["Category"]
    description = _standardize_string(row["Description"])
    value = row["Value"]

    # Evaluate only expenses
    if value > 0:
        return ""

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


def assign_dillution(row: pd.Series) -> str:
    """Assign dillution to the given data."""

    category = row["Category"]
    value = row["Value"]

    # Evaluate only expenses
    if value > 0:
        return None

    value = abs(value)

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


def _standardize_string(s: str) -> str:
    """Standardize a string by removing accents and converting to lowercase."""
    return unidecode(s).lower()
