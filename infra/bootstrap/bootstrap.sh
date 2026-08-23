#!/usr/bin/env bash
# One-time AWS bootstrap for niffler's infra: creates the three per-environment
# Terraform state buckets and the two-hop IAM role chain (niffler-infra-role ->
# niffler-infra-execution-role). Run once, manually, with the raw admin SSO
# profile - see docs/implementation/001__infra/PRD.md "Bootstrap" section for
# why this lives outside the infra/ Terraform project.
#
# Usage: bash infra/bootstrap/bootstrap.sh
#
# Not idempotent end-to-end: if it fails partway, inspect which resources
# already exist (see README.md "Re-running after a partial failure") and
# comment out the corresponding steps before re-running.

set -euo pipefail

SSO_PROFILE="fmassa"
ACCOUNT_ID="309917471802"
REGION="us-east-2"
ENVIRONMENTS=(dev demo prod)
INFRA_ROLE_NAME="niffler-infra-role"
EXECUTION_ROLE_NAME="niffler-infra-execution-role"
INFRA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${INFRA_ROLE_NAME}"
EXECUTION_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${EXECUTION_ROLE_NAME}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Verifying SSO session (profile: ${SSO_PROFILE})"
CALLER_IDENTITY="$(aws sts get-caller-identity --profile "$SSO_PROFILE" --output json)"
CALLER_ACCOUNT="$(echo "$CALLER_IDENTITY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Account"])')"
if [[ "$CALLER_ACCOUNT" != "$ACCOUNT_ID" ]]; then
  echo "ERROR: profile ${SSO_PROFILE} resolves to account ${CALLER_ACCOUNT}, expected ${ACCOUNT_ID}." >&2
  exit 1
fi

CALLER_ARN="$(echo "$CALLER_IDENTITY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Arn"])')"
# CALLER_ARN looks like:
#   arn:aws:sts::309917471802:assumed-role/AWSReservedSSO_AdministratorAccess_<hash>/<session>
# The trust-policy principal needs the underlying IAM role ARN, not the assumed-role
# session ARN. SSO permission-set roles live under a path that includes the SSO region
# (/aws-reserved/sso.amazonaws.com/<region>/...), which isn't safe to reconstruct by hand -
# look it up via IAM instead.
SSO_ROLE_NAME="$(echo "$CALLER_ARN" | sed -E 's#.*assumed-role/([^/]+)/.*#\1#')"
SSO_ROLE_ARN="$(aws iam list-roles --profile "$SSO_PROFILE" \
  --query "Roles[?RoleName=='${SSO_ROLE_NAME}'].Arn" --output text)"
if [[ -z "$SSO_ROLE_ARN" ]]; then
  echo "ERROR: could not resolve IAM role ARN for SSO role name ${SSO_ROLE_NAME}." >&2
  exit 1
fi
echo "    Resolved SSO permission-set role ARN: ${SSO_ROLE_ARN}"

echo "==> Creating per-environment Terraform state buckets"
for env in "${ENVIRONMENTS[@]}"; do
  bucket="niffler-${env}-tfstate-${ACCOUNT_ID}"
  if aws s3api head-bucket --bucket "$bucket" --profile "$SSO_PROFILE" >/dev/null 2>&1; then
    echo "    ${bucket} already exists, skipping creation"
  else
    echo "    Creating ${bucket}"
    aws s3api create-bucket \
      --bucket "$bucket" \
      --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" \
      --profile "$SSO_PROFILE" >/dev/null
  fi
  aws s3api put-bucket-versioning \
    --bucket "$bucket" \
    --versioning-configuration Status=Enabled \
    --profile "$SSO_PROFILE"
  aws s3api put-bucket-encryption \
    --bucket "$bucket" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    --profile "$SSO_PROFILE"
  aws s3api put-public-access-block \
    --bucket "$bucket" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
    --profile "$SSO_PROFILE"
done

echo "==> Writing IAM policy documents"

