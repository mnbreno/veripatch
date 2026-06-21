"""Tests for source validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from veripatch.detection.os_detect import OSType, PackageManager
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.registry import get_sources_for_os
from veripatch.sources.validator import SourceValidator, ValidationResult


@pytest.fixture
def validator(tmp_path: Path) -> SourceValidator:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    return SourceValidator(audit_logger=audit)


def test_windows_winget_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["winget", "list"],
        OSType.WINDOWS,
    )
    assert outcome.approved
    assert outcome.source is not None
    assert outcome.source.id == "winget"


def test_windows_unofficial_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["choco", "upgrade", "all"],
        OSType.WINDOWS,
    )
    assert not outcome.approved
    assert outcome.result == ValidationResult.REJECTED


def test_macos_softwareupdate_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["softwareupdate", "--list"],
        OSType.MACOS,
    )
    assert outcome.approved
    assert outcome.source is not None
    assert outcome.source.id == "softwareupdate"


def test_macos_unofficial_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["brew", "upgrade"],
        OSType.MACOS,
    )
    assert not outcome.approved


def test_linux_apt_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["apt", "upgrade"],
        OSType.LINUX,
        PackageManager.APT,
    )
    assert outcome.approved
    assert outcome.source is not None
    assert outcome.source.id == "apt"


def test_linux_wrong_pm_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["dnf", "upgrade"],
        OSType.LINUX,
        PackageManager.APT,
    )
    assert not outcome.approved


def test_empty_command_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command([], OSType.WINDOWS)
    assert not outcome.approved


def test_rejection_logged(validator: SourceValidator, tmp_path: Path) -> None:
    validator.validate_command(["curl", "http://evil.com"], OSType.WINDOWS)
    log_path = tmp_path / "audit.log"
    entries = AuditLogger(log_path=log_path).read_entries()
    assert any(e["event_type"] == "source_rejected" for e in entries)


def test_get_sources_for_windows() -> None:
    sources = get_sources_for_os(OSType.WINDOWS)
    ids = {s.id for s in sources}
    assert "windows_update_agent" in ids
    assert "winget" in ids


def test_winget_invalid_arg_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["winget", "install", "evil"],
        OSType.WINDOWS,
    )
    assert not outcome.approved
    assert outcome.reason != ""
    assert outcome.command == ("winget", "install", "evil")


def test_pacman_su_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["pacman", "-Su"],
        OSType.LINUX,
        PackageManager.PACMAN,
    )
    assert outcome.approved
    assert outcome.source is not None
    assert outcome.source.id == "pacman"


def test_pacman_syu_combined_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["pacman", "-Syu"],
        OSType.LINUX,
        PackageManager.PACMAN,
    )
    assert outcome.approved
    assert outcome.source.id == "pacman"


def test_pacman_install_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["pacman", "-S", "firefox"],
        OSType.LINUX,
        PackageManager.PACMAN,
    )
    assert not outcome.approved


def test_pacman_qu_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["pacman", "-Qu"],
        OSType.LINUX,
        PackageManager.PACMAN,
    )
    assert outcome.approved


def test_source_os_type_mismatch_rejected(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["winget", "list"],
        OSType.LINUX,
    )
    assert not outcome.approved
    assert "registered for" in outcome.reason


def test_winget_no_args_approved(validator: SourceValidator) -> None:
    outcome = validator.validate_command(
        ["winget"],
        OSType.WINDOWS,
    )
    assert outcome.approved


def test_approval_logged(validator: SourceValidator, tmp_path: Path) -> None:
    validator.validate_command(["winget", "list"], OSType.WINDOWS)
    log_path = tmp_path / "audit.log"
    entries = AuditLogger(log_path=log_path).read_entries()
    assert any(e["event_type"] == "source_approved" for e in entries)
