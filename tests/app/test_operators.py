"""Tests for the generic operator pipeline (utils/operators/*).

Not business rules - these are the data-shape/grouping mechanics every rule builds on.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from utils.operators import Operator
from utils.operators import aggregator as agg
from utils.operators.loader import PreProcessedLoader


class _FakeOperator(Operator):
    """Wraps a hand-built DataFrame as an `Operator`."""

    def __init__(self, data: pd.DataFrame) -> None:
        """Initialize with the given data."""
        self._data = data

    @property
    def data(self) -> pd.DataFrame:
        """Return the wrapped data."""
        return self._data


def test_preprocessed_loader_adds_year_and_month_columns() -> None:
    """Year/Month are both derived from Date, matching Loader's raw row shape.

    Regression test for YearlyAggregator (utils/operators/aggregator.py): it groups by
    a "Year" column that nothing derived before this fix - dormant today (yearly_view.py
    is a stub), but would have KeyError'd the moment that page got built.
    """
    raw_rows: list[dict[str, Any]] = [
        {
            "Date": "15/03/2025",
            "Description": "Test",
            "Value": -100.0,
            "Account": "Carteira",
            "Status": "Paid",
            "Category": "Restaurant",
            "Subcategory": None,
            "Tags": None,
        },
        {
            "Date": "20/07/2024",
            "Description": "Test 2",
            "Value": 5000.0,
            "Account": "Carteira",
            "Status": "Paid",
            "Category": "Salary",
            "Subcategory": None,
            "Tags": None,
        },
        # Loader's trailing blank + "Total (...)" summary rows, dropped by .tail(2)
        dict.fromkeys(
            [
                "Date",
                "Description",
                "Value",
                "Account",
                "Status",
                "Category",
                "Subcategory",
                "Tags",
            ]
        ),
        {
            "Date": None,
            "Description": "Total (incomes - expenses)",
            "Value": None,
            "Account": None,
            "Status": None,
            "Category": None,
            "Subcategory": None,
            "Tags": None,
        },
    ]

    result = PreProcessedLoader(_FakeOperator(pd.DataFrame(raw_rows))).data

    assert len(result) == 2
    assert result["Year"].tolist() == [2025, 2024]
    assert result["Month"].tolist() == [
        pd.Timestamp("2025-03-01"),
        pd.Timestamp("2024-07-01"),
    ]


def test_yearly_aggregator_sums_value_by_year() -> None:
    """YearlyAggregator groups by the Year column PreProcessedLoader now derives."""
    data = pd.DataFrame(
        [
            {"Year": 2024, "Value": -100.0},
            {"Year": 2024, "Value": -50.0},
            {"Year": 2025, "Value": 200.0},
        ]
    )

    result = agg.YearlyAggregator(_FakeOperator(data)).data

    by_year = dict(zip(result["Year"], result["Value"], strict=True))
    assert by_year == {2024: -150.0, 2025: 200.0}
