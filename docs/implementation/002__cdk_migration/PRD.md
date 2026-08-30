# Feature: Migrate niffler's AWS infra from Terraform to AWS CDK

> **Trust model superseded post-migration.** This PRD documents (and the migration executed) a
> `niffler-infra-exec` human CLI profile chained through `niffler-infra-execution-role`'s trust
> policy. That was deliberately changed afterward, at the user's explicit direction, to match
> `tfmcdigital/edap-iam`'s pattern exactly: the execution role now trusts only the CloudFormation
> service principal, never a human. The manual S3/Parameter Store capability the CLI profile
> existed for moved to `niffler-infra` itself instead. Every mention below of
> `niffler-infra-exec`, or of `niffler-infra` assuming the execution role, is historical - see
> `infra/bootstrap/README.md`'s "A deliberate deviation from edap-iam" section for the current
> model.

## Overview

`docs/implementation/001__infra/PRD.md` shipped niffler's AWS footprint — three per-environment
S3 data buckets, three per-environment read-only Streamlit IAM identities, and a two-hop IAM role
chain in front of them — managed by Terraform under `infra/`, with three S3 state buckets created
by a one-time `infra/bootstrap/bootstrap.sh`.

This PRD replaces Terraform with **AWS CDK (Python)** for the resources Terraform actually
manages, and removes every Terraform artifact afterwards. Two reference repos set the house
conventions it follows:

- **`tfmcdigital/kb-rma`** — the CDK app layout: `app.py` / `infra_stack.py` / `resource_utils.py`,
  one environment per synth, `DefaultStackSynthesizer` with a `toolkitv2` qualifier, npm-pinned
  CDK CLI, `[project.optional-dependencies] infra`.
- **`tfmcdigital/edap-iam`** — how the org builds the `{service}-infra` / `{service}-infra-execution-role`
  pair: the split of responsibility between them, and `aws:PrincipalTag/AppName` as the scoping
  mechanism for every policy.

**This is a tooling swap, not a redesign.** Every architectural decision from 001 is preserved:
same account (`309917471802`), same region (`us-east-2`), same three environments, same bucket
names, same IAM user names, same inline-policy names, same `snapshots/` prefix, the same two-hop
chain, same Streamlit Cloud hosting model.

**Zero application-code changes and zero credential changes.** `get_latest_snapshot()`
(`src/app/utils/__init__.py`) is untouched, and `src/app/.streamlit/secrets.toml` keeps working
with the credential it already holds — because nothing is destroyed and access keys stay outside
IaC entirely.

Three constraints drive the execution plan:

1. **Nothing is destroyed.** Every Terraform-managed resource is brought under CDK with
   `cdk import` (CloudFormation resource import), then dropped from Terraform state with
   `terraform state rm`. No bucket or user is ever deleted and recreated. This eliminates data
   loss and S3's documented _"the name might not become available immediately, and in some cases
   might not become available again at all"_ (`bucketnamingrules.md`) in one move.
2. **No lockout.** Permissions on the chain roles are added before any are revoked, and the roles
   themselves are never deleted or replaced.
3. **`dev` is a complete, verifiable slice with an explicit go/no-go gate.** `demo` and `prod` are
   not touched until `dev` is imported, drift-clean, and the live Streamlit app is confirmed
   loading its latest snapshot. The house one-environment-per-synth model (`ENVIRONMENT` env var)
   makes this the natural way to work rather than a special case.

## Reversals from earlier drafts of this PRD

The reference repos settle several questions that earlier revisions answered differently. Each
reversal is recorded so the history stays legible.

### From `tfmcdigital/kb-rma` (CDK app layout)

| #   | Earlier decision                                                    | Now                                                                                                          | Why                                                                                                                               |
| --- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Hand-written CloudFormation YAML templates                          | AWS CDK (Python)                                                                                             | User direction                                                                                                                    |
| R2  | Destroy and recreate every resource                                 | `cdk import`, nothing destroyed                                                                              | S3 global-namespace risk is unrecoverable; see "Why import"                                                                       |
| R3  | `for env in ENVIRONMENTS: ...` — three stacks per synth             | **One environment per synth**, selected by `ENVIRONMENT` and validated in `resource_utils.get_env()`         | House convention; also matches dev→gate→demo/prod sequencing                                                                      |
| R4  | `CliCredentialsStackSynthesizer`, no `cdk bootstrap`                | **`DefaultStackSynthesizer(cloud_formation_execution_role=..., qualifier="toolkitv2")`, bootstrap required** | House convention, independently confirmed by `edap-iam`'s `cdk-infra` policy                                                      |
| R5  | Everything in `app.py` + `infra_stack.py`                           | **Third module `infra/resource_utils.py`** plus `infra/__init__.py`                                          | House convention                                                                                                                  |
| R6  | Evaluate `aws-cdk-cli` from PyPI                                    | **CDK CLI from npm**, pinned in `package.json`, invoked as `uv run --no-sync npx cdk`                        | House convention. Question dropped                                                                                                |
| R7  | `[dependency-groups] infra` + `[tool.uv] default-groups`            | **`[project.optional-dependencies] infra`**, `uv sync --extra infra`; `aws-cdk-lib` pinned exactly           | House convention                                                                                                                  |
| R8  | `cdk.json` inside `infra/`                                          | **`cdk.json` at the repo root**, `"app": "python -m infra.app"`; `infra/` is an importable package           | House convention. Side benefit: the entrypoint is `infra.app`, so it cannot collide with niffler's runtime `app` package          |
| R9  | A `NifflerIamChainStack` importing and managing the two chain roles | **Dropped.** The chain roles stay bootstrap-managed platform infrastructure                                  | The roles are **not** in Terraform state (verified below), and both references treat `{app}-infra-execution-role` as pre-existing |
| R10 | `infra/bootstrap/` deleted entirely                                 | **Survives, rewritten**                                                                                      | Follows from R9                                                                                                                   |
| R11 | Stack names `niffler-{dev,demo,prod}`                               | **`niffler-infra-stack-<env>`** via `get_resource_name(f"{APP_NAME}-infra-stack")`                           | House convention. Stack names are new, so this does not conflict with preserving Terraform _resource_ names                       |
| R12 | `cfn-lint` as the validation gate                                   | `cdk synth`, then `cdk diff` before every `cdk deploy`                                                       | CDK makes `cfn-lint` redundant; `diff`-then-`deploy` mirrors the reference CI                                                     |

### From `tfmcdigital/edap-iam` (IAM policies)

| #   | Earlier decision                                                                                                                                             | Now                                                                                                                                             | Why                                                                                                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R13 | Every policy scoped by hand-enumerating three per-env ARNs (`.../niffler-dev-data-...`, `.../niffler-demo-data-...`, ...)                                    | **`aws:PrincipalTag/AppName` scoping** — roles tagged `AppName = niffler`, policies written generically against `${aws:PrincipalTag/AppName}-*` | House mechanism. Satisfies 001's no-`Resource: "*"` criterion with no per-env duplication and no policy edit when an environment is added                                                                                     |
| R14 | Parameter Store naming `/niffler/<env>/streamlit-app/{access-key-id,secret-access-key}`                                                                      | **`/config/niffler_<env>/streamlit-app-{access-key-id,secret-access-key}`**                                                                     | House convention (`infra-ssm` scopes to `parameter/config/${aws:PrincipalTag/AppName}*`; kb-rma reads `/config/{app}_{env}/<name>`). **Settled by convention — this replaces the open question the user was asked to answer** |
| R15 | `cloudformation:DeleteStack` deliberately withheld from the infra role; termination protection used instead                                                  | **Granted**, along with `UpdateTerminationProtection`, `ContinueUpdateRollback`, `CancelUpdateStack`                                            | House `cdk-infra` grants them, and `cdk deploy` genuinely needs `DeleteStack` to clean up a `ROLLBACK_COMPLETE` stack before retrying. `RemovalPolicy.RETAIN` on the buckets is the real data guard                           |
| R16 | Credential runbook mints keys as `--profile niffler-infra-exec`                                                                                              | **Mints as `--profile fmassa`**; the execution role deliberately gets **no** `iam:CreateAccessKey`                                              | The execution role can create and configure the _user_ but can never mint a credential for it — a genuine separation improvement. Storing the parameters still runs as `niffler-infra-exec` (house `infra-ssm`)               |
| R17 | Infra role trust hardcodes the SSO permission-set ARN including its Identity Center hash (`AWSReservedSSO_AdministratorAccess_c757f68eab8e5de2`), as 001 did | **Account-root principal gated by `ArnLike` on `aws:PrincipalArn`** matching `.../AWSReservedSSO_AdministratorAccess_*`                         | House pattern, and strictly better: survives the permission set being recreated. 001 explicitly documented having to look the hash up                                                                                         |

Everything else stands: import rather than recreate, exact Terraform resource names preserved,
access keys outside IaC, the service-role deploy model, the `dev` gate, grant-first/revoke-last on
the tfstate permissions, and the repo/docs cleanup.

## Current State (verified against the live account and toolchain on 2026-08-23)

**Buckets (6):**

| Bucket                                         | Contents                                                                                                                                |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `niffler-dev-data-309917471802`                | 1 object version, `snapshots/20260822.xlsx` (5410 B), currently shadowed by a delete marker — the Task-006 verification object from 001 |
| `niffler-demo-data-309917471802`               | empty (no versions, no delete markers)                                                                                                  |
| `niffler-prod-data-309917471802`               | empty (no versions, no delete markers)                                                                                                  |
| `niffler-{dev,demo,prod}-tfstate-309917471802` | Terraform state + lock files                                                                                                            |

**Terraform state — identical 9 addresses in all three environments** (`terraform state list` run
in each of `infra/envs/{dev,demo,prod}`):

```
module.data_bucket.aws_s3_bucket.this
module.data_bucket.aws_s3_bucket_lifecycle_configuration.this
module.data_bucket.aws_s3_bucket_public_access_block.this
module.data_bucket.aws_s3_bucket_server_side_encryption_configuration.this
module.data_bucket.aws_s3_bucket_versioning.this
module.streamlit_iam.data.aws_iam_policy_document.read_snapshots
module.streamlit_iam.aws_iam_access_key.streamlit_app
module.streamlit_iam.aws_iam_user.streamlit_app
module.streamlit_iam.aws_iam_user_policy.read_snapshots
```

**The two chain roles are NOT Terraform-managed — verified.** They appear in no environment's
state list, and the only mention of them anywhere in `infra/envs/` or `infra/modules/` is as a
_consumed_ ARN string in each `providers.tf`:

```hcl
role_arn = "arn:aws:iam::${var.account_id}:role/niffler-infra-execution-role"
```

They were created by `infra/bootstrap/bootstrap.sh` via the AWS CLI, exactly as 001 designed.
Live configuration:

|                  | `niffler-infra-role`                                                                  | `niffler-infra-execution-role`                                                  |
| ---------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `RoleId`         | `AROAUQKEFKQ5HZQ7A53DP`                                                               | `AROAUQKEFKQ5GDTMFWJ3K`                                                         |
| Trust principal  | the SSO `AdministratorAccess` role ARN, hash included, single statement, **no `Sid`** | `arn:aws:iam::309917471802:role/niffler-infra-role`, single statement, no `Sid` |
| Inline policy    | `niffler-infra-role-permissions`                                                      | `niffler-infra-execution-role-permissions`                                      |
| Managed policies | none                                                                                  | none                                                                            |
| **Tags**         | **none**                                                                              | **none**                                                                        |
| Other            | `MaxSessionDuration` 3600, `Path` `/`                                                 | `MaxSessionDuration` 3600, `Path` `/`                                           |

> **Neither role is tagged today.** Every policy in the new design is scoped by
> `aws:PrincipalTag/AppName`, so **both roles must be tagged `AppName = niffler` before those
> policies are attached**, or every statement evaluates to a non-matching ARN and denies
> everything. This is the single point of failure of the tag mechanism; it gets its own
> acceptance criterion, verification step and risk row.

