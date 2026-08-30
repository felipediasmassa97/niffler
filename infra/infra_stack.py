"""Stacks definitions."""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .resource_utils import get_account_id, get_resource_name


class InfraStack(Stack):
    """Infrastructure Stack definition."""

    def __init__(
        self, scope: Construct, construct_id: str, **kwargs: dict[str, Any]
    ) -> None:
        """Initialize the stack."""
        super().__init__(scope, construct_id, **kwargs)

        # These snapshots are the only copy of the user's financial data - RETAIN means
        # no stack operation can ever delete this bucket
        self.data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=f"{get_resource_name()}-data-{get_account_id()}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_key_enabled=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-noncurrent-versions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(90),
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )
        CfnOutput(
            self,
            "dataBucketName",
            value=self.data_bucket.bucket_name,
            description="S3 bucket holding this environment's Mobills snapshots",
            export_name=f"{get_resource_name()}-data-bucket-name",
        )

        # L1 CfnUser, not L2 iam.User: only the L1 renders the inline policy as a
        # property of the user. L2 emits a separate AWS::IAM::Policy, which
        # CloudFormation cannot import
        user_name = f"{get_resource_name()}-app"
        app_user = iam.CfnUser(
            self,
            "AppUser",
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
        app_user.apply_removal_policy(RemovalPolicy.RETAIN)
        CfnOutput(
            self,
            "appUserName",
            value=user_name,
            description="IAM user the app authenticates as",
            export_name=f"{get_resource_name()}-app-user-name",
        )

    @property
    def list_snapshots_policy_statement(self) -> iam.PolicyStatement:
        """Return the statement allowing the app to list only the snapshots prefix."""
        return iam.PolicyStatement(
            sid="ListSnapshotsPrefix",
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:ListBucket",
            ],
            resources=[
                self.data_bucket.bucket_arn,
            ],
            conditions={
                "StringLike": {
                    "s3:prefix": "snapshots/*",
                },
            },
        )

    @property
    def read_snapshots_policy_statement(self) -> iam.PolicyStatement:
        """Return the statement allowing the app to read snapshot objects."""
        return iam.PolicyStatement(
            sid="ReadSnapshotObjects",
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
            ],
            resources=[
                f"{self.data_bucket.bucket_arn}/snapshots/*",
            ],
        )
