"""OS-specific updater factory and exports."""

from __future__ import annotations

from veripatch.detection.os_detect import OSInfo, OSType
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator
from veripatch.updaters.base import Updater
from veripatch.updaters.linux import LinuxUpdater
from veripatch.updaters.macos import MacOSUpdater
from veripatch.updaters.windows import WindowsUpdater


def get_updater(
    os_info: OSInfo,
    validator: SourceValidator | None = None,
    audit_logger: AuditLogger | None = None,
) -> Updater:
    """Return the appropriate updater for the detected operating system."""
    validator = validator or SourceValidator(audit_logger)
    audit = audit_logger or AuditLogger()

    if os_info.os_type == OSType.WINDOWS:
        return WindowsUpdater(os_info, validator, audit)
    if os_info.os_type == OSType.MACOS:
        return MacOSUpdater(os_info, validator, audit)
    if os_info.os_type == OSType.LINUX:
        return LinuxUpdater(os_info, validator, audit)

    raise ValueError(f"No updater available for OS type: {os_info.os_type.value}")


__all__ = [
    "Updater",
    "WindowsUpdater",
    "MacOSUpdater",
    "LinuxUpdater",
    "get_updater",
]