**IAM users (3, Terraform-managed):** `niffler-streamlit-app-{dev,demo,prod}`, `Path` `/`, tags
`Environment=<env>` / `Project=niffler`, one inline policy
`niffler-streamlit-app-<env>-read-snapshots`, no attached managed policies, exactly one active
access key each (`dev`'s is `AKIAUQKEFKQ5ITANDIW4`, `UserId` `AIDAUQKEFKQ5DESYG4ZWR`).

**Exact live bucket configuration** (`niffler-dev-data-309917471802`; `demo`/`prod` identical
modulo the `Environment` tag) — the CDK code must mirror this exactly, because import records the
template as truth without reconciling:

- Versioning: `Enabled`
- Encryption: `SSEAlgorithm: AES256`, `BucketKeyEnabled: false`; S3 additionally reports
  `BlockedEncryptionTypes: {EncryptionType: [SSE-C]}`
- Public access block: all four `true`
- Ownership controls: `BucketOwnerEnforced` — an S3 account default, **not** set by Terraform
- Lifecycle: one rule, `ID: expire-noncurrent-versions`, `Status: Enabled`,
  `Filter: {Prefix: ""}`, `NoncurrentVersionExpiration: {NoncurrentDays: 90}`; S3 additionally
  reports `TransitionDefaultMinimumObjectSize: all_storage_classes_128K`
- Tags: `Project=niffler`, `Environment=dev`

**Live IAM user policy** (`niffler-streamlit-app-dev-read-snapshots`) — two statements,
`ListSnapshotsPrefix` (`s3:ListBucket` on the bucket ARN, `StringLike s3:prefix = snapshots/*`)
and `ReadSnapshotObjects` (`s3:GetObject` on `<bucket-arn>/snapshots/*`).

**Toolchain, already installed — no new prerequisites:** AWS CLI 2.34.19, Node v22.22.2 (nvm),
CDK CLI 2.1114.1 (global; will be pinned locally), `uv` 0.11.2, Terraform v1.15.9 (needed only
until Task-005). `aws-cdk-lib` **2.266.0** and `constructs` **10.8.1** resolve cleanly on
`requires-python = ">=3.13"` (verified in a throwaway venv). No CloudFormation stacks exist in
`us-east-2` today. `pyproject.toml` already carries `norecursedirs = "cdk.out node_modules"` —
consistent with the reference's **repo-root** `cdk.out`, i.e. the repo was already anticipating
this layout.

### Verified CDK/CloudFormation constraints

1. **Importability** (`aws cloudformation describe-type --type RESOURCE`; importable iff the
   schema declares a `read` handler): `AWS::S3::Bucket` ✅ (`BucketName`), `AWS::IAM::User` ✅
   (`UserName`), `AWS::IAM::Role` ✅ (`RoleName`), `AWS::IAM::Policy` ❌, `AWS::IAM::AccessKey` ❌
   (no handlers at all).
2. **CDK's L2 `iam.User` cannot express an inline policy or tags.** Introspecting
   `aws-cdk-lib` 2.266.0, `iam.User.__init__` accepts only
   `groups, managed_policies, password, password_reset_required, path, permissions_boundary, user_name`
   — no `policies`, no `tags`. Attaching a policy to an L2 `User` emits a **separate
   `AWS::IAM::Policy` resource**, which is not importable and whose name CDK generates.
   `iam.CfnUser` (L1) _does_ accept both. **The Streamlit app user must be `iam.CfnUser`.**
3. **`AWS::SSM::Parameter` cannot create `SecureString` parameters.** CloudFormation's template
   reference states verbatim: _"Parameters of type `SecureString` are not supported by AWS
   CloudFormation"_ — allowed values `String | StringList`. SecureStrings can only be _referenced_.
4. **`cdk import` requires a clean `cdk diff`**: _"the only changes allowed in an import operation
   are the addition of new resources being imported."_ Because access keys stay outside IaC, the
   stack contains only importable resource types, so one `cdk import` pass per environment
   suffices.
5. **`cdk import` "uses the deploy role credentials... requires version 12 of the bootstrap
   template."** Satisfied now that bootstrap is in use (R4).

## Why import, not destroy-and-recreate

From `AmazonS3/latest/userguide/bucketnamingrules.html`:

> _"When a bucket owner deletes their bucket, the bucket name might become available again in the
> global namespace for anyone to re-create. However, the name might not become available
> immediately, and in some cases might not become available again at all."_

and, under **"Don't delete buckets so that you can reuse bucket names"**:

> _"After a bucket is deleted, the name becomes available for reuse. However, you aren't
> guaranteed to be able to reuse the name right away, or at all... In addition, another AWS
> account might create a bucket with the same name before you can reuse the name."_

Preserving the exact names is a hard requirement — they are baked into `secrets.toml`, the
`README.md` upload command, and three IAM policies. Destroy-and-recreate would stake the migration
on an outcome AWS explicitly declines to guarantee, with **no rollback** once the original bucket
is gone. Import issues neither a create nor a delete, preserves object versions, bucket creation
dates and the users' ARNs and unique IDs, and is reversible — `cdk destroy` with
`RemovalPolicy.RETAIN` removes the stack and leaves every resource untouched.

## The chain roles stay out of CDK

`niffler-infra-role` and `niffler-infra-execution-role` are **not** in any Terraform state
(verified above). Two consequences:

- **"Clean up all pre-existing Terraform resources" does not cover them.** Terraform never owned
  them.
- **Both references treat this layer as pre-existing platform infrastructure.** kb-rma's `app.py`
  references `f"arn:aws:iam::{ACCOUNT}:role/{APP_NAME}-infra-execution-role"` as a given;
  `edap-iam` is a _separate repo_ that creates the role pair for every service. niffler's
  execution role is already named `niffler-infra-execution-role`, so with `APP_NAME = "niffler"`
  the reference's expression resolves to it **exactly**.

**Decision: no `NifflerIamChainStack`.** CDK manages only per-environment resources (data bucket +
Streamlit app user). This removes the import-the-roles step, the admin-only CDK deploy phase, the
circular dependency between the two roles, and the entire chain-stack lockout risk class.

**`infra/bootstrap/` therefore survives, rewritten** (R10) — it is niffler's single-file analogue
of `edap-iam`. It stays a plain, idempotent AWS CLI script run by `--profile fmassa`, for the same
reason 001 gave: the layer the IaC tool authenticates through cannot be managed by that tool. What
changes:

- **Removed:** creation of the three `niffler-*-tfstate-*` buckets (Terraform-only).
- **Added:** `AppName = niffler` tags on both roles; the `cdk bootstrap` step; the new policy
  documents below.
- **Changed:** both roles' trust policies and inline policies (see "IAM policies for the two chain
  roles").

### A naming discrepancy to resolve

The house module produces **`${service_name}-infra`** and `${service_name}-infra-execution-role`.
niffler's live roles are **`niffler-infra-role`** and `niffler-infra-execution-role`:

|                | House convention               | niffler today                  | Match?                       |
| -------------- | ------------------------------ | ------------------------------ | ---------------------------- |
| Execution role | `niffler-infra-execution-role` | `niffler-infra-execution-role` | ✅ exact                     |
| Infra role     | `niffler-infra`                | `niffler-infra-**role**`       | ❌ off by the `-role` suffix |

(`niffler-infra` _is_ already in use — as the name of the chained **CLI profile** in
`~/.aws/config`, which is a different thing from the IAM role name.)

This is cosmetic but permanent. It is **not** covered by the "preserve exact Terraform resource
names" contract, because the role is not Terraform-managed. Critically, **the infra role's own
name appears in no policy document** under the tag-scoping design — only in the execution role's
trust policy and in `~/.aws/config`. So renaming is cheap: create `niffler-infra`, update those
two places, verify, delete `niffler-infra-role`. All admin-run, all reversible, and the CLI
profile name does not change. See open question **O1**.

## Access keys are deliberately outside IaC

`AWS::IAM::AccessKey` has no CloudFormation read handler, so it can never be imported; and a
secret access key can only be surfaced by CloudFormation through a stack `Output`, which is always
plaintext in `describe-stacks`. Both are unacceptable, so:

- **CDK defines the IAM user and its inline policy only.** No `iam.AccessKey`, no secret in any
  template, output, or CloudFormation state.
- **The execution role gets no `iam:CreateAccessKey`** (R16). It can create and configure the
  _user_ but can never mint a credential for it. Minting is an admin action.
- **The three existing access keys are left exactly as they are** — not imported, not rotated, not
  deleted. `terraform state rm` makes Terraform forget them. `dev`'s `secrets.toml` and any
  Streamlit Cloud secret keep working with no edit and no outage.
- **The user stores them in Parameter Store.** This PRD documents the convention and the commands;
  it does not create the parameters.

**Consequence to accept:** access keys are outside IaC. Recreating or destroying a stack neither
rotates nor recreates them, and `cdk diff` will never show them. Rotation is a runbook.

Second-order benefit: because the execution role cannot list or delete access keys, it could never
delete a user that holds one — which makes `RemovalPolicy.RETAIN` on the user the only workable
choice anyway (see O5).

**The app does not read Parameter Store.** It reads `st.secrets["aws"]`. The parameters are the
user's record of the credential — the place they copy from when filling in
`src/app/.streamlit/secrets.toml` or the Streamlit Cloud Secrets UI. No application change is
implied anywhere in this PRD.

### Naming convention — settled by house convention (R14)

`edap-iam`'s `infra-ssm` policy scopes to `parameter/config/${aws:PrincipalTag/AppName}*`, and
kb-rma reads parameters as `/config/{app_name}_{env}/<name>`. niffler adopts the same shape,
replacing the `/niffler/<env>/streamlit-app/...` layout an earlier revision proposed:

| Environment | Access key ID (`String`)                           | Secret access key (`SecureString`)                     |
| ----------- | -------------------------------------------------- | ------------------------------------------------------ |
| dev         | `/config/niffler_dev/streamlit-app-access-key-id`  | `/config/niffler_dev/streamlit-app-secret-access-key`  |
| demo        | `/config/niffler_demo/streamlit-app-access-key-id` | `/config/niffler_demo/streamlit-app-secret-access-key` |
| prod        | `/config/niffler_prod/streamlit-app-access-key-id` | `/config/niffler_prod/streamlit-app-secret-access-key` |

Standard-tier parameters are free. `SecureString` uses the account default `alias/aws/ssm` key,
whose AWS-managed key policy already lets account principals decrypt via SSM — so no explicit
`kms:Decrypt` grant is needed. A customer-managed key would need one.

### Runbook — mint and store a credential (user-operated, not a task)

```bash
# 1. Mint. Runs as fmassa (admin): the execution role deliberately has no iam:CreateAccessKey,
#    so a compromised deploy path cannot mint itself a data-reading credential
aws iam create-access-key --user-name niffler-streamlit-app-dev --profile fmassa
# -> {"AccessKey": {"AccessKeyId": "AKIA...", "SecretAccessKey": "...", ...}}
# This is the ONLY time the secret is shown. It is never stored in CloudFormation.

# 2. Store. Runs as niffler-infra-exec, which carries the house infra-ssm permissions
#    (ssm:PutParameter on parameter/config/niffler*). --profile fmassa also works
aws ssm put-parameter --profile niffler-infra-exec --region us-east-2 \
  --name /config/niffler_dev/streamlit-app-access-key-id     --type String       --value "AKIA..." --overwrite
aws ssm put-parameter --profile niffler-infra-exec --region us-east-2 \
  --name /config/niffler_dev/streamlit-app-secret-access-key --type SecureString --value "..."    --overwrite

# 3. Copy both values into src/app/.streamlit/secrets.toml (gitignored) and/or the Streamlit
#    Cloud Secrets UI. Then, only if this was a rotation, retire the old key (admin again):
aws iam list-access-keys  --user-name niffler-streamlit-app-dev --profile fmassa
aws iam delete-access-key --user-name niffler-streamlit-app-dev \
  --access-key-id <OLD_KEY_ID> --profile fmassa

# Read one back:
aws ssm get-parameter --name /config/niffler_dev/streamlit-app-secret-access-key \
  --with-decryption --query Parameter.Value --output text --profile niffler-infra-exec
```

### Consuming the parameters from CDK

The house pattern for reading a hand-created parameter is
`ssm.StringParameter.from_string_parameter_name` (kb-rma reads its Snowflake secret ARN exactly
this way). The niffler equivalent:

```python
access_key_id = ssm.StringParameter.from_string_parameter_name(
    self,
    "StreamlitAppAccessKeyId",
    string_parameter_name=f"/config/{get_app_name()}_{get_env()}/streamlit-app-access-key-id",
).string_value
```

Two things to be clear about:

- **This works only for the `String` parameter (the access key ID).** The `SecureString` secret
  needs `ssm.StringParameter.from_secure_string_parameter_attributes(..., version=...)`; a plain
  `.string_value` on a SecureString does not resolve.
- **No niffler resource consumes either parameter today** — the app reads `st.secrets`, and the
  stack has no compute. The snippet is therefore **documented as the sanctioned pattern, not
  instantiated**; wiring it in now would add a stack dependency on a parameter nothing reads. It
  becomes real the moment there is a consumer — e.g. `DP-01`'s sync Lambda. See **O4**.

## IAM policies for the two chain roles

Derived from `edap-iam`, merged with the empirically-discovered action list 001 already proved
against this account. These are the documents `infra/bootstrap/bootstrap.sh` writes.

### The scoping mechanism

Both roles are tagged `AppName = niffler`. Every statement is then scoped generically:

| Pattern                                                                           | Resolves to                                                                            |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `arn:aws:s3:::${aws:PrincipalTag/AppName}-*`                                      | `niffler-{dev,demo,prod}-data-309917471802` (and, until Task-006, the tfstate buckets) |
| `arn:aws:cloudformation:*:309917471802:stack/${aws:PrincipalTag/AppName}*/*`      | `niffler-infra-stack-{dev,demo,prod}`                                                  |
| `arn:aws:iam::309917471802:role/${aws:PrincipalTag/AppName}-infra-execution-role` | `niffler-infra-execution-role`                                                         |
| `arn:aws:iam::309917471802:user/${aws:PrincipalTag/AppName}-*`                    | `niffler-streamlit-app-{dev,demo,prod}`                                                |
| `arn:aws:ssm:*:*:parameter/config/${aws:PrincipalTag/AppName}*`                   | `/config/niffler_{dev,demo,prod}/*`                                                    |

This replaces the per-env ARN enumeration earlier revisions used (R13): one document covers all
three environments, and adding an environment needs no policy change. `aws:PrincipalTag` resolves
from the assumed role's own tags, which is why the tagging step is load-bearing.

### 001's "no wildcards" criterion, refined

001 required that no policy contain `"Action": "s3:*"`, `"iam:*"` or `"Resource": "*"`. Adopting
the house policies requires two narrow, documented exceptions:

- **`sts:GetCallerIdentity` on `Resource: "*"`** — the action has no IAM resource type, so `*` is
  the only expressible value. It returns nothing but the caller's own identity. The reference has
  the same statement (`CliPermissions`). This is the **only** `Resource: "*"` in the design.
- **Suffix-anchored action patterns `s3:*Object` and `s3:*BucketVersioning`** — bounded wildcards
  from the house `infra-s3` policy, not unbounded `s3:*`. `s3:*Object` matches
  `GetObject/PutObject/DeleteObject/RestoreObject` and nothing else.

The criterion is therefore restated as: **no unbounded wildcard (`s3:*`, `iam:*`,
`cloudformation:*`, `Resource: "*"`) except `sts:GetCallerIdentity`.** See **O3** if you would
rather enumerate the object actions instead.

Statements from the reference that niffler **drops**, with reasons:
`PipelineCrossAccountArtifactsBucket` and `PipelineCrossAccountArtifactsKey` (both
`Resource: "*"`, both exist only for CDK Pipelines cross-account deploys — niffler has neither);
the SAM transform `CreateChangeSet` in `cdk-execution-role-policy` (no serverless transform);
and everything in `infra-deployment` (ECS/RDS/EC2).

### Policy documents: `niffler-infra` (the infra role)

One inline policy. Statement Sids follow the house policy names so the lineage stays visible.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateChangeSet",
        "cloudformation:DeleteChangeSet",
        "cloudformation:DescribeChangeSet",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:ListChangeSets",
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:ContinueUpdateRollback",
        "cloudformation:CancelUpdateStack",
        "cloudformation:UpdateTerminationProtection",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:GetTemplate",
        "cloudformation:GetTemplateSummary",
        "cloudformation:DescribeStackResource",
        "cloudformation:DescribeStackResources",
        "cloudformation:ListStackResources",
        "cloudformation:DetectStackDrift",
        "cloudformation:DescribeStackDriftDetectionStatus",
        "cloudformation:DescribeStackResourceDrifts"
      ],
      "Resource": "arn:aws:cloudformation:*:309917471802:stack/${aws:PrincipalTag/AppName}*/*"
    },
    {
      "Sid": "CliPermissions",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    },
    {
      "Sid": "CliStagingBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
      "Resource": [
        "arn:aws:s3:::cdk-toolkitv2-assets-309917471802-*",
        "arn:aws:s3:::cdk-toolkitv2-assets-309917471802-*/*"
      ]
    },
    {
      "Sid": "ReadVersion",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:*:309917471802:parameter/cdk-bootstrap/toolkitv2/version"
    },
    {
      "Sid": "AssumeRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": [
        "arn:aws:iam::309917471802:role/cdk-toolkitv2-deploy-role-309917471802-*",
        "arn:aws:iam::309917471802:role/cdk-toolkitv2-file-publishing-role-309917471802-*",
        "arn:aws:iam::309917471802:role/cdk-toolkitv2-image-publishing-role-309917471802-*",
        "arn:aws:iam::309917471802:role/cdk-toolkitv2-lookup-role-309917471802-*"
      ]
    },
    {
      "Sid": "PassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::309917471802:role/${aws:PrincipalTag/AppName}-infra-execution-role",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "cloudformation.amazonaws.com"
        }
      }
    },
    {
      "Sid": "TerraformStateAccessAllEnvs",
      "Effect": "Allow",
      "Comment": "REMOVED IN TASK-007 - kept only until the tfstate buckets are deleted",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-dev-tfstate-309917471802",
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-dev-tfstate-309917471802/*",
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-demo-tfstate-309917471802",
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-demo-tfstate-309917471802/*",
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-prod-tfstate-309917471802",
        "arn:aws:s3:::${aws:PrincipalTag/AppName}-prod-tfstate-309917471802/*"
      ]
    }
  ]
}
```

Deltas from the house `cdk-infra`, all additive and all stack-scoped: `ListChangeSets`,
`GetTemplateSummary`, `DescribeStackResource(s)`, `ListStackResources`, and the drift trio
(`DetectStackDrift`, `DescribeStackDriftDetectionStatus`, `DescribeStackResourceDrifts`) — this
PRD uses drift detection as a hard gate after every import, and EDAP does not. The `PassRole`
condition on `iam:PassedToService` is also a niffler addition. `TerraformStateAccessAllEnvs` is
transitional and is deleted in Task-007. The `"Comment"` key above is documentation only — IAM
ignores unknown keys, but drop it in the real document rather than relying on that.

**Note the infra role has no `sts:AssumeRole` on the execution role.** The house design routes
everything through CloudFormation. niffler additionally needs the human to assume it directly for
`aws s3 cp` uploads, so a `niffler`-specific `AssumeExecutionRole` statement (`sts:AssumeRole` on
`${aws:PrincipalTag/AppName}-infra-execution-role`) is added — see the trust-policy note below.

### Policy documents: `niffler-infra-execution-role`

One inline policy, four Sids named after the house policies they derive from.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CdkExecution",
      "Effect": "Allow",
      "Action": "ssm:GetParameters",
      "Resource": "arn:aws:ssm:*:309917471802:parameter/cdk-bootstrap/*"
    },
    {
      "Sid": "InfraS3Bucket",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:*BucketVersioning",
        "s3:GetEncryptionConfiguration",
        "s3:PutEncryptionConfiguration",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock",
        "s3:GetLifecycleConfiguration",
        "s3:PutLifecycleConfiguration",
        "s3:GetBucketTagging",
        "s3:PutBucketTagging",
        "s3:GetBucketPolicy",
        "s3:PutBucketPolicy",
        "s3:DeleteBucketPolicy",
        "s3:GetBucketPolicyStatus",
        "s3:GetBucketOwnershipControls",
        "s3:PutBucketOwnershipControls",
        "s3:GetBucketAcl",
        "s3:PutBucketAcl",
        "s3:GetBucketCORS",
        "s3:PutBucketCORS",
        "s3:GetBucketWebsite",
        "s3:PutBucketWebsite",
        "s3:DeleteBucketWebsite",
        "s3:GetBucketLogging",
        "s3:PutBucketLogging",
        "s3:GetBucketNotification",
        "s3:PutBucketNotification",
        "s3:GetBucketRequestPayment",
        "s3:PutBucketRequestPayment",
        "s3:GetAccelerateConfiguration",
        "s3:PutAccelerateConfiguration",
        "s3:GetReplicationConfiguration",
        "s3:PutReplicationConfiguration",
        "s3:GetBucketObjectLockConfiguration",
        "s3:PutBucketObjectLockConfiguration",
        "s3:GetIntelligentTieringConfiguration",
        "s3:PutIntelligentTieringConfiguration",
        "s3:GetAnalyticsConfiguration",
        "s3:PutAnalyticsConfiguration",
        "s3:GetInventoryConfiguration",
        "s3:PutInventoryConfiguration",
        "s3:GetMetricsConfiguration",
        "s3:PutMetricsConfiguration"
      ],
      "Resource": "arn:aws:s3:::${aws:PrincipalTag/AppName}-*"
    },
    {
      "Sid": "InfraS3Object",
      "Effect": "Allow",
      "Action": "s3:*Object",
      "Resource": "arn:aws:s3:::${aws:PrincipalTag/AppName}-*/*"
    },
    {
      "Sid": "InfraSsm",
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:DeleteParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:GetParameterHistory",
        "ssm:AddTagsToResource",
        "ssm:RemoveTagsFromResource",
        "ssm:ListTagsForResource"
      ],
      "Resource": [
        "arn:aws:ssm:*:309917471802:parameter/config/${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:309917471802:parameter/${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:309917471802:parameter/cdk/exports/${aws:PrincipalTag/AppName}*"
      ]
    },
    {
      "Sid": "InfraIamUsers",
      "Effect": "Allow",
      "Action": [
        "iam:CreateUser",
        "iam:DeleteUser",
        "iam:GetUser",
        "iam:UpdateUser",
        "iam:TagUser",
        "iam:UntagUser",
        "iam:ListUserTags",
        "iam:PutUserPolicy",
        "iam:DeleteUserPolicy",
        "iam:GetUserPolicy",
        "iam:ListUserPolicies",
        "iam:ListAttachedUserPolicies",
        "iam:ListGroupsForUser",
        "iam:GetLoginProfile"
      ],
      "Resource": "arn:aws:iam::309917471802:user/${aws:PrincipalTag/AppName}-*"
    }
  ]
}
```

Notes on the derivation:

- **`InfraS3Bucket` is the union** of the house `infra-s3` bucket-level list and the action list
  001 discovered empirically against this account. The house list alone is missing several actions
  CloudFormation's S3 read handler calls (notably `GetBucketTagging` — the house has only the
  `Put` — and the ownership-controls pair niffler needs for `BucketOwnerEnforced`). As in 001, treat
  this as a starting point to be **completed empirically**: run the operation, read each
  `AccessDenied`, add exactly the action it names, repeat.
- **`InfraIamUsers` has no template in the reference.** EDAP applications use IAM roles
  exclusively and never create users, so this statement is niffler-specific. It is the minimum
  `AWS::IAM::User` needs for create/read/update, scoped to the tag pattern. **`iam:CreateAccessKey`,
  `iam:DeleteAccessKey`, `iam:ListAccessKeys` and `iam:UpdateAccessKey` are deliberately absent**
  (R16) — keys are minted by hand as admin.
- **`InfraSsm`** is the house policy with the second statement dropped (it grants read on
  `/config/application*`, a shared EDAP namespace niffler does not have) and the region/account
  narrowed from `*:*` to `*:309917471802`.

### Trust policies

**`niffler-infra` (infra role)** — the house pattern (R17), adapted for a single-identity personal
account. The account-root principal with an `ArnLike` condition survives the SSO permission set
being recreated, which the hardcoded hash 001 used does not:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::309917471802:root" },
      "Action": ["sts:AssumeRole", "sts:TagSession"],
      "Condition": {
        "ArnLike": {
          "aws:PrincipalArn": "arn:aws:iam::309917471802:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_AdministratorAccess_*"
        }
      }
    }
  ]
}
```

