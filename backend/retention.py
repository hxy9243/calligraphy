"""Shared retention policy for finished Studio jobs and their output files."""
import base64
import hashlib
import hmac
import os
from typing import Optional

from calligraphy.paper import get_default_stamp_url

DEFAULT_RETENTION_SECONDS = 60 * 24 * 3600
OWNER_SESSION_TTL_SECONDS = 10 * 365 * 24 * 3600


def get_retention_seconds() -> int:
    return int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", DEFAULT_RETENTION_SECONDS))


def job_share_token(job_id: str) -> str:
    """Derive the initial 43-char URL-safe capability token for a job's QR seal stamp."""
    secret = os.environ.get("CALLIGRAPHY_SHARE_SECRET", "calligraphy-studio-qr-share-v1").encode("utf-8")
    digest = hmac.new(secret, str(job_id).encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def job_share_url(job_id: str, base_url: Optional[str] = None) -> str:
    """Return the share URL encoded in the artwork's QR code seal stamp."""
    origin = (base_url or get_default_stamp_url()).strip().rstrip("/")
    return f"{origin}/watch.html#{job_id}.{job_share_token(job_id)}"

