#!/usr/bin/env bash
# One-time AWS bootstrap for niffler's infra: creates the two-hop IAM role chain
# (niffler-infra -> niffler-infra-execution-role) that AWS CDK deploys through.
# Run manually with the raw admin SSO profile - see
# docs/implementation/002__cdk_migration/PRD.md for why this layer lives outside
# the CDK app.
#
# Usage: bash infra/bootstrap/bootstrap.sh
#
# Idempotent and re-runnable: every step either creates or updates in place.

# fixit move bootstrap to dedicated repository (similar to edap-iam)
# The objective of bootstrap is to create infra and infra execution roles for new apps
# This is similar to what Gandalf does
# Dispatch a scout agent on Gandalf repos to understand how Gandalf manages it, and
# try to replicate it here
# We should have one repository that governs policies for the apps we own in AWS,
# similar to edap-iam

set -euo pipefail

SSO_PROFILE="fmassa"
ACCOUNT_ID="309917471802"
APP_NAME="niffler"
INFRA_ROLE_NAME="niffler-infra"
EXECUTION_ROLE_NAME="niffler-infra-execution-role"
INFRA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${INFRA_ROLE_NAME}"

# GitHub Actions CI assumes niffler-infra too (see "GithubActionsOidc" trust statement
# below), scoped to this one repo via the OIDC `sub` claim - no separate CI role
GITHUB_REPO="felipediasmassa97/niffler"
GITHUB_OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
# AWS validates GitHub's certificate chain itself; these thumbprints are only kept
# because create-open-id-connect-provider still requires the field
GITHUB_OIDC_THUMBPRINTS=(
  "6938fd4d98bab03faadb97b34396831e3780aea1"
  "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
)

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Verifying SSO session (profile: ${SSO_PROFILE})"
CALLER_ACCOUNT="$(aws sts get-caller-identity --profile "$SSO_PROFILE" --query Account --output text)"
if [[ "$CALLER_ACCOUNT" != "$ACCOUNT_ID" ]]; then
  echo "ERROR: profile ${SSO_PROFILE} resolves to account ${CALLER_ACCOUNT}, expected ${ACCOUNT_ID}." >&2
  exit 1
fi

echo "==> Writing IAM policy documents"

# Two trust statements: the human SSO session (account-root principal + ArnLike,
# rather than the SSO permission-set role ARN directly - that role is recreated with a
# new hash whenever the permission set is edited, which would silently break a
# hardcoded principal), and GitHub Actions CI via OIDC, scoped to this exact repo so no
# other GitHub repo can assume this role
cat > "${WORKDIR}/infra-role-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HumanSsoSession",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::${ACCOUNT_ID}:root" },
      "Action": ["sts:AssumeRole", "sts:TagSession"],
      "Condition": {
        "ArnLike": {
          "aws:PrincipalArn": "arn:aws:iam::${ACCOUNT_ID}:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_AdministratorAccess_*"
        }
      }
    },
    {
      "Sid": "GithubActionsOidc",
      "Effect": "Allow",
      "Principal": { "Federated": "${GITHUB_OIDC_ARN}" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
        "StringLike": { "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*" }
      }
    }
  ]
}
EOF

