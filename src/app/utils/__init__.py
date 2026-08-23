"""General utils."""

from functools import cache

import boto3
import streamlit as st


@cache
def get_latest_snapshot() -> bytes:
    """Fetch the latest Mobills Excel snapshot from S3.

    Snapshots live at `<data_prefix>/YYYYMMDD.xlsx`; "latest" is the lexicographically-
    max key, mirroring the old local-disk `glob(...) + max()` behavior so out-of-order
    uploads/backfills resolve identically. Cached for the process lifetime, since a
    snapshot never changes mid-session - avoids re-downloading on every Streamlit rerun.

    Bucket, prefix, region and credentials come from `st.secrets["aws"]` - see
    `docs/implementation/001__infra/PRD.md`.
    """
    aws_secrets = st.secrets["aws"]
    bucket = aws_secrets["bucket_name"]
    prefix = aws_secrets["data_prefix"]

    client = boto3.client(
        "s3",
        region_name=aws_secrets["region"],
        aws_access_key_id=aws_secrets["access_key_id"],
        aws_secret_access_key=aws_secrets["secret_access_key"],
    )
    response = client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/")
    keys = [obj["Key"] for obj in response.get("Contents", [])]
    if not keys:
        message = f"No snapshot files found in s3://{bucket}/{prefix}/."
        raise FileNotFoundError(message)

    latest_key = max(keys)
    return client.get_object(Bucket=bucket, Key=latest_key)["Body"].read()
