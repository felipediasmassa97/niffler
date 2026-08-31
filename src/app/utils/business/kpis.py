"""Data KPIs."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import pandas as pd
import streamlit as st
from utils.business.budget import CATEGORY_BUDGETS
from utils.business.travel import TripBalanceCalculator
from utils.globals import Account
from utils.operators.filter import DateFilter, ThisYearFilter

if TYPE_CHECKING:
    from utils.operators import Operator

# fixit add percentages of target in parentheses in KPI cards (e.g. category KPIs)


# List of KPIs to track
# (consolidate in new screen, not in monthly or yearly view)

# Show in 2 sections (section in the left = default filter; section in the right =
# optional filter):
# - This month (default)
# - Enable custom date range picker (last year, last 6 months, last 3 months, last
#   month, this month, this year, all time)

# Big Picture:
# - Total income
# - Total expenses
# - Net Income Amount (absolute value)
# - Net Income Percentage (Net Income / Total Income)
#   - Target: Beginner = 10%-20%, Ideal = 25%-40%, Elite = 50%+

# Time Trends:
# - Expenses Inflation
#   - Income inflation vs expenses inflation: this time range (filter) vs last 3 / 6 /
#     12 months (show all 3 to see different trends)
#   - Target: Beginner = <5%, Ideal = <3%, Elite = <0%
# - Incomes increase: this time range (filter) vs last 3 / 6 / 12 months (show all 3
#   to see different trends)
# - Expenses increase: this time range (filter) vs last 3 / 6 / 12 months (show all 3
#   to see different trends)
#   - Target: ???

# Incomes Breakdown:
# - Percentage of fixed income against total income
# - Top 3 income categories (consider only expenses matching fixed tier)

# Expenses Breakdown:
# - Percentage of lifestyle expenses against total income
#   - Target for lifestyle: Beginner = X%, Ideal = Y%
# - Top 3 fixed expense categories (consider only expenses matching fixed tier)
# - Top 3 variable expense categories (same)
# - Top 3 lifestyle expense categories (same)
# - Expense breakdown by category (absolute values)
#   - Add expander with full breakdown by category
#   - Highlight some key categories to track (most actionable ones):
#     - Home
#     - Personal Felp
#     - Personal Lena
#     - Recreation
#     - Restaurant

# Travel:
# - Budget adherence: budgeted vs actual travel expenses
#   - Target: Beginner = <20%, Ideal = <10%, Elite = <0%
#   - Evaluate yearly, not monthly

# fixit long-term implement investments KPIs
# fixit long-term implement KPI based on how much of income is invested monthly
# fixit long-term implement "Months of Runway" KPI
# Months of Runway = Emergency Fund / Average Monthly Expenses Over Last 6 Months
# - Target: Beginner: 3 months, Strong: 6 months, Excellent: 12 months
# Investments:
# -
# -
# -


class KpiCalculator:
    """KPI calculator."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the KPI calculator."""
        self._data = operator.data

    @property
    def income(self) -> pd.DataFrame:
        """Income."""
        return self._data[self._data["Value"] > 0]

    @property
    def expenses(self) -> pd.DataFrame:
        """Expenses."""
        return self._data[self._data["Value"] < 0]

    @property
    def total_income(self) -> float:
        """Total income."""
        return self.income["Value"].sum()

    @property
    def total_expenses(self) -> float:
        """Total expenses."""
        return abs(self.expenses["Value"].sum())

    @property
    def net_income(self) -> float:
        """Net income."""
        return self.total_income - self.total_expenses

    @property
    def net_income_perc(self) -> float:
        """Net income percentage."""
        return self.net_income / (self.total_income + 1e-5)

    @property
    def fixed_income(self) -> float:
        """Fixed income."""
        return self.income[(self.income["Tier"] == "Fixed")]["Value"].sum()

    @property
    def fixed_income_perc(self) -> float:
        """Fixed income percentage."""
        return self.fixed_income / (self.total_income + 1e-5)

    @property
    def fixed_expenses(self) -> float:
        """Fixed expenses."""
        return abs(self.expenses[(self.expenses["Tier"] == "Fixed")]["Value"].sum())

    @property
    def fixed_expenses_perc(self) -> float:
        """Fixed expenses percentage."""
        return self.fixed_expenses / (self.total_income + 1e-5)

    @property
    def variable_expenses(self) -> float:
        """Variable expenses."""
        return abs(self.expenses[(self.expenses["Tier"] == "Variable")]["Value"].sum())

    @property
    def variable_expenses_perc(self) -> float:
        """Variable expenses percentage."""
        return self.variable_expenses / (self.total_income + 1e-5)

    @property
    def lifestyle_expenses(self) -> float:
        """Lifestyle expenses."""
        return abs(self.expenses[(self.expenses["Tier"] == "Lifestyle")]["Value"].sum())

    @property
    def lifestyle_expenses_perc(self) -> float:
        """Lifestyle expenses percentage."""
        return self.lifestyle_expenses / (self.total_income + 1e-5)


