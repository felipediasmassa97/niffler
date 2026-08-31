# Business Rules

Index of niffler's financial business rules. Update the relevant file here **before** changing
the corresponding logic in `src/app/utils/business/`, so the rule and the code never drift.

- [Dilution](dilution.md) — which transactions get smoothed over 12 months, and how
- [Tiers](tiers.md) — Fixed / Variable / Lifestyle classification
- [Travel / Trip Funds](travel.md) — main-trip pre-funding and budget-overrun accounting
- [Categories and Actionability](categories.md) — the category set and review-priority ranking
- [KPIs](kpis.md) — derived metrics, card pass/fail logic, and known (unset) targets

See also [`management-system.md`](../../management-system.md) for the human review cadence
(biweekly/monthly/yearly) these rules feed into.

## Pipeline order is load-bearing

`ProcessedLoader` (`src/app/utils/operators/loader.py`) always applies these rules in a fixed
order: `DilutionAssigner` → `TierAssigner` → `TripBalanceCalculator`. This isn't incidental -
two of the rules depend on it:

- `TripBalanceCalculator`'s synthetic `"Saldo Viagem {year}"` balance row is created *after*
  both assigners have already run, so it never passes through either of them - it hardcodes
  `Tier = "Lifestyle"` and `Dilution = True` directly instead (see [travel.md](travel.md)),
  matching what both rules would have assigned anyway.
- Because of that, `TierAssigner`'s income dict never needs a `travel` key (income-side
  `travel` only ever exists as this synthetic row) - but `DilutionAssigner`'s income dict
  *does* need one, since the "Dilute Costs" toggle (`Diluter`) re-runs `DilutionAssigner`
  from scratch over the *already fully processed* dataset, seeing the synthetic row a second
  time (see [dilution.md](dilution.md)).

Reordering this pipeline (e.g. running `TierAssigner` after `TripBalanceCalculator` "for
consistency") would immediately raise a `KeyError` looking up the synthetic row's income-side
`Tier`.
