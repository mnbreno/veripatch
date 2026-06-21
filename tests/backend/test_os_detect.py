"""Tests for OS detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from veripatch.detection.os_detect import OSType, PackageManager, detect_os


def test_detect_os_returns_valid_structure() -> None:
    info = detect_os()
    assert info.os_type in {OSType.WINDOWS, OSType.MACOS, OSType.LINUX, OSType.UNKNOWN}
    assert info.version
    assert info.architecture


def test_detect_linux_ubuntu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veripatch.detection.os_detect.platform.system", lambda: "Linux")
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 22.04.3 LTS"\n',
        encoding="utf-8",
    )
    info = detect_os(os_release_path=os_release)
    assert info.os_type == OSType.LINUX
    assert info.distro_id == "ubuntu"
    assert info.distro_name == "Ubuntu 22.04.3 LTS"
    assert info.package_manager == PackageManager.APT


def test_detect_linux_fedora(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veripatch.detection.os_detect.platform.system", lambda: "Linux")
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=fedora\nPRETTY_NAME="Fedora Linux 39"\n',
        encoding="utf-8",
    )
    info = detect_os(os_release_path=os_release)
    assert info.package_manager == PackageManager.DNF


def test_detect_linux_arch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veripatch.detection.os_detect.platform.system", lambda: "Linux")
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=arch\nPRETTY_NAME="Arch Linux"\n',
        encoding="utf-8",
    )
    info = detect_os(os_release_path=os_release)
    assert info.package_manager == PackageManager.PACMAN


def test_detect_linux_id_like_debian(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veripatch.detection.os_detect.platform.system", lambda: "Linux")
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=linuxmint\nID_LIKE="ubuntu debian"\nPRETTY_NAME="Linux Mint 21"\n',
        encoding="utf-8",
    )
    info = detect_os(os_release_path=os_release)
    assert info.package_manager == PackageManager.APT


def test_os_info_to_dict() -> None:
    info = detect_os()
    data = info.to_dict()
    assert "os_type" in data
    assert "version" in data
    assert "architecture" in data