The reference's GitHub-OIDC federated statement is **omitted** — it is the CI path, which is
`CL-02` and out of scope. It is the obvious thing to add when CI arrives, and this trust structure
is exactly the one that accommodates it. `sts:TagSession` is included for parity even though the
`AppName` tag comes from the role's own tags, not session tags.

**`niffler-infra-execution-role`** — the house version trusts only
`Service: cloudformation.amazonaws.com`. niffler must **also** keep the infra role as a principal,
because the weekly `aws s3 cp` snapshot upload and the credential runbook use the
`niffler-infra-exec` chained CLI profile. EDAP has no such manual path (everything goes through
CI), so this is a documented, justified deviation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationServiceRole",
      "Effect": "Allow",
      "Principal": { "Service": "cloudformation.amazonaws.com" },
      "Action": "sts:AssumeRole"
    },
    {
      "Sid": "HumanChain",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::309917471802:role/niffler-infra" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

(`niffler-infra` here becomes `niffler-infra-role` if O1 is answered "keep the current name".)

### Inline policies, not customer-managed

`edap-iam` uses customer-managed policies because it serves dozens of services from one repo and
composes them per app (`local.default_policies` + extras). niffler is one app in one account, so
the same conceptual split is expressed as **Sids inside the two existing inline policies**
(`niffler-infra-role-permissions`, `niffler-infra-execution-role-permissions`), which:

- keeps the existing policy names (no rename, no extra IAM objects to manage),
- keeps everything in one auditable place (`bootstrap.sh`),
- preserves the house's conceptual grouping through Sid naming (`CdkExecution`, `InfraS3Bucket`,
  `InfraSsm`, `InfraIamUsers`).

