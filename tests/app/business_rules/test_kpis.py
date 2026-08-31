"""Tests for the KPI business rules (docs/business_rules/kpis.md).

`CardKpi.card()` itself isn't tested here - it only renders Streamlit markup. Its
underlying pass/fail and formatting logic (`_evaluate_kpi`/`_format_value`) is pure and
Streamlit-free, so it's tested directly instead.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd
import pytest
from utils.business.budget import CATEGORY_BUDGETS
from utils.business.kpis import (
    CardKpi,
    CardKpiCurrency,
    CardKpiPercentage,
    KpiCalculator,
    KpiCategoryCalculator,
    KpiDateAdvancementCalculator,
    KpiMainTripCalculator,
    KpiTrendsCalculator,
    KpiVaCalculator,
    KpiVoucherCalculator,
    KpiVrCalculator,
)
from utils.globals import Account


class TestKpiCalculator:
    """Totals and tier percentages, all denominated against total income."""

    def test_totals_and_net_income(self, make_operator: Any) -> None:
        """Income and expenses are summed independently, net income is their diff."""
        operator = make_operator(
            [
                {"Value": 5000, "Tier": "Fixed"},
                {"Value": -2000, "Tier": "Fixed"},
                {"Value": -500, "Tier": "Variable"},
            ]
        )
        calculator = KpiCalculator(operator)

        assert calculator.total_income == 5000
        assert calculator.total_expenses == 2500
        assert calculator.net_income == 2500
        assert calculator.net_income_perc == pytest.approx(2500 / 5000, rel=1e-4)

    def test_tier_expense_percentages_are_divided_by_income_not_total_expenses(
        self, make_operator: Any
    ) -> None:
        """A common trap: the denominator is income, not total expenses."""
        operator = make_operator(
            [
                {"Value": 1000, "Tier": "Fixed"},  # income
                {"Value": -500, "Tier": "Fixed"},  # expense
                {"Value": -300, "Tier": "Variable"},
                {"Value": -100, "Tier": "Lifestyle"},
            ]
        )
        calculator = KpiCalculator(operator)

        assert calculator.total_expenses == 900
        assert calculator.fixed_expenses_perc == pytest.approx(500 / 1000, rel=1e-4)
        assert calculator.variable_expenses_perc == pytest.approx(300 / 1000, rel=1e-4)
        assert calculator.lifestyle_expenses_perc == pytest.approx(100 / 1000, rel=1e-4)

    def test_fixed_income_and_percentage(self, make_operator: Any) -> None:
        """Only income rows tiered Fixed count toward fixed income."""
        operator = make_operator(
            [
                {"Value": 4000, "Tier": "Fixed"},
                {"Value": 1000, "Tier": "Variable"},
            ]
        )
        calculator = KpiCalculator(operator)

        assert calculator.fixed_income == 4000
        assert calculator.fixed_income_perc == pytest.approx(4000 / 5000, rel=1e-4)

    def test_empty_data_yields_zero_not_nan(self, make_operator: Any) -> None:
        """No rows -> every sum is 0, and the 1e-5 epsilon keeps percentages finite."""
        calculator = KpiCalculator(make_operator([]))

        assert calculator.total_income == 0
        assert calculator.net_income_perc == 0


class TestKpiTrendsCalculator:
    """Period-over-period comparison between two independent KpiCalculators."""

    def test_income_and_expenses_increase_percentages(self, make_operator: Any) -> None:
        """Increase percentages compare current totals against the previous period."""
        current = KpiCalculator(make_operator([{"Value": 1200, "Tier": "Fixed"}]))
        previous = KpiCalculator(make_operator([{"Value": 1000, "Tier": "Fixed"}]))
        trends = KpiTrendsCalculator(current, previous)

        assert trends.income_increase_perc == pytest.approx(0.2, rel=1e-3)

    def test_expenses_inflation_percentage(self, make_operator: Any) -> None:
        """Inflation compares how much faster expenses grew than income."""
        current = KpiCalculator(
            make_operator(
                [{"Value": 1100, "Tier": "Fixed"}, {"Value": -1200, "Tier": "Fixed"}]
            )
        )
        previous = KpiCalculator(
            make_operator(
                [{"Value": 1000, "Tier": "Fixed"}, {"Value": -1000, "Tier": "Fixed"}]
            )
        )
        trends = KpiTrendsCalculator(current, previous)

        # income +10%, expenses +20% -> inflation = (0.2 - 0.1) / 0.1 = 1.0
        assert trends.expenses_inflation_perc == pytest.approx(1.0, rel=1e-3)


class TestKpiCategoryCalculator:
    """Per-category breakdowns, always keyed by every CATEGORY_BUDGETS category."""

    def test_expenses_by_category_covers_every_budgeted_category(
        self, make_operator: Any
    ) -> None:
        """Categories with zero transactions still appear, summed to zero."""
        operator = make_operator(
            [{"Category": "Restaurant", "Value": -150, "Tier": "Lifestyle"}]
        )
        calculator = KpiCategoryCalculator(operator)

        by_category = calculator.expenses_by_category
        assert set(by_category) == set(CATEGORY_BUDGETS)
        assert by_category["Restaurant"] == 150
        assert by_category["Car"] == 0

    def test_category_matching_is_case_and_accent_insensitive(
        self, make_operator: Any
    ) -> None:
        """A differently-cased Category still lands in its canonical bucket.

        Without standardizing both sides, this would silently vanish (contribute to
        no bucket) rather than crash - see docs/business_rules/categories.md.
        """
        operator = make_operator(
            [{"Category": "RESTAURANT", "Value": -150, "Tier": "Lifestyle"}]
        )
        calculator = KpiCategoryCalculator(operator)

        assert calculator.expenses_by_category["Restaurant"] == 150

    def test_expenses_budget_utilization_uses_the_flat_placeholder(
        self, make_operator: Any
    ) -> None:
        """Utilization is measured against the current flat CATEGORY_BUDGETS value."""
        operator = make_operator(
            [{"Category": "Restaurant", "Value": -500, "Tier": "Lifestyle"}]
        )
        calculator = KpiCategoryCalculator(operator)

        assert calculator.expenses_budget_utilization_perc_by_category[
            "Restaurant"
        ] == pytest.approx(0.5, rel=1e-4)

    def test_sort_categories_orders_descending(self, make_operator: Any) -> None:
        """Categories sort by value, largest first."""
        calculator = KpiCategoryCalculator(make_operator([]))

        result = calculator.sort_categories({"A": 10, "B": 30, "C": 20})

        assert result == ["B", "C", "A"]

    def test_expenses_fixed_by_category_filters_on_tier(
        self, make_operator: Any
    ) -> None:
        """Only rows tiered Fixed count toward the fixed-by-category breakdown."""
        operator = make_operator(
            [
                {"Category": "Car", "Value": -300, "Tier": "Fixed"},
                {"Category": "Car", "Value": -50, "Tier": "Variable"},
            ]
        )
        calculator = KpiCategoryCalculator(operator)

        assert calculator.expenses_fixed_by_category["Car"] == 300
        assert calculator.expenses_variable_by_category["Car"] == 50


@dataclass
class _StaticDateRange:
    """Minimal stand-in for a DateFilter: only start_date/end_date are read."""

    start_date: pd.Timestamp
    end_date: pd.Timestamp


class TestKpiDateAdvancementCalculator:
    """Elapsed-time percentage within a date range, clamped once the range ends."""

    def test_elapsed_date_perc_clamps_to_one_past_the_end_date(
        self, freeze_today: Any
    ) -> None:
        """Once "today" is past the range, the percentage clamps to 1.0."""
        freeze_today("2025-08-15")
        date_range = _StaticDateRange(
            pd.Timestamp("2025-01-01"), pd.Timestamp("2025-06-30")
        )

        calculator = KpiDateAdvancementCalculator(date_range)

        assert calculator.elapsed_date_perc == 1.0

    def test_elapsed_date_perc_is_the_ratio_of_days_elapsed(
        self, freeze_today: Any
    ) -> None:
        """Within the range, it's days-elapsed / days-in-range."""
        start_date = pd.Timestamp("2025-01-01")
        end_date = start_date + pd.Timedelta(days=100)
        today = start_date + pd.Timedelta(days=10)
        freeze_today(today.strftime("%Y-%m-%d"))
        date_range = _StaticDateRange(start_date, end_date)

        calculator = KpiDateAdvancementCalculator(date_range)

        assert calculator.elapsed_date_perc == pytest.approx(10 / 100, rel=1e-3)


