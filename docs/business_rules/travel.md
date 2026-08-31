# Travel / Trip Funds

## Scope

Applies to transactions on the `Trip Funds` Mobills account and the `Travel` category.
Implemented in `src/app/utils/business/travel.py` (`TripBalanceCalculator`), always applied by
`ProcessedLoader`.

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

## KPI usage

`KpiMainTripCalculator` (in `utils/business/kpis.py`) always evaluates **this year**
regardless of the page's date filter, and reads `budget_overrun` back out of the synthetic
balance transaction (negated, since the stored balance is budget − actuals but overrun should
read positive when over budget).
