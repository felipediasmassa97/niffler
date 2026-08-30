"""Tests for the tiers business rule (docs/business_rules/tiers.md)."""

from typing import Any

import pytest
from utils.business.tiers import TierAssigner


class TestTierAssignerIncome:
    """Income tier defaults (Value > 0)."""

    @pytest.mark.parametrize(
        ("category", "expected"),
        [
            ("Gift", "Variable"),
            ("Refund", "Variable"),
            ("Rewards", "Variable"),
            ("Salary", "Fixed"),
        ],
    )
    def test_assigns_tier_by_category(
        self, make_operator: Any, category: str, expected: str
    ) -> None:
        """Each income category maps to its documented tier."""
        operator = make_operator([{"Category": category, "Value": 1000}])

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == expected

    def test_unmapped_category_raises_key_error(self, make_operator: Any) -> None:
        """A category missing from the dict fails loudly, not silently."""
        operator = make_operator([{"Category": "Not A Real Category", "Value": 10}])

        with pytest.raises(KeyError):
            _ = TierAssigner(operator).data


class TestTierAssignerExpenseOverrides:
    """Specific description/tag overrides, checked before the category default."""

    @pytest.mark.parametrize(
        "description",
        ["Medcurso Mensalidade", "Pos Graduacao USP"],
    )
    def test_education_keyword_forces_fixed(
        self, make_operator: Any, description: str
    ) -> None:
        """Education is Variable by default, but these keywords force Fixed."""
        operator = make_operator(
            [{"Category": "Education", "Description": description, "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Fixed"

    def test_education_without_keyword_falls_back_to_default(
        self, make_operator: Any
    ) -> None:
        """Without a matching keyword, Education uses its Variable default."""
        operator = make_operator(
            [{"Category": "Education", "Description": "Random Course", "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Variable"

    def test_health_bradesco_saude_forces_fixed(self, make_operator: Any) -> None:
        """Health is Variable by default, but this specific plan is Fixed."""
        operator = make_operator(
            [
                {
                    "Category": "Health",
                    "Description": "Bradesco Saude Mensalidade",
                    "Value": -100,
                }
            ]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Fixed"

    def test_health_without_keyword_falls_back_to_default(
        self, make_operator: Any
    ) -> None:
        """Without the Bradesco Saude keyword, Health uses its Variable default."""
        operator = make_operator(
            [{"Category": "Health", "Description": "Farmacia", "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Variable"

    def test_travel_with_work_tag_is_variable(self, make_operator: Any) -> None:
        """Travel is Lifestyle by default, but a `work` tag makes it Variable."""
        operator = make_operator(
            [{"Category": "Travel", "Tags": ["work"], "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Variable"

    def test_travel_without_work_tag_falls_back_to_default(
        self, make_operator: Any
    ) -> None:
        """Without the `work` tag, Travel uses its Lifestyle default."""
        operator = make_operator(
            [{"Category": "Travel", "Tags": ["penedo"], "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Lifestyle"

    @pytest.mark.parametrize(
        "description",
        [
            "CREA Anuidade",
            "CRM Anuidade",
            "ChatGPT Plus",
            "ContabilEasy Mensalidade",
            "DARF",
            "Whitebook Assinatura",
        ],
    )
    def test_work_keyword_forces_fixed(
        self, make_operator: Any, description: str
    ) -> None:
        """Work is Variable by default, but these keywords force Fixed."""
        operator = make_operator(
            [{"Category": "Work", "Description": description, "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Fixed"

    def test_work_without_keyword_falls_back_to_default(
        self, make_operator: Any
    ) -> None:
        """Without a matching keyword, Work uses its Variable default."""
        operator = make_operator(
            [{"Category": "Work", "Description": "Congresso Inscricao", "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == "Variable"


class TestTierAssignerExpenseDefaults:
    """Expense category defaults (no override matched)."""

    @pytest.mark.parametrize(
        ("category", "expected"),
        [
            ("Car", "Fixed"),
            ("Commute", "Fixed"),
            ("Rent", "Fixed"),
            ("Services", "Fixed"),
            ("Supermarket", "Fixed"),
            ("Education", "Variable"),
            ("Health", "Variable"),
            ("High Costs", "Variable"),
            ("Home", "Variable"),
            ("Maintenance", "Variable"),
            ("Pharmacy", "Variable"),
            ("Physical", "Variable"),
            ("Transport", "Variable"),
            ("Unknown", "Variable"),
            ("Work Lunch", "Variable"),
            ("Donation", "Lifestyle"),
            ("Gift", "Lifestyle"),
            ("Personal Felp", "Lifestyle"),
            ("Personal Lena", "Lifestyle"),
            ("Recreation", "Lifestyle"),
            ("Restaurant", "Lifestyle"),
            ("Subscriptions", "Lifestyle"),
            ("Travel", "Lifestyle"),
        ],
    )
    def test_assigns_tier_by_category(
        self, make_operator: Any, category: str, expected: str
    ) -> None:
        """Each expense category maps to its documented default tier."""
        operator = make_operator(
            [{"Category": category, "Description": "Generic", "Value": -100}]
        )

        result = TierAssigner(operator).data

        assert result.iloc[0]["Tier"] == expected

    def test_unmapped_category_raises_key_error(self, make_operator: Any) -> None:
        """A category missing from the dict fails loudly, not silently."""
        operator = make_operator(
            [{"Category": "Not A Real Category", "Description": "x", "Value": -10}]
        )

        with pytest.raises(KeyError):
            _ = TierAssigner(operator).data
