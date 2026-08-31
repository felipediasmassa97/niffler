"""Tests for the dilution business rule (docs/business_rules/dilution.md)."""

from typing import Any

import pytest
from utils.business.dilution import Diluter, DilutionAssigner
from utils.globals import Account


class TestDilutionAssignerIncome:
    """Flag rule for income rows (Value > 0)."""

    @pytest.mark.parametrize(
        ("category", "value", "expected"),
        [
            ("Refund", 500, True),  # override threshold, inclusive
            ("Refund", 499.99, False),
            ("Rewards", 10, True),
            ("Salary", 5000, True),
            ("Gift", 100, False),
            ("Travel", 1, True),  # synthetic Saldo Viagem balance - see travel.md
        ],
    )
    def test_assigns_dilution_by_category_and_threshold(
        self, make_operator: Any, category: str, value: float, *, expected: bool
    ) -> None:
        """Each income category follows its documented threshold/default."""
        operator = make_operator([{"Category": category, "Value": value}])

        result = DilutionAssigner(operator).data

        assert result.iloc[0]["Dilution"] == expected

    def test_unmapped_category_raises_key_error(self, make_operator: Any) -> None:
        """A category missing from the dict fails loudly, not silently."""
        operator = make_operator([{"Category": "Not A Real Category", "Value": 10}])

        with pytest.raises(KeyError):
            _ = DilutionAssigner(operator).data


class TestDilutionAssignerExpense:
    """Flag rule for expense rows (Value <= 0, compared on the absolute value)."""

    @pytest.mark.parametrize(
        ("category", "value", "expected"),
        [
            ("Car", -300, True),  # override threshold, inclusive
            ("Car", -299.99, False),
            ("Donation", -200, True),
            ("Donation", -199.99, False),
            ("Home", -250, True),
            ("Home", -249.99, False),
            ("Subscriptions", -60, True),
            ("Subscriptions", -59.99, False),
            ("Work", -300, True),
            ("Work", -299.99, False),
            ("High Costs", -1, True),  # always diluted, no threshold
            ("Maintenance", -1, True),
            ("Commute", -10000, False),  # never diluted, regardless of size
            ("Education", -10000, False),
            ("Gift", -10000, False),
            ("Health", -10000, False),
            ("Personal Felp", -10000, False),
            ("Personal Lena", -10000, False),
            ("Pharmacy", -10000, False),
            ("Physical", -10000, False),
            ("Recreation", -10000, False),
            ("Rent", -10000, False),
            ("Restaurant", -10000, False),
            ("Services", -10000, False),
            ("Supermarket", -10000, False),
            ("Transport", -10000, False),
            ("Unknown", -10000, False),
            ("Work Lunch", -10000, False),
        ],
    )
    def test_assigns_dilution_by_category_and_threshold(
        self, make_operator: Any, category: str, value: float, *, expected: bool
    ) -> None:
        """Each expense category follows its documented threshold/default."""
        operator = make_operator([{"Category": category, "Value": value}])

        result = DilutionAssigner(operator).data

        assert result.iloc[0]["Dilution"] == expected

    def test_category_matching_is_case_insensitive(self, make_operator: Any) -> None:
        """`_standardize_string` lowercases before the dict lookup."""
        operator = make_operator([{"Category": "CAR", "Value": -100}])

        result = DilutionAssigner(operator).data

        assert not result.iloc[0]["Dilution"]  # below the Car dilution threshold

    def test_unmapped_category_raises_key_error(self, make_operator: Any) -> None:
        """A category missing from the dict fails loudly, not silently."""
        operator = make_operator([{"Category": "Not A Real Category", "Value": -10}])

        with pytest.raises(KeyError):
            _ = DilutionAssigner(operator).data


class TestDilutionAssignerExpenseTravel:
    """`travel` also checks Account, not just Category/Value (see dilution.md).

    Trip Funds is the single pre-funded main trip - always diluted, any amount.
    Any other account is ad-hoc travel (e.g. a one-off work trip), diluted only above
    the same threshold as the `work` category it's conceptually closest to.
    """

    def test_trip_funds_travel_is_always_diluted_regardless_of_amount(
        self, make_operator: Any
    ) -> None:
        """The main trip's synthetic balance row is diluted no matter how small."""
        operator = make_operator(
            [{"Category": "Travel", "Account": Account.TRIP_FUNDS, "Value": -1}]
        )

        result = DilutionAssigner(operator).data

        assert result.iloc[0]["Dilution"]

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (-300, True),  # override threshold, inclusive - same as `work`
            (-299.99, False),
        ],
    )
    def test_non_trip_funds_travel_uses_the_work_threshold(
        self, make_operator: Any, value: float, *, expected: bool
    ) -> None:
        """Ad-hoc travel (any account but Trip Funds) follows a value threshold."""
        operator = make_operator(
            [{"Category": "Travel", "Account": "Carteira", "Value": value}]
        )

        result = DilutionAssigner(operator).data

        assert result.iloc[0]["Dilution"] == expected


class TestDiluter:
    """Spreading rule: 12-way explode of every diluted row."""

    def test_diluted_row_is_spread_over_twelve_months_of_the_same_year(
        self, make_operator: Any
    ) -> None:
        """Value/12, 12 dates in the transaction's own year, description suffixed."""
        operator = make_operator(
            [{"Category": "High Costs", "Value": -1200, "Date": "2025-07-15"}]
        )

        result = Diluter(operator).data

        assert len(result) == 12
        assert result["Value"].sum() == pytest.approx(-1200)
        assert (result["Value"] == pytest.approx(-100)).all()
        assert (result["Date"].dt.year == 2025).all()
        assert sorted(result["Date"].dt.month) == list(range(1, 13))
        assert (result["Date"].dt.day == 1).all()
        assert set(result["Description"]) == {
            f"Test transaction ({i}/12)" for i in range(1, 13)
        }

    def test_month_column_is_recomputed_after_explode(self, make_operator: Any) -> None:
        """`Month` reflects each exploded row's own new `Date`, not the original."""
        operator = make_operator(
            [{"Category": "High Costs", "Value": -120, "Date": "2025-07-15"}]
        )

        result = Diluter(operator).data

        assert (result["Month"] == result["Date"]).all()

    def test_non_diluted_row_passes_through_unchanged(self, make_operator: Any) -> None:
        """A row that isn't diluted keeps its original Value/Date/Description."""
        operator = make_operator(
            [{"Category": "Rent", "Value": -2000, "Date": "2025-07-15"}]
        )

        result = Diluter(operator).data

        assert len(result) == 1
        assert result.iloc[0]["Value"] == -2000
        assert result.iloc[0]["Date"].strftime("%Y-%m-%d") == "2025-07-15"
        assert result.iloc[0]["Description"] == "Test transaction"

    def test_mixed_diluted_and_non_diluted_rows(self, make_operator: Any) -> None:
        """Diluted and non-diluted rows explode/pass through independently."""
        operator = make_operator(
            [
                {"Category": "High Costs", "Value": -1200, "Date": "2025-07-15"},
                {"Category": "Rent", "Value": -2000, "Date": "2025-07-15"},
            ]
        )

        result = Diluter(operator).data

        assert len(result) == 13  # 12 exploded + 1 passthrough
        assert (result["Value"] == -2000).sum() == 1