class KpiTrendsCalculator:
    """KPI trends calculator."""

    def __init__(
        self, kpi_calc_current: KpiCalculator, kpi_calc_previous: KpiCalculator
    ) -> None:
        """Initialize the KPI trends calculator."""
        self._kpi_calc_current = kpi_calc_current
        self._kpi_calc_previous = kpi_calc_previous

    @property
    def income_increase_perc(self) -> float:
        """Income increase percentage."""
        return (
            self._kpi_calc_current.total_income - self._kpi_calc_previous.total_income
        ) / (abs(self._kpi_calc_previous.total_income) + 1e-5)

    @property
    def expenses_increase_perc(self) -> float:
        """Expenses increase percentage."""
        return (
            self._kpi_calc_current.total_expenses
            - self._kpi_calc_previous.total_expenses
        ) / (abs(self._kpi_calc_previous.total_expenses) + 1e-5)

    @property
    def expenses_inflation_perc(self) -> float:
        """Expenses inflation percentage."""
        return (self.expenses_increase_perc - self.income_increase_perc) / (
            self.income_increase_perc + 1e-5
        )


class KpiCategoryCalculator(KpiCalculator):
    """KPI category calculator."""

    def sort_categories(self, values_by_category: dict[str, float]) -> list[str]:
        """Sort categories by value, descending."""
        items_sorted = sorted(
            values_by_category.items(), key=lambda item: item[1], reverse=True
        )
        return [item[0] for item in items_sorted]

    def get_category_data(self, data: pd.DataFrame, category: str) -> pd.DataFrame:
        """Get category data."""
        return data[data["Category"] == category]

    @property
    def income_categories_sorted(self) -> list[str]:
        """Income categories sorted by value, descending."""
        return self.sort_categories(self.income_by_category)

    @property
    def income_by_category(self) -> dict[str, float]:
        """Income by category."""
        return {
            category: self.get_category_data(self.income, category)["Value"].sum()
            for category in CATEGORY_BUDGETS
        }

    @property
    def income_perc_by_category(self) -> dict[str, float]:
        """Income percentage by category."""
        return {
            category: self.get_category_data(self.income, category)["Value"].sum()
            / (self.total_income + 1e-5)
            for category in CATEGORY_BUDGETS
        }

    @property
    def expenses_categories_sorted(self) -> list[str]:
        """Expenses categories sorted by value, descending."""
        return self.sort_categories(self.expenses_by_category)

    @property
    def expenses_by_category(self) -> dict[str, float]:
        """Expenses by category."""
        return {
            category: abs(
                self.get_category_data(self.expenses, category)["Value"].sum()
            )
            for category in CATEGORY_BUDGETS
        }

    @property
    def expenses_budget_utilization_perc_by_category(self) -> dict[str, float]:
        """Expenses budget utilization by category."""
        return {
            category: (
                abs(self.get_category_data(self.expenses, category)["Value"].sum())
            )
            / (budget + 1e-5)
            for category, budget in CATEGORY_BUDGETS.items()
        }

    @property
    def expenses_fixed_categories_sorted(self) -> list[str]:
        """Fixed expenses categories sorted by value, descending."""
        return self.sort_categories(self.expenses_fixed_by_category)

    @property
    def expenses_fixed_by_category(self) -> dict[str, float]:
        """Fixed expenses by category."""
        return {
            category: abs(
                self.expenses[
                    (self.expenses["Category"] == category)
                    & (self.expenses["Tier"] == "Fixed")
                ]["Value"].sum()
            )
            for category in CATEGORY_BUDGETS
        }

    @property
    def expenses_variable_categories_sorted(self) -> list[str]:
        """Variable expenses categories sorted by value, descending."""
        return self.sort_categories(self.expenses_variable_by_category)

    @property
    def expenses_variable_by_category(self) -> dict[str, float]:
        """Variable expenses by category."""
        return {
            category: abs(
                self.expenses[
                    (self.expenses["Category"] == category)
                    & (self.expenses["Tier"] == "Variable")
                ]["Value"].sum()
            )
            for category in CATEGORY_BUDGETS
        }

    @property
    def expenses_lifestyle_categories_sorted(self) -> list[str]:
        """Lifestyle expenses categories sorted by value, descending."""
        return self.sort_categories(self.expenses_lifestyle_by_category)

    @property
    def expenses_lifestyle_by_category(self) -> dict[str, float]:
        """Lifestyle expenses by category."""
        return {
            category: abs(
                self.expenses[
                    (self.expenses["Category"] == category)
                    & (self.expenses["Tier"] == "Lifestyle")
                ]["Value"].sum()
            )
            for category in CATEGORY_BUDGETS
        }