cat > "${WORKDIR}/infra-role-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "${SSO_ROLE_ARN}" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

cat > "${WORKDIR}/infra-role-permissions.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateAccessAllEnvs",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::niffler-dev-tfstate-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-dev-tfstate-${ACCOUNT_ID}/*",
        "arn:aws:s3:::niffler-demo-tfstate-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-demo-tfstate-${ACCOUNT_ID}/*",
        "arn:aws:s3:::niffler-prod-tfstate-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-prod-tfstate-${ACCOUNT_ID}/*"
      ]
    },
    {
      "Sid": "AssumeExecutionRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "${EXECUTION_ROLE_ARN}"
    }
  ]
}
EOF

cat > "${WORKDIR}/execution-role-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "${INFRA_ROLE_ARN}" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

cat > "${WORKDIR}/execution-role-permissions.json" <<EOF
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
        "arn:aws:s3:::niffler-dev-data-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-dev-data-${ACCOUNT_ID}/*",
        "arn:aws:s3:::niffler-demo-data-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-demo-data-${ACCOUNT_ID}/*",
        "arn:aws:s3:::niffler-prod-data-${ACCOUNT_ID}",
        "arn:aws:s3:::niffler-prod-data-${ACCOUNT_ID}/*"
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
      "Resource": "arn:aws:iam::${ACCOUNT_ID}:user/niffler-streamlit-app-*"
    }
  ]
}
EOF

echo "==> Creating ${INFRA_ROLE_NAME}"
if aws iam get-role --role-name "$INFRA_ROLE_NAME" --profile "$SSO_PROFILE" >/dev/null 2>&1; then
  echo "    Role already exists, updating trust + inline policy"
  aws iam update-assume-role-policy --role-name "$INFRA_ROLE_NAME" \
    --policy-document "file://${WORKDIR}/infra-role-trust.json" --profile "$SSO_PROFILE"
else
  aws iam create-role --role-name "$INFRA_ROLE_NAME" \
    --assume-role-policy-document "file://${WORKDIR}/infra-role-trust.json" \
    --description "Assumable by the human SSO session; can only drive Terraform state + assume ${EXECUTION_ROLE_NAME}" \
    --profile "$SSO_PROFILE" >/dev/null
fi
aws iam put-role-policy --role-name "$INFRA_ROLE_NAME" \
  --policy-name "niffler-infra-role-permissions" \
  --policy-document "file://${WORKDIR}/infra-role-permissions.json" \
  --profile "$SSO_PROFILE"

echo "==> Creating ${EXECUTION_ROLE_NAME}"
if aws iam get-role --role-name "$EXECUTION_ROLE_NAME" --profile "$SSO_PROFILE" >/dev/null 2>&1; then
  echo "    Role already exists, updating trust + inline policy"
  aws iam update-assume-role-policy --role-name "$EXECUTION_ROLE_NAME" \
    --policy-document "file://${WORKDIR}/execution-role-trust.json" --profile "$SSO_PROFILE"
else
  aws iam create-role --role-name "$EXECUTION_ROLE_NAME" \
    --assume-role-policy-document "file://${WORKDIR}/execution-role-trust.json" \
    --description "Assumable only by ${INFRA_ROLE_NAME}; the only identity that can manage niffler's actual AWS resources" \
    --profile "$SSO_PROFILE" >/dev/null
fi
aws iam put-role-policy --role-name "$EXECUTION_ROLE_NAME" \
  --policy-name "niffler-infra-execution-role-permissions" \
  --policy-document "file://${WORKDIR}/execution-role-permissions.json" \
  --profile "$SSO_PROFILE"

echo "==> Bootstrap complete."
echo ""
echo "Next: add the chained profiles from infra/bootstrap/README.md to ~/.aws/config,"
echo "then verify the chain with:"
echo "  aws sts get-caller-identity --profile niffler-infra"
echo "  aws sts get-caller-identity --profile niffler-infra-exec"
