"""Guard the physical resource names the CDK migration must not change.

Every name asserted her is depended on by live Streamlit secrets, IAM policies or the
weekly upload routine. A rename would orphan the imported resource, so these assertions
are the automated backstop for the PRD's "Names that must not change" table. Offline and
deterministic - no AWS calls.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from infra import resource_utils
from infra.infra_stack import InfraStack

if TYPE_CHECKING:
    from collections.abc import Iterator

ACCOUNT_ID = resource_utils.get_account_id()
ENVIRONMENTS = ("dev", "demo", "prod")


@pytest.fixture(params=ENVIRONMENTS)
def environment(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str:
    """Set ENVIRONMENT for one environment and reload the modules that read it."""
    monkeypatch.setenv("ENVIRONMENT", request.param)
    importlib.reload(resource_utils)
    return request.param


@pytest.fixture
def template(environment: str) -> assertions.Template:
    """Synthesize the stack for the current environment."""
    app = cdk.App()
    stack = InfraStack(
        app,
        f"niffler-infra-stack-{environment}",
        env=cdk.Environment(account=ACCOUNT_ID, region="us-east-2"),
    )
    return assertions.Template.from_stack(stack)


def test_stack_name_matches_convention(environment: str) -> None:
    """Assert the stack name follows the {app}-infra-stack-{env} house convention."""
    assert (
        resource_utils.get_resource_name("niffler-infra-stack")
        == f"niffler-infra-stack-{environment}"
    )


def test_data_bucket_name_is_preserved(
    template: assertions.Template, environment: str
) -> None:
    """Assert the bucket keeps the exact name Terraform created."""
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {"BucketName": f"niffler-{environment}-data-{ACCOUNT_ID}"},
    )


def test_app_user_name_and_policy_name_are_preserved(
    template: assertions.Template, environment: str
) -> None:
    """Assert the IAM user and its inline policy keep the current app-user names."""
    user_name = f"niffler-{environment}-app"
    template.has_resource_properties(
        "AWS::IAM::User",
        {
            "UserName": user_name,
            "Policies": [
                assertions.Match.object_like(
                    {"PolicyName": f"{user_name}-read-snapshots"}
                )
            ],
        },
    )


def test_policy_statement_sids_are_preserved(template: assertions.Template) -> None:
    """Assert both statement Sids survive - part of the imported policy document."""
    users = template.find_resources("AWS::IAM::User")
    (user,) = users.values()
    document = user["Properties"]["Policies"][0]["PolicyDocument"]
    assert [statement["Sid"] for statement in document["Statement"]] == [
        "ListSnapshotsPrefix",
        "ReadSnapshotObjects",
    ]


def test_no_access_key_resource(template: assertions.Template) -> None:
    """Assert access keys stay outside IaC - minted by hand, never by CloudFormation."""
    assert template.find_resources("AWS::IAM::AccessKey") == {}


def test_no_standalone_iam_policy_resource(template: assertions.Template) -> None:
    """Assert the inline policy renders on the user itself.

    A standalone AWS::IAM::Policy has no CloudFormation read handler and therefore
    cannot be imported - emitting one would break the migration.
    """
    assert template.find_resources("AWS::IAM::Policy") == {}


def test_no_cdk_metadata_resource(template: assertions.Template) -> None:
    """Assert no CDKMetadata resource exists - it would block an import changeset."""
    assert template.find_resources("AWS::CDK::Metadata") == {}


def test_bucket_and_user_are_retained(template: assertions.Template) -> None:
    """Assert both resources carry Retain - required at import, and the data guard."""
    for resource_type in ("AWS::S3::Bucket", "AWS::IAM::User"):
        resources = template.find_resources(resource_type)
        (resource,) = resources.values()
        assert resource["DeletionPolicy"] == "Retain"


def test_unknown_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a typo in ENVIRONMENT fails at synth, before any AWS call."""
    monkeypatch.setenv("ENVIRONMENT", "bogus")
    importlib.reload(resource_utils)
    with pytest.raises(ValueError, match="Unexpected bogus variable"):
        resource_utils.get_env()


@pytest.fixture(autouse=True)
def _restore_resource_utils() -> Iterator[None]:
    """Reload resource_utils after each test so module state never leaks."""
    yield
    importlib.reload(resource_utils)