class KpiDateAdvancementCalculator:
    """KPI date advancement calculator."""

    def __init__(self, date_filter: DateFilter) -> None:
        """Initialize the date advancement calculator."""
        self.date_filter = date_filter

    @property
    def elapsed_date_perc(self) -> float:
        """Elapsed date percentage."""
        today = pd.Timestamp.today()
        if today > self.date_filter.end_date:
            return 1.0
        return pd.Timedelta(today - self.date_filter.start_date).days / (
            pd.Timedelta(self.date_filter.end_date - self.date_filter.start_date).days
            + 1e-5
        )


class KpiVoucherCalculator(KpiCalculator):
    """KPI voucher calculator."""

    def __init__(self, voucher_type: Account, operator: Operator) -> None:
        """Initialize the voucher calculator."""
        self.voucher_type = voucher_type
        super().__init__(operator)

    @property
    def voucher_budget(self) -> float:
        """Voucher budget."""
        return self.income[self.income["Account"] == self.voucher_type]["Value"].sum()

    @property
    def voucher_consumption(self) -> float:
        """Voucher consumption."""
        return abs(
            self.expenses[self.expenses["Account"] == self.voucher_type]["Value"].sum()
        )

    @property
    def voucher_consumption_perc(self) -> float:
        """Voucher consumption percentage."""
        return self.voucher_consumption / (self.voucher_budget + 1e-5)


class KpiVrCalculator(KpiVoucherCalculator):
    """KPI VR calculator."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the VR calculator."""
        super().__init__(Account.VR, operator)


class KpiVaCalculator(KpiVoucherCalculator):
    """KPI VA calculator."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the VA calculator."""
        super().__init__(Account.VA, operator)


class KpiMainTripCalculator(KpiCalculator):
    """KPI main trip calculator."""

    def __init__(self, operator: Operator) -> None:
        """Initialize the main trip calculator."""
        # Enforce this year filter for main trip
        date_filter = ThisYearFilter(operator)
        self._data = date_filter.data
        self.year = date_filter.year

        self.budget = TripBalanceCalculator.get_budget(self.year)

        super().__init__(ThisYearFilter(operator))

    @property
    def budget_overrun(self) -> float:
        """Budget overrun."""
        # TripBalanceCalculator creates a transaction with the overrun amount in the
        # Account.TRIP_FUNDS. Negate it because in TripBalanceCalculator the balance
        # is budget - actuals.
        return -self._data[
            (self._data["Category"] == "Travel")
            & (self._data["Account"] == Account.TRIP_FUNDS)
            & (self._data["Date"].dt.year == self.year)
        ]["Value"].sum()

    @property
    def budget_overrun_perc(self) -> float:
        """Budget overrun percentage."""
        return self.budget_overrun / (self.budget + 1e-5)


