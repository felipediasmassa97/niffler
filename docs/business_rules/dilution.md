# Dilution

## Scope

Applies to every transaction (income and expense) loaded from the Mobills export, before or
after the "Dilute Costs" toggle is applied on a screen. Implemented in
`src/app/utils/business/dilution.py`.

## Goal

Some transactions are lumpy (an annual insurance payment, a big donation, a trip) and would
distort a month-by-month view if counted entirely in the month they were paid. Dilution flags
which transactions should instead be smoothed across a 12-month window, so KPIs and charts
reflect the ongoing cost/benefit rather than a one-off spike.

## Rule: assigning the `Dilution` flag (`DilutionAssigner`)

Every row gets a boolean `Dilution` flag, decided by category (case/accent-insensitive) and the
absolute value of the transaction. Specific value-based overrides are checked first; anything not
matched falls back to a per-category default.

**Income** — `Value > 0`:

| Category                      | Diluted?       |
| ----------------------------- | -------------- |
| `refund` >= R$500             | Yes (override) |
| `rewards`, `salary`, `travel` | Yes            |
| `gift`, `refund` (< R$500)    | No             |

`travel` shows up on the income side only via `TripBalanceCalculator`'s synthetic
`"Saldo Viagem {year}"` balance transaction (see [travel.md](travel.md)) when a trip finishes
under budget (`Value > 0`); it's diluted to match the expense-side `travel` treatment below, so
the yearly trip result smooths the same way regardless of surplus or overrun.

**Expenses** — `Value <= 0` (compared on the absolute value):

| Category                                                                                                                                                                                                                                        | Diluted?       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| `car` >= R$300                                                                                                                                                                                                                                  | Yes (override) |
| `donation` >= R$200                                                                                                                                                                                                                             | Yes (override) |
| `home` >= R$250                                                                                                                                                                                                                                 | Yes (override) |
| `subscriptions` >= R$60                                                                                                                                                                                                                         | Yes (override) |
| `work` >= R$300                                                                                                                                                                                                                                 | Yes (override) |
| `travel`, account = `Trip Funds`                                                                                                                                                                                                                | Yes (override) |
| `travel`, any other account, >= R$300                                                                                                                                                                                                          | Yes (override) |
| `high costs`, `maintenance`                                                                                                                                                                                                                    | Yes            |
| everything else (car/donation/home/subscriptions/work/travel below threshold, commute, education, gift, health, personal felp, personal lena, pharmacy, physical, recreation, rent, restaurant, services, supermarket, transport, unknown, work lunch) | No             |

`travel` is the one category where dilution also checks `Account`, not just `Category` and
`Value`: the `Trip Funds` account is reserved for the single pre-funded main trip (see
[travel.md](travel.md)), which is always diluted regardless of amount - this is also how
`TripBalanceCalculator`'s synthetic `"Saldo Viagem"` balance row is tagged. Any other account is
ad-hoc travel (e.g. a one-off business trip - see [tiers.md](tiers.md)'s `travel` + tag `work`
override), treated like the `work` category it's conceptually closest to: diluted only above the
same R$300 threshold, not unconditionally.

Every category used across the app must appear in these dicts — a category missing from the
dict raises a `KeyError`. See [categories](categories.md) for the full category list.

## Rule: performing the dilution (`Diluter`)

For every row where `Dilution` is `True`:

- The `Value` is divided by 12.
- The `Date` is replaced with 12 dates: the 1st of each month of the **same calendar year** as
  the original transaction (not a rolling 12 months from the transaction date).
- The `Description` is suffixed with `(i/12)` for each of the 12 rows.
- One row becomes 12 rows (`DataFrame.explode`); non-diluted rows pass through unchanged.
- `Month` is recomputed from the new `Date` after exploding.

`Diluter` is applied on demand (the "Dilute Costs" toggle in `monthly_view.py` and `kpis.py`); the
underlying `Dilution` flag itself is always computed by `ProcessedLoader`.
