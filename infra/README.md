# infra

AWS CDK (Python) app managing niffler's data buckets and Streamlit IAM users, one environment per
stack. See `docs/implementation/002__cdk_migration/PRD.md` for the full design and migration
history, and `infra/bootstrap/README.md` for the one-time account setup this app depends on.

## Layout

- `app.py` - entrypoint (`python -m infra.app`). Synthesizes exactly one environment's stack per
  invocation, selected by the `ENVIRONMENT` variable.
- `infra_stack.py` - `InfraStack`: one data bucket + one Streamlit app IAM user per environment.
- `resource_utils.py` - name/account/region accessors. The single source of truth for every
  physical resource name.
- `bootstrap/` - account-level setup (the IAM role chain, the `CDKToolkit` stack). Run once,
  before this app can deploy anything.

## Prerequisites

```bash
uv sync --all-extras --all-groups   # installs aws-cdk-lib + constructs (the `infra` extra)
npm install                          # installs the pinned CDK CLI (package.json)
```

Both from the repo root - `cdk.json`'s `"app": "python -m infra.app"` only resolves
`infra.resource_utils`/`infra.infra_stack` when run from there, and `cdk.out/`/`node_modules/`
live at the root too.

## Commands

Every command needs `ENVIRONMENT` set to one of `dev`, `demo`, `prod`, and runs as the
`niffler-infra` profile (see `bootstrap/README.md` for how that profile is set up):

```bash
ENVIRONMENT=dev uv run --no-sync npx cdk synth --no-notices   # render the template, no AWS calls
ENVIRONMENT=dev uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
ENVIRONMENT=dev uv run --no-sync npx cdk deploy --profile niffler-infra --no-notices
```

Always `diff` before `deploy`. An unrecognised `ENVIRONMENT` fails immediately in
`resource_utils.get_env()`, before any AWS call is made.

CloudFormation assumes `niffler-infra-execution-role` as every stack's service role (configured
via `DefaultStackSynthesizer(cloud_formation_execution_role=..., qualifier="toolkitv2")` in
`app.py`) - this is what preserves the project's two-hop identity chain. The execution role is
trusted **only** by the CloudFormation service principal, matching `tfmcdigital/edap-iam`'s
pattern exactly: a human never assumes it directly, even for manual operations. For the manual
S3/Parameter Store work niffler's workflow needs (edap-iam's apps have no equivalent - everything
there goes through CI), the human-assumable `niffler-infra` role carries its own scoped S3 and SSM
permissions instead - a deliberate, documented deviation from the reference pattern.

## Access keys are outside IaC

CDK defines the `niffler-<env>-app` IAM **users** only - never their access keys.
`AWS::IAM::AccessKey` can only expose its secret through a stack Output (plaintext in
`describe-stacks`), and the execution role's policy deliberately excludes every
`iam:*AccessKey` action, so CloudFormation could not create one even if the stack asked it to.

To mint or rotate a key:

```bash
aws iam create-access-key --user-name niffler-<env>-app --profile fmassa
```

Then store both values yourself in Parameter Store, under `/config/niffler_<env>/`:

```bash
aws ssm put-parameter --name /config/niffler_<env>/app-access-key-id \
  --type String --value <AccessKeyId> --profile niffler-infra
aws ssm put-parameter --name /config/niffler_<env>/app-secret-access-key \
  --type SecureString --value <SecretAccessKey> --profile niffler-infra
```

(`niffler-infra` can read/write under `/config/niffler_*` - see the `InfraSsm` statement in
`bootstrap/bootstrap.sh`.) Copy the same values into that environment's Streamlit secrets
(`src/app/.streamlit/secrets.toml` locally, or the Streamlit Cloud Secrets UI when deployed) - the
app reads credentials from `st.secrets`, not from Parameter Store directly. Wiring the app to read
from Parameter Store instead is deferred until `DP-01`'s sync Lambda needs it.

## Names that must not change

Every physical name below is depended on by live Streamlit secrets or the weekly upload routine.
`tests/infra/test_infra_stack.py` asserts all of them offline. The data bucket's name dates back to
the original Terraform resources; the app user was renamed once already
(`niffler-streamlit-app-<env>` -> `niffler-<env>-app`, August 2026) - see the migration history
below.

| Resource              | Name                                |
| --------------------- | ------------------------------------ |
| Stack                 | `niffler-infra-stack-<env>`         |
| Data bucket           | `niffler-<env>-data-309917471802`   |
| App user              | `niffler-<env>-app`                 |
| User's inline policy  | `niffler-<env>-app-read-snapshots`  |

## Migration history

These resources were originally created by Terraform and brought into CDK via `cdk import` in
August 2026 - nothing was destroyed or recreated. That import is a one-time historical event: once
imported, CloudFormation treats a resource exactly like any other stack member (`UPDATE_COMPLETE`,
not a lingering import state), so ordinary `cdk deploy` works from here on with no special
handling. See the PRD for the full account-by-account migration record.

The app user was renamed `niffler-streamlit-app-<env>` -> `niffler-<env>-app` shortly after,
across all three environments. `AWS::IAM::User` treats a `UserName` change as a replacement, and
`RemovalPolicy.RETAIN` meant the old user was orphaned rather than deleted by the deploy - each was
then removed by hand (`aws iam delete-user`, after deactivating and deleting its access key and
inline policy). `dev`'s access key was live in `secrets.toml`; a replacement key was minted for
`niffler-dev-app` and swapped in before the old user was deleted, so the running app never lost
credentials. `demo`/`prod` had no dependents on their old keys.
