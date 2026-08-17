# niffler

Personal financial tracking dashboard. A Streamlit app reads a manually-exported Mobills Excel
report, applies a set of financial business rules (dilution, tiers, trip-fund accounting), and
renders monthly/yearly views and KPI cards to support a recurring personal finance review.

There is no backend, database, or auth - it's a single-user local app that reads one Excel file
per run.

## Tech stack

- Python >=3.13, managed with `uv`
- Streamlit (`st.navigation` multi-page app) for the UI
- pandas for data processing, `openpyxl` for reading `.xlsx`
- Plotly for charts
- `unidecode` for accent/case-insensitive category matching

## Project structure

```
niffler/
├── docs/
│   └── business_rules/              # human-readable business rule docs, one file per domain
├── src/
│   └── app/
│       ├── main.py                  # st.navigation entry point, registers all pages
│       ├── screens/                 # one module per page (monthly_view, yearly_view, kpis, patrimony, validation)
│       ├── utils/
│       │   ├── business/            # financial business rules - see docs/business_rules/
│       │   │   ├── dilution.py      # DilutionAssigner, Diluter
│       │   │   ├── tiers.py         # TierAssigner (Fixed/Variable/Lifestyle)
│       │   │   ├── travel.py        # TripBalanceCalculator (main-trip pre-funding)
│       │   │   ├── budget.py        # CATEGORY_BUDGETS - category source of truth
│       │   │   ├── kpis.py          # KPI calculators + CardKpi rendering
│       │   │   └── forecast.py      # dead code, not wired up anywhere (see below)
│       │   ├── operators/           # composable data-pipeline building blocks (see Architecture)
│       │   │   ├── loader.py
│       │   │   ├── filter.py
│       │   │   ├── aggregator.py
│       │   │   └── transformer.py
│       │   ├── charts.py            # Plotly chart wrapper classes
│       │   └── globals.py           # Account enum (Mobills account names used in rules)
│       └── data/                    # gitignored - Mobills xlsx exports live here, named YYYYMMDD.xlsx
└── tests/
    └── app/                         # pytest tests (currently a placeholder)
```

## Architecture: the Operator pipeline

Every transformation on the transaction data implements the `Operator` ABC
(`utils/operators/__init__.py`): a single `.data -> pd.DataFrame` property. Operators wrap
other operators, so a pipeline reads as nested constructors, e.g.:

```python
loader = ldr.ProcessedLoader()  # load + apply all business rules
loader = Diluter(loader)  # optionally explode diluted rows over 12mo
expenses = fl.ExpensesFilter(loader)  # Value < 0 only
expenses = tr.Inverter(expenses)  # flip sign for chart display
monthly = agg.MonthlyCategoryAggregator(expenses)  # group by Month + Category
```

Four operator kinds, each in its own module under `utils/operators/`:

- **Loaders** (`loader.py`): read the Excel file, preprocess it, apply business rules
- **Filters** (`filter.py`): row subsets (expenses/incomes, date ranges)
- **Aggregators** (`aggregator.py`): group + sum `Value` by one or more columns
- **Transformers** (`transformer.py`): reshape without filtering (invert sign, merge frames,
  add a label column, remove rows matching a predicate)

`ProcessedLoader` is the standard entry point every screen should start from - it chains
`Loader → PreProcessedLoader → DilutionAssigner → TierAssigner → TripBalanceCalculator`, so
every downstream operator sees rows already carrying `Dilution`, `Tier`, and trip-fund-adjusted
values. See the `niffler-business-rules` skill and `docs/business_rules/` for what each rule
actually does - read those, and the rule doc closest to what you're changing, before editing
anything under `utils/business/`.

## Commands

Run everything from the repo root unless noted. Requires `uv` (see
`~/.claude/rules/tooling/tooling.md` for general `uv` conventions).

```bash
# Install dependencies
uv sync --all-extras --all-groups

# Run the app (must run from src/app/ - screens/utils are imported as top-level packages,
# and data loading resolves the relative path data/????????.xlsx from the cwd)
cd src/app && uv run streamlit run main.py

# Run tests
uv run pytest tests/ -v

# Lint
uvx ruff check

# Format
uvx ruff format
```

## Data

- Weekly routine and file naming convention: see [`README.md`](README.md).
- Input is a single Excel file per snapshot, at `src/app/data/YYYYMMDD.xlsx` (gitignored -
  real financial data never gets committed). `get_latest_data_path()` (`utils/__init__.py`)
  always picks the lexicographically-latest filename, i.e. the most recent date.
- Two sheets are read: `"Receitas e Despesas"` (all transactions, the main dataset) and
  `"Transfers"` (used only by `TripBalanceCalculator` for trip-fund transfers - see
  [`docs/business_rules/travel.md`](docs/business_rules/travel.md)).
- `src/app/data/tiers.xlsx` / `tiers_old.xlsx` are present locally but unreferenced by any code
  - tier assignment is fully rule-based in `tiers.py`, not read from a spreadsheet.

## Review cadence

The app is built around a recurring personal review process (biweekly / monthly / yearly), not
a passive dashboard. See [`management-system.md`](management-system.md) for the actual routine
and the category actionability ranking it references (also documented in
[`docs/business_rules/categories.md`](docs/business_rules/categories.md)).

## Known gaps (tracked in `docs/backlog.md`)

- `yearly_view.py`, `patrimony.py`, `validation.py` are stub pages (no content yet).
- Most KPI targets are unset (`None`) placeholders - see
  [`docs/business_rules/kpis.md`](docs/business_rules/kpis.md) for the intended values.
- `CATEGORY_BUDGETS` is a flat placeholder (every category = R$1,000).
- No custom date-range picker; only preset ranges (This Month, Last 3 Months, etc.).
- No automated tests covering business rules yet (`tests/app/test_app.py` is a placeholder).

## Documentation upkeep

- Update [`docs/business_rules/`](docs/business_rules/) **before** changing the corresponding
  logic in `utils/business/` - keep the rule and the code in sync.
- Update this file and `README.md` if commands, structure, or the tech stack change.
