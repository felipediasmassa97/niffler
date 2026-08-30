# Backlog

## General

- GN-01: Turn fixits into to-dos

- GN-02: Add view with both non-diluted and diluted (in same page, side-by-side)

## Data Pipeline

- DP-01:
  - Add async data project
  - Load latest report from S3 not repo
  - Create lambda function that reads Excel file in S3 and syncs state to database (upserts + delete data in database)
  - To start, no need to fetch reports from Mobills automatically

- DP-02:
  - Fetch Mobills reports automatically weekly, dump to S3 raw report

## Harness

## Cloud

- CL-01: Migrate to cloud
  - [x] AWS with CDK (Python) for IaC (`infra/`, three env stacks: dev/demo/prod)
  - [ ] Check appropriate database (pricing) - deferred, no database yet
  - [x] Set up profiles (`fmassa` SSO -> `niffler-infra`; `niffler-infra-execution-role` is
        assumed only by CloudFormation, never directly by a human)
  - [ ] Check billing periodically
  - [x] App in Streamlit Cloud not AWS (infra only hosts data + IAM, no compute)
  - [x] Set up AWS auth in Streamlit Cloud secrets (`dev` wired; `demo`/`prod` deferred until
        those environments actually get a Streamlit Cloud deployment)
  - [x] S3 in infra stack (database still deferred, no lambda)
  - See `docs/implementation/001__infra/PRD.md` for the original design and
    `docs/implementation/002__cdk_migration/PRD.md` for the Terraform -> CDK migration.

- CL-02: Set up CICD
  - Shape is already visible in the reference repos this migration drew from: `cdk diff` then
    `cdk deploy` with `ENVIRONMENT` set per job, and a GitHub-OIDC trust statement added to the
    `niffler-infra` role's trust policy (see `edap-iam`'s `role/main.tf` federated-principal
    pattern, omitted from `infra/bootstrap/bootstrap.sh` for now since there is no CI yet)

- CL-03: Add auth to cloud
  - Allowed emails as AWS parameter

- CL-04: Narrow fmassa SSO permission set away from AdministratorAccess
  - Needed to make the niffler-infra-role chain a real technical boundary rather than just a
    workflow convention (see "SSO role scope" in `docs/implementation/001__infra/PRD.md`)

## Tests

- TS-01: Create automated tests based on business rules
  - Freeze mock data locally
  - Have Claude set up consistency tests for each business rule

- TS-02: Create playwright tests
  - Goal: assert app renders without error

## User Experience

- UX-01: Improve plotly tooltips
