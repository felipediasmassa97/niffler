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
