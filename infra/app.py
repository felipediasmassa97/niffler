"""Define and synthesize app."""

import aws_cdk as cdk

from infra import resource_utils
from infra.infra_stack import InfraStack

APP_NAME = resource_utils.get_app_name()
ENV = resource_utils.get_env()
ACCOUNT = resource_utils.get_account_id()
REGION = resource_utils.get_region()
NAME = resource_utils.get_resource_name()
STACK_NAME = resource_utils.get_resource_name(f"{APP_NAME}-infra-stack")

# Pre-existing platform role, created by infra/bootstrap/bootstrap.sh - not managed by
# this app. CloudFormation assumes it to act on resources
role = f"arn:aws:iam::{ACCOUNT}:role/{APP_NAME}-infra-execution-role"
synthesizer = cdk.DefaultStackSynthesizer(
    cloud_formation_execution_role=role,
    qualifier="toolkitv2",
)

# AppName matches the tag key the two chain roles carry (bootstrap.sh) and the
# aws:PrincipalTag/AppName scoping their policies use - kept consistent on purpose,
# though it's a resource tag here, not the IAM condition key.
tags = {
    "AppName": APP_NAME,
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

# fixit check if needed
# The tags= prop above only tags the CloudFormation stack; it never renders into the
# template. The live resources were tagged by Terraform, so the same tags must appear as
# resource properties or the imported stack reports drift on day one
for key, value in tags.items():
    cdk.Tags.of(stack).add(key, value)

app.synth()
