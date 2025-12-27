"""KPIs page definition."""

import streamlit as st

from utils.business import rules as rl
from utils.business import kpis as kp
from utils.operators import filter as fl
from utils.operators import loader as ldr
from utils.operators import transformer as tr


PAGE_TITLE = "KPIs View"
PAGE_URL = "kpis"


def kpis_view():
    """KPIs View page."""
    st.title("KPIs View")

    # Load processed data
    loader = ldr.ProcessedLoader()

    # Data dilution toggle
    if st.checkbox("Dilute Costs", value=True):
        loader = rl.Diluter(loader)

    # Apply date filter and instantiate KPI calculator
    calc = kp.KpiCalculator(fl.ThisMonthFilter(loader))

    st.header("Big Picture")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Total Income", subtitle="This month", value=calc.get_total_income()
        ).card()
    with cols[1]:
        kp.CurrencyKpiCard(
            title="Total Expenses",
            subtitle="This month",
            value=calc.get_total_expenses(),
        ).card()

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Net Income", subtitle="This month", value=calc.get_net_income()
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Net Income (%)",
            subtitle="This month",
            value=calc.get_net_income_percentage(),
        ).card()

    st.header("Time Trends")

    cols = st.columns(3)
    with cols[0]:
        kp.PercentageKpiCard(
            title="Income Increase (%)", subtitle="This month", value=0.5
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Expenses Increase (%)", subtitle="This month", value=0.5
        ).card()
    with cols[2]:
        kp.PercentageKpiCard(
            title="Expenses Inflation (%)", subtitle="This month", value=0.5
        ).card()

    st.header("Income Breakdown")

    st.subheader("Fixed Income")
    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Fixed Income", subtitle="This month", value=500
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Income (%)", subtitle="This month", value=0.5
        ).card()

    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    with st.expander("See per-category KPIs"):
        categories = ["Foo", "Bar", "Baz"]

        for category in categories:
            st.markdown(f"**{category}**")

            cols = st.columns(2)
            with cols[0]:
                kp.CurrencyKpiCard(
                    title="Actual Income", subtitle="This month", value=500
                ).card()
            with cols[1]:
                kp.PercentageKpiCard(
                    title="Percentage of Total Income (%)",
                    subtitle="This month",
                    value=0.5,
                ).card()

    st.header("Expenses Breakdown")

    st.subheader("Fixed Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Fixed Expenses", subtitle="This month", value=500
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Expenses (%)", subtitle="This month", value=0.5
        ).card()

    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    st.subheader("Variable Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Variable Expenses", subtitle="This month", value=500
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Variable Expenses (%)", subtitle="This month", value=0.5
        ).card()

    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    st.subheader("Lifestyle Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Lifestyle Expenses", subtitle="This month", value=500
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Lifestyle Expenses (%)", subtitle="This month", value=0.5
        ).card()

    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    st.subheader("Category Breakdown")

    with st.expander("See per-category KPIs"):
        categories = ["Foo", "Bar", "Baz"]

        for category in categories:
            st.markdown(f"**{category}**")

            cols = st.columns(3)
            with cols[0]:
                kp.CurrencyKpiCard(
                    title="Actual Expense", subtitle="This month", value=500
                ).card()
            with cols[1]:
                pass
                # fixit add "Budget Overrun (%)"
                kp.PercentageKpiCard(
                    title="Budget Overrun (%)", subtitle="This month", value=0.5
                ).card()
            with cols[2]:
                pass
                # fixit add "Forecast Expense" (if this pace continues, total expenses will be XXX)
                kp.CurrencyKpiCard(
                    title="Forecast Expense", subtitle="This month", value=500
                ).card()

    st.subheader("Travel")

    # fixit always evaluate budget overrun KPIs yearly, not monthly (long-term)
    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Budget Overrun", subtitle="This year", value=500
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Budget Overrun (%)", subtitle="This year", value=0.5
        ).card()


kpis_view_page = st.Page(kpis_view, title=PAGE_TITLE, url_path=PAGE_URL)
