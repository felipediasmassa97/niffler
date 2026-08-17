---
name: niffler-business-rules
description: Financial business rules for the niffler personal-finance app — dilution, tiers (Fixed/Variable/Lifestyle), trip fund accounting, category budgets, and KPI formulas. Use before changing anything under src/app/utils/business/ or src/app/screens/kpis.py, before adding/renaming a transaction category, or when asked how dilution, tiers, trip budget, or a KPI is calculated.
---

# Niffler Business Rules

Niffler classifies and reshapes raw Mobills export transactions before any chart or KPI reads
them. Full rule text lives in `docs/business_rules/` — read the relevant file there before
touching the matching code; this skill is the index plus the pitfalls that don't fit a rule doc.

## Rule domains

| Domain                                     | Doc                                 | Code                         |
| ------------------------------------------ | ----------------------------------- | ---------------------------- |
| Dilution (smoothing lumpy costs over 12mo) | `docs/business_rules/dilution.md`   | `utils/business/dilution.py` |
| Tiers (Fixed/Variable/Lifestyle)           | `docs/business_rules/tiers.md`      | `utils/business/tiers.py`    |
| Trip Funds accounting                      | `docs/business_rules/travel.md`     | `utils/business/travel.py`   |
| Categories & actionability                 | `docs/business_rules/categories.md` | `utils/business/budget.py`   |
| KPI formulas & targets                     | `docs/business_rules/kpis.md`       | `utils/business/kpis.py`     |

## Non-negotiable invariant

`CATEGORY_BUDGETS` in `budget.py` is the category source of truth. `DilutionAssigner` and
`TierAssigner` each key a plain dict by category name (lowercased, accent-stripped via
`unidecode`) with **no `.get()` fallback** — a category present in one place but missing from
another raises `KeyError` at row-processing time, not at import time. Whenever you add, rename,
or remove a category:

1. Update `CATEGORY_BUDGETS` (`budget.py`).
2. Update both category dicts in `dilution.py` (`_assign_dilution_income` /
   `_assign_dilution_expense`).
3. Update the category dict in `tiers.py` (`_assign_tiers_expense`, and `_assign_tiers_income`
   if it's an income category).
4. Update the actionability list in `docs/business_rules/categories.md` and
   `management-system.md`.

## Processing order matters

`ProcessedLoader` (`utils/operators/loader.py`) always applies, in order:
`PreProcessedLoader → DilutionAssigner → TierAssigner → TripBalanceCalculator`.

- `DilutionAssigner` only **flags** rows (`Dilution` column); it does not explode them. The
  actual 12-month spreading (`Diluter`) is opt-in per screen (the "Dilute Costs" checkbox) and
  must run _after_ `TierAssigner`/`TripBalanceCalculator`, or diluted rows won't carry a `Tier`.
  Follow the existing pattern in `screens/kpis.py` and `screens/monthly_view.py`.
- `TripBalanceCalculator` deletes and re-synthesizes Trip Funds rows for every year from 2024 to
  the current year, every time it runs — it is not incremental. If a screen needs raw
  (un-adjusted) trip data, read `TripBalanceCalculator.raw_data` instead of `.data`.

## Value sign convention

Expenses are negative, income is positive, throughout the raw and processed data — `Value < 0`
is the standard expense filter (`ExpensesFilter`). Charts that need positive expense bars go
through `tr.Inverter` (see `monthly_view.py`) rather than re-deriving sign logic locally.

## Known unfinished areas (safe to extend, not yet wired up)

- KPI targets are mostly `None` placeholders in `screens/kpis.py`
  (`fixit collab add real targets`) — see `docs/business_rules/kpis.md` for the intended
  Beginner/Ideal/Elite bands to fill in.
- `CATEGORY_BUDGETS` is a flat R$1,000 placeholder for every category
  (`fixit collab add monthly budgets`).
- Actionability tiers (most/mid/least actionable) exist only as a list in
  `management-system.md`, not as an assignable field.
- `utils/business/forecast.py` is dead code (confirmed unused anywhere in `src/`) — the file's
  own comment already flags it `fixit deprecated file, remove after verifying no usage`.
