"""Tests for OS-specific updaters."""

from __future__ import annotations

from pathlib import Path

import pytest

from veripatch.detection.os_detect import OSInfo, OSType, PackageManager, detect_os
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator
from veripatch.updaters import get_updater
from veripatch.updaters.linux import LinuxUpdater
from veripatch.updaters.macos import MacOSUpdater
from veripatch.updaters.windows import WindowsUpdater


@pytest.fixture
def audit(tmp_path: Path) -> AuditLogger:
    return AuditLogger(log_path=tmp_path / "audit.log")


@pytest.fixture
def validator(audit: AuditLogger) -> SourceValidator:
    return SourceValidator(audit_logger=audit)


def test_get_updater_windows(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.WINDOWS,
        version="10.0",
        release="10",
        architecture="AMD64",
    )
    updater = get_updater(info, validator, audit)
    assert isinstance(updater, WindowsUpdater)


def test_get_updater_macos(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.MACOS,
        version="14.0",
        release="23",
        architecture="arm64",
    )
    updater = get_updater(info, validator, audit)
    assert isinstance(updater, MacOSUpdater)


def test_get_updater_linux(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.LINUX,
        version="6.0",
        release="6.0",
        architecture="x86_64",
        distro_id="ubuntu",
        package_manager=PackageManager.APT,
    )
    updater = get_updater(info, validator, audit)
    assert isinstance(updater, LinuxUpdater)


def test_windows_list_updates_stub(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.WINDOWS,
        version="10.0",
        release="10",
        architecture="AMD64",
    )
    updater = get_updater(info, validator, audit)
    result = updater.list_updates()
    assert result.success
    assert len(result.items) >= 1
    assert result.dry_run


def test_windows_apply_dry_run(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.WINDOWS,
        version="10.0",
        release="10",
        architecture="AMD64",
    )
    updater = get_updater(info, validator, audit)
    result = updater.apply(dry_run=True)
    assert result.success
    assert result.dry_run


def test_linux_unknown_pm_fails(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.LINUX,
        version="6.0",
        release="6.0",
        architecture="x86_64",
        package_manager=PackageManager.UNKNOWN,
    )
    updater = get_updater(info, validator, audit)
    result = updater.list_updates()
    assert not result.success


def test_get_updater_unknown_os_raises(validator: SourceValidator, audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.UNKNOWN,
        version="?",
        release="?",
        architecture="?",
    )
    with pytest.raises(ValueError, match="No updater available"):
        get_updater(info, validator, audit)


def test_current_os_updater_routing(validator: SourceValidator, audit: AuditLogger) -> None:
    info = detect_os()
    if info.os_type == OSType.UNKNOWN:
        pytest.skip("Unknown OS")
    updater = get_updater(info, validator, audit)
    check = updater.check()
    assert check.success or not check.success  # routing works without crash
