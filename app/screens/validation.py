"""Validation page definition."""

import streamlit as st


def validation():
    """Validation page."""
    st.title("Validation")
    st.write("This is the Validation page.")

    # fixit long-term implement validation content


validation_page = st.Page(validation, title="Validation", url_path="validation")
