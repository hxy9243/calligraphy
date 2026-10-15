"""Shared retention policy for finished Studio jobs and their output files."""
import os

DEFAULT_RETENTION_SECONDS = 7 * 24 * 3600


def get_retention_seconds():
    return int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", DEFAULT_RETENTION_SECONDS))
