"""Tests for utils.get_latest_snapshot."""

from unittest.mock import MagicMock

import pytest
import utils


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear get_latest_snapshot's cache so each test starts fresh."""
    utils.get_latest_snapshot.cache_clear()


@pytest.fixture(autouse=True)
def aws_secrets(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stub st.secrets["aws"] with fake AWS config."""
    secrets = {
        "bucket_name": "niffler-dev-data-309917471802",
        "data_prefix": "snapshots",
        "region": "us-east-2",
        "access_key_id": "fake-access-key",
        "secret_access_key": "fake-secret-key",
    }
    monkeypatch.setattr(utils.st, "secrets", {"aws": secrets})
    return secrets


def _mock_s3_client(
    monkeypatch: pytest.MonkeyPatch, keys: list[str], body: bytes = b""
) -> MagicMock:
    """Patch boto3.client to return a client whose list/get calls are mocked."""
    client = MagicMock()
    client.list_objects_v2.return_value = {"Contents": [{"Key": key} for key in keys]}
    client.get_object.return_value = {"Body": MagicMock(read=lambda: body)}
    monkeypatch.setattr(utils.boto3, "client", MagicMock(return_value=client))
    return client


def test_get_latest_snapshot_picks_lexicographically_max_key(
    aws_secrets: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Out-of-order object listing still resolves to the latest-dated snapshot."""
    keys = [
        "snapshots/20250601.xlsx",
        "snapshots/20260101.xlsx",
        "snapshots/20251231.xlsx",
    ]
    client = _mock_s3_client(monkeypatch, keys=keys, body=b"latest-bytes")

    result = utils.get_latest_snapshot()

    assert result == b"latest-bytes"
    client.get_object.assert_called_once_with(
        Bucket=aws_secrets["bucket_name"], Key="snapshots/20260101.xlsx"
    )


def test_get_latest_snapshot_raises_on_empty_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty prefix raises a clear error, not a leaking S3 error."""
    _mock_s3_client(monkeypatch, keys=[])

    with pytest.raises(FileNotFoundError, match="No snapshot files found"):
        utils.get_latest_snapshot()


def test_get_latest_snapshot_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second call does not hit S3 again."""
    keys = ["snapshots/20260101.xlsx"]
    client = _mock_s3_client(monkeypatch, keys=keys, body=b"data")

    utils.get_latest_snapshot()
    utils.get_latest_snapshot()

    client.list_objects_v2.assert_called_once()
