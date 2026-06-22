"""VeriPatch runtime configuration."""

from __future__ import annotations

import os

APPLY_CONFIRMATION_TOKEN = "veripatch-confirm-apply"

DEFAULT_APPLY_TIMEOUT_SECONDS = 1800


def apply_command_timeout() -> int:
    """Return subprocess timeout for apply operations (seconds)."""
    raw = os.getenv("VERIPATCH_APPLY_TIMEOUT", str(DEFAULT_APPLY_TIMEOUT_SECONDS))
    try:
        timeout = int(raw)
    except ValueError:
        return DEFAULT_APPLY_TIMEOUT_SECONDS
    return max(timeout, 60)
