"""Official source registry for VeriPatch."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from veripatch.detection.os_detect import OSType, PackageManager


class SourceKind(StrEnum):
    CLI = "cli"
    COM = "com"
    API = "api"


@dataclass(frozen=True)
class OfficialSource:
    """An approved official update source."""

    id: str
    name: str
    os_type: OSType
    kind: SourceKind
    executable: str
    allowed_args_prefixes: tuple[str, ...]
    description: str


# Windows official sources
WINDOWS_SOURCES: tuple[OfficialSource, ...] = (
    OfficialSource(
        id="windows_update_agent",
        name="Windows Update Agent",
        os_type=OSType.WINDOWS,
        kind=SourceKind.COM,
        executable="WUApiLib",
        allowed_args_prefixes=(),
        description="Microsoft Windows Update via COM API (official WUA)",
    ),
    OfficialSource(
        id="winget",
        name="Microsoft WinGet",
        os_type=OSType.WINDOWS,
        kind=SourceKind.CLI,
        executable="winget",
        allowed_args_prefixes=(
            "upgrade",
            "update",
            "list",
            "source",
        ),
        description="Microsoft official package manager (WinGet)",
    ),
    OfficialSource(
        id="msstore",
        name="Microsoft Store",
        os_type=OSType.WINDOWS,
        kind=SourceKind.API,
        executable="msstore",
        allowed_args_prefixes=(),
        description="Microsoft Store official update APIs",
    ),
)

# macOS official sources
MACOS_SOURCES: tuple[OfficialSource, ...] = (
    OfficialSource(
        id="softwareupdate",
        name="macOS softwareupdate",
        os_type=OSType.MACOS,
        kind=SourceKind.CLI,
        executable="softwareupdate",
        allowed_args_prefixes=(
            "--list",
            "--install",
            "--download",
            "--fetch-full-installer",
            "--schedule",
        ),
        description="Apple built-in softwareupdate CLI utility",
    ),
    OfficialSource(
        id="appstore",
        name="Mac App Store",
        os_type=OSType.MACOS,
        kind=SourceKind.API,
        executable="mas",
        allowed_args_prefixes=(),
        description="Apple App Store official APIs (mas CLI when available)",
    ),
)

# Linux package manager sources mapped by PackageManager
_LINUX_SOURCE_BY_PM: dict[PackageManager, OfficialSource] = {
    PackageManager.APT: OfficialSource(
        id="apt",
        name="APT",
        os_type=OSType.LINUX,
        kind=SourceKind.CLI,
        executable="apt",
        allowed_args_prefixes=("update", "upgrade", "list", "show"),
        description="Debian/Ubuntu official Advanced Package Tool",
    ),
    PackageManager.DNF: OfficialSource(
        id="dnf",
        name="DNF",
        os_type=OSType.LINUX,
        kind=SourceKind.CLI,
        executable="dnf",
        allowed_args_prefixes=("check-update", "upgrade", "info", "list"),
        description="Fedora/RHEL official DNF package manager",
    ),
    PackageManager.PACMAN: OfficialSource(
        id="pacman",
        name="Pacman",
        os_type=OSType.LINUX,
        kind=SourceKind.CLI,
        executable="pacman",
        allowed_args_prefixes=("-Sy", "-Su", "-Qu", "-Qi"),
        description="Arch Linux official Pacman package manager",
    ),
    PackageManager.ZYPPER: OfficialSource(
        id="zypper",
        name="Zypper",
        os_type=OSType.LINUX,
        kind=SourceKind.CLI,
        executable="zypper",
        allowed_args_prefixes=("refresh", "update", "list-updates", "info"),
        description="openSUSE official Zypper package manager",
    ),
}


def get_sources_for_os(
    os_type: OSType,
    package_manager: PackageManager | None = None,
) -> list[OfficialSource]:
    """Return official sources available for the given OS."""
    if os_type == OSType.WINDOWS:
        return list(WINDOWS_SOURCES)
    if os_type == OSType.MACOS:
        return list(MACOS_SOURCES)
    if os_type == OSType.LINUX:
        if package_manager and package_manager in _LINUX_SOURCE_BY_PM:
            return [_LINUX_SOURCE_BY_PM[package_manager]]
        return list(_LINUX_SOURCE_BY_PM.values())
    return []


def get_all_sources() -> list[OfficialSource]:
    """Return all registered official sources."""
    sources = list(WINDOWS_SOURCES) + list(MACOS_SOURCES) + list(_LINUX_SOURCE_BY_PM.values())
    return sources


def find_source_by_executable(executable: str) -> OfficialSource | None:
    """Find a source by its executable name."""
    normalized = executable.lower().strip()
    for source in get_all_sources():
        if source.executable.lower() == normalized:
            return source
    return None