@dataclass
class CardKpi:
    """KPI card."""

    title: str
    subtitle: str = ""
    kind: str = "currency"  # "currency" | "percentage"
    value: float | Literal["N/A"] | None = None
    target: float | Literal["N/A"] | None = None
    higher_is_better: bool | None = None

    def _format_value(self, value: float | Literal["N/A"] | None) -> str:
        """Format value."""
        if value == "N/A":
            return "N/A"
        if self.kind == "currency":
            return f"R$ {value:,.0f}" if value is not None else None
        if self.kind == "percentage":
            return f"{value:.1%}" if value is not None else None
        msg = f"Unknown kind: {self.kind}"
        raise ValueError(msg)

    def _evaluate_kpi(self) -> str:
        """Evaluate KPI status and return (css_class, icon)."""
        if self.value == "N/A":
            return ""
        if self.target is None:
            return ""
        if self.target is not None and self.higher_is_better is None:
            msg = "higher_is_better must be passed"
            raise ValueError(msg)
        # Hitting the target exactly always counts as met, in either direction -
        # previously always compared with `>=` then XOR'd against higher_is_better,
        # which made value == target "not met" whenever higher_is_better was False
        # (e.g. landing exactly on a spending cap read as a failure)
        is_met = (
            self.value >= self.target
            if self.higher_is_better
            else self.value <= self.target
        )
        if is_met:
            return "kpi-card-met"
        return "kpi-card-not-met"

    def card(self) -> None:
        """Card."""
        value_actual = self._format_value(self.value)
        value_target = self._format_value(self.target)

        # Determine card status and icon
        class_delta = self._evaluate_kpi()
        icon = {
            "kpi-card-met": "✓",
            "kpi-card-not-met": "✗",
        }.get(class_delta, "")

        st.markdown(
            """
            <style>
            .kpi-card {
                margin: 0px 0px 24px 0px;
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 14px;
                padding: 16px;
                background: rgba(255, 255, 255, 0.03);
                text-align: center;
                position: relative;
            }
            .kpi-card-met {
                border-color: rgba(16, 185, 129, 0.8);
                background: rgba(16, 185, 129, 0.15);
                border-left: 4px solid rgba(16, 185, 129, 1);
            }
            .kpi-card-not-met {
                border-color: rgba(220, 38, 38, 0.8);
                background: rgba(220, 38, 38, 0.15);
                border-left: 4px solid rgba(220, 38, 38, 1);
            }
            .kpi-icon {
                position: absolute;
                top: 12px;
                right: 12px;
                font-size: 1.2rem;
                font-weight: bold;
            }
            .kpi-title {
                font-size: 1.00rem;
                opacity: 0.7;
                margin-bottom: 0px;
            }
            .kpi-subtitle {
                font-size: 0.75rem;
                opacity: 0.7;
                margin-bottom: 6px;
            }
            .kpi-value {
                font-size: 1.9rem;
                font-weight: 700;
            }
            .kpi-target {
                font-size: 0.9rem;
                opacity: 0.75;
            }
            .kpi-delta {
                margin-top: 6px;
                font-size: 0.9rem;
                font-weight: 600;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="kpi-card {class_delta}">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-title">{self.title}</div>
                <div class="kpi-subtitle">{self.subtitle}</div>
                <div class="kpi-value">{value_actual}</div>
                <div class="kpi-target">Target: <b>{value_target}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


class CardKpiCurrency(CardKpi):
    """Currency KPI card."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        value: float | Literal["N/A"] | None = None,
        target: float | Literal["N/A"] | None = None,
        *,
        higher_is_better: bool | None = None,
    ) -> None:
        """Initialize the currency KPI card."""
        super().__init__(
            title=title,
            subtitle=subtitle,
            kind="currency",
            value=value,
            target=target,
            higher_is_better=higher_is_better,
        )


class CardKpiPercentage(CardKpi):
    """Percentage KPI card."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        value: float | Literal["N/A"] | None = None,
        target: float | Literal["N/A"] | None = None,
        *,
        higher_is_better: bool | None = None,
    ) -> None:
        """Initialize the percentage KPI card."""
        super().__init__(
            title=title,
            subtitle=subtitle,
            kind="percentage",
            value=value,
            target=target,
            higher_is_better=higher_is_better,
        )
