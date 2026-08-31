"""Shared fixtures for the business-rule test suite.

These tests exercise `utils/business/*` directly against hand-built DataFrames matching
`PreProcessedLoader`'s output shape (see `utils/operators/loader.py`), bypassing
`Loader`/S3 entirely - the pure-logic rules (dilution, tiers, budget, most KPIs) never
touch the network. Only the travel/trip-fund rule needs S3 mocking, since
`TripBalanceCalculator` reads the "Transfers" sheet via `get_latest_snapshot()`.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
import pytest
from utils.business.travel import TripBalanceCalculator
from utils.operators import Operator


class FakeOperator(Operator):
    """Wraps a hand-built DataFrame as an `Operator`, bypassing `Loader`/S3 entirely."""

    def __init__(self, data: pd.DataFrame) -> None:
        """Initialize with the given data."""
        self._data = data

    @property
    def data(self) -> pd.DataFrame:
        """Return the wrapped data."""
        return self._data


def make_transactions(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a DataFrame matching `DilutionAssigner`'s output shape.

    Each row may omit any column; sensible defaults fill in the rest so a test only
    has to specify the fields relevant to the rule under test. `Month` is derived from
    `Date`, matching what `PreProcessedLoader` itself computes. `Dilution` defaults to
    `False` since `TripBalanceCalculator` (the last pipeline stage) expects it already
    assigned by `DilutionAssigner` - a real bool-dtype column, not an absent one.
    """
    defaults = {
        "Date": pd.Timestamp.now().normalize(),
        "Description": "Test transaction",
        "Value": 0.0,
        "Account": "Carteira",
        "Status": "Paid",
        "Category": "Unknown",
        "Subcategory": None,
        "Tags": [],
        "Dilution": False,
    }
    columns = [*defaults, "Month"]
    if not rows:
        return pd.DataFrame(columns=columns)

    full_rows = [{**defaults, **row} for row in rows]
    data = pd.DataFrame(full_rows)
    data["Date"] = pd.to_datetime(data["Date"])
    data["Month"] = data["Date"].dt.to_period("M").dt.to_timestamp()
    return data


@pytest.fixture
def make_operator() -> Any:
    """Build a `FakeOperator` from a list of row dicts."""

    def _make(rows: list[dict[str, Any]]) -> FakeOperator:
        return FakeOperator(make_transactions(rows))

    return _make


@pytest.fixture(autouse=True)
def _clear_transfer_cache() -> None:
    """Clear TripBalanceCalculator's cached Transfers-sheet load before each test.

    `_load_transfer_data` is `@cache`d at the class level (process lifetime), so a
    stale result from one test would otherwise leak into the next.
    """
    TripBalanceCalculator._load_transfer_data.cache_clear()  # noqa: SLF001


@pytest.fixture
def mock_transfers(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Make `TripBalanceCalculator` read a fake Transfers sheet.

    Patches `get_latest_snapshot` directly at its import site in `utils.business.travel`
    (rather than mocking boto3/S3), returning an in-memory workbook built from the given
    rows - `["Date", "Conta origem", "Conta destino", "Value", "Tags"]`, matching the
    real Transfers sheet.
    """

    def _mock(transfer_rows: list[dict[str, Any]]) -> None:
        columns = ["Date", "Conta origem", "Conta destino", "Value", "Tags"]
        transfers_df = pd.DataFrame(transfer_rows, columns=columns)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            transfers_df.to_excel(writer, sheet_name="Transfers", index=False)
        monkeypatch.setattr(
            "utils.business.travel.get_latest_snapshot", buffer.getvalue
        )

    return _mock


@pytest.fixture
def freeze_today(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Fix `pd.Timestamp.now()` for date-dependent KPI rules.

    `DateFilter`/`ThisYearFilter` (and `KpiDateAdvancementCalculator`) call
    `pd.Timestamp.now()`/`.today()` directly - without freezing this, "this year" and
    "elapsed date" drift as real time passes.
    """

    def _freeze(today: str) -> None:
        fixed = pd.Timestamp(today)
        monkeypatch.setattr(
            pd.Timestamp,
            "now",
            classmethod(lambda cls, tz=None: fixed),  # noqa: ARG005
        )
        monkeypatch.setattr(
            pd.Timestamp,
            "today",
            classmethod(lambda cls, tz=None: fixed),  # noqa: ARG005
        )

    return _freeze


@pytest.fixture
def freeze_year(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Fix "today" for `TripBalanceCalculator`'s year loop.

    `_adjust_data` loops `range(2024, datetime.now(tz=UTC).year + 1)` - without
    freezing this, the set of years exercised silently grows every January.
    """

    def _freeze(year: int) -> None:
        class _FixedDatetime(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:
                return cls(year, 6, 15, tzinfo=tz)

        monkeypatch.setattr("utils.business.travel.datetime", _FixedDatetime)

    return _freeze
