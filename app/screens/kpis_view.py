"""KPIs page definition."""

import streamlit as st

from utils.business import rules as rl
from utils.business import kpis as kp
from utils.operators import filter as fl
from utils.operators import loader as ldr


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
    calc_tr_3mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(fl.ThisMonthFilter(loader)),
        kp.KpiCalculator(fl.Last3MonthsFilter(loader)),
    )
    calc_tr_6mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(fl.ThisMonthFilter(loader)),
        kp.KpiCalculator(fl.Last6MonthsFilter(loader)),
    )
    calc_tr_12mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(fl.ThisMonthFilter(loader)),
        kp.KpiCalculator(fl.Last12MonthsFilter(loader)),
    )

    st.header("Big Picture")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Total Income", subtitle="This month", value=calc.total_income
        ).card()
        kp.CurrencyKpiCard(
            title="Net Income", subtitle="This month", value=calc.net_income
        ).card()
    with cols[1]:
        kp.CurrencyKpiCard(
            title="Total Expenses", subtitle="This month", value=calc.total_expenses
        ).card()
        kp.PercentageKpiCard(
            title="Net Income (%)", subtitle="This month", value=calc.net_income_perc
        ).card()

    st.header("Time Trends")

    cols = st.columns(3)
    with cols[0]:
        kp.PercentageKpiCard(
            title="Income Increase (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.income_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Increase (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.expenses_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.expenses_inflation_perc,
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Income Increase (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.income_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Increase (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.expenses_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.expenses_inflation_perc,
        ).card()
    with cols[2]:
        kp.PercentageKpiCard(
            title="Income Increase (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.income_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Increase (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.expenses_increase_perc,
        ).card()
        kp.PercentageKpiCard(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.expenses_inflation_perc,
        ).card()

    st.header("Income Breakdown")

    st.subheader("Fixed Income")
    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Fixed Income",
            subtitle="This month",
            value=calc.fixed_income,
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Income (% Income)",
            subtitle="This month",
            value=calc.fixed_income_perc,
        ).card()

    # fixit implement top categories dynamically
    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    # fixit implement per-category KPIs dynamically
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
                    title="Actual Income (% Income)", subtitle="This month", value=0.5
                ).card()

    st.header("Expenses Breakdown")

    # fixit implement top categories (all) dynamically
    st.markdown("**Top 3 Categories**")
    cats = ["Foo", "Bar", "Baz"]
    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(title=cats[0], subtitle="This month", value=500).card()
    with cols[1]:
        kp.CurrencyKpiCard(title=cats[1], subtitle="This month", value=500).card()
    with cols[2]:
        kp.CurrencyKpiCard(title=cats[2], subtitle="This month", value=500).card()

    st.subheader("Fixed Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Fixed Expenses",
            subtitle="This month",
            value=calc.fixed_expenses,
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Expenses (% Income)",
            subtitle="This month",
            value=calc.fixed_expenses_perc,
        ).card()

    # fixit implement top categories (fixed) dynamically
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
            title="Variable Expenses",
            subtitle="This month",
            value=calc.variable_expenses,
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Variable Expenses (% Income)",
            subtitle="This month",
            value=calc.variable_expenses_perc,
        ).card()

    # fixit implement top categories (variable) dynamically
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
            title="Lifestyle Expenses",
            subtitle="This month",
            value=calc.lifestyle_expenses,
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Lifestyle Expenses (% Income)",
            subtitle="This month",
            value=calc.lifestyle_expenses_perc,
        ).card()

    # fixit implement top categories (lifestyle) dynamically
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

    # fixit implement per-category KPIs dynamically
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

    # fixit implement travel KPIs dynamically
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
