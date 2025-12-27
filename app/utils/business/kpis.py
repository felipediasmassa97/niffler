"""Data KPIs."""

from dataclasses import dataclass

import streamlit as st


# fixit add KPIs

# fixit implement per-category monthly budget

# List of KPIs to track
# (consolidate in new screen, not in monthly or yearly view)

# Show in 2 sections (section in the left = default filter; section in the right = optional filter):
# - This month (default)
# - Enable custom date range picker (last year, last 6 months, last 3 months, last month, this month, this year, all time)

# Show in two flavors:
# - Projected (default)
# - Actual
# fixit implement projected expenses and incomes (consider pending incomes - more predictable - and pending expenses - only the ones already accounted for)

# Define target for each KPI
# fixit implement target visualization

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


@dataclass
class KpiCard:
    """KPI card."""

    title: str
    subtitle: str
    kind: str
    value: float
    target: float = None

    def card(self) -> None:
        """Card."""
        assert self.kind in {"currency", "percentage"}

        if self.kind == "currency":
            value_actual = f"R$ {self.value:,.0f}"
            value_target = f"R$ {self.target:,.0f}" if self.target is not None else None
        if self.kind == "percentage":
            value_actual = f"{self.value:.1%}"
            value_target = f"{self.target:.1%}" if self.target is not None else None

        st.markdown(
            """
            <style>
            .kpi-card {
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 14px;
                padding: 16px;
                background: rgba(255,255,255,0.03);
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


class CurrencyKpiCard(KpiCard):
    """Currency KPI card."""

    def __init__(self, title: str, subtitle: str, value: float, target: float = None):
        super().__init__(
            title=title, subtitle=subtitle, kind="currency", value=value, target=target
        )


class PercentageKpiCard(KpiCard):
    """Percentage KPI card."""

    def __init__(self, title: str, subtitle: str, value: float, target: float = None):
        super().__init__(
            title=title,
            subtitle=subtitle,
            kind="percentage",
            value=value,
            target=target,
        )
