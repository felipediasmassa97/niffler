# niffler

Financial Tracking

## Weekly Routine

- Log in to (Mobills)[https://mobills.com]
- Sidebar -> export transactions
- Date range from 01-Jan-2023 until end of current month
- Download Excel report
- Save report in `src/app/data/` with naming like YYYYMMDD.xlsx

## Running

```bash
uv sync --all-extras --all-groups
cd src/app && uv run streamlit run main.py
```
