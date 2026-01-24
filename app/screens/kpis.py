"""KPIs page definition."""

import streamlit as st

from utils.business.budget import CATEGORY_BUDGETS
from utils.business.dilution import Diluter
from utils.business.kpis import (
    CardKpiCurrency,
    CardKpiPercentage,
    KpiCalculator,
    KpiTrendsCalculator,
    KpiCategoryCalculator,
    KpiVrCalculator,
    KpiVaCalculator,
    KpiMainTripCalculator,
)
from utils.operators import filter as fl
from utils.operators import loader as ldr


PAGE_TITLE = "KPIs"
PAGE_URL = "kpis"

# fixit collab add real targets
TARGET_TOTAL_INCOME = None
TARGET_TOTAL_EXPENSES = None
TARGET_NET_INCOME = None
TARGET_NET_INCOME_PERC = None

# fixit collab add real targets
TARGET_INCOME_INCREASE_PERC = None
TARGET_EXPENSES_INCREASE_PERC = None
TARGET_EXPENSES_INFLATION_PERC = None

TARGET_TRIP_BUDGET_OVERRUN = 0
TARGET_TRIP_BUDGET_OVERRUN_PERC = 0


def kpis():
    """KPIs page."""
    st.title("KPIs")

    # Date filter
    # fixit long-term add custom date range picker
    cmp_date_filter = st.selectbox(
        "Date Range",
        options=[
            {"label": "This Month", "filter": fl.ThisMonthFilter},
            {"label": "Last Month", "filter": fl.LastMonthFilter},
            {"label": "Last 3 Months", "filter": fl.Last3MonthsFilter},
        ],
        index=0,
        format_func=lambda x: x["label"],
    )

    # Load processed data
    loader = ldr.ProcessedLoader()

    # Data dilution toggle
    if st.checkbox("Dilute Costs", value=True):
        loader = Diluter(loader)

    # Apply date filter
    date_filter = cmp_date_filter["filter"](loader)

    # Instantiate KPI calculators
    calc = KpiCalculator(date_filter)
    calc_tr_3mo = KpiTrendsCalculator(
        KpiCalculator(date_filter),
        KpiCalculator(fl.Last3MonthsFilter(loader)),
    )
    calc_tr_6mo = KpiTrendsCalculator(
        KpiCalculator(date_filter),
        KpiCalculator(fl.Last6MonthsFilter(loader)),
    )
    calc_tr_12mo = KpiTrendsCalculator(
        KpiCalculator(date_filter),
        KpiCalculator(fl.Last12MonthsFilter(loader)),
    )
    calc_cat = KpiCategoryCalculator(date_filter)
    calc_vr = KpiVrCalculator(date_filter)
    calc_va = KpiVaCalculator(date_filter)
    calc_trip = KpiMainTripCalculator(loader)  # do not filter by date for trip budget

    st.header("Big Picture")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="Total Income",
            value=calc.total_income,
            target=TARGET_TOTAL_INCOME,
            higher_is_better=True,
        ).card()
    with cols[1]:
        CardKpiCurrency(
            title="Total Expenses",
            value=calc.total_expenses,
            target=TARGET_TOTAL_EXPENSES,
            higher_is_better=False,
        ).card()

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="Net Income",
            value=calc.net_income,
            target=TARGET_NET_INCOME,
            higher_is_better=True,
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="Net Income (%)",
            value=calc.net_income_perc,
            target=TARGET_NET_INCOME_PERC,
            higher_is_better=True,
        ).card()

    st.header("Time Trends")

    cols = st.columns(3)
    with cols[0]:
        CardKpiPercentage(
            title="Income Increase (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.income_increase_perc,
            target=TARGET_INCOME_INCREASE_PERC,
            higher_is_better=True,
        ).card()
        CardKpiPercentage(
            title="Expenses Increase (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.expenses_increase_perc,
            target=TARGET_EXPENSES_INCREASE_PERC,
            higher_is_better=False,
        ).card()
        CardKpiPercentage(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 3 months average",
            value=calc_tr_3mo.expenses_inflation_perc,
            target=TARGET_EXPENSES_INFLATION_PERC,
            higher_is_better=False,
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="Income Increase (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.income_increase_perc,
            target=TARGET_INCOME_INCREASE_PERC,
            higher_is_better=True,
        ).card()
        CardKpiPercentage(
            title="Expenses Increase (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.expenses_increase_perc,
            target=TARGET_EXPENSES_INCREASE_PERC,
            higher_is_better=False,
        ).card()
        CardKpiPercentage(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 6 months average",
            value=calc_tr_6mo.expenses_inflation_perc,
            target=TARGET_EXPENSES_INFLATION_PERC,
            higher_is_better=False,
        ).card()
    with cols[2]:
        CardKpiPercentage(
            title="Income Increase (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.income_increase_perc,
            target=TARGET_INCOME_INCREASE_PERC,
            higher_is_better=True,
        ).card()
        CardKpiPercentage(
            title="Expenses Increase (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.expenses_increase_perc,
            target=TARGET_EXPENSES_INCREASE_PERC,
            higher_is_better=False,
        ).card()
        CardKpiPercentage(
            title="Expenses Inflation (%)",
            subtitle="Compared to last 12 months average",
            value=calc_tr_12mo.expenses_inflation_perc,
            target=TARGET_EXPENSES_INFLATION_PERC,
            higher_is_better=False,
        ).card()

    st.header("Income Breakdown")

    st.subheader("Fixed Income")
    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(title="Fixed Income", value=calc.fixed_income).card()
    with cols[1]:
        CardKpiPercentage(
            title="Fixed Income (% Income)", value=calc.fixed_income_perc
        ).card()

    inc_cats = calc_cat.income_categories_sorted
    with st.expander("Per-category KPIs"):
        for cat in inc_cats:
            st.markdown(f"**{cat}**")

            cols = st.columns(2)
            with cols[0]:
                CardKpiCurrency(
                    title="Income", value=calc_cat.income_by_category[cat]
                ).card()
            with cols[1]:
                CardKpiPercentage(
                    title="Income (%)", value=calc_cat.income_perc_by_category[cat]
                ).card()

    st.header("Expenses Breakdown")

    exp_cats = calc_cat.expenses_categories_sorted
    exp_by_cat = calc_cat.expenses_by_category

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    for idx_cat, cat in enumerate(exp_cats[:3]):
        with cols[idx_cat]:
            CardKpiCurrency(title=cat, value=exp_by_cat[cat]).card()

    st.subheader("Fixed Expenses")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(title="Fixed Expenses", value=calc.fixed_expenses).card()
    with cols[1]:
        CardKpiPercentage(
            title="Fixed Expenses (% Income)", value=calc.fixed_expenses_perc
        ).card()

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    exp_fixed_cats = calc_cat.expenses_fixed_categories_sorted
    for idx_cat, cat in enumerate(exp_fixed_cats[:3]):
        with cols[idx_cat]:
            CardKpiCurrency(
                title=cat, value=calc_cat.expenses_fixed_by_category[cat]
            ).card()

    st.subheader("Variable Expenses")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(title="Variable Expenses", value=calc.variable_expenses).card()
    with cols[1]:
        CardKpiPercentage(
            title="Variable Expenses (% Income)", value=calc.variable_expenses_perc
        ).card()

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    exp_variable_cats = calc_cat.expenses_variable_categories_sorted
    for idx_cat, cat in enumerate(exp_variable_cats[:3]):
        with cols[idx_cat]:
            CardKpiCurrency(
                title=cat, value=calc_cat.expenses_variable_by_category[cat]
            ).card()

    st.subheader("Lifestyle Expenses")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="Lifestyle Expenses", value=calc.lifestyle_expenses
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="Lifestyle Expenses (% Income)", value=calc.lifestyle_expenses_perc
        ).card()

    st.markdown("**Top 3 Categories**")
    cols = st.columns(3)
    exp_lifestyle_cats = calc_cat.expenses_lifestyle_categories_sorted
    for idx_cat, cat in enumerate(exp_lifestyle_cats[:3]):
        with cols[idx_cat]:
            CardKpiCurrency(
                title=cat, value=calc_cat.expenses_lifestyle_by_category[cat]
            ).card()

    st.subheader("Category Breakdown")

    with st.expander("Per-category KPIs"):
        for cat in exp_cats:
            st.markdown(f"**{cat}**")

            cols = st.columns(3)
            with cols[0]:
                CardKpiCurrency(
                    title="Actual Expense",
                    value=exp_by_cat[cat],
                    target=CATEGORY_BUDGETS[cat],
                    higher_is_better=False,
                ).card()
            with cols[1]:
                CardKpiPercentage(
                    title="Budget Utilization (%)",
                    value=calc_cat.expenses_budget_utilization_perc_by_category[cat],
                    target=1,
                    higher_is_better=False,
                ).card()
            with cols[2]:
                CardKpiCurrency(
                    title="Forecast Expense",
                    value=calc_cat.expenses_forecast_by_category[cat],
                    target=CATEGORY_BUDGETS[cat],
                    higher_is_better=False,
                ).card()

    st.subheader("Vouchers")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="VR Consumption",
            value=calc_vr.voucher_consumption,
            target=calc_vr.voucher_budget,
            higher_is_better=False,
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="VR Consumption (%)",
            value=calc_vr.voucher_consumption_perc,
            target=1,
            higher_is_better=False,
        ).card()

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="VA Consumption",
            value=calc_va.voucher_consumption,
            target=calc_va.voucher_budget,
            higher_is_better=False,
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="VA Consumption (%)",
            value=calc_va.voucher_consumption_perc,
            target=1,
            higher_is_better=False,
        ).card()

    st.subheader("Travel")

    cols = st.columns(2)
    with cols[0]:
        CardKpiCurrency(
            title="Budget Overrun",
            subtitle="This year",
            value=calc_trip.budget_overrun,
            target=TARGET_TRIP_BUDGET_OVERRUN,
            higher_is_better=False,
        ).card()
    with cols[1]:
        CardKpiPercentage(
            title="Budget Overrun (%)",
            subtitle="This year",
            value=calc_trip.budget_overrun_perc,
            target=TARGET_TRIP_BUDGET_OVERRUN_PERC,
            higher_is_better=False,
        ).card()


kpis_page = st.Page(kpis, title=PAGE_TITLE, url_path=PAGE_URL)