# Every resource ARN below is scoped by \${aws:PrincipalTag/AppName}, which resolves
# from the AppName tag applied to the role further down - the tag is load-bearing,
# and an untagged role matches nothing and is denied everything
cat > "${WORKDIR}/infra-role-permissions.json" <<EOF
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
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:ContinueUpdateRollback",
        "cloudformation:CancelUpdateStack",
        "cloudformation:UpdateTerminationProtection",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:GetTemplate"
      ],
      "Resource": "arn:aws:cloudformation:*:${ACCOUNT_ID}:stack/\${aws:PrincipalTag/AppName}*/*"
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
        "arn:aws:s3:::cdk-toolkitv2-assets-${ACCOUNT_ID}-*",
        "arn:aws:s3:::cdk-toolkitv2-assets-${ACCOUNT_ID}-*/*"
      ]
    },
    {
      "Sid": "ReadVersion",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/cdk-bootstrap/toolkitv2/version"
    },
    {
      "Sid": "AssumeRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": [
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-toolkitv2-deploy-role-${ACCOUNT_ID}-*",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-toolkitv2-file-publishing-role-${ACCOUNT_ID}-*",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-toolkitv2-image-publishing-role-${ACCOUNT_ID}-*",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-toolkitv2-lookup-role-${ACCOUNT_ID}-*"
      ]
    },
    {
      "Sid": "PassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::${ACCOUNT_ID}:role/\${aws:PrincipalTag/AppName}-infra-execution-role",
      "Condition": {
        "StringEquals": { "iam:PassedToService": "cloudformation.amazonaws.com" }
      }
    },
    {
      "Sid": "InfraS3Data",
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": [
        "arn:aws:s3:::\${aws:PrincipalTag/AppName}-*",
        "arn:aws:s3:::\${aws:PrincipalTag/AppName}-*/*"
      ]
    },
    {
      "Sid": "InfraSsm",
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter", "ssm:DeleteParameter",
        "ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath",
        "ssm:GetParameterHistory",
        "ssm:AddTagsToResource", "ssm:RemoveTagsFromResource", "ssm:ListTagsForResource"
      ],
      "Resource": [
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/config/\${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/\${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/cdk/exports/\${aws:PrincipalTag/AppName}*"
      ]
    }
  ]
}
EOF

# CloudFormation assumes this role as the stacks' service role (hop 2 of the chain).
# Deliberately trusted by CloudFormation only, matching edap-iam's pattern exactly -
# the human never assumes this role directly, even for manual operations. The infra
# role carries its own S3/SSM permissions above for that (a documented deviation from
# edap-iam, which has no equivalent manual-CLI need)
cat > "${WORKDIR}/execution-role-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationServiceRole",
      "Effect": "Allow",
      "Principal": { "Service": "cloudformation.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# No iam:*AccessKey actions: access keys are minted by hand as admin and stored in
# Parameter Store, deliberately outside IaC
cat > "${WORKDIR}/execution-role-permissions.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CdkExecution",
      "Effect": "Allow",
      "Action": "ssm:GetParameters",
      "Resource": "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/cdk-bootstrap/*"
    },
    {
      "Sid": "InfraS3Bucket",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket", "s3:DeleteBucket", "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:*BucketVersioning",
        "s3:GetEncryptionConfiguration", "s3:PutEncryptionConfiguration",
        "s3:GetBucketPublicAccessBlock", "s3:PutBucketPublicAccessBlock",
        "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration",
        "s3:GetBucketTagging", "s3:PutBucketTagging",
        "s3:GetBucketPolicy", "s3:PutBucketPolicy", "s3:DeleteBucketPolicy",
        "s3:GetBucketPolicyStatus",
        "s3:GetBucketOwnershipControls", "s3:PutBucketOwnershipControls",
        "s3:GetBucketCORS", "s3:PutBucketCORS",
        "s3:GetBucketWebsite", "s3:PutBucketWebsite", "s3:DeleteBucketWebsite"
      ],
      "Resource": "arn:aws:s3:::\${aws:PrincipalTag/AppName}-*"
    },
    {
      "Sid": "InfraS3Object",
      "Effect": "Allow",
      "Action": "s3:*Object",
      "Resource": "arn:aws:s3:::\${aws:PrincipalTag/AppName}-*/*"
    },
    {
      "Sid": "InfraSsm",
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter", "ssm:DeleteParameter",
        "ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath",
        "ssm:GetParameterHistory",
        "ssm:AddTagsToResource", "ssm:RemoveTagsFromResource", "ssm:ListTagsForResource"
      ],
      "Resource": [
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/config/\${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/\${aws:PrincipalTag/AppName}*",
        "arn:aws:ssm:*:${ACCOUNT_ID}:parameter/cdk/exports/\${aws:PrincipalTag/AppName}*"
      ]
    },
    {
      "Sid": "InfraIamUsers",
      "Effect": "Allow",
      "Action": [
        "iam:CreateUser", "iam:DeleteUser", "iam:GetUser", "iam:UpdateUser",
        "iam:TagUser", "iam:UntagUser", "iam:ListUserTags",
        "iam:PutUserPolicy", "iam:DeleteUserPolicy", "iam:GetUserPolicy",
        "iam:ListUserPolicies", "iam:ListAttachedUserPolicies",
        "iam:ListGroupsForUser", "iam:GetLoginProfile"
      ],
      "Resource": "arn:aws:iam::${ACCOUNT_ID}:user/\${aws:PrincipalTag/AppName}-*"
    }
  ]
}
EOF

