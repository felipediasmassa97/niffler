# Backlog

## General

- GN-01: Turn fixits into to-dos

- GN-02: Add view with both non-diluted and diluted (in same page, side-by-side)

## Data Pipeline

- DP-01:
  - Add async data projec
  - Load latest report from S3 not repo
  - Create lambda function that reads Excel file in S3 and syncs state to database (upserts + delete data in database)
  - To start, no need to fetch reports from Mobills automatically

- DP-02:
  - Fetch Mobills reports automatically weekly, dump to S3 raw report

## Harness

## Cloud

- CL-01: Migrate to cloud
  - AWS with Terraform for IaC
  - Check appropriate database (pricing)
  - Set up profiles
  - Check billing periodically
  - App in Streamlit Cloud not AWS
  - Set up AWS auth in Streamlit Cloud secrets
  - S3 + database in infra stack (no lambda in start)

- CL-02: Add auth to cloud
  - Allowed emails as AWS parameter

## Tests

- TS-01: Create automated tests based on business rules
  - Freeze mock data locally
  - Have Claude set up consistency tests for each business rule

- TS-02: Create playwright tests
  - Goal: assert app renders without error

## User Experience

- UX-01: Improve plotly tooltips
