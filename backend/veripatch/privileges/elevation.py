"""Privilege elevation detection and requests."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veripatch.privileges.audit import AuditLogger


def is_elevated() -> bool:
    """Return True if the process has elevated/administrator privileges."""
    if sys.platform == "win32":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return False

    if sys.platform in ("darwin", "linux"):
        geteuid = getattr(os, "geteuid", None)
        if geteuid is not None:
            return geteuid() == 0
        return False

    return False


def request_elevation(
    argv: list[str] | None = None,
    audit_logger: AuditLogger | None = None,
) -> bool:
    """
    Request elevation for the current process.

    Returns True if already elevated. On Windows, spawns an elevated process
    and returns False. On macOS/Linux, logs guidance for sudo/pkexec re-launch.
    """
    if is_elevated():
        if audit_logger:
            audit_logger.log_action("elevation_already_granted", {})
        return True

    args = argv or sys.argv
    cmd_line = " ".join(args)

    if audit_logger:
        audit_logger.log_action(
            "elevation_requested",
            {"platform": sys.platform, "argv": args},
        )

    if sys.platform == "win32":
        try:
            import ctypes

            params = " ".join(f'"{a}"' if " " in a else a for a in args[1:])
            rc = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
                None,
                "runas",
                sys.executable,
                params or "",
                None,
                1,
            )
            if rc <= 32:
                if audit_logger:
                    audit_logger.log_action("elevation_failed", {"return_code": rc})
                return False
            if audit_logger:
                audit_logger.log_action("elevation_spawned", {"method": "UAC runas"})
            return False
        except (AttributeError, OSError) as exc:
            if audit_logger:
                audit_logger.log_action("elevation_failed", {"error": str(exc)})
            return False

    if sys.platform in ("darwin", "linux"):
        if audit_logger:
            details: dict[str, str] = {
                "message": "Re-run with sudo for privileged updates",
                "suggested_sudo": f"sudo {cmd_line}",
            }
            if sys.platform.startswith("linux"):
                details["suggested_pkexec"] = (
                    f"pkexec {sys.executable} {' '.join(args[1:])}"
                )
            audit_logger.log_action("elevation_guidance", details)
        return False

    return False