Note `edap-iam` sets `lifecycle { ignore_changes = [inline_policy] }` on both roles — a
Terraform-specific guard that has no analogue in a shell script and is not needed.

### Permission boundary: skipped, with justification

`edap-iam` attaches `default-infra-permissions-boundary` to the infra role. Its content is
`Allow *` on `*`, plus three `Deny`s: Secrets Manager reads outside `${AppName}-cicd-*` for
sessions whose `aws:userid` ends in `-cicd`, and two API Gateway api-key/usage-plan enumeration
denies.

For niffler **none of the three denies can ever fire**: there are no `-cicd` sessions (no CI —
`CL-02`), no Secrets Manager usage, and no API Gateway. What would remain is a policy whose only
effective statement is `Allow *` on `*` — which constrains nothing, adds an IAM object to
maintain, and introduces the one thing 001 explicitly forbade (an unbounded wildcard document) into
the account.

**Recommendation: skip it.** Revisit when `CL-02` introduces CI sessions or `CL-03` introduces
Secrets Manager, at which point a trimmed boundary carrying only the relevant denies becomes
worth attaching. Recorded as **O6**.

## Scope

**In scope:**

- A CDK (Python) app following the kb-rma layout, replacing `infra/modules/` + `infra/envs/`.
- One CloudFormation stack per environment: `niffler-infra-stack-{dev,demo,prod}`, produced by
  the same `InfraStack` class, one per `cdk` invocation, selected by `ENVIRONMENT`.
- Importing the Terraform-managed resources (per env: 1 bucket, 1 user with its inline policy)
  with zero deletion or recreation.
- A rewritten `infra/bootstrap/bootstrap.sh`: `AppName` tags, the edap-derived policies above
  (additive first, revoking last), and the `cdk bootstrap` step.
- Deleting every Terraform artifact: `infra/envs/`, `infra/modules/`, the three `*-tfstate-*`
  buckets, and the Terraform block in `.gitignore`.
- `package.json` / `.nvmrc` / root `cdk.json` per the reference.
- Documentation: `CLAUDE.md`, `README.md`, `docs/backlog.md` (`CL-01`), a "superseded in part"
  banner on `001__infra/PRD.md`, `infra/README.md`, and the rewritten
  `infra/bootstrap/README.md`.

**Out of scope:**

- Any change to the architecture 001 designed — environments, naming, region, the role chain, the
  `snapshots/` prefix, Streamlit Cloud hosting, the per-env credential model.
- Any application-code change. `src/app/` is not touched.
- Bringing the chain roles under CDK.
- Creating, rotating or deleting IAM access keys; creating SSM parameters.
- CI/CD (`CL-02`) — the references' GitHub Actions and OIDC trust statements are read for their
  shape only; no workflow and no OIDC provider is added here. Database (`CL-01` sub-item), app
  auth (`CL-03`), narrowing the SSO permission set (`CL-04`), Mobills automation
  (`DP-01`/`DP-02`).
- A permission boundary (see above), nested stacks, `cdk-nag`, CDK Pipelines, construct libraries,
  StackSets, custom resources, Lambdas, multi-region, multi-account.
- Hardening beyond current parity (`enforce_ssl`, KMS CMKs, bucket policies, per-env execution
  roles).
- Uploading snapshot data; deploying `demo`/`prod` to Streamlit Cloud.

## Names that must not change

Every entry is asserted by the Task-001 unit test and re-verified in the post-cutover checklist.

| Kind                     | Name                                                                         | Derived in code as                                     |
| ------------------------ | ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| S3 buckets               | `niffler-{dev,demo,prod}-data-309917471802`                                  | `f"{get_resource_name()}-data-{get_account_id()}"`     |
| S3 lifecycle rule ID     | `expire-noncurrent-versions`                                                 | literal                                                |
| S3 key prefix            | `snapshots/`                                                                 | `get_snapshot_prefix()`                                |
| IAM users                | `niffler-streamlit-app-{dev,demo,prod}`                                      | `get_resource_name(f"{get_app_name()}-streamlit-app")` |
| IAM user inline policies | `niffler-streamlit-app-<env>-read-snapshots`                                 | `f"{user_name}-read-snapshots"`                        |
| IAM user policy Sids     | `ListSnapshotsPrefix`, `ReadSnapshotObjects`                                 | literals                                               |
| Tags on bucket + user    | `Environment=<env>`, `Project=niffler`                                       | stack `tags=`                                          |
| Execution role           | `niffler-infra-execution-role`                                               | `bootstrap.sh`                                         |
| Role inline policies     | `niffler-infra-role-permissions`, `niffler-infra-execution-role-permissions` | `bootstrap.sh`                                         |

Both preserved resource names decompose cleanly into the house helper — `get_resource_name()`
returns `niffler-dev`, so `niffler-dev-data-309917471802` and `niffler-streamlit-app-dev` both
fall out with no special-casing, and both are covered by the `${aws:PrincipalTag/AppName}-*`
scoping. That is a strong sign the conventions fit niffler as-is.

**Names that are new or may change**: CloudFormation stacks `niffler-infra-stack-{dev,demo,prod}`;
the CDK bootstrap qualifier `toolkitv2`; the `CfnOutput` export names `niffler-<env>-<thing>`;
Parameter Store paths `/config/niffler_<env>/*`; the `AppName = niffler` role tags; and — pending
**O1** — possibly the infra role, `niffler-infra-role` → `niffler-infra`.

## Target architecture

```
niffler/
├── cdk.json                      # NEW - repo root: {"app": "python -m infra.app", ...}
├── package.json                  # NEW - pins the CDK CLI
├── package-lock.json             # NEW - committed, for `npm ci`
├── .nvmrc                        # NEW
├── infra/
│   ├── __init__.py               # """AWS Infrastructure."""
│   ├── app.py                    # entrypoint: one env per invocation
│   ├── infra_stack.py            # InfraStack
│   ├── resource_utils.py         # get_app_name / get_env / get_resource_name / ...
│   ├── README.md
│   └── bootstrap/                # SURVIVES, rewritten - niffler's edap-iam analogue
│       ├── bootstrap.sh
│       └── README.md
└── tests/
    └── infra/
        └── test_infra_stack.py   # NEW - asserts every preserved name, offline
```

`cdk` runs from the **repo root**, so `cdk.out/` and `node_modules/` live there — matching the
existing `norecursedirs = "cdk.out node_modules"`. `python -m infra.app` puts the repo root on
`sys.path`, which is how `infra.app` imports `infra.resource_utils` and `infra.infra_stack`.
Because the entrypoint is the submodule `infra.app`, it can never shadow niffler's runtime `app`
package (`[tool.uv.build-backend] module-name = ["app"]`).

Identity chain after migration — unchanged in shape from 001:

1. `fmassa` SSO `AdministratorAccess` — runs `bootstrap.sh` and `cdk bootstrap`, and mints access
   keys; never touches data.
2. `niffler-infra` — CloudFormation on `stack/niffler*/*`, `iam:PassRole` and `sts:AssumeRole` on
   the execution role, plus the CDK toolkit-role assume-rights. No direct data access.
3. `niffler-infra-execution-role` — assumed by CloudFormation as the stacks' service role (set in
   the synthesizer, so no CLI flag needed), and by the human via `niffler-infra-exec` for
   `aws s3 cp` and `ssm put-parameter`. The only identity that can manage the data buckets and
   `niffler-streamlit-app-*` users — but it cannot mint their credentials.
4. `niffler-streamlit-app-<env>` — read-only on `s3://niffler-<env>-data-.../snapshots/*`,
   credential in Parameter Store and copied into Streamlit secrets by hand.

### `cdk.json` (repo root)

```json
{
  "app": "python -m infra.app",
  "versionReporting": false,
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "**/__init__.py",
      "**/__pycache__",
      "tests"
    ]
  },
  "context": {
    "...": "the standard cdk-init feature-flag block, copied from the reference"
  }
}
```

Two deviations from the reference's `cdk.json`, both migration-driven:

- **`"versionReporting": false`** — suppresses the `CDKMetadata` resource CDK otherwise injects
  into every stack. Not cosmetic: an import changeset may contain _only_ the resources being
  imported, so a stray `CDKMetadata` resource would block it. Harmless to keep afterwards.
- **`@aws-cdk/aws-iam:minimizePolicies` and `@aws-cdk/core:explicitStackTags`** in the context
  block must be checked against `cdk synth` output before importing — see "Expected import
  wrinkles". Set either to `false` if it changes how the policy or the tags render.

### `infra/resource_utils.py`

```python
"""Define resource constants."""

from __future__ import annotations

import os

ENVIRONMENTS = ("dev", "demo", "prod")


def get_app_name() -> str:
    """Get application name."""
    return "niffler"


def get_env() -> str:
    """Get and validate the target environment from the ENVIRONMENT variable."""
    env = os.environ["ENVIRONMENT"]
    if env.lower() not in ENVIRONMENTS:
        msg = f"Unexpected {env} variable"
        raise ValueError(msg)
    return env


def get_account_id() -> str:
    """Get AWS account ID."""
    return "309917471802"


def get_region() -> str:
    """Get AWS region."""
    return "us-east-2"


def get_resource_name(base_name: str = "niffler") -> str:
    """Get full (including environment) resource name."""
    return f"{base_name}-{get_env()}"


def get_data_bucket_name() -> str:
    """Get this environment's S3 snapshot bucket name (pinned to the name Terraform created)."""
    return f"{get_resource_name()}-data-{get_account_id()}"


def get_snapshot_prefix() -> str:
    """Get the S3 key prefix snapshots are stored under."""
    return "snapshots"


def get_config_parameter_path(name: str) -> str:
    """Get the Parameter Store path for a config value, per the /config/{app}_{env}/ convention."""
    return f"/config/{get_app_name()}_{get_env()}/{name}"
```

`get_env()` raising `ValueError` on anything outside `ENVIRONMENTS` is the guard that makes
one-environment-per-invocation safe: a typo in `ENVIRONMENT` fails at synth, before any AWS call.

### `infra/app.py`

```python
"""Define and synthesize app."""

import aws_cdk as cdk

from infra import resource_utils
from infra.infra_stack import InfraStack

APP_NAME = resource_utils.get_app_name()
ENV = resource_utils.get_env()
ACCOUNT = resource_utils.get_account_id()
REGION = resource_utils.get_region()
STACK_NAME = resource_utils.get_resource_name(f"{APP_NAME}-infra-stack")

# Pre-existing platform role, created by infra/bootstrap/bootstrap.sh - not managed by this app.
# CloudFormation assumes it to act on resources, which is hop 2 of the chain 001 designed
role = f"arn:aws:iam::{ACCOUNT}:role/{APP_NAME}-infra-execution-role"
synthesizer = cdk.DefaultStackSynthesizer(
    cloud_formation_execution_role=role,
    qualifier="toolkitv2",
)

# Tag keys are the ones Terraform already applied - changing them would show up as drift
tags = {
    "Project": APP_NAME,
    "Environment": ENV,
}

app = cdk.App(context={"app_name": APP_NAME, "environment": ENV})

stack = InfraStack(
    app,
    STACK_NAME,
    env=cdk.Environment(account=ACCOUNT, region=REGION),
    synthesizer=synthesizer,
    tags=tags,
)

app.synth()
```

