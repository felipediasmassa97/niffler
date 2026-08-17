# Categories and Actionability

## Scope

All 24 expense categories and 4 income categories used across dilution, tiers, and budget
rules. Source of truth for the category _set_ is `CATEGORY_BUDGETS` in
`src/app/utils/business/budget.py` — every dict keyed by category elsewhere in the codebase
(dilution, tiers) must have exactly this key set or a `KeyError` is raised at runtime.

## Goal

Rank categories by how much reviewing them regularly is expected to change behavior, so
biweekly/monthly reviews (see [`management-system.md`](../../management-system.md)) focus
effort where it matters.

## Rule: actionability tiers

Currently a manual list (not yet a code-assigned field — see the known gap in
[tiers.md](tiers.md)):

- **Most actionable**: Unknown, Personal Felp, Personal Lena, Restaurant, Recreation, Travel,
  Gift
- **Mid actionable**: Donation, High Costs, Transport, Home, Physical, Subscriptions,
  Work Lunch
- **Least actionable**: Rent, Supermarket, Commute, Car, Education, Health, Maintenance,
  Pharmacy, Services, Work

## Income categories

`gift`, `refund`, `rewards`, `salary` — see [dilution.md](dilution.md) and [tiers.md](tiers.md)
for how each is diluted/tiered.

## Budgets

`CATEGORY_BUDGETS` currently hardcodes every category to R$1,000/period as a placeholder
(`fixit collab add monthly budgets`) — not yet real per-category targets. Used by
`KpiCategoryCalculator.expenses_budget_utilization_perc_by_category` and the per-category KPI
expander on the KPIs page.
