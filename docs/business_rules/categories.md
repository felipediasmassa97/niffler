# Categories and Actionability

## Scope

All 24 expense categories and 4 income categories used across dilution, tiers, and budget
rules. Source of truth for the category _set_ is `CATEGORY_BUDGETS` in
`src/app/utils/business/budget.py` — every dict keyed by category elsewhere in the codebase
(dilution, tiers) must have exactly this key set or a `KeyError` is raised at runtime.

## Rule: case/accent-insensitive matching

Every comparison against a `Category` value — dilution and tier assignment, and the KPI
category breakdown — standardizes with `standardize_string`
(`src/app/utils/business/__init__.py`: strip accents, lowercase) before comparing, so
`"Personal Felp"`, `"personal felp"`, and `"PERSONAL FELP"` are all the same category. This
matters most for the KPI breakdown (`KpiCategoryCalculator`): unlike dilution/tiers (which
raise `KeyError` on an unrecognized category), it does an exact-match dict comprehension over
`CATEGORY_BUDGETS`, so a mismatch there doesn't crash — it silently contributes to no bucket.
`CATEGORY_BUDGETS`'s own keys are the canonical display-cased strings and are only used
as-is for labels and dict lookups keyed by those exact strings (e.g. `CATEGORY_BUDGETS[cat]`
for a `cat` already drawn from its own keys) — never compared directly against raw `Category`
values.

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
