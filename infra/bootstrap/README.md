# Bootstrap

Account-level setup that has to exist before AWS CDK can deploy anything: the two-hop IAM role
chain (`niffler-infra` -> `niffler-infra-execution-role`), and the `CDKToolkit` stack CDK itself
depends on. Both are created manually with the raw admin SSO session, and neither is managed by
the `InfraStack` app - see `docs/implementation/002__cdk_migration/PRD.md` for why bootstrap has
to live outside the thing it bootstraps.

## What it creates

### `bootstrap.sh` - the GitHub OIDC provider + the two chain roles

1. `niffler-infra` - assumable by the `fmassa` SSO session (account-root principal, gated by
   an `ArnLike` condition on the `AdministratorAccess` permission set - this survives the
   permission set being recreated, unlike a hardcoded role ARN), **and** by GitHub Actions CI for
   the `felipediasmassa97/niffler` repo, via a second trust statement federated through the
   account's GitHub OIDC provider (`token.actions.githubusercontent.com`, created by this same
   script) and scoped with a `StringLike` condition on the OIDC `sub` claim
   (`repo:felipediasmassa97/niffler:*`) - no other GitHub repo can assume this role. Drives
   CloudFormation, and also carries its own S3 object CRUD and Parameter Store permissions for the
   manual CLI path (`aws s3 cp` uploads, the access-key runbook) - see "A deliberate deviation from
   edap-iam" below. CI gets exactly the same permissions as the human path (no separate CI role) -
   a deliberate choice to keep one role instead of two, since GitHub's OIDC `sub` scoping already
   restricts *who* can assume it to this one repo.
2. `niffler-infra-execution-role` - assumed **only** by the CloudFormation service principal, as
   every stack's service role. The only identity that can manage niffler's actual resources: the
   data buckets and the `niffler-<env>-app` IAM users. Never assumable by a human, matching
   `tfmcdigital/edap-iam`'s pattern exactly.

Both roles are tagged `AppName = niffler` - **load-bearing**, since every statement in both
policies is scoped by `${aws:PrincipalTag/AppName}` rather than a hand-enumerated per-environment
ARN list. An untagged role is denied everything. Re-verify after any change:

```bash
aws iam list-role-tags --role-name niffler-infra --profile fmassa
aws iam list-role-tags --role-name niffler-infra-execution-role --profile fmassa
aws iam get-role --role-name niffler-infra --profile fmassa   # both trust statements
```

Neither policy contains an unbounded wildcard `Action` or `Resource` - the two narrow, documented
exceptions (`sts:GetCallerIdentity`, and the suffix-anchored `s3:*Object`/`s3:*BucketVersioning`)
are covered in the PRD's "IAM policies for the two chain roles" section.

### A deliberate deviation from edap-iam

In `edap-iam`, an app's execution role is trusted only by CloudFormation - the human path doesn't
exist, because everything runs through CI. niffler has no CI yet (`CL-02`), but does have a
recurring manual workflow: the weekly snapshot upload and the access-key-in-Parameter-Store
runbook. Rather than let the human assume the execution role directly (which would have meant
trusting `niffler-infra` as a principal on `niffler-infra-execution-role` - the model this project
used briefly during migration, since abandoned), `niffler-infra` itself carries two extra
statements: `InfraS3Data` (`s3:ListBucket`/`GetObject`/`PutObject`/`DeleteObject` on
`niffler-*` buckets) and `InfraSsm` (parameter read/write/tag under `/config/niffler*`). This
keeps the execution role's trust policy identical to `edap-iam`'s pattern - CloudFormation only,
no human principal - while still giving the human everything the manual workflow needs, from the
one role they're allowed to assume in the first place.

### `cdk bootstrap` - the CDKToolkit stack

CDK's own deploy-time infrastructure (a staging S3 bucket, an ECR repo, and four IAM roles) is
**not** created by `bootstrap.sh` - it's a separate, one-time `cdk bootstrap` call. It uses a
custom `toolkitv2` qualifier so its resources are namespaced independently of any other CDK usage
in this account, matching the pattern from `tfmcdigital/edap-iam`.

The stock bootstrap template is not enough on its own: its `DeploymentActionRole` can only
`iam:PassRole` the bootstrap's own `CloudFormationExecutionRole`, but niffler's stacks deploy with
`niffler-infra-execution-role` as their service role (that's what preserves the two-hop chain).
Bootstrap with an extra `iam:PassRole` statement scoped to `*-infra-execution-role`:

```bash
cdk bootstrap --show-template --no-notices > /tmp/cdk-bootstrap-template.yaml
```

In the generated file, find `DeploymentActionRole`'s policy statements and add, immediately after
the existing `iam:PassRole` statement for `CloudFormationExecutionRole.Arn`:

```yaml
- Sid: PassAppExecutionRole
  Action: iam:PassRole
  Resource:
    Fn::Sub: arn:${AWS::Partition}:iam::${AWS::AccountId}:role/*-infra-execution-role
  Effect: Allow
```

Then bootstrap with it:

```bash
cdk bootstrap aws://309917471802/us-east-2 --profile fmassa --qualifier toolkitv2 \
  --template /tmp/cdk-bootstrap-template.yaml \
  --cloudformation-execution-policies arn:aws:iam::aws:policy/AWSDenyAll \
  --termination-protection
```

`AWSDenyAll` is deliberate: the bootstrap's own `CloudFormationExecutionRole` is never used to
deploy niffler's stacks (the synthesizer overrides it with `niffler-infra-execution-role`), so it
carries no real permissions. `--termination-protection` guards the `CDKToolkit` stack itself
against accidental deletion.

This template is generated fresh each time, not committed to the repo - `cdk bootstrap`'s default
template changes across CDK versions, and freezing a copy here would drift from those updates.
Re-derive it with `--show-template` and reapply the one-statement patch above whenever the
`CDKToolkit` stack needs updating (a CDK CLI major upgrade, most likely).

## Prerequisites

- Node (see `.nvmrc`) and `npm install` run at the repo root, so `npx cdk` resolves.
- `aws sso login --profile fmassa` completed (`aws sts get-caller-identity --profile fmassa`
  returns account `309917471802`).

## Running `bootstrap.sh`

```bash
bash infra/bootstrap/bootstrap.sh
```

Safe to re-run: every step creates-or-updates in place. IAM's eventual consistency means a
freshly created role can briefly be rejected as an "Invalid principal" when referenced by another
role's trust policy - the script retries automatically for a few seconds before giving up.

## After running: add the CLI profile

The script only creates AWS-side resources. Add this profile to `~/.aws/config` yourself
(per-machine local config, not committed anywhere):

```ini
[profile niffler-infra]
role_arn       = arn:aws:iam::309917471802:role/niffler-infra
source_profile = fmassa
region         = us-east-2
```

Then verify it:

```bash
aws sts get-caller-identity --profile niffler-infra   # shows niffler-infra
```

There is no third profile for `niffler-infra-execution-role` - it is never assumed by a human.
`niffler-infra` is what you use for everything: `cdk diff`/`cdk deploy` (CloudFormation itself
assumes the execution role as the service role, per the synthesizer config in `infra/app.py`), a
manual `aws s3 cp` snapshot upload, or an `aws ssm put-parameter` call.
