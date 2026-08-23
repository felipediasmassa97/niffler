# Bootstrap

One-time setup that creates everything Terraform itself depends on, run manually with the raw
admin SSO session. It is **not** a Terraform config, and it is **not** part of `infra/`'s
Terraform state - see `docs/implementation/001__infra/PRD.md` ("Bootstrap" section) for why: the
project that manages the Terraform state backend can't itself be managed by that same state.

## What it creates

Running `bootstrap.sh` once creates:

1. Three Terraform state buckets, one per environment: `niffler-{dev,demo,prod}-tfstate-309917471802`
   (versioned, SSE-S3 encrypted, fully public-access-blocked). No DynamoDB lock table - each
   environment's `backend.tf` uses Terraform's native S3-backend locking instead.
2. `niffler-infra-role` - assumable only by the `fmassa` SSO session. Scoped to read/write the
   three state buckets and `sts:AssumeRole` into `niffler-infra-execution-role`. Nothing else.
3. `niffler-infra-execution-role` - assumable only by `niffler-infra-role` (not by the SSO
   session directly). The only identity that can create/manage niffler's actual resources: the
   three data buckets and the `niffler-streamlit-app-*` IAM users.

Neither role's policy contains a wildcard `Action` or `Resource`.

## Prerequisites

- Terraform `>= 1.10.0` installed (`terraform version`).
- `aws sso login --profile fmassa` completed successfully (`aws sts get-caller-identity --profile
  fmassa` returns account `309917471802`).

## Running it

```bash
bash infra/bootstrap/bootstrap.sh
```

The script is safe to re-run: bucket creation and IAM role/policy calls are guarded with
existence checks or are naturally idempotent (`put-bucket-versioning`,
`put-role-policy`, etc. overwrite rather than error). It is not, however, guaranteed
*transactional* - if it fails partway (e.g. a transient AWS API error), just re-run it; already-
created resources are detected and left alone or have their policies refreshed to match this
script's current contents.

## After running: add the chained CLI profiles

The script only creates AWS-side resources. Add these two profiles to `~/.aws/config` yourself
(per-machine local config, not committed anywhere):

```ini
[profile niffler-infra]
role_arn       = arn:aws:iam::309917471802:role/niffler-infra-role
source_profile = fmassa
region         = us-east-2

[profile niffler-infra-exec]
role_arn       = arn:aws:iam::309917471802:role/niffler-infra-execution-role
source_profile = niffler-infra
region         = us-east-2
```

Then verify the full two-hop chain:

```bash
aws sts get-caller-identity --profile niffler-infra        # shows niffler-infra-role
aws sts get-caller-identity --profile niffler-infra-exec   # shows niffler-infra-execution-role
```

`infra/envs/*/backend.tf` and `providers.tf` use these profiles - `niffler-infra` for Terraform
state access (hop 1), and `niffler-infra` -> `niffler-infra-execution-role` inside the AWS
provider's `assume_role` block for all actual resource operations (hop 2). The same
`niffler-infra-exec` profile is what you'd use later for a manual `aws s3 cp` snapshot upload.