class TestKpiVoucherCalculator:
    """Voucher (VR/VA) budget consumption."""

    def test_voucher_consumption_percentage(self, make_operator: Any) -> None:
        """Consumption is expenses paid from the voucher account over its income."""
        operator = make_operator(
            [
                {"Account": Account.VR, "Value": 800, "Tier": "Fixed"},
                {"Account": Account.VR, "Value": -600, "Tier": "Variable"},
                # Different account - must not count
                {"Account": "Carteira", "Value": -100, "Tier": "Variable"},
            ]
        )
        calculator = KpiVrCalculator(operator)

        assert calculator.voucher_budget == 800
        assert calculator.voucher_consumption == 600
        assert calculator.voucher_consumption_perc == pytest.approx(0.75, rel=1e-4)

    def test_va_calculator_uses_the_va_account(self, make_operator: Any) -> None:
        """KpiVaCalculator is the same rule, scoped to the VA account."""
        operator = make_operator(
            [{"Account": Account.VA, "Value": 400, "Tier": "Fixed"}]
        )
        calculator = KpiVaCalculator(operator)

        assert calculator.voucher_budget == 400

    def test_generic_voucher_calculator_accepts_any_account(
        self, make_operator: Any
    ) -> None:
        """KpiVoucherCalculator itself takes the target account explicitly."""
        operator = make_operator(
            [{"Account": Account.VR, "Value": 100, "Tier": "Fixed"}]
        )
        calculator = KpiVoucherCalculator(Account.VR, operator)

        assert calculator.voucher_budget == 100


