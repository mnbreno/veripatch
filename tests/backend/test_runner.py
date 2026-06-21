"""Tests for CommandRunner."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from veripatch.detection.os_detect import OSInfo, OSType
from veripatch.execution.runner import CommandRunner
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator


@pytest.fixture
def audit(tmp_path: Path) -> AuditLogger:
    return AuditLogger(log_path=tmp_path / "audit.log")


@pytest.fixture
def windows_info() -> OSInfo:
    return OSInfo(
        os_type=OSType.WINDOWS,
        version="10.0",
        release="10",
        architecture="AMD64",
    )


def test_runner_dry_run(windows_info: OSInfo, audit: AuditLogger) -> None:
    runner = CommandRunner(
        windows_info,
        SourceValidator(audit),
        audit,
        dry_run=True,
    )
    result = runner.run(["winget", "list"])
    assert result.success
    assert result.dry_run
    assert "Dry-run" in result.message


def test_runner_rejects_unofficial(windows_info: OSInfo, audit: AuditLogger) -> None:
    runner = CommandRunner(windows_info, SourceValidator(audit), audit, dry_run=False)
    result = runner.run(["choco", "upgrade", "all"])
    assert not result.success
    assert result.metadata.get("rejected")


def test_runner_executes_mocked(windows_info: OSInfo, audit: AuditLogger) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    runner = CommandRunner(
        windows_info,
        SourceValidator(audit),
        audit,
        dry_run=False,
        subprocess_runner=fake_run,
    )
    result = runner.run(["winget", "list"])
    assert result.success
    assert result.stdout == "ok"
    assert result.exit_code == 0


def test_runner_timeout(windows_info: OSInfo, audit: AuditLogger) -> None:
    def slow_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, 1)

    runner = CommandRunner(
        windows_info,
        SourceValidator(audit),
        audit,
        dry_run=False,
        timeout=1,
        subprocess_runner=slow_run,
    )
    result = runner.run(["winget", "list"])
    assert not result.success
    assert "timed out" in result.message.lower()


def test_runner_dry_run_override(windows_info: OSInfo, audit: AuditLogger) -> None:
    runner = CommandRunner(
        windows_info,
        SourceValidator(audit),
        audit,
        dry_run=False,
    )
    result = runner.run(["winget", "list"], dry_run=True)
    assert result.dry_run
    assert result.success