One adaptation to the reference: kb-rma tags with `{"AppName": ..., "Environment": ...}`. niffler's
live resources carry `Project=niffler`, so the tag _keys_ are preserved while the _mechanism_
(stack-level tags at instantiation) is adopted — changing `Project` to `AppName` would be
gratuitous drift on day one. Note this is the **resource** tag; the `AppName` tag that drives the
IAM policies lives on the two chain roles and is set by `bootstrap.sh`, not here.

### `infra/infra_stack.py`

```python
"""Stacks definitions."""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .resource_utils import (
    get_app_name,
    get_data_bucket_name,
    get_resource_name,
    get_snapshot_prefix,
)

NONCURRENT_VERSION_EXPIRATION_DAYS = 90
LIFECYCLE_RULE_ID = "expire-noncurrent-versions"


class InfraStack(Stack):
    """Infrastructure Stack definition.

    One environment's private snapshot bucket plus the least-privilege, read-only IAM
    identity that environment's Streamlit app instance uses to read it. Physical names are
    pinned to the values Terraform created - see the PRD's "Names that must not change".
    """

    def __init__(
        self, scope: Construct, construct_id: str, **kwargs: dict[str, Any]
    ) -> None:
        """Initialize the stack."""
        super().__init__(scope, construct_id, **kwargs)

        # These snapshots are the only copy of the user's financial data - RETAIN means no
        # stack operation can ever delete this bucket
        self.data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=get_data_bucket_name(),
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_key_enabled=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id=LIFECYCLE_RULE_ID,
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(
                        NONCURRENT_VERSION_EXPIRATION_DAYS
                    ),
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )
        CfnOutput(
            self,
            "dataBucketName",
            value=self.data_bucket.bucket_name,
            description="Name of the S3 bucket holding this environment's Mobills snapshots",
            export_name=f"{get_resource_name()}-data-bucket-name",
        )

        user_name = get_resource_name(f"{get_app_name()}-streamlit-app")
        # L1 CfnUser, not L2 iam.User: only the L1 renders the inline policy as a property of
        # the user. L2 emits a separate AWS::IAM::Policy, which CloudFormation cannot import
        streamlit_app_user = iam.CfnUser(
            self,
            "StreamlitAppUser",
            user_name=user_name,
            policies=[
                iam.CfnUser.PolicyProperty(
                    policy_name=f"{user_name}-read-snapshots",
                    policy_document=iam.PolicyDocument(
                        statements=[
                            self.list_snapshots_policy_statement,
                            self.read_snapshots_policy_statement,
                        ],
                    ),
                ),
            ],
        )
        streamlit_app_user.apply_removal_policy(RemovalPolicy.RETAIN)
        CfnOutput(
            self,
            "streamlitAppUserName",
            value=user_name,
            description="IAM user the Streamlit app authenticates as",
            export_name=f"{get_resource_name()}-streamlit-app-user-name",
        )

    @property
    def list_snapshots_policy_statement(self) -> iam.PolicyStatement:
        """Return the statement allowing the app to list only the snapshots prefix."""
        return iam.PolicyStatement(
            sid="ListSnapshotsPrefix",
            effect=iam.Effect.ALLOW,
            actions=["s3:ListBucket"],
            resources=[self.data_bucket.bucket_arn],
            conditions={"StringLike": {"s3:prefix": f"{get_snapshot_prefix()}/*"}},
        )

    @property
    def read_snapshots_policy_statement(self) -> iam.PolicyStatement:
        """Return the statement allowing the app to read snapshot objects."""
        return iam.PolicyStatement(
            sid="ReadSnapshotObjects",
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=[f"{self.data_bucket.bucket_arn}/{get_snapshot_prefix()}/*"],
        )
```

### `package.json`, `.nvmrc`, `pyproject.toml`

```json
{
  "name": "niffler",
  "private": true,
  "devDependencies": {
    "aws-cdk": "2.1114.1"
  }
}
```

`.nvmrc` contains `22` (matching the installed Node v22.22.2). `package-lock.json` is committed so
`npm ci` is reproducible.

```toml
[project.optional-dependencies]
infra = [
    "aws-cdk-lib==2.266.0",
    "constructs>=10.0.0,<11.0.0",
]
```

Installed with `uv sync --extra infra`; the project's documented
`uv sync --all-extras --all-groups` already covers it. `aws-cdk-lib` is pinned exactly, per the
reference — CDK's generated templates change between minor versions, and after an import a
template change means drift.

The invocation is `uv run --no-sync npx cdk <command>`: `uv run` activates the project venv so the
`python` that `cdk.json` spawns resolves `aws_cdk`, and `npx` runs the `package.json`-pinned CLI
rather than whatever is global.

## CDK bootstrap

`DefaultStackSynthesizer` requires `cdk bootstrap`. The `toolkitv2` qualifier is confirmed
independently in both references — kb-rma's `app.py` passes it, and `edap-iam`'s `cdk-infra`
policy grants rights on `cdk-toolkitv2-*` roles, the `cdk-toolkitv2-assets-*` bucket and
`/cdk-bootstrap/toolkitv2/version`. The house **does** bootstrap, with a custom qualifier.

Resources created in `309917471802` / `us-east-2`:

| Resource                      | Physical name                                                |
| ----------------------------- | ------------------------------------------------------------ |
| Staging/assets S3 bucket      | `cdk-toolkitv2-assets-309917471802-us-east-2`                |
| Container assets ECR repo     | `cdk-toolkitv2-container-assets-309917471802-us-east-2`      |
| CloudFormation execution role | `cdk-toolkitv2-cfn-exec-role-309917471802-us-east-2`         |
| Deployment action role        | `cdk-toolkitv2-deploy-role-309917471802-us-east-2`           |
| File publishing role          | `cdk-toolkitv2-file-publishing-role-309917471802-us-east-2`  |
| Image publishing role         | `cdk-toolkitv2-image-publishing-role-309917471802-us-east-2` |
| Lookup role                   | `cdk-toolkitv2-lookup-role-309917471802-us-east-2`           |
| Bootstrap version parameter   | SSM `/cdk-bootstrap/toolkitv2/version`                       |

**Run by `--profile fmassa` only.** AWS documents the bootstrapping identity as needing
`cloudformation:*, ecr:*, ssm:*, s3:*, iam:*` on `*` — which no chain role has, or should have.
This goes into the rewritten `infra/bootstrap/README.md` alongside the role creation, and
`CLAUDE.md` records `CDKToolkit` as account-level infrastructure not defined in `infra/`.

### The `AdministratorAccess` concern, resolved

The default bootstrap grants `AdministratorAccess` to `cdk-toolkitv2-cfn-exec-role` — a standing
account-wide wildcard, against 001's criterion and against `CL-04`. It is resolved cleanly because
**niffler never uses that role**: `app.py` sets
`cloud_formation_execution_role=niffler-infra-execution-role`, so CloudFormation always acts as
niffler's own least-privilege role. The bootstrap execution role is therefore made inert:

```bash
cdk bootstrap aws://309917471802/us-east-2 \
  --profile fmassa \
  --qualifier toolkitv2 \
  --cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll \
  --termination-protection
```

If the synthesizer's execution role is ever accidentally dropped, the deploy fails loudly instead
of silently running as an administrator. `--trust` is not needed: it takes account IDs, and this
is a single-account setup. Cost is effectively zero (an empty S3 bucket and an empty ECR repo;
current bootstrap templates no longer create a KMS key).

### Who calls the CloudFormation API — validated in Task-002

`DefaultStackSynthesizer` has the CLI assume `cdk-toolkitv2-deploy-role-...` to make the
CloudFormation calls — which `edap-iam`'s `assumerole` statement explicitly grants, so that is the
house's intended path. The open detail is that a stock bootstrap template scopes the deploy role's
`iam:PassRole` to the **bootstrap's own** `cfn-exec-role`, not to `niffler-infra-execution-role`.
EDAP's `toolkitv2` toolkit is a platform-team template that evidently permits it; niffler has no
platform team, so both paths are provisioned and the working one is confirmed empirically:

- **Config A (try first — no template surgery).** The infra role holds both `AssumeRole` on the
  toolkit roles _and_ `PassRole` on the execution role (exactly as the house policy above does).
  If the deploy role cannot pass niffler's execution role, CDK's documented behaviour is to fall
  back to the CLI credentials — which then satisfy `PassRole` directly. Nothing else changes.
- **Config B (fallback).** Customise the bootstrap template so the deploy role may pass niffler's
  execution role:

  ```bash
  cdk bootstrap --show-template > infra/bootstrap/cdk-bootstrap-template.yaml
  # add arn:aws:iam::309917471802:role/niffler-infra-execution-role to DeploymentActionRole's
  # iam:PassRole Resource list, commit the file, then:
  cdk bootstrap aws://309917471802/us-east-2 --profile fmassa --qualifier toolkitv2 \
    --template infra/bootstrap/cdk-bootstrap-template.yaml \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll \
    --termination-protection
  ```

  The chain then reads SSO → `niffler-infra` → `cdk-toolkitv2-deploy-role` → CloudFormation →
  `niffler-infra-execution-role`. The security-relevant property is unchanged: the CDK deploy role
  holds CloudFormation-API and staging-bucket permissions, never resource permissions, and the
  execution role remains the only identity that can touch niffler's buckets and users.

Whichever config wins is recorded in this PRD and in `infra/README.md` before Task-003 runs.

## Expected import wrinkles

Import does not reconcile — it records the template as truth and surfaces any mismatch as drift.
Four known candidates, each resolvable with a small code or config change plus a `cdk deploy`:

- **Lifecycle rule shape.** S3 reports `Filter: {Prefix: ""}` (what Terraform wrote); CDK's
  `LifecycleRule` omits `Prefix` by default. If drift flags the rule, set `prefix=""` on the rule,
  or escape-hatch:
  `self.data_bucket.node.default_child.add_property_override("LifecycleConfiguration.Rules.0.Prefix", "")`.
  Rewriting a lifecycle rule has zero data impact.
- **`@aws-cdk/core:explicitStackTags`.** With this flag on, CDK may stop rendering `Tags` into each
  resource's properties and rely on CloudFormation stack-tag propagation instead — which would not
  match the live resources, both of which carry explicit `Tags`. **Task-001 must confirm
  `cdk synth` renders `Tags` on both the bucket and the user.** If not, set the flag `false` or
  switch to `Tags.of(self).add(...)` inside `InfraStack`.
- **`@aws-cdk/aws-iam:minimizePolicies`.** Merges compatible policy statements. niffler's two
  statements differ in action, resource and condition so they should not merge, but the
  synthesized policy document must be diffed against `$BK/dev-user-policy.json` before importing;
  set the flag `false` if rendering differs.
- **`BootstrapVersion` parameter / `CheckBootstrapVersion` rule.** `DefaultStackSynthesizer` adds
  both to every template. Neither is a _resource_, so an import changeset should accept them; if
  the import is rejected, pass `generate_bootstrap_version_rule=False` to the synthesizer.

Rule of thumb: **the code must mirror reality first; change reality only in a later `cdk deploy` —
never both in one operation.**

## Success Criteria

- [ ] All tasks complete, in order, with each "Verification" step passing.
- [ ] Both chain roles carry the tag `AppName = niffler`.
- [ ] Three stacks exist in `us-east-2` (`niffler-infra-stack-{dev,demo,prod}`), all
      `CREATE_COMPLETE`/`UPDATE_COMPLETE`/`IMPORT_COMPLETE`, all `IN_SYNC`.
- [ ] `ENVIRONMENT=<env> uv run --no-sync npx cdk diff` is empty for all three environments.
- [ ] Every data bucket's object-and-version inventory and every bucket/user configuration is
      byte-identical to the Task-000 capture; no `RoleId`, `UserId` or bucket creation date has
      changed.
- [ ] Every name in "Names that must not change" is unchanged, asserted both by the Task-001 unit
      test and by live AWS inspection.
- [ ] `aws sts get-caller-identity --profile niffler-infra-exec` still resolves through both hops.
- [ ] The `dev` Streamlit app loads its latest snapshot with **no change to `src/app/` and no
      change to `secrets.toml`**.
- [ ] The three existing IAM access keys are still active and unmodified, and neither chain role
      holds `iam:CreateAccessKey`.
