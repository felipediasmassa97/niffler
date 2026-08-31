# Travel / Trip Funds

## Scope

Applies to transactions on the `Trip Funds` Mobills account and the `Travel` category.
Implemented in `src/app/utils/business/travel.py` (`TripBalanceCalculator`), always applied by
`ProcessedLoader`.

This rule assumes **one main trip per year**. Every `Trip Funds`/`Travel` transaction in a
given year is combined into that year's single balance figure — there's no notion of "which
trip" a transaction belongs to. This is a deliberate scope limit, not an oversight: keep
`Trip Funds` reserved for the single pre-funded main trip, and route any other travel (a
work trip, a smaller side trip) through a different account instead — which the app's own
data already does naturally (see [dilution.md](dilution.md)'s account-based main-trip vs.
ad-hoc-travel distinction, and [tiers.md](tiers.md)'s `travel` + tag `work` override). If a
second trip is ever funded through `Trip Funds` in the same calendar year, its budget and
actuals will silently merge into the main trip's balance.

## Goal

The main yearly trip is pre-funded a year in advance: money is set aside in year N-1 and spent
during the trip in year N. Shown naively, this would look like a huge Travel expense in N-1 (the
transfer) and then real spending in N on top of it — double-counting the cost and hiding whether
the trip went over or under budget. This rule replaces both pieces with a single "did we
over/underspend the trip budget" transaction.

## Rule

For each year N from 2024 to the current year:

1. **Budget for year N** = sum of all `Transfer` transactions into the `Trip Funds` account
   during year **N-1** (read from the raw Mobills "Transfers" sheet, not the main
   "Receitas e Despesas" sheet — `TripBalanceCalculator._load_transfer_data`).
2. **Actuals for year N** = sum of all `Travel`-category expenses paid from the `Trip Funds`
   account during year N.
3. **Balance** = Budget − Actuals (positive = under budget, negative = overrun).
4. Data adjustment applied to the working dataset:
   - Remove the raw `Trip Funds` / `Travel` expense rows for year N (the actuals already
     captured in the balance).
   - Insert one synthetic transaction dated Dec 31 of year N: description
     `"Saldo Viagem {year}"`, `Value = balance`, `Account = Trip Funds`,
     `Category = Travel`, `Tier = Lifestyle`, `Dilution = True`. `Tier` and `Dilution`
     are hardcoded rather than computed by `TierAssigner`/`DilutionAssigner`, since this
     row is created downstream of both in the pipeline and neither ever sees it - both
     values match what those rules would have assigned anyway, since `Travel` is always
     Lifestyle-tiered and always diluted regardless of income/expense direction (see
     [dilution.md](dilution.md)/[tiers.md](tiers.md)). This only holds because
     `TripBalanceCalculator` runs last in the pipeline - see
     [README.md](README.md#pipeline-order-is-load-bearing).

Note: the pre-funding transfer transaction (year N-1, `Wallet` → `Trip Funds`) is a `Transfer`
type and is separate from the "Receitas e Despesas" sheet dataset the app otherwise loads — it
never appears as an expense in year N-1's view.

**The current year's balance is provisional, not a final result.** The rule doesn't know
whether this year's trip has actually happened yet — it just computes budget minus
spend-to-date, for every year from 2024 through today, unconditionally. Mid-year, before most
of the trip's spending has occurred, this reads as "under budget" simply because the money
hasn't been spent yet, not because the trip actually came in under budget. Treat the current
year's figure as in-progress; only a past year's balance is a settled result.

## KPI usage

`KpiMainTripCalculator` (in `utils/business/kpis.py`) always evaluates **this year**
regardless of the page's date filter, and reads `budget_overrun` back out of the synthetic
balance transaction (negated, since the stored balance is budget − actuals but overrun should
read positive when over budget).
