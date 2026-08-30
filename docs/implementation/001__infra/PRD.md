# Feature: AWS Infra for niffler (S3 data buckets + least-privilege IAM)

> **IaC tool superseded.** The architecture below (buckets, IAM role chain, the two-hop identity
> model) is current and accurate. The IaC *tool* is not - as of
> `docs/implementation/002__cdk_migration/PRD.md`, all of it is managed by AWS CDK (Python), not
> Terraform. Every mention below of Terraform, `infra/modules`, `infra/envs`, or the tfstate
> buckets is historical - this document is the record of what originally shipped, not rewritten
> after the migration. See `002__cdk_migration/PRD.md` for the current tooling and `infra/README.md`
> for day-to-day commands.

## Overview

niffler currently reads a single Mobills Excel export per run from `src/app/data/YYYYMMDD.xlsx`
on local disk (gitignored, real financial data). This PRD sets up the first slice of
`CL-01: Migrate to cloud` (see `docs/backlog.md`): an AWS account, managed via Terraform under
`infra/`, that stores those Excel snapshots in S3 so the app can run on **Streamlit Cloud** (not
AWS) and read its data from the cloud instead of a local file.

This is infrastructure + a focused loader rewrite — not a broader app rewrite. No database, no
CI/CD, and no app-level auth are introduced here; those are tracked separately as `CL-02`
(CI/CD) and `CL-03` (auth) and the database sub-item of `CL-01`, all explicitly deferred.

Two design constraints run through the whole document:

