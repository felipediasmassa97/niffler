"""Yearly View page definition."""

import streamlit as st


def yearly_view():
    """Yearly View page."""
    st.title("Yearly View")
    st.write("This is the Yearly View page.")

    # fixit implement yearly view content (long-term)


yearly_view_page = st.Page(yearly_view, title="Yearly View", url_path="yearly")
