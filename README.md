# niffler

Financial Tracking

## Weekly Routine

- Log in to (Mobills)[https://mobills.com]
- Sidebar -> export transactions
- Date range from 01-Jan-2023 until end of current month
- Download Excel report
- Upload it to S3, named `YYYYMMDD.xlsx`, under the `dev` bucket's `snapshots/` prefix (this step
  is manual - see `docs/implementation/001__infra/PRD.md`):
  ```bash
  aws s3 cp <report>.xlsx s3://niffler-dev-data-309917471802/snapshots/ --profile niffler-infra-exec
  ```

## Running

The app reads its data from S3 - no local file is needed. Requires a populated
`src/app/.streamlit/secrets.toml` (see `infra/envs/dev`'s Terraform outputs for the
`niffler-streamlit-app-dev` credential) and network access to AWS.

```bash
uv sync --all-extras --all-groups
cd src/app && uv run streamlit run main.py
```
