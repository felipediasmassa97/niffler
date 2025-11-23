"""Monthly View page definition."""

import streamlit as st

from utils.charts import BarChart
from utils.data.aggregator import MonthlyCategoryAggregator
from utils.data.filterer import ExpensesFilterer, IncomesFilterer
from utils.data.loader import Loader


def monthly_view():
    """Monthly View page."""
    st.title("Monthly View")

    # Load data from report
    loader = Loader()
    expenses = ExpensesFilterer(loader)
    incomes = IncomesFilterer(loader)

    # Monthly trend

    ## Filters:
    ## - Last 12 months (default)
    ## - This year
    ## - All time
    ## - Custom range

    ## Total monthly incomes, expenses and net income

    ## Fixed, variable and lifestyle costs

    ## Per-category expenses breakdown
    st.plotly_chart(
        BarChart(
            operator=MonthlyCategoryAggregator(expenses),
            column_x="Month",
            column_y="Value",
            column_cat="Category",
            title="Monthly Expenses by Category",
        ).chart
    )

    ## Per-category incomes breakdown
    st.plotly_chart(
        BarChart(
            operator=MonthlyCategoryAggregator(incomes),
            column_x="Month",
            column_y="Value",
            column_cat="Category",
            title="Monthly Incomes by Category",
        ).chart
    )

    # Period summary

    ## Filters:
    ## - Current month (default)
    ## - Last 3 months
    ## - This year
    ## - All time
    ## - Custom range

    ## Fixed, variable and lifestyle costs

    ## Per-category expenses breakdown

    ## Per-category incomes breakdown


monthly_view_page = st.Page(
    monthly_view,
    title="Monthly View",
    url_path="monthly",
)