class TestKpiMainTripCalculator:
    """Current-year trip budget overrun, regardless of the caller's own date filter."""

    def test_budget_overrun_when_over_budget(
        self, make_operator: Any, mock_transfers: Any, freeze_today: Any
    ) -> None:
        """A negative synthetic balance (overspend) reports a positive overrun."""
        freeze_today("2025-06-15")  # ThisYearFilter -> 2025, ignoring any page filter
        mock_transfers(
            [
                {
                    "Date": "31/12/2024",
                    "Conta origem": "Carteira",
                    "Conta destino": "Trip Funds",
                    "Value": 30000,
                    "Tags": "orlando",
                }
            ]
        )
        operator = make_operator(
            [
                {
                    "Account": Account.TRIP_FUNDS,
                    "Category": "Travel",
                    "Value": -5000,
                    "Date": "2025-12-31",
                    "Tier": "Lifestyle",
                }
            ]
        )

        calculator = KpiMainTripCalculator(operator)

        assert calculator.budget == 30000
        assert calculator.budget_overrun == pytest.approx(5000)
        assert calculator.budget_overrun_perc == pytest.approx(5000 / 30000, rel=1e-3)

    def test_budget_overrun_is_negative_when_under_budget(
        self, make_operator: Any, mock_transfers: Any, freeze_today: Any
    ) -> None:
        """A positive synthetic balance (surplus) reports a negative overrun."""
        freeze_today("2025-06-15")
        mock_transfers(
            [
                {
                    "Date": "31/12/2024",
                    "Conta origem": "Carteira",
                    "Conta destino": "Trip Funds",
                    "Value": 30000,
                    "Tags": "orlando",
                }
            ]
        )
        operator = make_operator(
            [
                {
                    "Account": Account.TRIP_FUNDS,
                    "Category": "Travel",
                    "Value": 2000,
                    "Date": "2025-12-31",
                    "Tier": "Lifestyle",
                }
            ]
        )

        calculator = KpiMainTripCalculator(operator)

        assert calculator.budget_overrun == pytest.approx(-2000)


class TestCardKpi:
    """Pass/fail evaluation and value formatting for KPI cards."""

    def test_no_target_is_neutral(self) -> None:
        """Without a target, a card never shows a met/not-met status."""
        card = CardKpi(title="x", value=100, target=None)

        assert card._evaluate_kpi() == ""  # noqa: SLF001

    def test_target_without_higher_is_better_raises(self) -> None:
        """A target requires an explicit direction, or the intent is ambiguous."""
        card = CardKpi(title="x", value=100, target=50, higher_is_better=None)

        with pytest.raises(ValueError, match="higher_is_better"):
            card._evaluate_kpi()  # noqa: SLF001

    @pytest.mark.parametrize(
        ("value", "target", "expected"),
        [
            (100, 50, "kpi-card-met"),  # higher is better, value >= target
            (50, 50, "kpi-card-met"),  # boundary: equal counts as met
            (30, 50, "kpi-card-not-met"),
        ],
    )
    def test_higher_is_better_evaluation(
        self, value: float, target: float, expected: str
    ) -> None:
        """higher_is_better=True: met when value >= target."""
        card = CardKpi(title="x", value=value, target=target, higher_is_better=True)

        assert card._evaluate_kpi() == expected  # noqa: SLF001

    @pytest.mark.parametrize(
        ("value", "target", "expected"),
        [
            (30, 50, "kpi-card-met"),  # lower is better, value <= target
            (50, 50, "kpi-card-met"),  # boundary: equal counts as met either direction
            (80, 50, "kpi-card-not-met"),
        ],
    )
    def test_lower_is_better_evaluation(
        self, value: float, target: float, expected: str
    ) -> None:
        """higher_is_better=False: met when value <= target."""
        card = CardKpi(title="x", value=value, target=target, higher_is_better=False)

        assert card._evaluate_kpi() == expected  # noqa: SLF001

    def test_na_value_is_neutral_even_with_a_target(self) -> None:
        """The "N/A" value short-circuits to neutral, target/higher_is_better aside."""
        card = CardKpi(title="x", value="N/A", target=50, higher_is_better=True)

        assert card._evaluate_kpi() == ""  # noqa: SLF001

    def test_format_value_currency_and_percentage(self) -> None:
        """Currency rounds to whole reais; percentage keeps one decimal place."""
        currency = CardKpiCurrency(title="x", value=1234.56)
        percentage = CardKpiPercentage(title="x", value=0.12345)

        assert currency._format_value(currency.value) == "R$ 1,235"  # noqa: SLF001
        assert percentage._format_value(percentage.value) == "12.3%"  # noqa: SLF001

    def test_format_value_passes_through_na_and_none(self) -> None:
        """The "N/A" and None values pass through as-is, not formatted."""
        card = CardKpiCurrency(title="x", value=None)

        assert card._format_value("N/A") == "N/A"  # noqa: SLF001
        assert card._format_value(None) is None  # noqa: SLF001

    def test_unknown_kind_raises(self) -> None:
        """An unsupported `kind` fails loudly rather than silently misformatting."""
        card = CardKpi(title="x", kind="bogus", value=1)

        with pytest.raises(ValueError, match="Unknown kind"):
            card._format_value(1)  # noqa: SLF001
