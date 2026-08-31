"""Business rules."""

from unidecode import unidecode


def standardize_string(value: str) -> str:
    """Standardize a string for case/accent-insensitive comparison.

    Removes accents and lowercases - used everywhere a Category, Description, or Tag
    needs matching regardless of how it was typed in the Mobills export: dilution and
    tier assignment (dilution.py/tiers.py), and the KPI category breakdown (kpis.py).
    """
    return unidecode(value).lower()