1. **Three environments, one AWS account.** niffler gets `dev`/`demo`/`prod` Terraform
   environments (mirroring `fantasy-br`'s pattern) even though it's a personal, single-user app
   — the user has chosen this over a single-env setup. Each environment gets its own S3 data
   bucket and its own Terraform state bucket; the app's runtime code is env-agnostic and simply
   reads whichever bucket its credentials point at. Local development targets the `dev` bucket.
2. **The human's AWS SSO session never touches niffler resources directly.** It is only ever
   used to assume a narrow `niffler-infra-role`, which is in turn only used to assume an even
   narrower `niffler-infra-execution-role` that actually has permission to create/manage
   niffler's AWS resources. Both roles, plus the three Terraform state buckets, are created once
   by a bootstrap step that lives *outside* the `infra/` Terraform project (see "Bootstrap"
   below) — the project that manages the state backend can't itself be managed by that same
   state.

## Current State (verified before any AWS work)

- `~/.aws/config` has two profiles, `default` and `fmassa`, both AWS SSO:
  `sso_start_url = https://d-9a6756a9b2.awsapps.com/start/`, `sso_region = us-east-2`,
  `sso_account_id = 309917471802`, `sso_role_name = AdministratorAccess`, `region = us-east-2`.
- No `~/.aws/credentials` file — auth is SSO-only, no long-lived local admin keys.
- `aws sts get-caller-identity` currently fails ("Error loading SSO Token ... does not exist")
  — the SSO session is logged out. `aws sso login --profile fmassa` is required before any
  `terraform init/plan/apply`.
- AWS CLI v2 is installed (`aws-cli/2.34.19`). **Terraform is not installed** on this machine —
  install via the official HashiCorp apt repository, pinned to `>= 1.10.0` (this PRD relies on
  Terraform's native S3-backend locking, which needs `>= 1.10`; see "Bootstrap" below).
- Both profiles resolve to the same account (`309917471802`) with `AdministratorAccess`.
  `fmassa` is used as the `source_profile` for every chained profile in this doc (`default` is
  left untouched). There is no non-admin human identity — see the caveat under "SSO role scope"
  below.

## Reference pattern (adapted, not copied)

`fantasy-br` (`/home/fmassa/github/fantasy-br/infra/`) uses GCP + Terraform with
`infra/modules/{bigquery,firestore,iam}/` and `infra/envs/{dev,demo,prod}/`, each env with its
own GCS state bucket (`fantasy-br-tfstate-{env}`) created by CI. niffler keeps the module/env
split and the per-env state bucket pattern, and changes the rest:

1. **AWS instead of GCP** — S3 module replaces bigquery/firestore modules; IAM module creates
   actual identities (users + policies), not just role bindings onto a pre-existing service
   account (fantasy-br's IAM module assumes the SA already exists via CI/Workload Identity).
2. **A `bootstrap/` step instead of CI-driven bootstrap** — fantasy-br's per-env tfstate buckets
   are created by a CI pipeline before `terraform init`. niffler has no CI/CD, so all three
   state buckets (and the two IAM roles below) are created once, manually.
3. **A two-hop IAM role chain in front of Terraform, which fantasy-br does not have** —
   fantasy-br's CI uses Workload Identity Federation to act as a GCP service account directly.
   niffler has no CI/CD and would otherwise run every `terraform apply` as the raw
   `AdministratorAccess` SSO session. To avoid that, bootstrap creates `niffler-infra-role`
   (assumable only by the SSO session) and `niffler-infra-execution-role` (assumable only by
   `niffler-infra-role`, and the only identity with permission to touch niffler's actual AWS
   resources). See "Bootstrap" below for the full chain.
4. **IAM roles are account-wide, not per-env** (unlike the three data/state buckets, which are
   per-env). See "Why the IAM roles are shared across environments" below for the reasoning.

## Scope

**In scope:**

- Three S3 buckets for Excel snapshots, one per environment (`dev`/`demo`/`prod`).
- Three Terraform state buckets, one per environment, created via a manual one-time bootstrap
  step that lives outside the `infra/` Terraform project.
- Two account-wide IAM roles, also created by that bootstrap step, forming the chain the human
  uses to drive Terraform for any environment: `niffler-infra-role` (assumable by the SSO
  session) and `niffler-infra-execution-role` (assumable only by `niffler-infra-role`; the only
  identity that can create/manage niffler's actual AWS resources in any environment).
- IAM: one narrowly-scoped, read-only IAM user per environment for that environment's Streamlit
  app instance to read its own bucket, created by the `infra/` Terraform project (i.e. by
  `niffler-infra-execution-role`).
- `infra/` module + env layout, documented local `terraform init/plan/apply` workflow (via the
  role chain above), for all three environments.
- A loader rewrite in `src/app/utils/` so the app reads its latest snapshot from S3
  unconditionally — this fully replaces the local-disk read path (no toggle, no fallback; see
  Task-005).
- Streamlit Cloud Secrets UI wiring for the `dev` environment's AWS credential (used for local
  development) — see "What this PRD does not cover" for `demo`/`prod` deployment.

**Out of scope (tracked elsewhere, do not fold in):**

- Any database (`CL-01` sub-item, deferred pending pricing research).
- CI/CD of any kind (`CL-02`) — every `terraform apply` in this PRD is a manual command run by
  a human from their machine.
- App-level auth / allowed-emails (`CL-03`).
- Automatic Mobills fetching (`DP-01`, `DP-02`) and the sync-to-database Lambda mentioned in
  `DP-01` — no Lambda is created here.
- Multi-region or multi-account design; disaster recovery beyond S3 versioning.
- **Uploading snapshot data to S3.** This PRD delivers the mechanism (buckets, IAM, the app's
  read path) but not any data migration. The user uploads snapshots to the `dev` bucket by hand,
  asynchronously, outside this project's scope, once the infra exists. Verification in this doc
  proves the read path works against whatever is in the bucket at the time (including "empty
  bucket raises a clear error"), not against a specific real snapshot.
- Narrowing the `fmassa` SSO permission set away from `AdministratorAccess` — tracked as a new
  backlog item, `CL-04` (see `docs/backlog.md`), not part of this PRD.

**What this PRD does not cover (explicit follow-up, not blocking):** whether `demo` and/or
`prod` ever get an actual Streamlit Cloud deployment (and thus their own Secrets UI wiring) is a
hosting decision the user makes at deploy time, independent of the infra this PRD builds — all
three environments' infra is built uniformly regardless. Only `dev`'s Streamlit Cloud secrets
(used for local development) are wired up as part of this PRD.

## Decisions (all 11 originally-open questions, now resolved)

- **Terraform**: install via the official HashiCorp apt repository, pinned `>= 1.10.0`.
- **Environments**: `dev`, `demo`, `prod` — three full Terraform environments under
  `infra/envs/`, each with its own data bucket and state bucket. Local development and this
  PRD's Streamlit secrets wiring target `dev`.
- **Naming**: account-ID-suffixed, with the environment segment in the bucket name:
  `niffler-<env>-data-309917471802` and `niffler-<env>-tfstate-309917471802` (e.g.
  `niffler-dev-data-309917471802`). IAM role names (`niffler-infra-role`,
  `niffler-infra-execution-role`) stay env-agnostic — they're account-wide, not per-env (see
  "Why the IAM roles are shared across environments"). Per-env Streamlit-app IAM users are named
  `niffler-streamlit-app-<env>`.
- **SSO source profile**: `fmassa`, not `default`, as the `source_profile` for every chained
  profile in this doc.
- **Region**: `us-east-2` for everything (matches the existing SSO profile default).
- **State locking**: Terraform's native S3-backend locking (`use_lockfile = true`), one lock
  file per state bucket — no DynamoDB table anywhere. Requires Terraform `>= 1.10`.
- **Snapshot uploads**: out of scope for this PRD (see Scope above) — no infra-deployment task
  uploads data. When the user does upload by hand later, it's a manual `aws s3 cp` to the
  relevant env's bucket under the `snapshots/` prefix (chosen for consistency with `DP-01`'s
  future "raw report" dump using a sibling prefix in the same bucket), through the
  `niffler-infra-exec` chained profile (see "Bootstrap").
- **New dependency**: `boto3`, added to the `app` optional-dependencies group.
- **Local dev**: no toggle, no local-disk code path. The app always reads from S3 — local
  development requires a working `secrets.toml` `[aws]` block (pointed at `dev`) and network
  access to AWS, same as a deployed instance. `get_latest_data_path()`'s local-disk logic is
  removed from the app's runtime path entirely (see Task-005) — existing `.xlsx` files may still
  be kept under `tests/` purely as offline unit-test fixtures, which is unrelated to the app's
  production read path.
- **Credential type**: static, long-lived IAM user access key/secret (no OIDC — Streamlit Cloud
  doesn't support it). One IAM user *per environment* (`niffler-streamlit-app-<env>`), not one
  shared user across environments — this falls out naturally from each env directory applying
  its own `iam` module instance with its own bucket, and it means a leaked `dev` credential
  can't read `prod` data. The same per-env user/credential is used both for that environment's
  local-dev `secrets.toml` (only relevant for `dev`, today) and its Streamlit Cloud Secrets UI
  if/when that environment is deployed.
- **SSO role scope**: kept as `AdministratorAccess` — the two-hop role chain is a *workflow*
  convention, not a hard technical barrier, since an admin session is technically capable of
  bypassing it. It still adds real value (a narrow, auditable, CloudTrail-visible path for the
  intended workflow), and would matter immediately if the permission set were ever narrowed.
  That narrowing is tracked as a new backlog item, `CL-04`, not part of this PRD.

### Why the IAM roles are shared across environments

The two chain roles (`niffler-infra-role`, `niffler-infra-execution-role`) are **not**
duplicated per environment, unlike the data/state buckets. Reasoning:

- All three environments live in the *same* AWS account — there's no account-level isolation
  boundary to mirror with per-env roles the way there might be in a multi-account setup.
- niffler is a single-user personal project. Per-env roles would exist to stop one environment's
  automation from touching another's resources, but there is no separate automation per
  environment here (no CI/CD) — the same human runs `terraform apply` for all three, from the
  same machine, with the same SSO session. Three copies of the same two roles would add
  bootstrap complexity with no real isolation benefit.
- The trade-off this creates: `niffler-infra-execution-role`'s policy must explicitly enumerate
  all three environments' bucket ARNs (see "Bootstrap" below) rather than a single bucket ARN.
  This means a `terraform apply` run from `infra/envs/dev/` is, at the IAM-permission level,
  technically also capable of modifying `infra/envs/prod/`'s bucket — nothing in IAM stops it.
  The only thing preventing that in practice is that each env directory's own Terraform config
  only references its own environment's bucket name/variables. This is isolation by
  code-review/convention, not by IAM boundary — an accepted trade-off given the single-user,
  no-CI/CD context above. If cross-env blast-radius ever becomes a real concern, the fix is
  per-env execution roles, which the module structure already supports adding later without a
  restructure.

## Bootstrap: state backend + the two-hop IAM role chain

Bootstrap creates everything Terraform itself depends on, and therefore cannot be managed by
the `infra/` Terraform project (it would need to already exist to manage itself). It is done
**once**, manually, via a shell script under `infra/bootstrap/` that calls the AWS CLI directly
— not a Terraform config. This is a deliberate choice over a second, local-state Terraform
config: a shell script makes it structurally impossible to confuse bootstrap's state with the
main project's state (there is no bootstrap state to confuse), and these resources are created
once and essentially never change, so losing Terraform's plan/diff ergonomics here is an
acceptable trade for simplicity.

**What it creates** (see Task-001 for the concrete script contents):

1. **Three Terraform state buckets** — `niffler-dev-tfstate-309917471802`,
   `niffler-demo-tfstate-309917471802`, `niffler-prod-tfstate-309917471802`, each versioned,
   SSE-S3 encrypted, and fully public-access-blocked. No DynamoDB lock table anywhere — each
   env's `backend.tf` uses Terraform's native S3-backend locking (`use_lockfile = true`)
   instead, which stores the lock alongside the state object in the same bucket.
2. **`niffler-infra-role`** — assumable only by the existing SSO `AdministratorAccess` role. Its
   own permissions are narrow: read/write all three tfstate buckets, and `sts:AssumeRole` on
   `niffler-infra-execution-role`'s ARN only. It cannot touch any data bucket or IAM user
   directly.
3. **`niffler-infra-execution-role`** — assumable only by `niffler-infra-role` (role chaining:
   its trust policy's `Principal` is `niffler-infra-role`'s ARN, not the SSO role). This is the
   only identity with permission to create/manage niffler's actual resources: all three data
   buckets (Task-002) and the three `niffler-streamlit-app-<env>` IAM users (Task-003). No
   `*:*`, no unscoped `Resource: "*"` — resources are enumerated explicitly per environment (see
   "Why the IAM roles are shared across environments" above for why this enumeration exists
   instead of a per-env role).

**Trust policies** (identical regardless of environment, since the roles are account-wide):

```json
// niffler-infra-role's trust policy
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::309917471802:role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess_<hash>" },
    "Action": "sts:AssumeRole"
  }]
}
```

```json
// niffler-infra-execution-role's trust policy
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::309917471802:role/niffler-infra-role" },
    "Action": "sts:AssumeRole"
  }]
}
```

The `<hash>` suffix in the SSO role ARN is generated by IAM Identity Center and isn't knowable
ahead of time — Task-001 documents looking it up via `aws sts get-caller-identity --profile
fmassa` after `aws sso login` (it returns an `assumed-role/<RoleName>/<SessionName>` ARN; drop
the session-name segment and swap `assumed-role` for `role` to get the trust-policy principal).

**Permissions policies** (each enumerates all three environments explicitly — see "Why the IAM
roles are shared across environments"):

```json
// niffler-infra-role's permissions policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateAccessAllEnvs",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::niffler-dev-tfstate-309917471802",
        "arn:aws:s3:::niffler-dev-tfstate-309917471802/*",
        "arn:aws:s3:::niffler-demo-tfstate-309917471802",
        "arn:aws:s3:::niffler-demo-tfstate-309917471802/*",
        "arn:aws:s3:::niffler-prod-tfstate-309917471802",
        "arn:aws:s3:::niffler-prod-tfstate-309917471802/*"
      ]
    },
    {
      "Sid": "AssumeExecutionRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::309917471802:role/niffler-infra-execution-role"
    }
  ]
}
```

```json
// niffler-infra-execution-role's permissions policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ManageDataBucketsAllEnvs",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket", "s3:DeleteBucket", "s3:GetBucketLocation",
        "s3:GetBucketVersioning", "s3:PutBucketVersioning",
        "s3:GetEncryptionConfiguration", "s3:PutEncryptionConfiguration",
        "s3:GetBucketPublicAccessBlock", "s3:PutBucketPublicAccessBlock",
        "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration",
        "s3:GetBucketTagging", "s3:PutBucketTagging",
        "s3:GetBucketPolicy", "s3:PutBucketPolicy", "s3:DeleteBucketPolicy",
        "s3:GetBucketAcl", "s3:PutBucketAcl",
        "s3:GetBucketCORS", "s3:PutBucketCORS",
        "s3:GetBucketLogging", "s3:PutBucketLogging",
        "s3:GetBucketRequestPayment", "s3:PutBucketRequestPayment",
        "s3:GetAccelerateConfiguration", "s3:PutAccelerateConfiguration",
        "s3:GetBucketWebsite", "s3:PutBucketWebsite",
        "s3:GetReplicationConfiguration", "s3:PutReplicationConfiguration",
        "s3:GetBucketObjectLockConfiguration", "s3:PutBucketObjectLockConfiguration",
        "s3:GetBucketOwnershipControls", "s3:PutBucketOwnershipControls",
        "s3:GetBucketNotification", "s3:PutBucketNotification",
        "s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::niffler-dev-data-309917471802",
        "arn:aws:s3:::niffler-dev-data-309917471802/*",
        "arn:aws:s3:::niffler-demo-data-309917471802",
        "arn:aws:s3:::niffler-demo-data-309917471802/*",
        "arn:aws:s3:::niffler-prod-data-309917471802",
        "arn:aws:s3:::niffler-prod-data-309917471802/*"
      ]
    },
    {
      "Sid": "ManageStreamlitAppIdentities",
      "Effect": "Allow",
      "Action": [
        "iam:CreateUser", "iam:DeleteUser", "iam:GetUser", "iam:TagUser",
        "iam:PutUserPolicy", "iam:DeleteUserPolicy", "iam:GetUserPolicy",
        "iam:CreateAccessKey", "iam:DeleteAccessKey", "iam:ListAccessKeys"
      ],
      "Resource": "arn:aws:iam::309917471802:user/niffler-streamlit-app-*"
    }
  ]
}
```

The execution role's S3 action list is longer than a first read of "manage the data buckets"
suggests: Terraform's `aws_s3_bucket` resource reads a broad set of bucket-level attributes
(policy, ACL, CORS, logging, etc.) on every `plan`/`refresh` for backward-compatibility reasons,
even though this module only configures versioning/encryption/public-access-block/lifecycle. All
of these were discovered by actually running `terraform apply` against the real account and
adding the specific `AccessDenied` action each error named - the list above is the exact set
required, not a guess; it still contains no wildcard `Action` and every statement is scoped to
niffler's own bucket ARNs, never `Resource: "*"`.

**How the local Terraform workflow uses the chain (two hops, at two different points, the same
for every environment):**

- **Hop 1 (SSO → `niffler-infra-role`)** happens at the AWS CLI/SDK level via a chained profile
  added to `~/.aws/config`:

  ```ini
  [profile niffler-infra]
  role_arn       = arn:aws:iam::309917471802:role/niffler-infra-role
  source_profile = fmassa
  region         = us-east-2
  ```

  Every environment's `backend.tf` sets `profile = "niffler-infra"` in its `backend "s3"` block,
  so every `terraform init`/state operation, in any of `infra/envs/{dev,demo,prod}/`,
  authenticates as `niffler-infra-role` directly — which already has the permissions it needs
  for all three state buckets, no second hop required for state.

- **Hop 2 (`niffler-infra-role` → `niffler-infra-execution-role`)** happens inside each
  environment's `provider "aws"` block, so it applies to every actual resource API call
  (`terraform plan`/`apply` against that environment's `s3_bucket` and `iam` modules):

  ```hcl
  provider "aws" {
    region  = var.region
    profile = "niffler-infra"

    assume_role {
      role_arn     = "arn:aws:iam::309917471802:role/niffler-infra-execution-role"
      session_name = "niffler-terraform-${var.environment}"
    }
  }
  ```

- **The same hop 2 is needed outside Terraform**, for the future manual `aws s3 cp` snapshot
  uploads (out of scope for this PRD, but the mechanism should exist since `niffler-infra-role`
  itself has no data-bucket permissions by design). Add a second chained CLI profile that stacks
  on top of the first:

  ```ini
  [profile niffler-infra-exec]
  role_arn       = arn:aws:iam::309917471802:role/niffler-infra-execution-role
  source_profile = niffler-infra
  region         = us-east-2
  ```

  `aws sts get-caller-identity --profile niffler-infra-exec` should show the execution role,
  having chained through both hops.

## Success Criteria

- [x] All tasks below complete, in order, with each "Verification" step passing.
- [x] `terraform plan` in each of `infra/envs/{dev,demo,prod}/` shows zero drift after `apply`.
- [x] No IAM policy anywhere (bootstrap roles or `infra/`-managed resources) contains
      `"Action": "s3:*"`, `"Action": "iam:*"`, or `"Resource": "*"`.
- [x] The two-hop chain is verified end to end: `aws sts get-caller-identity --profile
      niffler-infra-exec` resolves through `fmassa` -> `niffler-infra-role` ->
      `niffler-infra-execution-role`, and the raw `fmassa`/`default` SSO profiles are never used
      directly in any `terraform apply` command in the final docs/scripts.
- [x] The app (run locally) reads its data exclusively from the `dev` S3 bucket — no local-disk
      code path remains in the runtime loader.
- [x] `docs/backlog.md`'s `CL-01` entry reflects what shipped vs what's still open, and a new
      `CL-04` entry exists for narrowing the SSO permission set.

## Tasks

### Task-000: Prerequisites (local machine setup, not a PR)

**Priority**: High
**Estimated Iterations**: 1

**Acceptance Criteria**:

- [x] Terraform `>= 1.10.0` installed locally via the HashiCorp apt repository.
- [x] `aws sso login --profile fmassa` completes successfully.

**Verification**:

```bash
terraform version                                   # >= 1.10.0
aws sts get-caller-identity --profile fmassa         # returns account 309917471802
```

### Task-001: Bootstrap — three state buckets + the two IAM roles

**Priority**: High
**Estimated Iterations**: 2-3

**Acceptance Criteria**:

- [x] `infra/bootstrap/bootstrap.sh` created — a plain AWS CLI shell script, **not Terraform**
      (see "Bootstrap" section above for why), run once with `--profile fmassa`.
      `infra/bootstrap/README.md` documents what it does and how to re-run pieces of it by hand
      if something fails partway (it is not expected to be idempotent/re-runnable end-to-end).
- [x] Script creates all three tfstate S3 buckets (`niffler-{dev,demo,prod}-tfstate-309917471802`)
      with versioning on, SSE-S3 encryption on, and all four public-access-block settings
      enabled. No DynamoDB table is created (native S3-backend locking is used instead).
- [x] Script documents looking up the SSO `AdministratorAccess` permission-set role ARN via
      `aws sts get-caller-identity --profile fmassa`, per the note above.
- [x] Script creates `niffler-infra-role` with the trust policy and permissions policy shown
      above (all three tfstate buckets + `sts:AssumeRole` on `niffler-infra-execution-role`
      only — no data-bucket or IAM permissions).
- [x] Script creates `niffler-infra-execution-role` with the trust policy shown above (trusts
      only `niffler-infra-role`) and the permissions policy from the "Bootstrap" section, scoped
      to all three data buckets and `niffler-streamlit-app-*` IAM users only.
- [x] `infra/bootstrap/README.md` includes the exact `~/.aws/config` blocks to add for the
      `niffler-infra` and `niffler-infra-exec` chained profiles (per-developer-machine config,
      not committed as files — this is a single-developer project run from one machine, so
      documenting the block is enough).
- [x] No wildcard `Action` or `Resource` in either role's permissions policy.

**Verification**:

```bash
aws sso login --profile fmassa
bash infra/bootstrap/bootstrap.sh   # uses --profile fmassa internally

# after adding the niffler-infra / niffler-infra-exec profile blocks to ~/.aws/config:
aws sts get-caller-identity --profile niffler-infra        # shows niffler-infra-role
aws sts get-caller-identity --profile niffler-infra-exec   # shows niffler-infra-execution-role,
                                                            # proving the full two-hop chain works
```

### Task-002: S3 bucket module for snapshot data

**Priority**: High
**Estimated Iterations**: 1-2

**Acceptance Criteria**:

- [x] `infra/modules/s3_bucket/` (`main.tf`, `variables.tf`, `outputs.tf`) is a generic,
      reusable module: bucket resource, `aws_s3_bucket_versioning` (Enabled), server-side
      encryption (SSE-S3/AES256), `aws_s3_bucket_public_access_block` (all four `true`).
- [x] Optional lifecycle rule: expire noncurrent object versions after 90 days (bounds storage
      cost from versioning; data volume is tiny so this is hygiene, not a cost necessity).
- [x] Module takes bucket name and tags as variables; outputs bucket name + ARN. Same module is
      instantiated once per environment with a different `bucket_name`.
- [x] No public read/write of any kind — bucket is 100% private, accessed only via IAM.

**Verification**:

```bash
cd infra/envs/dev && terraform validate
terraform plan   # shows the s3_bucket module's planned resources with versioning/encryption/PAB set
# repeat for infra/envs/demo and infra/envs/prod
```

### Task-003: IAM module — per-env, least-privilege Streamlit-app identity

**Priority**: High
**Estimated Iterations**: 1-2

**Acceptance Criteria**:

- [x] `infra/modules/iam/` creates one `aws_iam_user` (name passed in as a variable, e.g.
      `niffler-streamlit-app-dev`) with an `aws_iam_user_policy` built from an
      `aws_iam_policy_document` data source — no managed/wildcard policies.
- [x] Policy grants exactly:
      - `s3:ListBucket` on the bucket ARN, scoped with an `s3:prefix` condition to
        `snapshots/*` (so the identity can't enumerate anything outside that prefix).
      - `s3:GetObject` on `arn:aws:s3:::<bucket>/snapshots/*` only.
      - No `PutObject`, `DeleteObject`, `s3:*`, or `Resource: "*"` anywhere.
- [x] Creates an `aws_iam_access_key` for the user; the secret key output is marked
      `sensitive = true` in `outputs.tf` (never printed in plain `terraform plan`/`apply` logs).
- [x] Module is instantiated once per environment with that environment's bucket ARN and user
      name — a `dev` credential can only ever read the `dev` bucket, `demo`'s only `demo`'s, and
      so on.

**Verification**:

```bash
cd infra/envs/dev && terraform plan
# manually inspect the plan output / policy document for niffler-streamlit-app-dev — confirm
# only s3:ListBucket + s3:GetObject appear, both resource-scoped to the dev data bucket/prefix
```

### Task-004: Wire the `dev`, `demo`, and `prod` environments

**Priority**: High
**Estimated Iterations**: 2

**Acceptance Criteria**:

- [x] `infra/envs/{dev,demo,prod}/` each created with `backend.tf` (S3 backend pointing at that
      environment's Task-001 state bucket, `profile = "niffler-infra"`,
      `use_lockfile = true`), `providers.tf` (AWS provider pinned `~> 5.0`, Terraform
      `required_version >= 1.10.0`, region `us-east-2`, `profile = "niffler-infra"` +
      `assume_role { role_arn = niffler-infra-execution-role }` per the "Bootstrap" section's
      hop 2), `main.tf` (wires `s3_bucket` + `iam` modules together with that environment's
      values), `variables.tf`, `terraform.tfvars` (`environment`, `region`, bucket/user names —
      no secrets), `outputs.tf` (bucket name, IAM user name, sensitive access key/secret),
      `.terraform.lock.hcl` (committed, generated by `terraform init`).
- [x] `terraform init && terraform plan && terraform apply` succeed end-to-end, independently,
      in each of the three env directories, from a clean checkout, using only the chained
      `niffler-infra` profile — never a raw admin SSO profile, and no manual state surgery.
- [x] Applying `dev` does not require `demo`/`prod` to exist yet and vice versa — the three
      environments are fully independent Terraform root modules.

**Verification**:

```bash
for env in dev demo prod; do
  (cd infra/envs/$env && terraform init && terraform plan -out=tfplan && terraform apply tfplan)
done
aws s3 ls s3://niffler-dev-data-309917471802/ --profile niffler-infra-exec    # exists, empty
aws s3 ls s3://niffler-demo-data-309917471802/ --profile niffler-infra-exec   # exists, empty
aws s3 ls s3://niffler-prod-data-309917471802/ --profile niffler-infra-exec   # exists, empty
```

### Task-005: Replace the local-disk loader with an S3-backed loader

**Priority**: High
**Estimated Iterations**: 2-3

**Acceptance Criteria**:

- [x] `boto3` added to the `app` optional-dependencies group in `pyproject.toml`.
- [x] `src/app/utils/__init__.py`'s `get_latest_data_path()` (local-disk `glob` + `max()`) is
      removed from the app's runtime path and replaced with an S3 equivalent — lists objects
      under the configured prefix and returns the lexicographically-**max key**, mirroring the
      old `glob(...) + max()` semantics exactly (correctness must depend on the
      `YYYYMMDD.xlsx` filename, not S3's `LastModified`, so out-of-order uploads/backfills
      behave identically to the old local-disk behavior).
- [x] Both existing read sites are updated to use it: `src/app/utils/operators/loader.py`'s
      `Loader` (`"Receitas e Despesas"` sheet) and
      `src/app/utils/business/travel.py`'s `TripBalanceCalculator._load_transfer_data`
      (`"Transfers"` sheet) — both currently call `get_latest_data_path()` independently and
      both must read from the same resolved S3 key. Each reads the object body into a `BytesIO`
      and passes that to `pd.read_excel` instead of a local path.
- [x] There is **no** local-disk fallback and **no** config toggle — the app always reads from
      S3. Bucket name / prefix / region / credentials come entirely from `st.secrets["aws"]`,
      never hardcoded.
- [x] Unit tests added under `tests/app/` that mock the S3 client (e.g. `moto` or
      `unittest.mock`, per "mock only external dependencies") covering: latest-key selection
      with out-of-order object listing, and empty-bucket error handling (a clear,
      actionable error — e.g. `FileNotFoundError` — mirroring the old empty-`data/`-dir case).
      Existing local `.xlsx` files may be kept under `tests/` purely as fixtures for these
      mocked tests; that's unrelated to the app's production read path.

**Verification**:

```bash
uv run pytest tests/ -v
cd src/app && uv run streamlit run main.py   # works end-to-end reading from the dev S3 bucket
                                              # (requires a populated secrets.toml, Task-006)
```

### Task-006: Wire `dev` Streamlit secrets for local development

**Priority**: Medium
**Estimated Iterations**: 1

**Acceptance Criteria**:

- [x] `src/app/.streamlit/secrets.toml` created locally (gitignored — add `.streamlit/` or
      `secrets.toml` to `.gitignore` if not already covered) with an `[aws]` block:
      `access_key_id`, `secret_access_key`, `region`, `bucket_name`, `data_prefix`, populated
      from `niffler-streamlit-app-dev`'s Task-003 Terraform output — never committed.
- [x] No data upload happens as part of this task (see Scope — snapshot upload is explicitly
      out of scope). Verification instead proves the *mechanism*: the app correctly raises the
      Task-005 empty-bucket error against the freshly-created, still-empty `dev` bucket, and
      then correctly reads a manually-placed test object once one exists.
- [x] `demo`/`prod` Streamlit Cloud secrets are **not** wired up here — deferred to whenever
      those environments actually get a Streamlit Cloud deployment (see "What this PRD does not
      cover").

**Verification**:

```bash
cd src/app && uv run streamlit run main.py
# with dev bucket empty: app surfaces the Task-005 empty-bucket error clearly, no stack trace to the user
aws s3 cp <any>.xlsx s3://niffler-dev-data-309917471802/snapshots/ --profile niffler-infra-exec
cd src/app && uv run streamlit run main.py
# now renders the dashboard using that object's data
```

### Task-007: Documentation

**Priority**: Low
**Estimated Iterations**: 1

**Acceptance Criteria**:

- [x] `docs/backlog.md`'s `CL-01` entry updated to strike through/annotate completed sub-items
      (Terraform IaC, profiles, S3, Streamlit Cloud secrets for local dev) and leave the
      database sub-item open; `CL-02`/`CL-03` untouched. New `CL-04` entry added (see below).
- [x] Root `README.md`'s "Weekly Routine" section updated: the local `src/app/data/` save step
      is replaced with a note that data now lives in S3 (`dev` bucket for local development;
      upload is manual and out of this PRD's scope, per Scope above).
- [x] `CLAUDE.md`'s "Project structure" / "Data" sections updated to describe the S3-backed
      loader (replacing the local-file description) and mention `infra/`.

**Verification**:

- Manual read-through: a new reader can follow `README.md` + this doc to redeploy the whole
  stack (all three environments) from a clean AWS account and a clean checkout.

## Technical Constraints

- IaC: Terraform `>= 1.10.0`, AWS provider `hashicorp/aws ~> 5.0`.
- Cloud: AWS only, account `309917471802`, region `us-east-2` for every environment and every
  resource. App hosting stays on Streamlit Cloud — no compute is created in AWS by this PRD.
- Python: `boto3` added to the existing `uv`-managed `pyproject.toml` `app` extra.
- Testing: `pytest`, mocking only the boto3/S3 boundary (per repo + global testing conventions).

## Architecture Notes

- Identities, in chain order: (1) human's `fmassa` SSO `AdministratorAccess` session — never
  used directly against niffler resources; (2) `niffler-infra-role` (account-wide) — assumable
  only by (1), permissions limited to the three Terraform state buckets + assuming (3); (3)
  `niffler-infra-execution-role` (account-wide) — assumable only by (2), the only identity that
  can create/manage the three data buckets and the three `niffler-streamlit-app-<env>` IAM
  users; (4) `niffler-streamlit-app-<env>` IAM users, one per environment — created by (3),
  each read-only and scoped to its own environment's `s3://<bucket>/snapshots/*`, credential
  lives only in that environment's Streamlit Cloud Secrets (`dev`'s also mirrored in the local
  gitignored `secrets.toml`).
- Data flow: (out of this PRD's scope) a snapshot is uploaded by hand to an environment's
  bucket under `snapshots/YYYYMMDD.xlsx` -> that environment's Streamlit app instance (using its
  own `niffler-streamlit-app-<env>` credential) lists the prefix, picks the max key, reads it
  via `s3:GetObject` -> existing `ProcessedLoader` pipeline (dilution/tiers/travel rules) is
  unchanged downstream of the loader.
- State: `infra/bootstrap/bootstrap.sh` (plain AWS CLI, no Terraform state at all — see
  "Bootstrap" section) creates the three tfstate buckets and both IAM roles once. Every
  subsequent `terraform init/plan/apply`, in any of `infra/envs/{dev,demo,prod}/`, authenticates
  through the `niffler-infra` -> `niffler-infra-execution-role` chain, never as the raw SSO
  session.
- Cross-env blast radius: because the two chain roles are account-wide (see "Why the IAM roles
  are shared across environments"), IAM alone does not stop a `dev` Terraform run from being
  *capable* of touching `prod`'s bucket — isolation between environments is enforced by each env
  directory only referencing its own resources, not by an IAM boundary. Accepted trade-off for a
  single-user, no-CI/CD project; revisit with per-env execution roles if that ever changes.

## Out of Scope

- Database of any kind (`CL-01` sub-item — pricing research not done yet).
- CI/CD (`CL-02`) — everything here is a manual, local command.
- App-level auth / allowed-emails (`CL-03`).
- Narrowing the `fmassa` SSO permission set (`CL-04`, newly tracked — see `docs/backlog.md`).
- Automatic Mobills fetching or a sync Lambda (`DP-01`, `DP-02`).
- Uploading any snapshot data to S3 (see Scope above) — the buckets are delivered empty.
- Deploying `demo`/`prod` to Streamlit Cloud (a hosting decision, not an infra one).
- Per-env IAM roles for the Terraform chain (possible future hardening, not needed now).
