"""Dilution business rules."""

import pandas as pd
from unidecode import unidecode
from utils.globals import Account
from utils.operators import Operator

# Value-based dilution overrides - see docs/business_rules/dilution.md
REFUND_DILUTION_THRESHOLD = 500
CAR_DILUTION_THRESHOLD = 300
DONATION_DILUTION_THRESHOLD = 200
HOME_DILUTION_THRESHOLD = 250
SUBSCRIPTIONS_DILUTION_THRESHOLD = 60
WORK_DILUTION_THRESHOLD = 300


class DilutionAssigner(Operator):
    """Data expense dilution assigner.

    Transactions to be diluted depend on business rules associated to their
    category and value.
    """

    def __init__(self, operator: Operator) -> None:
        """Initialize the tier assigner."""
        self._data = operator.data.copy()
        self._data["Dilution"] = self._data.apply(self._assign_dilution, axis=1)

    @property
    def data(self) -> pd.DataFrame:
        """Data with the `Dilution` flag assigned."""
        return self._data

    def _assign_dilution(self, row: pd.Series) -> bool:
        """Assign dilution to the given data."""
        category = self._standardize_string(row["Category"])
        value = row["Value"]
        if value > 0:
            return self._assign_dilution_income(category, value)
        return self._assign_dilution_expense(category, abs(value), row["Account"])

    def _assign_dilution_income(self, category: str, value: float) -> bool:
        """Assign dilution for income entries."""
        # Specific cases
        if category == "refund" and value >= REFUND_DILUTION_THRESHOLD:
            return True

        # General per-category assignment
        return {
            "gift": False,
            "refund": False,
            "rewards": True,
            "salary": True,
            # Synthetic trip balance from TripBalanceCalculator - see travel.md
            "travel": True,
        }[category]

    def _assign_dilution_expense(
        self, category: str, value: float, account: str
    ) -> bool:
        """Assign dilution for expense entries."""
        # Travel is always diluted for the main trip (Trip Funds account - this is
        # also how TripBalanceCalculator's synthetic "Saldo Viagem" balance row is
        # tagged, see travel.md). Any other account is ad-hoc travel (e.g. a one-off
        # work trip - see tiers.md's `travel` + tag `work` override), treated like the
        # `work` category it's conceptually closest to: diluted only above threshold
        if category == "travel":
            return account == Account.TRIP_FUNDS or value >= WORK_DILUTION_THRESHOLD

        # Value-based overrides, checked before the per-category default
        thresholds = {
            "car": CAR_DILUTION_THRESHOLD,
            "donation": DONATION_DILUTION_THRESHOLD,
            "home": HOME_DILUTION_THRESHOLD,
            "subscriptions": SUBSCRIPTIONS_DILUTION_THRESHOLD,
            "work": WORK_DILUTION_THRESHOLD,
        }
        if category in thresholds:
            return value >= thresholds[category]

        # General per-category assignment - car/donation/home/subscriptions/work are
        # handled entirely by the threshold check above (in or out, never falls here)
        return {
            "commute": False,
            "education": False,
            "gift": False,
            "health": False,
            "high costs": True,
            "maintenance": True,
            "personal felp": False,
            "personal lena": False,
            "pharmacy": False,
            "physical": False,
            "recreation": False,
            "rent": False,
            "restaurant": False,
            "services": False,
            "supermarket": False,
            "transport": False,
            "unknown": False,
            "work lunch": False,
        }[category]

    def _standardize_string(self, s: str) -> str:
        """Standardize a string by removing accents and converting to lowercase."""
        return unidecode(s).lower()


class Diluter(DilutionAssigner):
    """Data expenses diluter.

    Dilutes specific incomes and expenses over a 12-month period.
    """

    def __init__(self, operator: Operator) -> None:
        """Initialize the tier assigner."""
        super().__init__(operator)

        self._data = self._dilute_costs(self._data)

        # Update Month column after dilution
        self._data["Month"] = self._data["Date"].dt.to_period("M").dt.to_timestamp()

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
