"""Tests for the category budget rule (docs/business_rules/categories.md).

`CATEGORY_BUDGETS` is the source-of-truth key set for every expense category in the
app - `DilutionAssigner` and `TierAssigner` each keep an independent dict keyed by the
same categories, and a category missing from one of them only raises `KeyError` at
row-apply time, not at import time (the exact class of bug `CLAUDE.md`'s "Known gaps"
section says is only caught today by the UI regression test). These tests catch it
directly, by driving every budgeted category through both assigners.
"""

from typing import Any

from utils.business.budget import CATEGORY_BUDGETS
from utils.business.dilution import DilutionAssigner
from utils.business.tiers import TierAssigner

# Income categories aren't in CATEGORY_BUDGETS (that dict is expenses-only), but still
# need Dilution/Tier coverage. "Travel" is deliberately excluded: its only income
# appearance is TripBalanceCalculator's synthetic "Saldo Viagem" row, which is created
# *after* TierAssigner runs in the pipeline and hardcodes its own Tier - so
# TierAssigner's income dict never needs a "travel" key (see travel.md/tiers.md).
INCOME_CATEGORIES = ["Gift", "Refund", "Rewards", "Salary"]


def test_category_budgets_placeholder_is_documented_current_behavior() -> None:
    """Every category budgets to the same flat placeholder (see budget.py's fixit)."""
    assert set(CATEGORY_BUDGETS.values()) == {1000}


def test_every_budgeted_category_is_assignable_a_dilution_flag(
    make_operator: Any,
) -> None:
    """A category missing from DilutionAssigner's dicts would raise KeyError here."""
    for category in CATEGORY_BUDGETS:
        operator = make_operator([{"Category": category, "Value": -1}])
        _ = DilutionAssigner(operator).data  # raises KeyError on a missing category


def test_every_budgeted_category_is_assignable_a_tier(make_operator: Any) -> None:
    """A category missing from TierAssigner's dicts would raise KeyError here."""
    for category in CATEGORY_BUDGETS:
        operator = make_operator([{"Category": category, "Value": -1}])
        _ = TierAssigner(operator).data  # raises KeyError on a missing category


def test_every_income_category_is_assignable_a_dilution_flag_and_tier(
    make_operator: Any,
) -> None:
    """Income categories aren't budgeted, but still need Dilution/Tier coverage."""
    for category in INCOME_CATEGORIES:
        operator = make_operator([{"Category": category, "Value": 1}])
        _ = DilutionAssigner(operator).data
        _ = TierAssigner(operator).data


def test_synthetic_travel_income_is_assignable_a_dilution_flag(
    make_operator: Any,
) -> None:
    """The Dilute Costs toggle re-runs DilutionAssigner over the synthetic Travel row.

    That row is created downstream of ProcessedLoader's own DilutionAssigner pass, by
    TripBalanceCalculator - so this income category still needs Dilution coverage.
    """
    operator = make_operator([{"Category": "Travel", "Value": 1}])

    _ = DilutionAssigner(operator).data  # raises KeyError if "travel" income is missing
