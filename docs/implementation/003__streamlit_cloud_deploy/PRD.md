# Feature: Deploy niffler to Streamlit Community Cloud

## Overview

`docs/implementation/001__infra/PRD.md` and `002__cdk_migration/PRD.md` set up the AWS side (S3
data buckets, per-environment IAM identities) on the premise that the app itself would run on
**Streamlit Community Cloud**, not AWS. This PRD documents that deployment: the app now runs
publicly at `mojo-niffler.streamlit.app`, tracking the `main` branch, backed by the `prod`
environment's bucket and credentials.

## Environment choice

Three environments exist (`dev`/`demo`/`prod`); only `dev` had Streamlit secrets wired up before
this change (used for local development). This deployment targets **`prod`** - the natural choice
for the one public, always-on instance of a personal finance app the user actually reviews data
in, as opposed to `dev`'s throwaway/local-iteration credentials.

## No CLI or API for Community Cloud

Unlike the AWS side, Streamlit Community Cloud has no CLI or public API for creating an app,
connecting a repo, or writing secrets - the entire flow (GitHub OAuth, repo/branch/main-file
selection, custom subdomain, the Secrets editor) is a web UI at `share.streamlit.io`. This
deployment was driven through that UI via Claude Code's Chrome browser automation, not scripted.

## Dependency file fix (`src/app/requirements.txt`)

Community Cloud looks for a dependency file in the entrypoint's directory first, then the repo
root, and uses the first one found from this priority list: `uv.lock` > `Pipfile` >
`environment.yml` > `requirements.txt` > `pyproject.toml`. The repo root's `uv.lock` would
otherwise win - but `pyproject.toml`'s app dependencies live under
`[project.optional-dependencies].app` (kept separate from the `infra` extra so local infra-only
work doesn't need `streamlit`/`pandas`/etc. installed), and a plain lockfile sync does not pull in
optional extras by default. That would leave Community Cloud unable to even import `streamlit`.

Fixed by adding `src/app/requirements.txt`, pinned identically to `[project.optional-dependencies]
app` in `pyproject.toml`. Sitting next to `main.py`, it's found before the root `uv.lock` and
installed directly - no change to `pyproject.toml`, `uv.lock`, or the local `uv sync --all-extras
--all-groups` workflow. Keep the two lists in sync by hand when app dependencies change.

## Credential runbook executed for `prod`

Followed `infra/README.md`'s "Access keys are outside IaC" runbook:

```bash
aws iam create-access-key --user-name niffler-prod-app --profile fmassa
aws ssm put-parameter --name /config/niffler_prod/app-access-key-id \
  --type String --value <AccessKeyId> --profile niffler-infra
aws ssm put-parameter --name /config/niffler_prod/app-secret-access-key \
  --type SecureString --value <SecretAccessKey> --profile niffler-infra
```

The same key pair was then pasted into Community Cloud's Secrets UI (not committed anywhere) as:

```toml
[aws]
access_key_id = "..."
secret_access_key = "..."
region = "us-east-2"
bucket_name = "niffler-prod-data-309917471802"
data_prefix = "snapshots"
```

`demo` still has no key minted and no Streamlit deployment - deferred until it actually needs one,
per `infra/README.md`.

## App configuration on Community Cloud

| Setting          | Value                          |
| ----------------- | ------------------------------- |
| Repository         | `felipediasmassa97/niffler`    |
| Branch              | `main`                          |
| Main file path      | `src/app/main.py`               |
| Custom app URL      | `mojo-niffler.streamlit.app`    |
| Python version      | 3.13                             |

## Data upload target

The weekly upload routine (`README.md`) still targets `dev`'s bucket by default for local
iteration. To update the data the live app serves, upload to `prod` instead:

```bash
aws s3 cp <report>.xlsx s3://niffler-prod-data-309917471802/snapshots/ --profile niffler-infra
```
