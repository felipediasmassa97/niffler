"""Validation page definition."""

import streamlit as st

# fixit add duplicate detection validation
# fixit add tier assignment validation (based on rules in tiers.py)
# fixit add dilution assignment validation (based on rules in kpis.py)


def validation() -> None:
    """Render the validation page."""
    st.title("Validation")
    st.write("This is the Validation page.")

    # fixit long-term implement validation content


validation_page = st.Page(validation, title="Validation", url_path="validation")
