"""Operating system detection for VeriPatch."""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class OSType(StrEnum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PackageManager(StrEnum):
    APT = "apt"
    DNF = "dnf"
    PACMAN = "pacman"
    ZYPPER = "zypper"
    UNKNOWN = "unknown"


# Map ID_LIKE and ID values to package managers
_DISTRO_PKG_MAP: dict[str, PackageManager] = {
    "debian": PackageManager.APT,
    "ubuntu": PackageManager.APT,
    "linuxmint": PackageManager.APT,
    "pop": PackageManager.APT,
    "fedora": PackageManager.DNF,
    "rhel": PackageManager.DNF,
    "centos": PackageManager.DNF,
    "rocky": PackageManager.DNF,
    "almalinux": PackageManager.DNF,
    "arch": PackageManager.PACMAN,
    "manjaro": PackageManager.PACMAN,
    "opensuse": PackageManager.ZYPPER,
    "opensuse-leap": PackageManager.ZYPPER,
    "suse": PackageManager.ZYPPER,
}


@dataclass(frozen=True)
class OSInfo:
    """Detected operating system information."""

    os_type: OSType
    version: str
    release: str
    architecture: str
    distro_id: str | None = None
    distro_name: str | None = None
    package_manager: PackageManager | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "os_type": self.os_type.value,
            "version": self.version,
            "release": self.release,
            "architecture": self.architecture,
            "distro_id": self.distro_id,
            "distro_name": self.distro_name,
            "package_manager": (
                self.package_manager.value if self.package_manager else None
            ),
        }


def _normalize_os_name(system: str) -> OSType:
    normalized = system.lower()
    if normalized == "windows":
        return OSType.WINDOWS
    if normalized == "darwin":
        return OSType.MACOS
    if normalized == "linux":
        return OSType.LINUX
    return OSType.UNKNOWN


def _parse_os_release(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'^([A-Z0-9_]+)="?(.*?)"?$', line)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def _resolve_package_manager(os_release: dict[str, str]) -> PackageManager:
    distro_id = os_release.get("ID", "").lower()
    if distro_id in _DISTRO_PKG_MAP:
        return _DISTRO_PKG_MAP[distro_id]

    id_like = os_release.get("ID_LIKE", "").lower().split()
    for token in id_like:
        if token in _DISTRO_PKG_MAP:
            return _DISTRO_PKG_MAP[token]

    return PackageManager.UNKNOWN


def _read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        return _parse_os_release(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def detect_os(os_release_path: Path | None = None) -> OSInfo:
    """Detect the current operating system and relevant metadata."""
    system = platform.system()
    os_type = _normalize_os_name(system)
    version = platform.version()
    release = platform.release()
    architecture = platform.machine()

    distro_id: str | None = None
    distro_name: str | None = None
    package_manager: PackageManager | None = None
    raw: dict[str, Any] = {
        "system": system,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }

    if os_type == OSType.LINUX:
        path = os_release_path or Path("/etc/os-release")
        os_release = _read_os_release(path)
        raw["os_release"] = os_release
        distro_id = os_release.get("ID")
        distro_name = os_release.get("PRETTY_NAME") or os_release.get("NAME")
        package_manager = _resolve_package_manager(os_release)
    elif os_type == OSType.WINDOWS:
        raw["win32_edition"] = (
            platform.win32_edition() if hasattr(platform, "win32_edition") else None
        )
    elif os_type == OSType.MACOS:
        mac_ver = platform.mac_ver()
        raw["mac_ver"] = mac_ver

    return OSInfo(
        os_type=os_type,
        version=version,
        release=release,
        architecture=architecture,
        distro_id=distro_id,
        distro_name=distro_name,
        package_manager=package_manager,
        raw=raw,
    )
