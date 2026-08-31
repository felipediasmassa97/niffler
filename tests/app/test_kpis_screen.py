"""Value-level regression test for the KPIs page's elapsed-time card title.

Unlike test_screens.py (deliberately scoped to "renders without raising" only), this
asserts an actual rendered value - regression coverage for a bug where the elapsed-time
card's title was hardcoded to "Month Advancement (%)" regardless of the selected date
range.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[2] / "src" / "app"
MAIN_PY = APP_DIR / "main.py"
SECRETS_PATH = APP_DIR / ".streamlit" / "secrets.toml"


def test_elapsed_date_card_title_follows_the_selected_date_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The elapsed-time card's title names the selected range, not a fixed "Month"."""
    if not SECRETS_PATH.exists():
        pytest.fail(
            f"No {SECRETS_PATH} - set up AWS secrets to run UI screen tests "
            "(see infra/README.md)"
        )
    monkeypatch.chdir(APP_DIR)

    at = AppTest.from_file(str(MAIN_PY), default_timeout=60)
    at.run()
    at.switch_page("screens/kpis.py")
    at.run()

    at.selectbox[0].select_index(3).run()  # "Last Year"

    titles = " ".join(md.value for md in at.markdown if "kpi-title" in md.value)
    assert "Last Year Advancement" in titles
    assert "Month Advancement" not in titles