# IAM is eventually consistent: a role named as a principal in another role's trust
# policy is rejected as "Invalid principal" for a few seconds after it is created
retry_on_invalid_principal() {
  local attempt
  for attempt in 1 2 3 4 5 6; do
    if "$@" 2>"${WORKDIR}/iam-error"; then
      return 0
    fi
    if ! grep -q "Invalid principal" "${WORKDIR}/iam-error"; then
      cat "${WORKDIR}/iam-error" >&2
      return 1
    fi
    echo "    Principal not yet propagated, retrying (${attempt}/6)"
    sleep 5
  done
  echo "ERROR: principal never propagated." >&2
  return 1
}

create_or_update_role() {
  local role_name="$1" trust_file="$2" description="$3"
  if aws iam get-role --role-name "$role_name" --profile "$SSO_PROFILE" >/dev/null 2>&1; then
    echo "    Role exists, updating trust policy"
    retry_on_invalid_principal aws iam update-assume-role-policy --role-name "$role_name" \
      --policy-document "file://${trust_file}" --profile "$SSO_PROFILE"
  else
    echo "    Creating role"
    retry_on_invalid_principal aws iam create-role --role-name "$role_name" \
      --assume-role-policy-document "file://${trust_file}" \
      --description "$description" \
      --profile "$SSO_PROFILE" >/dev/null
  fi
  # Tag before attaching permissions: every statement is scoped by
  # \${aws:PrincipalTag/AppName}, so an untagged role is denied everything
  aws iam tag-role --role-name "$role_name" \
    --tags "Key=AppName,Value=${APP_NAME}" --profile "$SSO_PROFILE"
}

echo "==> Ensuring the GitHub Actions OIDC provider exists"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$GITHUB_OIDC_ARN" \
    --profile "$SSO_PROFILE" >/dev/null 2>&1; then
  echo "    Provider already exists"
else
  echo "    Creating provider"
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "${GITHUB_OIDC_THUMBPRINTS[@]}" \
    --profile "$SSO_PROFILE" >/dev/null
fi

echo "==> Creating ${INFRA_ROLE_NAME}"
create_or_update_role "$INFRA_ROLE_NAME" "${WORKDIR}/infra-role-trust.json" \
  "Assumable by the human SSO session; drives CloudFormation and manual S3/SSM operations"
aws iam put-role-policy --role-name "$INFRA_ROLE_NAME" \
  --policy-name "niffler-infra-role-permissions" \
  --policy-document "file://${WORKDIR}/infra-role-permissions.json" \
  --profile "$SSO_PROFILE"

echo "==> Creating ${EXECUTION_ROLE_NAME}"
create_or_update_role "$EXECUTION_ROLE_NAME" "${WORKDIR}/execution-role-trust.json" \
  "Assumed only by CloudFormation as the stacks' service role - never by a human directly"
aws iam put-role-policy --role-name "$EXECUTION_ROLE_NAME" \
  --policy-name "niffler-infra-execution-role-permissions" \
  --policy-document "file://${WORKDIR}/execution-role-permissions.json" \
  --profile "$SSO_PROFILE"

echo "==> Bootstrap complete."
echo ""
echo "Verify the AppName tag (load-bearing - every policy is scoped by it):"
echo "  aws iam list-role-tags --role-name ${INFRA_ROLE_NAME} --profile ${SSO_PROFILE}"
echo "  aws iam list-role-tags --role-name ${EXECUTION_ROLE_NAME} --profile ${SSO_PROFILE}"
echo ""
echo "Verify both trust statements on ${INFRA_ROLE_NAME} (human SSO + GitHub OIDC):"
echo "  aws iam get-role --role-name ${INFRA_ROLE_NAME} --profile ${SSO_PROFILE}"
echo ""
echo "Then verify it:"
echo "  aws sts get-caller-identity --profile niffler-infra"