- [ ] No unbounded wildcard in any niffler policy (`s3:*`, `iam:*`, `cloudformation:*`,
      `Resource: "*"`), with the single documented exception of `sts:GetCallerIdentity`; the
      bootstrap `cfn-exec-role` carries `AWSDenyAll`, not `AdministratorAccess`.
- [ ] `infra/` contains no `.tf`, `.tfvars`, `.hcl` or `.terraform*` file; `infra/modules/` and
      `infra/envs/` no longer exist; `infra/bootstrap/` remains, rewritten.
- [ ] The three `*-tfstate-*` buckets no longer exist (`head-bucket` → 404).
- [ ] `docs/backlog.md` `CL-01`, `README.md`, `CLAUDE.md` and the `001__infra/PRD.md` banner all
      describe CDK, not Terraform.

## Tasks

### Task-000: Pre-flight — capture current state

**Priority**: High
**Estimated Iterations**: 1

**Acceptance Criteria**:

- [ ] The open questions at the end of this document are confirmed by the user.
- [ ] `aws sso login --profile fmassa` succeeds; all three profiles resolve.
- [ ] A complete inventory of live configuration is captured to `~/niffler-migration-backup/`,
      **outside the repo** — the Terraform state files it contains hold plaintext access-key
      secrets and must never be committed.
- [ ] Data-bucket contents copied to local disk (defence in depth; nothing is destroyed).

**Verification**:

```bash
BK=~/niffler-migration-backup && mkdir -p "$BK"
aws sso login --profile fmassa
for p in fmassa niffler-infra niffler-infra-exec; do aws sts get-caller-identity --profile $p; done

for env in dev demo prod; do
  b=niffler-$env-data-309917471802
  aws s3api list-object-versions --bucket $b --profile fmassa --output json > "$BK/$env-inventory.json"
  for call in lifecycle-configuration encryption versioning tagging ownership-controls; do
    aws s3api get-bucket-$call --bucket $b --profile fmassa > "$BK/$env-$call.json" 2>/dev/null
  done
  aws s3api get-public-access-block --bucket $b --profile fmassa > "$BK/$env-pab.json"
  aws iam get-user --user-name niffler-streamlit-app-$env --profile fmassa > "$BK/$env-user.json"
  aws iam get-user-policy --user-name niffler-streamlit-app-$env \
    --policy-name niffler-streamlit-app-$env-read-snapshots --profile fmassa > "$BK/$env-user-policy.json"
  aws iam list-access-keys --user-name niffler-streamlit-app-$env --profile fmassa > "$BK/$env-access-keys.json"
  aws s3 cp "s3://niffler-$env-tfstate-309917471802/$env/terraform.tfstate" "$BK/$env-terraform.tfstate" --profile niffler-infra
  (cd infra/envs/$env && terraform state list) > "$BK/$env-tfstate-addresses.txt"
  aws s3 sync "s3://$b/" "$BK/$env-data/" --profile niffler-infra-exec
done

for r in niffler-infra-role niffler-infra-execution-role; do
  aws iam get-role --role-name $r --profile fmassa > "$BK/$r.json"
  aws iam get-role-policy --role-name $r --policy-name $r-permissions --profile fmassa > "$BK/$r-policy.json"
done
```

### Task-001: Build the CDK app

**Priority**: High
**Estimated Iterations**: 2-3

No AWS calls — files and local `cdk synth` only.

**Acceptance Criteria**:

- [ ] `infra/__init__.py`, `infra/app.py`, `infra/infra_stack.py`, `infra/resource_utils.py`,
      `infra/README.md` created per "Target architecture".
- [ ] Root `cdk.json`, `package.json`, `.nvmrc` created; `npm install` run and
      `package-lock.json` committed.
- [ ] `pyproject.toml` gains `[project.optional-dependencies] infra`;
      `uv sync --all-extras --all-groups` succeeds.
- [ ] `.gitignore` gains `cdk.out/` and `node_modules/` (the Terraform block is removed in
      Task-005).
- [ ] `ENVIRONMENT=<env> ... cdk synth` renders the stack for each of the three environments;
      `ENVIRONMENT=bogus` raises `ValueError` from `get_env()`.
- [ ] Each rendered template is diffed by hand against the Task-000 captures until every property
      matches: bucket name, versioning, encryption (+`BucketKeyEnabled: false`), public access
      block, ownership controls, lifecycle rule, tags, user name, inline policy name, both
      statement Sids, conditions and resources.
