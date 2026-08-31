# KPIs

## Scope

`KpisPage` (`src/app/screens/kpis.py`) and the calculators in
`src/app/utils/business/kpis.py`.

## Goal

Turn the (diluted or non-diluted, date-filtered) transaction set into a single-page financial
health check, with visual pass/fail against a target where a target is known.

## Rule: card evaluation

A `CardKpi` shows `value` vs. `target`. If `target` is set, `higher_is_better` is required
(raises `ValueError` otherwise) and the card is styled green (met) or red (not met) by
comparing `value` against `target` in the direction `higher_is_better` implies. If `target` is
`None`, the card renders neutrally (informational only, no pass/fail).

## Rule: derived metrics (all formulas add `1e-5` to denominators to avoid division by zero)

- `net_income = total_income - total_expenses`
- `net_income_perc = net_income / total_income`
- `fixed/variable/lifestyle_expenses_perc = <tier expenses> / total_income` (note: divided by
  **income**, not by total expenses)
- `income_increase_perc`, `expenses_increase_perc`: current period vs. a comparison period
  (last 3/6/12 months), each computed independently via `KpiTrendsCalculator`
- `expenses_inflation_perc = (expenses_increase_perc - income_increase_perc) / income_increase_perc`
  — how much faster expenses are growing than income, normalized by income growth
- `elapsed_date_perc` (`KpiDateAdvancementCalculator`): how far through the selected date
  range "today" is; clamped to 1.0 once the range has fully elapsed — used to judge whether a
  category is on pace mid-period
- Voucher (`VR`/`VA`) consumption %: spend on that account / income credited to that account
  in the period
- Trip budget overrun: see [travel.md](travel.md) — always evaluated for the current year,
  independent of the page's date filter

## Known targets (not yet wired to code — currently `None` placeholders, `fixit collab add real
targets` in `kpis.py`)

These are documented intent from `utils/business/kpis.py` comments, useful when the targets are
eventually filled in:

- Net Income %: Beginner 10–20%, Ideal 25–40%, Elite 50%+
- Expenses inflation %: Beginner <5%, Ideal <3%, Elite <0%
- Travel budget adherence (evaluated yearly): Beginner <20% overrun, Ideal <10%, Elite <0%
  (already partially wired: `TARGET_TRIP_BUDGET_OVERRUN = 0`)
- Months of Runway (not implemented) = Emergency Fund / Average Monthly Expenses over last 6
  months — Beginner 3mo, Strong 6mo, Excellent 12mo

## Category KPI breakdown: three actuals variants

The per-category expander computes the same category's expenses three ways side by side:
- **Only Ordinary**: dilutable transactions removed entirely (`tr.Remover` dropping every
  row where `Dilution` is `True`) — i.e. only non-diluted-eligible spend
- **With Extraordinary**: all transactions as paid, dilution not applied
- **Diluted**: dilution applied (lumpy costs smoothed over 12 months)

All three are compared against the same `CATEGORY_BUDGETS` target, which the code itself flags
as wrong (`fixit correct without/with/diluted extraordinary` — the budget should likely differ
per variant, since "Diluted" and "With Extraordinary" are not directly comparable to the same
number).
