"""Optional encrypted off-host backup delivery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def offsite_backup_configured() -> bool:
    """Return whether an S3-compatible off-host target has been configured."""

    return bool(os.getenv("CARRIEROS_OFFSITE_BACKUP_BUCKET", "").strip())


def _s3_client() -> Any:
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - deployment-only failure
        raise RuntimeError(
            "boto3 is required when CARRIEROS_OFFSITE_BACKUP_BUCKET is configured"
        ) from exc

    kwargs: dict[str, str] = {}
    region = os.getenv("CARRIEROS_OFFSITE_BACKUP_REGION", "").strip()
    endpoint = os.getenv("CARRIEROS_OFFSITE_BACKUP_ENDPOINT", "").strip()
    if region:
        kwargs["region_name"] = region
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def upload_backup_if_configured(path: Path) -> dict[str, object] | None:
    """Upload a verified backup when configured and confirm the remote object."""

    bucket = os.getenv("CARRIEROS_OFFSITE_BACKUP_BUCKET", "").strip()
    if not bucket:
        return None
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"backup file does not exist: {path}")

    prefix = os.getenv("CARRIEROS_OFFSITE_BACKUP_PREFIX", "carrieros").strip().strip("/")
    key = f"{prefix}/{path.name}" if prefix else path.name
    sse = os.getenv("CARRIEROS_OFFSITE_BACKUP_SSE", "AES256").strip() or "AES256"
    extra_args: dict[str, str] = {"ServerSideEncryption": sse}
    kms_key = os.getenv("CARRIEROS_OFFSITE_BACKUP_KMS_KEY_ID", "").strip()
    if sse == "aws:kms" and kms_key:
        extra_args["SSEKMSKeyId"] = kms_key

    client = _s3_client()
    client.upload_file(str(path), bucket, key, ExtraArgs=extra_args)
    head = client.head_object(Bucket=bucket, Key=key)
    return {
        "configured": True,
        "uploaded": True,
        "bucket": bucket,
        "key": key,
        "size_bytes": int(head.get("ContentLength", path.stat().st_size)),
        "server_side_encryption": head.get("ServerSideEncryption", sse),
    }
