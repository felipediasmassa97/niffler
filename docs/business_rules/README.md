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
