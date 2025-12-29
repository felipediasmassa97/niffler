"""Data KPIs."""

import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import pandas as pd
import streamlit as st

from utils.business.budget import CATEGORY_BUDGETS
from utils.business.forecast import CATEGORY_MUST_PROJECT
from utils.business.travel import TripBalanceCalculator
from utils.operators import Operator
from utils.operators.filter import ThisYearFilter


# List of KPIs to track
# (consolidate in new screen, not in monthly or yearly view)

# Show in 2 sections (section in the left = default filter; section in the right = optional filter):
# - This month (default)
# - Enable custom date range picker (last year, last 6 months, last 3 months, last month, this month, this year, all time)

# Define target for each KPI
# fixit define targets for each KPI (long-term)
# fixit implement target and delta visualization

# Big Picture:
# - Total income
# - Total expenses
# - Net Income Amount (absolute value)
# - Net Income Percentage (Net Income / Total Income)
#   - Target: Beginner = 10%-20%, Ideal = 25%-40%, Elite = 50%+

# Time Trends:
# - Expenses Inflation
#   - Income inflation vs expenses inflation: this time range (filter) vs last 3 / 6 / 12 months (show all 3 to see different trends)
#   - Target: Beginner = <5%, Ideal = <3%, Elite = <0%
# - Incomes increase: this time range (filter) vs last 3 / 6 / 12 months (show all 3 to see different trends)
# - Expenses increase: this time range (filter) vs last 3 / 6 / 12 months (show all 3 to see different trends)
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

# fixit implement investments KPIs (long-term)
# fixit implement KPI based on how much of income is invested monthly (long-term)
# fixit implement "Months of Runway" KPI (long-term)
# Months of Runway = Emergency Fund / Average Monthly Expenses Over Last 6 Months
# - Target: Beginner: 3 months, Strong: 6 months, Excellent: 12 months
# Investments:
# -
# -
# -


class KpiCalculator:
    """KPI calculator."""

    def __init__(self, operator: Operator) -> None:
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
        return (
            self.expenses_increase_perc - self.income_increase_perc
        ) / self.income_increase_perc


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
            for category in self.income["Category"].unique()
        }

    @property
    def income_perc_by_category(self) -> dict[str, float]:
        """Income percentage by category."""
        return {
            category: self.get_category_data(self.income, category)["Value"].sum()
            / (self.total_income + 1e-5)
            for category in self.income["Category"].unique()
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
            for category in self.expenses["Category"].unique()
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
    def expenses_forecast_by_category(self) -> dict[str, float]:
        """Expenses forecast by category."""
        today = datetime.today()
        elapsed_days = today.day
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        return {
            category: abs(
                self.get_category_data(self.expenses, category)["Value"].sum()
            )
            / (elapsed_days / days_in_month)
            if must_project is True
            else "N/A"
            for category, must_project in CATEGORY_MUST_PROJECT.items()
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
            for category in self.expenses["Category"].unique()
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
            for category in self.expenses["Category"].unique()
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
            for category in self.expenses["Category"].unique()
        }


class KpiMainTripCalculator(KpiCalculator):
    """KPI main trip calculator."""

    def __init__(self, operator: Operator) -> None:
        # Enforce this year filter for main trip
        date_filter = ThisYearFilter(operator)
        self.year = date_filter.year

        self.trip_calc = TripBalanceCalculator(date_filter)

        super().__init__(ThisYearFilter(operator))

    @property
    def budget_overrun(self) -> float:
        """Budget overrun."""
        return self.trip_calc.sum_actuals(self.year) - self.trip_calc.get_budget(
            self.year
        )

    @property
    def budget_overrun_perc(self) -> float:
        """Budget overrun percentage."""
        return self.budget_overrun / (self.trip_calc.get_budget(self.year) + 1e-5)


@dataclass
class CardKpi:
    """KPI card."""

    title: str
    subtitle: str = ""
    kind: str = "currency"  # "currency" | "percentage"
    value: float = None
    target: float = None

    def _format_value(self, value: float | Literal["N/A"] | None) -> str:
        """Format value."""
        if value == "N/A":
            return "N/A"
        if self.kind == "currency":
            return f"R$ {value:,.0f}" if value is not None else None
        if self.kind == "percentage":
            return f"{value:.1%}" if value is not None else None
        raise ValueError(f"Unknown kind: {self.kind}")

    def card(self) -> None:
        """Card."""
        value_actual = self._format_value(self.value)
        value_target = self._format_value(self.target)

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

        # fixit implement delta vs target (long-term)
        # fixit remove target if not passed
        st.markdown(
            f"""
            <div class="kpi-card">
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
        self, title: str, subtitle: str = "", value: float = None, target: float = None
    ):
        super().__init__(
            title=title,
            subtitle=subtitle,
            kind="currency",
            value=value,
            target=target,
        )


class CardKpiPercentage(CardKpi):
    """Percentage KPI card."""

    def __init__(
        self, title: str, subtitle: str = "", value: float = None, target: float = None
    ):
        super().__init__(
            title=title,
            subtitle=subtitle,
            kind="percentage",
            value=value,
            target=target,
        )
