# Tiers

## Scope

Applies to every transaction. Implemented in `src/app/utils/business/tiers.py`
(`TierAssigner`), always applied by `ProcessedLoader` (not optional, unlike dilution).
`TierAssigner` runs *before* `TripBalanceCalculator` in that pipeline - which is why the
income dict below never needs a `travel` key, unlike dilution's - see
[README.md](README.md#pipeline-order-is-load-bearing).

## Goal

Classify every transaction into a spending/income tier so KPIs can answer "how much of my
income is committed (Fixed) vs. discretionary-but-necessary (Variable) vs. pure lifestyle
choice (Lifestyle)?" — the classic fixed/variable/lifestyle budgeting split.

Tiers are: `"Fixed"`, `"Variable"`, `"Lifestyle"` (expenses), plus `"Fixed"`/`"Variable"`
(income).

## Rule: assigning tiers

Decided by category, description, and tags (case/accent-insensitive). Specific
description/tag-based overrides are checked first; anything unmatched falls back to a
per-category default. A category/description combination not covered raises a `KeyError`.

**Income** — `Value > 0`:

| Category                    | Tier     |
| --------------------------- | -------- |
| `salary`                    | Fixed    |
| `gift`, `refund`, `rewards` | Variable |

**Expenses** — `Value <= 0`, specific overrides (checked before the per-category default):

| Category    | Description/Tag contains   | Tier     |
| ----------- | -------------------------- | -------- |
| `education` | "medcurso"                 | Fixed    |
| `education` | "pos graduacao"            | Fixed    |
| `health`    | "bradesco saude"           | Fixed    |
| `travel`    | tag `work`                 | Variable |
| `work`      | "crea"                     | Fixed    |
| `work`      | "crm"                      | Fixed    |
| `work`      | "chatgpt"                  | Fixed    |
| `work`      | "contabileasy mensalidade" | Fixed    |
| `work`      | "darf"                     | Fixed    |
| `work`      | "whitebook"                | Fixed    |

**Expenses** — per-category default:

| Tier      | Categories                                                                                                 |
| --------- | ---------------------------------------------------------------------------------------------------------- |
| Fixed     | car, commute, rent, services, supermarket                                                                  |
| Variable  | education, health, high costs, home, maintenance, pharmacy, physical, transport, unknown, work, work lunch |
| Lifestyle | donation, gift, personal felp, personal lena, recreation, restaurant, subscriptions, travel                |

## Known gap

`fixit add most actionable, mid-actionable, least actionable tiers` — the "actionability"
ranking currently only exists as a plain list in [`management-system.md`](../../management-system.md)
(used manually during biweekly reviews); it is not yet an assignable field on transactions. See
[categories.md](categories.md) for that list.
