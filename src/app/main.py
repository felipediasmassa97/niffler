"""Streamlit app entry point."""

import streamlit as st
from screens.kpis import kpis_page
from screens.monthly_view import monthly_view_page
from screens.patrimony import patrimony_page
from screens.validation import validation_page
from screens.yearly_view import yearly_view_page

app = st.navigation(
    [
        monthly_view_page,
        yearly_view_page,
        kpis_page,
        patrimony_page,
        validation_page,
    ],
)

# fixit validate all calculations

app.run()
