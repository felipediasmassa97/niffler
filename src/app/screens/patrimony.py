"""Patrimony page definition."""

import streamlit as st


def patrimony():
    """Patrimony page."""
    st.title("Patrimony")
    st.write("This is the Patrimony page.")

    # fixit long-term implement patrimony content


patrimony_page = st.Page(patrimony, title="Patrimony", url_path="patrimony")
