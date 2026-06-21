"""Diagnostics and capability reporting."""

from __future__ import annotations

import shutil
import sys
from typing import Any

from veripatch import __version__
from veripatch.detection.os_detect import detect_os
from veripatch.privileges.audit import AuditLogger
from veripatch.privileges.elevation import is_elevated
from veripatch.sources.registry import get_sources_for_os


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def get_capabilities() -> dict[str, Any]:
    """Return a capability matrix for the current system."""
    info = detect_os()
    caps: dict[str, bool | str] = {
        "python": sys.version.split()[0],
        "veripatch": __version__,
    }
    if info.os_type.value == "windows":
        caps["winget"] = _tool_available("winget")
        caps["wua_com"] = sys.platform == "win32"
    elif info.os_type.value == "macos":
        caps["softwareupdate"] = _tool_available("softwareupdate")
    elif info.os_type.value == "linux":
        pm = info.package_manager.value if info.package_manager else "unknown"
        caps["package_manager"] = pm
        caps[pm] = _tool_available(pm) if pm != "unknown" else False
    return caps


def get_diagnostics(audit: AuditLogger | None = None, audit_limit: int = 20) -> dict[str, Any]:
    """Return diagnostics payload for JSON-RPC."""
    info = detect_os()
    logger_audit = audit or AuditLogger()
    entries = logger_audit.read_entries()
    return {
        "version": __version__,
        "python": sys.version,
        "os": info.to_dict(),
        "elevated": is_elevated(),
        "capabilities": get_capabilities(),
        "official_sources": [
            {"id": s.id, "name": s.name}
            for s in get_sources_for_os(info.os_type, info.package_manager)
        ],
        "recent_audit_entries": entries[-audit_limit:],
    }
