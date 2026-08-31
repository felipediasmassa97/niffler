"""Tests for the travel/trip-fund business rule (docs/business_rules/travel.md)."""

from typing import Any

import pytest
from utils.business.travel import TripBalanceCalculator
from utils.globals import Account


def test_get_budget_sums_trip_funds_transfers_from_year_n_minus_1(
    mock_transfers: Any,
) -> None:
    """Budget for year N is the sum of transfers to Trip Funds in year N-1."""
    mock_transfers(
        [
            {
                "Date": "31/12/2024",
                "Conta origem": "Carteira",
                "Conta destino": "Trip Funds",
                "Value": 30000,
                "Tags": "orlando",
            },
            # Different destination account - must not count toward the budget
            {
                "Date": "24/12/2024",
                "Conta origem": "Carteira",
                "Conta destino": "Investments",
                "Value": 12300,
                "Tags": None,
            },
        ]
    )

    assert TripBalanceCalculator.get_budget(2025) == 30000


def test_get_budget_is_zero_for_a_year_with_no_transfers(
    mock_transfers: Any,
) -> None:
    """A year with no matching transfer contributes no budget."""
    mock_transfers(
        [
            {
                "Date": "31/12/2024",
                "Conta origem": "Carteira",
                "Conta destino": "Trip Funds",
                "Value": 30000,
                "Tags": "orlando",
            }
        ]
    )

    assert TripBalanceCalculator.get_budget(2024) == 0


def test_sum_actuals_sums_trip_funds_travel_expenses_in_year_n(
    make_operator: Any, mock_transfers: Any
) -> None:
    """Actuals for year N are Trip-Funds/Travel expenses paid during year N."""
    mock_transfers([])
    operator = make_operator(
        [
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -735,
                "Date": "2025-07-01",
            },
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -90,
                "Date": "2025-07-01",
            },
            # Wrong account - must not count
            {
                "Account": "Carteira",
                "Category": "Travel",
                "Value": -100,
                "Date": "2025-07-01",
            },
            # Wrong category - must not count
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Restaurant",
                "Value": -50,
                "Date": "2025-07-01",
            },
            # Wrong year - must not count
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -1000,
                "Date": "2024-07-01",
            },
        ]
    )
    calculator = TripBalanceCalculator(operator)

    assert calculator.sum_actuals(2025) == pytest.approx(825)


def test_calculate_balance_is_budget_minus_actuals(
    make_operator: Any, mock_transfers: Any
) -> None:
    """A trip under budget yields a positive balance."""
    mock_transfers(
        [
            {
                "Date": "31/12/2024",
                "Conta origem": "Carteira",
                "Conta destino": "Trip Funds",
                "Value": 30000,
                "Tags": "orlando",
            }
        ]
    )
    operator = make_operator(
        [
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -20000,
                "Date": "2025-07-01",
            }
        ]
    )
    calculator = TripBalanceCalculator(operator)

    assert calculator.calculate_balance(2025) == pytest.approx(10000)


def test_adjust_data_replaces_raw_rows_with_a_single_synthetic_balance_row(
    make_operator: Any, mock_transfers: Any, freeze_year: Any
) -> None:
    """Raw Trip-Funds/Travel rows for the year are dropped, one balance row added."""
    freeze_year(2025)
    mock_transfers(
        [
            {
                "Date": "31/12/2024",
                "Conta origem": "Carteira",
                "Conta destino": "Trip Funds",
                "Value": 30000,
                "Tags": "orlando",
            }
        ]
    )
    operator = make_operator(
        [
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -735,
                "Date": "2025-07-01",
            },
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Travel",
                "Value": -90,
                "Date": "2025-07-01",
            },
            # Untouched: a different category in the same account/year
            {
                "Account": Account.TRIP_FUNDS,
                "Category": "Restaurant",
                "Value": -50,
                "Date": "2025-07-01",
            },
        ]
    )

    result = TripBalanceCalculator(operator).data

    year_2025_travel = result[
        (result["Category"] == "Travel")
        & (result["Account"] == Account.TRIP_FUNDS)
        & (result["Date"].dt.year == 2025)
    ]
    assert len(year_2025_travel) == 1
    balance_row = year_2025_travel.iloc[0]
    assert balance_row["Description"] == "Saldo Viagem 2025"
    assert balance_row["Value"] == pytest.approx(30000 - 825)
    assert balance_row["Tier"] == "Lifestyle"
    assert balance_row["Dilution"]
    assert balance_row["Date"].strftime("%Y-%m-%d") == "2025-12-31"
    # The untouched Restaurant row survives unchanged
    assert (result["Category"] == "Restaurant").sum() == 1
    # The synthetic row must not upcast Dilution from bool to object/float - which
    # happens if pd.concat ever sees a row missing the "Dilution" key entirely
    assert result["Dilution"].dtype == bool


def test_adjust_data_inserts_a_balance_row_for_every_year_even_with_no_trip(
    make_operator: Any, mock_transfers: Any, freeze_year: Any
) -> None:
    """A year with no transfers and no actuals still gets a zero-balance row."""
    freeze_year(2024)
    mock_transfers([])
    operator = make_operator([{"Category": "Restaurant", "Value": -50}])

    result = TripBalanceCalculator(operator).data

    balance_rows = result[result["Description"] == "Saldo Viagem 2024"]
    assert len(balance_rows) == 1
    assert balance_rows.iloc[0]["Value"] == 0
