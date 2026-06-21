"""Privilege elevation detection and requests."""

from __future__ import annotations

import os
import sys


def is_elevated() -> bool:
    """Return True if the process has elevated/administrator privileges."""
    if sys.platform == "win32":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return False

    if sys.platform == "darwin":
        return os.geteuid() == 0

    if sys.platform.startswith("linux"):
        return os.geteuid() == 0

    return False


def request_elevation() -> bool:
    """
    Request elevation for the current process.

    Stub: returns False and logs that elevation must be performed externally.
    """
    return False
