# Backlog

## General

- [ ] Turn fixits into to-dos

- [ ] Add view with both non-diluted and diluted (in same page, side-by-side)

## Data Pipeline

- [ ] Automated data project
  - Load latest report from S3 not repo
  - Create lambda function that reads Excel file in S3 and syncs state to database (upserts + delete data in database)
  - To start, no need to fetch reports from Mobills automatically
  - Check appropriate database (pricing) - deferred, no database yet
  - Lambda function upserting from S3 bucket to database
  - Must be idempotent
  - Must keep, add, update or delete items from the same time window (e.g. if two reports cover the same day, the latest wins on all additions and deletions)

- [ ] Automate Mobills reports
  - Fetch Mobills reports automatically weekly, dump to S3 raw report

## Cloud

- [x] Migrate to cloud
  - AWS with CDK (Python) for IaC (`infra/`, three env stacks: dev/demo/prod)
  - Set up profiles (`fmassa` SSO -> `niffler-infra`; `niffler-infra-execution-role` is assumed only by CloudFormation, never directly by a human)
  - App in Streamlit Cloud not AWS (infra only hosts data + IAM, no compute)
  - Set up AWS auth in Streamlit Cloud secrets (`dev` wired; `demo`/`prod` deferred until those environments actually get a Streamlit Cloud deployment)
  - S3 in infra stack (database still deferred, no lambda)

- [x] Streamlit Cloud app

- [ ] Set up CICD
  - Shape is already visible in the reference repos this migration drew from: `cdk diff` then `cdk deploy` with `ENVIRONMENT` set per job, and a GitHub-OIDC trust statement added to the `niffler-infra` role's trust policy (see `edap-iam`'s `role/main.tf` federated-principal pattern, omitted from `infra/bootstrap/bootstrap.sh` for now since there is no CI yet)

- [ ] Add auth to cloud
  - Google Mail integration
  - Allowed emails as AWS parameter

- [ ] Automate and centralize bootstrap
  - Dedicated repo to manage creation of infra and execution role in all AWS projects
  - This repository manages policies for infra and execution roles (similar to edap-iam)

- [ ] Narrow fmassa SSO permission set away from AdministratorAccess
  - Needed to make the niffler-infra-role chain a real technical boundary rather than just a
    workflow convention (see "SSO role scope" in `docs/implementation/001__infra/PRD.md`)

- [ ] Billing
  - Check billing periodically

## Tests

- [ ] Create automated tests based on business rules
  - Freeze mock data locally
  - Have Claude set up consistency tests for each business rule

- [ ] Create playwright tests
  - Goal: assert app renders without error

## User Experience

- [ ] Improve plotly tooltips