- [ ] **`Tags` render on both the bucket and the user** in the synthesized template; the policy
      document matches `$BK/dev-user-policy.json` statement-for-statement (see "Expected import
      wrinkles").
- [ ] No `CDKMetadata` resource appears in any template.
- [ ] `tests/infra/test_infra_stack.py` added: uses `aws_cdk.assertions.Template`, monkeypatching
      `ENVIRONMENT` for each of the three environments, to assert every entry in "Names that must
      not change", plus that no `AWS::IAM::AccessKey` and no standalone `AWS::IAM::Policy`
      resource is present. Offline, deterministic, no AWS calls.
- [ ] Ruff clean under niffler's existing config, with house-style docstrings on every module,
      class, method and function, and `from __future__ import annotations`.

**Verification**:

```bash
uv sync --all-extras --all-groups && npm install
for env in dev demo prod; do ENVIRONMENT=$env uv run --no-sync npx cdk synth --no-notices > /tmp/niffler-$env.yaml; done
ENVIRONMENT=bogus uv run --no-sync npx cdk synth 2>&1 | grep ValueError
uv run pytest tests/ -v
uvx ruff check && uvx ruff format --check
```

### Task-002: Rewrite bootstrap — role tags, edap-derived policies, CDK toolkit

**Priority**: High
**Estimated Iterations**: 2-3

Runs entirely under **`--profile fmassa`** (admin). Strictly **additive**: the
`TerraformStateAccessAllEnvs` statement stays until Task-007, and the execution role's existing
ARN trust principal is kept alongside the service principal. Grant-before-revoke is what makes
lockout impossible; the roles are never deleted or replaced (except the optional rename in O1,
which is create-verify-switch-delete).

**Acceptance Criteria**:

- [ ] `infra/bootstrap/bootstrap.sh` rewritten: tfstate bucket creation removed; **`AppName =
    niffler` tags applied to both roles first**; both trust policies and both inline policies
      replaced with the documents in "IAM policies for the two chain roles". Still idempotent and
      re-runnable.
- [ ] If O1 is answered "rename": `niffler-infra` created, `~/.aws/config`'s `niffler-infra`
      profile `role_arn` updated, the chain re-verified, and only then `niffler-infra-role`
      deleted.
- [ ] `infra/bootstrap/README.md` rewritten: what the script creates, the `AppName` tag and why it
      is load-bearing, the `cdk bootstrap` command, the two `~/.aws/config` profile blocks, and
      the rule that this layer is admin-only.
- [ ] `cdk bootstrap` run with `--qualifier toolkitv2`,
      `--cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll` and
      `--termination-protection`; `CDKToolkit` is `CREATE_COMPLETE`.
- [ ] **Config A/B settled:** `ENVIRONMENT=dev ... cdk diff --profile niffler-infra` completes as
      the infra role. If CDK cannot pass niffler's execution role, take Config B and record the
      choice here and in `infra/README.md`.
- [ ] `niffler-infra-execution-role`'s `RoleId` is unchanged from `$BK` (never recreated).
- [ ] `niffler-infra-exec` still works for `aws s3 cp` and `ssm put-parameter`; Terraform still
      works; `aws iam create-access-key --profile niffler-infra-exec` is now **denied** (proving
      R16).

**Verification**:

```bash
bash infra/bootstrap/bootstrap.sh                       # uses --profile fmassa internally
cdk bootstrap aws://309917471802/us-east-2 --profile fmassa --qualifier toolkitv2 \
  --cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll --termination-protection

# The tag mechanism is load-bearing - verify it before anything relies on it
for r in niffler-infra niffler-infra-execution-role; do
  aws iam list-role-tags --role-name $r --profile fmassa   # expect AppName=niffler
done
diff <(jq -S .Role.RoleId "$HOME/niffler-migration-backup/niffler-infra-execution-role.json") \
     <(aws iam get-role --role-name niffler-infra-execution-role --profile fmassa | jq -S .Role.RoleId)

aws sts get-caller-identity --profile niffler-infra-exec
aws s3 ls s3://niffler-dev-data-309917471802/ --profile niffler-infra-exec
aws s3 ls s3://niffler-dev-tfstate-309917471802/ --profile niffler-infra   # Terraform still works
aws iam create-access-key --user-name niffler-streamlit-app-dev --profile niffler-infra-exec
# expect AccessDenied - the execution role must NOT be able to mint credentials
ENVIRONMENT=dev uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
```

### Task-003: Migrate `dev` (complete slice + GO/NO-GO gate)

**Priority**: High
**Estimated Iterations**: 2-3

`dev` is migrated alone and fully verified — including the live Streamlit app — before `demo` or
`prod` is touched. It is the only environment with wired-up secrets, so it is both the
highest-signal and the only user-visible one.

**Acceptance Criteria**:

- [ ] `niffler-infra-stack-dev` exists containing `DataBucket` and `StreamlitAppUser` and nothing
      else, reports `IN_SYNC` drift, and `cdk diff` is empty.
- [ ] The bucket was not recreated: `CreationDate` and the full `list-object-versions` output
      match `$BK/dev-inventory.json` exactly.
- [ ] The user was not recreated: `UserId` still `AIDAUQKEFKQ5DESYG4ZWR`; inline policy name,
      statements and tags unchanged; access key `AKIAUQKEFKQ5ITANDIW4` still `Active`.
- [ ] The `dev` Terraform state is empty — including the access-key address, which Terraform
      forgets without deleting the key.
- [ ] **GATE:** the Streamlit app, run locally with an **unmodified** `secrets.toml`, loads its
      latest snapshot (or raises the clear `FileNotFoundError` from `get_latest_snapshot()` if the
      bucket is empty). Do not start Task-004 until this passes.

**Verification**:

```bash
export ENVIRONMENT=dev
uv run --no-sync npx cdk diff --profile niffler-infra --no-notices     # only the two importable additions
uv run --no-sync npx cdk import --profile niffler-infra --no-notices \
  --record-resource-mapping /tmp/dev-mapping.json                       # dry run: writes the mapping only
cat /tmp/dev-mapping.json   # DataBucket -> BucketName niffler-dev-data-309917471802
                            # StreamlitAppUser -> UserName niffler-streamlit-app-dev
uv run --no-sync npx cdk import --profile niffler-infra --no-notices \
  --resource-mapping /tmp/dev-mapping.json
uv run --no-sync npx cdk diff --profile niffler-infra --no-notices      # expect: no differences

# Prove the import matched reality
ID=$(aws cloudformation detect-stack-drift --profile niffler-infra --region us-east-2 \
  --stack-name niffler-infra-stack-dev --query StackDriftDetectionId --output text)
aws cloudformation describe-stack-drift-detection-status --profile niffler-infra \
  --region us-east-2 --stack-drift-detection-id "$ID"       # expect StackDriftStatus=IN_SYNC
aws cloudformation describe-stack-resource-drifts --profile niffler-infra --region us-east-2 \
  --stack-name niffler-infra-stack-dev

# Let Terraform forget the resources (nothing destroyed; the access key survives, unmanaged)
cd infra/envs/dev
terraform state rm \
  module.data_bucket.aws_s3_bucket.this \
  module.data_bucket.aws_s3_bucket_versioning.this \
  module.data_bucket.aws_s3_bucket_server_side_encryption_configuration.this \
  module.data_bucket.aws_s3_bucket_public_access_block.this \
  module.data_bucket.aws_s3_bucket_lifecycle_configuration.this \
  module.streamlit_iam.aws_iam_user.streamlit_app \
  module.streamlit_iam.aws_iam_user_policy.read_snapshots \
  module.streamlit_iam.aws_iam_access_key.streamlit_app \
  module.streamlit_iam.data.aws_iam_policy_document.read_snapshots
terraform state list          # expect empty
cd -

# Nothing moved, nothing rotated
diff <(jq -S . "$HOME/niffler-migration-backup/dev-inventory.json") \
     <(aws s3api list-object-versions --bucket niffler-dev-data-309917471802 --profile fmassa --output json | jq -S .)
aws iam get-user --user-name niffler-streamlit-app-dev --profile fmassa | jq -r .User.UserId
aws iam list-access-keys --user-name niffler-streamlit-app-dev --profile fmassa

# GATE: the live app, with an untouched secrets.toml
uv run pytest tests/ -v
cd src/app && uv run streamlit run main.py
```

### Task-004: Migrate `demo` and `prod`

**Priority**: High
**Estimated Iterations**: 1-2

Only after Task-003's gate passes. Identical to Task-003 for each environment, minus the app step.
Run `demo` first, then `prod`. The one-environment-per-synth model means this is literally the same
commands with `ENVIRONMENT` changed — and the tag-scoped policies need no edit for either.

**Acceptance Criteria**:

- [ ] `niffler-infra-stack-demo` and `niffler-infra-stack-prod` exist, `IN_SYNC`, `cdk diff` empty.
- [ ] Both environments' Terraform state lists are empty.
- [ ] Both buckets' version inventories and both users' `UserId`s and access keys are unchanged
      from the Task-000 capture.

**Verification**:

```bash
for env in demo prod; do
  ENVIRONMENT=$env uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
  aws cloudformation describe-stacks --profile niffler-infra --region us-east-2 \
    --stack-name niffler-infra-stack-$env \
    --query 'Stacks[0].[StackName,StackStatus,DriftInformation.StackDriftStatus]'
  aws iam list-access-keys --user-name niffler-streamlit-app-$env --profile fmassa
  (cd infra/envs/$env && terraform state list)   # expect empty
done
```

### Task-005: Decommission the Terraform repo artifacts

**Priority**: High
**Estimated Iterations**: 1

Nothing in AWS changes — only files.

**Acceptance Criteria**:

- [ ] `infra/envs/` and `infra/modules/` deleted (`git rm -r`), including the untracked
      `.terraform/` provider caches. `infra/bootstrap/` stays (rewritten in Task-002).
- [ ] `.gitignore`'s Terraform block removed: `# Terraform local artifacts (...)`, `.terraform/`,
      `*.tfplan`, `tfplan`, `crash.log`, `crash.*.log`. `cdk.out/` and `node_modules/` are the
      replacements.
- [ ] `infra/` contains exactly `__init__.py`, `app.py`, `infra_stack.py`, `resource_utils.py`,
      `README.md`, and `bootstrap/`.
- [ ] Terraform is no longer required to work on this repo (uninstalling the binary is optional).

**Verification**:

```bash
find infra -type f | sort                          # 5 files + bootstrap/, no .tf/.tfvars/.hcl
grep -rn "terraform\|tfstate\|tfplan" .gitignore   # no matches
git status                                          # only intended deletions
ENVIRONMENT=dev uv run --no-sync npx cdk synth --no-notices > /dev/null
```

### Task-006: Delete the three Terraform state buckets

**Priority**: Medium
**Estimated Iterations**: 1

Runs under **`--profile fmassa`** — neither chain role has `s3:DeleteBucket` on the tfstate
buckets in the new policy. **Point of no return for reverting to Terraform**, so it is gated on
all three environments being verified in Tasks 003-004.

**Acceptance Criteria**:

- [ ] All object versions and delete markers removed from all three `*-tfstate-*` buckets, then
      the buckets deleted; `head-bucket` returns 404 for each.
- [ ] The archived state files stay in `~/niffler-migration-backup/` until the user is satisfied,
      then are shredded — they contain plaintext access-key secrets.

**Verification**:

```bash
for env in dev demo prod; do
  b=niffler-$env-tfstate-309917471802
  aws s3api list-object-versions --bucket "$b" --profile fmassa --output json \
    | jq '{Objects: [ (.Versions // [])[], (.DeleteMarkers // [])[] | {Key, VersionId} ], Quiet: true}' \
    > /tmp/$b-delete.json
  aws s3api delete-objects --bucket "$b" --delete "file:///tmp/$b-delete.json" --profile fmassa
  aws s3api delete-bucket --bucket "$b" --profile fmassa
  aws s3api head-bucket --bucket "$b" --profile fmassa   # expect 404
done
```

> `delete-objects` handles at most 1000 keys per call; these buckets hold a handful of versions.

### Task-007: Revoke the Terraform-state permissions

**Priority**: Medium
**Estimated Iterations**: 1

Runs under **`--profile fmassa`**. The "revoke last" step.

**Acceptance Criteria**:

- [ ] The `TerraformStateAccessAllEnvs` statement removed from `bootstrap.sh`'s infra-role policy
      document; the script re-run.
- [ ] The deployed policy contains exactly the house Sids plus niffler's additions —
      `CloudFormationPermissions`, `CliPermissions`, `CliStagingBucket`, `ReadVersion`,
      `AssumeRole`, `PassRole`, `AssumeExecutionRole` — and nothing referencing tfstate.
- [ ] The full workflow still works after the revoke.

**Verification**:

```bash
bash infra/bootstrap/bootstrap.sh
aws iam get-role-policy --role-name niffler-infra \
  --policy-name niffler-infra-role-permissions --profile fmassa \
  | jq '[.PolicyDocument.Statement[].Sid]'   # no TerraformStateAccessAllEnvs

for env in dev demo prod; do
  ENVIRONMENT=$env uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
done   # all empty
```

### Task-008: Documentation

**Priority**: Low
**Estimated Iterations**: 1

**Acceptance Criteria**:

- [ ] `docs/implementation/001__infra/PRD.md` gains a banner under its title: the architecture it
      describes is current, but the IaC tool is AWS CDK as of `002__cdk_migration/PRD.md`; every
      mention of Terraform, `infra/modules`, `infra/envs` and the tfstate buckets is historical.
      The body is **not** rewritten — 001 is the record of what shipped.
- [ ] `docs/backlog.md` `CL-01`: first bullet becomes
      `[x] AWS with CDK (Python) for IaC (infra/, three env stacks: dev/demo/prod)`, with a
      pointer to this PRD alongside the 001 pointer. `CL-02` gains a note that CI is `cdk diff`
      then `cdk deploy` with an `ENVIRONMENT` variable and a GitHub-OIDC trust statement added to
      the infra role — both reference repos show the exact shape. `CL-03`/`CL-04` untouched.
- [ ] `README.md` line 20: `see infra/envs/dev's Terraform outputs` → point at the credential
      runbook in `infra/README.md`. The weekly-routine `aws s3 cp ... --profile niffler-infra-exec`
      command is unchanged.
- [ ] `CLAUDE.md`: the project-structure tree replaces the three `infra/` sub-entries with the CDK
      layout (plus root-level `cdk.json`/`package.json`/`.nvmrc`); the tech-stack section mentions
      AWS CDK (Python) + the npm CDK CLI; the `docs/implementation/` entry mentions both PRDs; the
      "Data" section links both; an `ENVIRONMENT=dev uv run --no-sync npx cdk diff/deploy` entry
      is added to "Commands"; the access-key / Parameter Store convention
      (`/config/niffler_<env>/...`) is described so the next reader knows access keys are outside
      IaC; the `AppName = niffler` role tag is described as load-bearing; and `CDKToolkit` is
      recorded as account-level infrastructure not defined in `infra/`.
- [ ] `infra/README.md` documents: the stack and who runs what, the `ENVIRONMENT` variable, the
      `~/.aws/config` profile blocks, the exact `cdk diff` / `cdk deploy` / `cdk import` commands,
      the minimum CDK CLI and `aws-cdk-lib` versions, the credential runbook, the chosen bootstrap
      config (A or B), and the `diff`-then-`deploy` discipline.
- [ ] `src/app/utils/__init__.py`'s docstring reference to `001__infra/PRD.md` still resolves —
      confirm, no edit required.
- [ ] `docs/business_rules/` untouched — no financial logic changes.

**Verification**:

- `grep -rn -i "terraform\|tfstate\|tfvars" --include="*.md" .` returns only the intentional
  historical mentions in `001__infra/PRD.md` and this file.
- Manual read-through: a new reader can rebuild the whole stack in a clean AWS account from
  `infra/bootstrap/README.md` + `infra/README.md` alone — run `bootstrap.sh` and `cdk bootstrap`
  as admin, then `ENVIRONMENT=<env> cdk deploy` per environment, then the credential runbook.
  Import is migration-only scaffolding and is not part of the from-scratch path.

## Risks and rollback

Dropping the chain stack (R9) removed an entire risk class. The tag-scoping mechanism (R13) adds
one new, cheap-to-verify risk.

| #   | Risk                                                                                    | Likelihood                                                                                  | Mitigation                                                                                                                                                                                                        | Rollback                                                                                           |
| --- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1   | **`AppName` tag missing from a role → every tag-scoped statement denies**               | Medium (neither role is tagged today)                                                       | Tagging is the first thing `bootstrap.sh` does; explicit `list-role-tags` verification in Task-002 before anything depends on it; the failure mode is a loud `AccessDenied`, never a silent wrong-resource action | `aws iam tag-role --tags Key=AppName,Value=niffler --profile fmassa`                               |
| 2   | CDK code diverges from live state → silent drift after import                           | Medium                                                                                      | Code built from the Task-000 capture and hand-diffed against `cdk synth`; drift detection is a hard gate before any deploy                                                                                        | `cdk destroy` — `RemovalPolicy.RETAIN` leaves every resource untouched; fix the code, re-import    |
| 3   | Toolkit deploy role cannot pass `niffler-infra-execution-role` (Config A fails)         | Medium                                                                                      | Settled in Task-002 before anything is imported                                                                                                                                                                   | Config B: customised bootstrap template committed at `infra/bootstrap/cdk-bootstrap-template.yaml` |
| 4   | Execution role lacks a CloudFormation-only permission                                   | Medium (lower than before — the merged S3 list already covers 001's empirically-proven set) | Read the `AccessDenied`, add exactly that action, re-run `bootstrap.sh`                                                                                                                                           | N/A — additive fix                                                                                 |
| 5   | `explicitStackTags` / `minimizePolicies` feature flags change rendering → drift         | Medium                                                                                      | Explicit Task-001 acceptance criteria check both against the captured live state                                                                                                                                  | Set the flag `false` in `cdk.json`, or use `Tags.of(self)`                                         |
| 6   | Lifecycle-rule representation mismatch                                                  | Medium                                                                                      | Anticipated; drift detection catches it                                                                                                                                                                           | `prefix=""` or `add_property_override`; zero data impact                                           |
| 7   | `BootstrapVersion` parameter / `CheckBootstrapVersion` rule blocks the import changeset | Low                                                                                         | Neither is a resource, so it should be accepted                                                                                                                                                                   | `generate_bootstrap_version_rule=False`                                                            |
| 8   | L2/L1 mix-up recreates the user's policy as a standalone `AWS::IAM::Policy`             | Low                                                                                         | `iam.CfnUser` is mandated; the Task-001 test asserts no standalone `AWS::IAM::Policy` exists                                                                                                                      | Fix code before importing; nothing applied                                                         |
| 9   | Infra-role rename (O1) leaves `~/.aws/config` pointing at a dead ARN                    | Low, if O1 is taken                                                                         | Create-verify-switch-delete ordering; the old role is deleted only after the new chain is proven                                                                                                                  | Re-point the profile at `niffler-infra-role`, which still exists until the final step              |
| 10  | Operator locked out mid-migration                                                       | Very low                                                                                    | Permissions added in Task-002, revoked only in Task-007; the execution role is never deleted; `fmassa` admin never modified                                                                                       | Restore either policy from `$BK/*-policy.json` with `aws iam put-role-policy --profile fmassa`     |
| 11  | Bootstrap `cfn-exec-role` holds standing admin                                          | Eliminated                                                                                  | `--cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll`; niffler always passes its own execution role                                                                                            | Re-run `cdk bootstrap`; idempotent                                                                 |
| 12  | Access keys drift out of anyone's awareness (outside IaC)                               | Accepted                                                                                    | Documented here, in `infra/README.md` and `CLAUDE.md`; Parameter Store is the record of truth; the execution role provably cannot mint them                                                                       | N/A — by design                                                                                    |
| 13  | tfstate buckets deleted too early                                                       | Low                                                                                         | Task-006 gated on all three envs verified; state archived locally first                                                                                                                                           | Reconstruct a Terraform bootstrap + `terraform import` (below)                                     |

**Rollback to Terraform, per stage:**

- _After import, before `terraform state rm`_ — both tools track the resources; nothing mutated.
  `ENVIRONMENT=<env> cdk destroy`; `RETAIN` keeps every resource, and Terraform is authoritative
  again with no further action.
- _After `terraform state rm`, before Task-006_ — `cdk destroy` as above, then re-import into
  Terraform:

  ```bash
  cd infra/envs/dev
  terraform import module.data_bucket.aws_s3_bucket.this                                       niffler-dev-data-309917471802
  terraform import module.data_bucket.aws_s3_bucket_versioning.this                            niffler-dev-data-309917471802
  terraform import module.data_bucket.aws_s3_bucket_server_side_encryption_configuration.this  niffler-dev-data-309917471802
  terraform import module.data_bucket.aws_s3_bucket_public_access_block.this                   niffler-dev-data-309917471802
  terraform import module.data_bucket.aws_s3_bucket_lifecycle_configuration.this               niffler-dev-data-309917471802
  terraform import module.streamlit_iam.aws_iam_user.streamlit_app                             niffler-streamlit-app-dev
  terraform import module.streamlit_iam.aws_iam_user_policy.read_snapshots                     niffler-streamlit-app-dev:niffler-streamlit-app-dev-read-snapshots
  # aws_iam_access_key cannot be re-imported with its secret. It is untouched by this migration,
  # so it keeps working; it simply stays outside both tools' state.
  ```

  Note Terraform's `providers.tf` assumes `niffler-infra-execution-role`, whose trust policy keeps
  the human principal — so this rollback path stays open even after Task-002. If O1's rename was
  taken, update `~/.aws/config` accordingly.
  Alternatively restore `$BK/<env>-terraform.tfstate` with `aws s3 cp`.

- _After Task-006_ — no Terraform rollback. Re-bootstrapping state buckets and re-importing is a
  fresh project, not a rollback. This is why Task-006 is gated.

## Verification checklist (post-cutover)

```bash
BK=~/niffler-migration-backup

# The tag mechanism
for r in niffler-infra niffler-infra-execution-role; do
  aws iam list-role-tags --role-name $r --profile fmassa   # AppName=niffler
done

# Stacks
for env in dev demo prod; do
  aws cloudformation describe-stacks --profile fmassa --region us-east-2 \
    --stack-name niffler-infra-stack-$env \
    --query 'Stacks[0].[StackName,StackStatus,DriftInformation.StackDriftStatus]'
  ENVIRONMENT=$env uv run --no-sync npx cdk diff --profile niffler-infra --no-notices
done

# Nothing was recreated
for env in dev demo prod; do
  diff <(jq -S . "$BK/$env-inventory.json") \
       <(aws s3api list-object-versions --bucket niffler-$env-data-309917471802 --profile fmassa --output json | jq -S .)
  diff <(jq -S .User.UserId "$BK/$env-user.json") \
       <(aws iam get-user --user-name niffler-streamlit-app-$env --profile fmassa | jq -S .User.UserId)
  diff <(jq -S '[.AccessKeyMetadata[].AccessKeyId]' "$BK/$env-access-keys.json") \
       <(aws iam list-access-keys --user-name niffler-streamlit-app-$env --profile fmassa | jq -S '[.AccessKeyMetadata[].AccessKeyId]')
  diff <(jq -S .PolicyDocument "$BK/$env-user-policy.json") \
       <(aws iam get-user-policy --user-name niffler-streamlit-app-$env \
           --policy-name niffler-streamlit-app-$env-read-snapshots --profile fmassa | jq -S .PolicyDocument)
done
diff <(jq -S .Role.RoleId "$BK/niffler-infra-execution-role.json") \
     <(aws iam get-role --role-name niffler-infra-execution-role --profile fmassa | jq -S .Role.RoleId)

# Role chain, both hops
aws sts get-caller-identity --profile niffler-infra
aws sts get-caller-identity --profile niffler-infra-exec
aws s3 ls s3://niffler-dev-data-309917471802/snapshots/ --profile niffler-infra-exec
aws iam create-access-key --user-name niffler-streamlit-app-dev --profile niffler-infra-exec
# expect AccessDenied

# No unbounded wildcards (sts:GetCallerIdentity on "*" is the one allowed exception)
for r in niffler-infra niffler-infra-execution-role; do
  aws iam get-role-policy --role-name $r --policy-name $r-permissions --profile fmassa \
    | jq '[.PolicyDocument.Statement[] | select(.Sid != "CliPermissions") | (.Action, .Resource)]
          | flatten | map(select(. == "*" or . == "s3:*" or . == "iam:*" or . == "cloudformation:*"))'
  # expect []
done
aws iam list-attached-role-policies --role-name cdk-toolkitv2-cfn-exec-role-309917471802-us-east-2 \
  --profile fmassa   # expect AWSDenyAll, not AdministratorAccess

# Terraform gone
find infra -name '*.tf' -o -name '*.tfvars' -o -name '*.hcl' -o -name '.terraform' | wc -l   # 0
for env in dev demo prod; do
  aws s3api head-bucket --bucket niffler-$env-tfstate-309917471802 --profile fmassa   # 404
done

# App unchanged and still working
git diff --stat main -- src/                    # empty
uv run pytest tests/ -v
cd src/app && uv run streamlit run main.py
```

## Technical Constraints

- IaC: AWS CDK v2 (Python), following `tfmcdigital/kb-rma`; IAM policies following
  `tfmcdigital/edap-iam`. `aws-cdk-lib==2.266.0`; `constructs>=10.0.0,<11.0.0`; CDK CLI pinned in
  `package.json` (`aws-cdk` 2.1114.1), invoked as `uv run --no-sync npx cdk`. No nested stacks,
  StackSets, custom resources, Lambdas, `cdk-nag`, or CDK Pipelines.
- One environment per `cdk` invocation, selected by `ENVIRONMENT` and validated in
  `resource_utils.get_env()`.
- Cloud: AWS account `309917471802`, region `us-east-2` for every stack and resource. Hosting stays
  on Streamlit Cloud; no compute is created in AWS.
- Python: `>=3.13` (unchanged). No change to the `app` extra; `boto3` stays.
- Node.js: `>=22` (`.nvmrc`), required by the CDK CLI.
- Testing: `pytest`. One new offline module (`tests/infra/`) using `aws_cdk.assertions.Template`;
  no AWS calls.
- Style: niffler's existing ruff config applies to `infra/` too — module/class/method docstrings
  everywhere, full type hints, `from __future__ import annotations`. `infra/__init__.py` keeps the
  package out of implicit-namespace-package territory.

## Architecture Notes

- **State**: server-side, in CloudFormation. After Task-006 nothing in the repo or in S3 holds
  infrastructure state. `cdk.out/` and `node_modules/` are build artifacts and are gitignored.
- **Two layers, cleanly separated.** `infra/bootstrap/` is the platform layer — niffler's
  single-file `edap-iam`: the role pair, their tags and policies, and the CDK toolkit. It is
  created once by admin, outside CDK, because CDK authenticates through it.
  `infra/{app,infra_stack,resource_utils}.py` is the application layer — niffler's `kb-rma`. This
  is the same split 001 drew, with "the tfstate backend" replaced by "the CDK toolkit", and it is
  the same split the two reference repos draw between themselves.
- **Identities**, in chain order: (1) `fmassa` SSO admin — `bootstrap.sh`, `cdk bootstrap`, and
  minting access keys; (2) `niffler-infra` — CloudFormation on `stack/niffler*/*` plus
  `PassRole`/`AssumeRole`; (3) `niffler-infra-execution-role` — assumed by CloudFormation as the
  stacks' service role and by the human for `aws s3 cp` and `ssm put-parameter`; the only identity
  that can manage the data buckets and app users, and provably unable to mint their credentials;
  (4) `niffler-streamlit-app-<env>` — read-only on its own `snapshots/*` prefix.
- **Cross-env blast radius** is unchanged in kind from 001 but expressed differently: the
  `${aws:PrincipalTag/AppName}-*` pattern covers all three environments, so IAM alone still does
  not isolate them. What enforces isolation is that every name derives from `get_env()`, a single
  validated value, and a stack can only ever reference its own environment's resources. Per-env
  execution roles remain the future hardening option — and the tag mechanism makes them easy
  (tag per-env roles `AppName = niffler-dev` and the same policy documents narrow automatically).
- **New guardrails** relative to 001: `RemovalPolicy.RETAIN` on the data buckets; the infra role
  losing all direct data-bucket access; the execution role losing `iam:CreateAccessKey`; the
  bootstrap `cfn-exec-role` carrying `AWSDenyAll`; a trust policy that survives the SSO permission
  set being recreated; and a unit test that fails if any preserved name changes.
- **Data flow** is unchanged: a snapshot is uploaded by hand to
  `s3://niffler-<env>-data-309917471802/snapshots/YYYYMMDD.xlsx` → the environment's Streamlit
  instance lists the prefix, picks the lexicographically-max key, reads it → the existing
  `ProcessedLoader` pipeline runs downstream.

## Open questions

Reduced again — `edap-iam` settles the Parameter Store naming (R14), the bootstrap qualifier, and
the policy content, on top of what kb-rma already settled.

- **O1 — Rename `niffler-infra-role` → `niffler-infra`?** The house module produces
  `{service}-infra`; niffler's execution role already matches the convention exactly but the infra
  role is off by a `-role` suffix. It is not Terraform-managed, so the "preserve exact names"
  contract does not cover it, and its name appears in no policy document — only in the execution
  role's trust policy and in `~/.aws/config` (whose _profile_ name, confusingly, is already
  `niffler-infra` and would not change). **Recommendation: rename**, as part of the Task-002
  bootstrap rewrite, create-verify-switch-delete. Say if you would rather leave it.
- **O2 — Bootstrap Config A vs B.** Config A needs no template surgery but relies on CDK's
  fall-back-to-CLI-credentials behaviour when the toolkit deploy role cannot pass niffler's
  execution role; Config B customises the bootstrap template (and is what EDAP evidently does).
  Task-002 settles it empirically before anything is imported — confirm you are happy for it to be
  decided there rather than up front.
- **O3 — Bounded action wildcards.** The house `infra-s3` uses `s3:*Object` and
  `s3:*BucketVersioning`. These are suffix-anchored, not `s3:*`, but they do relax 001's literal
  "no wildcard action" criterion. **Recommendation: adopt them** (house convention, and the blast
  radius is already bounded by the tag-scoped resource ARN). Say if you would rather enumerate
  `GetObject`/`PutObject`/`DeleteObject` and the two versioning actions explicitly.
- **O4 — Parameter Store: convention only, or wire it in?** The `/config/niffler_<env>/...` naming
  and the `ssm.StringParameter.from_string_parameter_name` pattern are documented, but nothing in
  the stack consumes the parameters today. **Recommendation: document now, wire in when `DP-01`'s
  sync Lambda needs it.** Confirm, or say if you want the access-key-ID parameter referenced and
  re-emitted as a `CfnOutput` immediately.
- **O5 — `RemovalPolicy.RETAIN` on the IAM user.** Mandatory at import time; keeping it
  permanently means a future `cdk destroy` orphans the user. It is now doubly justified — without
  `iam:DeleteAccessKey` the execution role could not delete a key-holding user anyway.
  **Recommendation: keep.** Say if you disagree.
- **O6 — Permission boundary.** `edap-iam` attaches `default-infra-permissions-boundary` to the
  infra role; for niffler all three of its `Deny`s are unreachable, leaving only `Allow *` on `*`.
  **Recommendation: skip**, revisit at `CL-02`/`CL-03`. Say if you would rather adopt a trimmed
  version now for convention's sake.
- **O7 — `.python-version`.** Both references commit one. niffler does not have one and only
  declares `requires-python = ">=3.13"`. Adding `.python-version` (`3.13`) matches the convention
  and pins the toolchain; nothing in this PRD requires it. Confirm whether to add it.

## Out of Scope

- Any redesign of the 001 architecture (environments, naming, region, role chain, prefixes).
- Any change to `src/app/`, `tests/app/`, or `secrets.toml`.
- Bringing the chain roles under CDK; creating, rotating or deleting IAM access keys; creating SSM
  parameters.
- CI/CD (`CL-02`), including the GitHub-OIDC trust statement and the `-cicd` session conventions
  both references carry. Database (`CL-01` sub-item), app auth (`CL-03`), narrowing the SSO
  permission set (`CL-04`), Mobills automation (`DP-01`/`DP-02`).
- A permission boundary; nested stacks; StackSets; CDK Pipelines; `cdk-nag`; custom resources;
  multi-region; multi-account.
- Hardening beyond current parity (`enforce_ssl`, KMS CMKs, bucket policies, per-env execution
  roles).
- Uploading snapshot data; deploying `demo`/`prod` to Streamlit Cloud.
