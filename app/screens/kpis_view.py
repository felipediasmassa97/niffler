"""KPIs page definition."""

import streamlit as st

from utils.business import kpis as kp
from utils.business import rules as rl
from utils.operators import filter as fl
from utils.operators import loader as ldr


PAGE_TITLE = "KPIs View"
PAGE_URL = "kpis"


def kpis_view():
    """KPIs View page."""
    st.title("KPIs View")

    # Date filter
    # fixit add custom date range picker (long-term)
    cmp_date_filter = st.selectbox(
        "Date Range",
        options=[
            {"label": "This Month", "filter": fl.ThisMonthFilter},
        ],
        index=0,
        format_func=lambda x: x["label"],
    )
    date_filter = cmp_date_filter["filter"]

    # Load processed data
    loader = ldr.ProcessedLoader()

    # Data dilution toggle
    if st.checkbox("Dilute Costs", value=True):
        loader = rl.Diluter(loader)

    # Apply date filter
    date_filter = date_filter(loader)

    # Instantiate KPI calculators
    calc = kp.KpiCalculator(date_filter)
    calc_tr_3mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(date_filter),
        kp.KpiCalculator(fl.Last3MonthsFilter(loader)),
    )
    calc_tr_6mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(date_filter),
        kp.KpiCalculator(fl.Last6MonthsFilter(loader)),
    )
    calc_tr_12mo = kp.KpiTrendsCalculator(
        kp.KpiCalculator(date_filter),
        kp.KpiCalculator(fl.Last12MonthsFilter(loader)),
    )
    calc_cat = kp.KpiCategoryCalculator(date_filter)

    st.header("Big Picture")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(title="Total Income", value=calc.total_income).card()
        kp.CurrencyKpiCard(title="Net Income", value=calc.net_income).card()
    with cols[1]:
        kp.CurrencyKpiCard(title="Total Expenses", value=calc.total_expenses).card()
        kp.PercentageKpiCard(title="Net Income (%)", value=calc.net_income_perc).card()

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
        kp.CurrencyKpiCard(title="Fixed Income", value=calc.fixed_income).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Income (% Income)", value=calc.fixed_income_perc
        ).card()

    inc_cats = calc_cat.income_categories_sorted
    inc_by_cat = calc_cat.income_by_category
    inc_perc_by_cat = calc_cat.income_perc_by_category

    with st.expander("Per-category KPIs"):
        for category in inc_cats:
            st.markdown(f"**{category}**")

            cols = st.columns(2)
            with cols[0]:
                kp.CurrencyKpiCard(title="Income", value=inc_by_cat[category]).card()
            with cols[1]:
                kp.PercentageKpiCard(
                    title="Income (%)", value=inc_perc_by_cat[category]
                ).card()

    st.header("Expenses Breakdown")

    exp_cats = calc_cat.expenses_categories_sorted
    exp_by_cat = calc_cat.expenses_by_category

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    for idx_cat, category in enumerate(exp_cats[:3]):
        with cols[idx_cat]:
            kp.CurrencyKpiCard(title=category, value=exp_by_cat[category]).card()

    st.subheader("Fixed Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(title="Fixed Expenses", value=calc.fixed_expenses).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Fixed Expenses (% Income)", value=calc.fixed_expenses_perc
        ).card()

    exp_fixed_cats = calc_cat.expenses_fixed_categories_sorted
    exp_fixed_by_cat = calc_cat.expenses_fixed_by_category

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    for idx_cat, category in enumerate(exp_fixed_cats[:3]):
        with cols[idx_cat]:
            kp.CurrencyKpiCard(title=category, value=exp_fixed_by_cat[category]).card()

    st.subheader("Variable Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Variable Expenses", value=calc.variable_expenses
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Variable Expenses (% Income)", value=calc.variable_expenses_perc
        ).card()

    exp_variable_cats = calc_cat.expenses_variable_categories_sorted
    exp_variable_by_cat = calc_cat.expenses_variable_by_category

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    for idx_cat, category in enumerate(exp_variable_cats[:3]):
        with cols[idx_cat]:
            kp.CurrencyKpiCard(
                title=category, value=exp_variable_by_cat[category]
            ).card()

    st.subheader("Lifestyle Expenses")

    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Lifestyle Expenses", value=calc.lifestyle_expenses
        ).card()
    with cols[1]:
        kp.PercentageKpiCard(
            title="Lifestyle Expenses (% Income)", value=calc.lifestyle_expenses_perc
        ).card()

    exp_lifestyle_cats = calc_cat.expenses_lifestyle_categories_sorted
    exp_lifestyle_by_cat = calc_cat.expenses_lifestyle_by_category

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    for idx_cat, category in enumerate(exp_lifestyle_cats[:3]):
        with cols[idx_cat]:
            kp.CurrencyKpiCard(
                title=category, value=exp_lifestyle_by_cat[category]
            ).card()

    st.subheader("Category Breakdown")

    with st.expander("Per-category KPIs"):
        for category in exp_cats:
            st.markdown(f"**{category}**")

            cols = st.columns(3)
            with cols[0]:
                kp.CurrencyKpiCard(
                    title="Actual Expense", value=exp_by_cat[category]
                ).card()
            with cols[1]:
                pass
                # fixit add "Budget Overrun (%)"
                kp.PercentageKpiCard(title="Budget Overrun (%)", value=None).card()
            with cols[2]:
                pass
                # fixit add "Forecast Expense" (if this pace continues, total expenses will be XXX)
                kp.CurrencyKpiCard(title="Forecast Expense", value=None).card()

    st.subheader("Travel")

    # fixit implement travel KPIs dynamically
    # fixit always evaluate budget overrun KPIs yearly, not monthly (long-term) (instantiate a KpiCalculator with ThisYearFilter)
    cols = st.columns(2)
    with cols[0]:
        kp.CurrencyKpiCard(title="Budget Overrun", value=None).card()
    with cols[1]:
        kp.PercentageKpiCard(title="Budget Overrun (%)", value=None).card()


kpis_view_page = st.Page(kpis_view, title=PAGE_TITLE, url_path=PAGE_URL)
