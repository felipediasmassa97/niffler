# niffler

Financial Tracking

## Live App

The app is deployed on Streamlit Community Cloud at
[niffler.streamlit.app](https://niffler.streamlit.app), tracking the `main` branch and
reading from the `prod` bucket. See
[`docs/implementation/003__streamlit_cloud_deploy/PRD.md`](docs/implementation/003__streamlit_cloud_deploy/PRD.md)
for how it's configured.

## Weekly Routine

- Log in to (Mobills)[https://mobills.com]
- Sidebar -> export transactions
- Date range from 01-Jan-2023 until end of current month
- Download Excel report
- Upload it to S3, named `YYYYMMDD.xlsx`, under the target environment's `snapshots/` prefix (this
  step is manual - see `docs/implementation/001__infra/PRD.md`). Use `prod` to update the live
  app, `dev` when iterating locally:
  ```bash
  aws s3 cp <report>.xlsx s3://niffler-prod-data-309917471802/snapshots/ --profile niffler-infra
  ```

## Running

The app reads its data from S3 - no local file is needed. Requires a populated
`src/app/.streamlit/secrets.toml` (see `infra/README.md`'s credential runbook for the
`niffler-dev-app` access key) and network access to AWS.

```bash
uv sync --all-extras --all-groups
cd src/app && uv run streamlit run main.py
```
