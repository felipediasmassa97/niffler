"""Monthly View page definition."""

import streamlit as st

from utils import charts as ch
from utils.business.dilution import Diluter
from utils.operators import aggregator as agg
from utils.operators import filter as fl
from utils.operators import loader as ldr
from utils.operators import transformer as tr


PAGE_TITLE = "Monthly View"
PAGE_URL = "monthly"

TIER_ORDER = ["Fixed", "Variable", "Lifestyle"]
TIER_COLORS = {"Fixed": "#1f77b4", "Variable": "#ff7f0e", "Lifestyle": "#2ca02c"}


def monthly_view():
    """Monthly View page."""
    st.title("Monthly View")

    # Date filter
    # fixit long-term add custom date range picker
    cmp_date_filter = st.selectbox(
        "Date Range",
        options=[
            {"label": "This Year", "filter": fl.ThisYearFilter},
            {"label": "This Month", "filter": fl.ThisMonthFilter},
            {"label": "Last Month", "filter": fl.LastMonthFilter},
            {"label": "Last 3 Months", "filter": fl.Last3MonthsFilter},
            {"label": "Last 12 Months", "filter": fl.Last12MonthsFilter},
            {"label": "Last Year", "filter": fl.LastYearFilter},
            {"label": "All Time", "filter": fl.AllTimeFilter},
        ],
        index=0,
        format_func=lambda x: x["label"],
    )
    date_filter = cmp_date_filter["filter"]

    # Load processed data
    loader = ldr.ProcessedLoader()

    # Data dilution toggle
    if st.checkbox("Dilute Costs", value=True):
        loader = Diluter(loader)

    # Split data into expenses and incomes
    expenses_raw = tr.Inverter(fl.ExpensesFilter(loader))
    incomes_raw = fl.IncomesFilter(loader)

    # Apply date filter
    all_data = date_filter(loader)
    expenses = date_filter(expenses_raw)
    incomes = date_filter(incomes_raw)

    st.subheader("Monthly Trend")

    # Total monthly incomes, expenses and net income
    st.plotly_chart(
        ch.MonthlyTrendGroupedBarChart(
            operator=tr.Merger(
                # Add labels to distinguish the three series in chart
                tr.LabelAssigner(
                    agg.MonthlyAggregator(incomes),
                    label_col="Type",
                    label_val="Income",
                ),
                tr.LabelAssigner(
                    agg.MonthlyAggregator(expenses),
                    label_col="Type",
                    label_val="Expense",
                ),
                tr.LabelAssigner(
                    agg.MonthlyAggregator(all_data),
                    label_col="Type",
                    label_val="Net Income",
                ),
            ),
            column_x="Month",
            column_y="Value",
            column_cat="Type",
            column_text="Value",
            column_cat_orders={"Type": ["Income", "Expense", "Net Income"]},
            title="Monthly Balance",
        ).chart
    )

    # Per-tier expenses breakdown
    st.plotly_chart(
        ch.MonthlyTrendSimpleBarChart(
            operator=agg.MonthlyTierAggregator(expenses),
            column_x="Month",
            column_y="Value",
            column_cat="Tier",
            column_cat_orders={"Tier": TIER_ORDER},
            column_cat_colors=TIER_COLORS,
            title="Monthly Expenses by Tier",
        ).chart
    )

    # Per-category expenses breakdown
    st.plotly_chart(
        ch.MonthlyTrendSimpleBarChart(
            operator=agg.MonthlyCategoryAggregator(expenses),
            column_x="Month",
            column_y="Value",
            column_cat="Category",
            title="Monthly Expenses by Category",
        ).chart
    )

    # Per-tier incomes breakdown
    st.plotly_chart(
        ch.MonthlyTrendSimpleBarChart(
            operator=agg.MonthlyTierAggregator(incomes),
            column_x="Month",
            column_y="Value",
            column_cat="Tier",
            column_cat_orders={"Tier": TIER_ORDER},
            column_cat_colors=TIER_COLORS,
            title="Monthly Incomes by Tier",
        ).chart
    )

    # Per-category incomes breakdown
    st.plotly_chart(
        ch.MonthlyTrendSimpleBarChart(
            operator=agg.MonthlyCategoryAggregator(incomes),
            column_x="Month",
            column_y="Value",
            column_cat="Category",
            title="Monthly Incomes by Category",
        ).chart
    )

    st.subheader("Period Summary")

    # Per-tier expenses breakdown
    st.plotly_chart(
        ch.PeriodSummarySimpleBarChart(
            operator=agg.TierAggregator(expenses),
            column_x="Tier",
            column_y="Value",
            column_cat_orders={"Tier": TIER_ORDER},
            column_cat_colors=TIER_COLORS,
            title="All Expenses by Tier",
        ).chart
    )

    # Per-category expenses breakdown
    st.plotly_chart(
        ch.PeriodSummarySimpleBarChart(
            operator=agg.CategoryAggregator(expenses),
            column_x="Category",
            column_y="Value",
            title="All Expenses by Category",
        ).chart
    )

    # Per-tier incomes breakdown
    st.plotly_chart(
        ch.PeriodSummarySimpleBarChart(
            operator=agg.TierAggregator(incomes),
            column_x="Tier",
            column_y="Value",
            column_cat_orders={"Tier": TIER_ORDER},
            column_cat_colors=TIER_COLORS,
            title="All Incomes by Tier",
        ).chart
    )

    # Per-category incomes breakdown
    st.plotly_chart(
        ch.PeriodSummarySimpleBarChart(
            operator=agg.CategoryAggregator(incomes),
            column_x="Category",
            column_y="Value",
            title="All Incomes by Category",
        ).chart
    )

    st.dataframe(all_data.data)


monthly_view_page = st.Page(monthly_view, title=PAGE_TITLE, url_path=PAGE_URL)
