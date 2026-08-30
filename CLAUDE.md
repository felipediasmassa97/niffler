# niffler

Personal financial tracking dashboard. A Streamlit app reads a manually-exported Mobills Excel
report, applies a set of financial business rules (dilution, tiers, trip-fund accounting), and
renders monthly/yearly views and KPI cards to support a recurring personal finance review.

There is no backend, database, or auth - it's a single-user app that reads one Excel snapshot from
S3 per run. It's deployed publicly on Streamlit Community Cloud (see "Data" below), though only
the user has any reason to open it.

## Tech stack

- Python >=3.14, managed with `uv`
- Streamlit (`st.navigation` multi-page app) for the UI
- pandas for data processing, `openpyxl` for reading `.xlsx`
- Plotly for charts
- `unidecode` for accent/case-insensitive category matching
- AWS CDK (Python) for infra IaC, deployed with the npm-installed CDK CLI

## Project structure

```
niffler/
├── cdk.json, package.json, .nvmrc   # CDK app entrypoint config + pinned CDK CLI
├── docs/
│   ├── business_rules/              # human-readable business rule docs, one file per domain
│   └── implementation/
│       ├── 001__infra/              # PRD for the original AWS infra design (buckets, IAM chain)
│       ├── 002__cdk_migration/      # PRD for the Terraform -> CDK migration (current IaC tool)
│       └── 003__streamlit_cloud_deploy/  # PRD for the Streamlit Community Cloud deployment
├── infra/
│   ├── app.py                      # CDK entrypoint - one env's stack per invocation (ENVIRONMENT)
│   ├── infra_stack.py              # InfraStack: data bucket + Streamlit app IAM user
│   ├── resource_utils.py           # name/account/region accessors - source of truth for names
│   └── bootstrap/                  # one-time, admin-only: IAM role chain + CDKToolkit stack
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
│       ├── requirements.txt         # app deps for Streamlit Community Cloud, mirrors pyproject's
│       │                            # `app` extra - see docs/implementation/003__streamlit_cloud_deploy
│       └── .streamlit/secrets.toml  # gitignored - AWS credentials, see "Data" below
└── tests/
    └── app/                         # pytest tests
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

# Run the app (must run from src/app/ - screens/utils are imported as top-level packages).
# Requires a populated src/app/.streamlit/secrets.toml (AWS credentials) and network access
# to AWS - the app reads its data from S3, not local disk. See "Data" below.
cd src/app && uv run streamlit run main.py

# Run tests
uv run pytest tests/ -v

# Lint
uvx ruff check

# Format
uvx ruff format

# Infra: diff/deploy one environment's CDK stack (see infra/README.md for the full runbook)
ENVIRONMENT=dev uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
ENVIRONMENT=dev uv run --no-sync npx cdk deploy --profile niffler-infra --no-notices
```

## Data

- Weekly routine and upload convention: see [`README.md`](README.md).
- Input is a single Excel snapshot per environment, read from S3 (never local disk) - see
  [`docs/implementation/001__infra/PRD.md`](docs/implementation/001__infra/PRD.md) for the
  original infra design (buckets, IAM, the two-hop role chain) and
  [`docs/implementation/002__cdk_migration/PRD.md`](docs/implementation/002__cdk_migration/PRD.md)
  for the current IaC tool (AWS CDK). `get_latest_snapshot()` (`utils/__init__.py`) lists
  `<bucket>/snapshots/*` and picks the lexicographically-latest key (i.e. the most recent
  `YYYYMMDD.xlsx`), then reads the object body - mirroring the old local-disk `glob(...) + max()`
  behavior exactly. Bucket/prefix/region/credentials come from `st.secrets["aws"]`, populated in
  `src/app/.streamlit/secrets.toml` locally (gitignored) or the Streamlit Cloud Secrets UI when
  deployed.
- Three environments exist (`dev`/`demo`/`prod`, each with its own bucket + IAM identity); local
  development targets `dev`. The live Streamlit Community Cloud deployment
  (`niffler.streamlit.app`, see
  [`docs/implementation/003__streamlit_cloud_deploy/PRD.md`](docs/implementation/003__streamlit_cloud_deploy/PRD.md))
  targets `prod`. `demo` has no key minted and no deployment yet.
- **Access keys are never managed by IaC** - CDK defines the IAM users only; keys are minted by
  hand and stored in Parameter Store under `/config/niffler_<env>/` before being copied into
  Streamlit secrets. See `infra/README.md`'s credential runbook.
- `niffler-infra-execution-role` is assumed **only** by CloudFormation - never directly by a
  human, matching `tfmcdigital/edap-iam`'s pattern. There is no `niffler-infra-exec` CLI profile;
  manual operations (`aws s3 cp`, `aws ssm put-parameter`) run as `--profile niffler-infra`
  directly, which carries its own scoped S3/SSM permissions for exactly that purpose.
- The `AppName = niffler` tag on both chain roles (`niffler-infra`,
  `niffler-infra-execution-role`) is load-bearing - every IAM statement in
  `infra/bootstrap/bootstrap.sh` is scoped by `${aws:PrincipalTag/AppName}` rather than a
  hand-enumerated ARN list. An untagged role is denied everything.
- The `CDKToolkit` stack (CDK's own deploy-time infra: staging bucket, IAM roles, ECR) is
  account-level infrastructure, not defined anywhere in `infra/` - see
  `infra/bootstrap/README.md` for how and when it's (re)created.
- Two sheets are read: `"Receitas e Despesas"` (all transactions, the main dataset) and
  `"Transfers"` (used only by `TripBalanceCalculator` for trip-fund transfers - see
  [`docs/business_rules/travel.md`](docs/business_rules/travel.md)).
- `tiers.xlsx` / `tiers_old.xlsx` (formerly under `src/app/data/`) are unreferenced by any code
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
