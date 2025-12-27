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

    # Split data into expenses and incomes
    expenses_raw = tr.Inverter(fl.ExpensesFilter(loader))
    incomes_raw = fl.IncomesFilter(loader)

    # Apply date filter
    all_data = fl.ThisMonthFilter(loader)
    expenses = fl.ThisMonthFilter(expenses_raw)
    incomes = fl.ThisMonthFilter(incomes_raw)

    st.subheader("General")

    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Total Incomes", subtitle="This month", value=500
        ).card()
        kp.CurrencyKpiCard(
            title="Total Expenses", subtitle="This month", value=500
        ).card()
    with cols[1]:
        kp.CurrencyKpiCard(
            title="Total Incomes", subtitle="Last 3 months", value=3 * 500
        ).card()
        kp.CurrencyKpiCard(
            title="Total Expenses", subtitle="Last 3 months", value=3 * 500
        ).card()
    with cols[2]:
        kp.CurrencyKpiCard(
            title="Total Incomes", subtitle="This year", value=12 * 500
        ).card()
        kp.CurrencyKpiCard(
            title="Total Expenses", subtitle="This year", value=12 * 500
        ).card()

    st.subheader("Net Income")

    cols = st.columns(3)
    with cols[0]:
        kp.CurrencyKpiCard(
            title="Net Income (R$)", subtitle="This month", value=500
        ).card()
        kp.PercentageKpiCard(
            title="Net Income (%)", subtitle="This month", value=0.5
        ).card()
        # fixit implement expenses inflation (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Expenses Inflation (%)", subtitle="This month", value=0.5
        # ).card()
    with cols[1]:
        kp.CurrencyKpiCard(
            title="Net Income (R$)", subtitle="Last 3 months", value=500
        ).card()
        kp.PercentageKpiCard(
            title="Net Income (%)", subtitle="Last 3 months", value=0.5
        ).card()
        # fixit implement expenses inflation (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Expenses Inflation (%)", subtitle="Last 3 months", value=0.5
        # ).card()
    with cols[2]:
        kp.CurrencyKpiCard(
            title="Net Income (R$)", subtitle="This year", value=500
        ).card()
        kp.PercentageKpiCard(
            title="Net Income (%)", subtitle="This year", value=0.5
        ).card()
        # fixit implement expenses inflation (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Expenses Inflation (%)", subtitle="This year", value=0.5
        # ).card()

    st.subheader("Income")

    cols = st.columns(3)
    with cols[0]:
        # fixit implement salary increase (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Salary Increase (%)", subtitle="This month", value=0.5
        # ).card()
        kp.PercentageKpiCard(
            title="Fixed Income (%)", subtitle="This month", value=0.5
        ).card()
    with cols[1]:
        # fixit implement salary increase (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Salary Increase (%)", subtitle="Last 3 months", value=0.5
        # ).card()
        kp.PercentageKpiCard(
            title="Fixed Income (%)", subtitle="Last 3 months", value=0.5
        ).card()
    with cols[2]:
        # fixit implement salary increase (how to calculate? time range?)
        # kp.PercentageKpiCard(
        #     title="Salary Increase (%)", subtitle="This year", value=0.5
        # ).card()
        kp.PercentageKpiCard(
            title="Fixed Income (%)", subtitle="This year", value=0.5
        ).card()

    st.subheader("Expenses")

    cols = st.columns(3)
    with cols[0]:
        pass
    with cols[1]:
        pass
    with cols[2]:
        pass

    st.subheader("Travel")

    cols = st.columns(3)
    with cols[0]:
        pass
    with cols[1]:
        pass
    with cols[2]:
        pass


kpis_view_page = st.Page(kpis_view, title=PAGE_TITLE, url_path=PAGE_URL)
