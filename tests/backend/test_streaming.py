"""Tests for streaming command execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from veripatch.detection.os_detect import OSInfo, OSType, PackageManager
from veripatch.execution.runner import CommandRunner
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator
from veripatch.updaters.linux import LinuxUpdater


@pytest.fixture
def audit(tmp_path: Path) -> AuditLogger:
    return AuditLogger(log_path=tmp_path / "audit.log")


def test_run_streaming_dry_run(audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.WINDOWS,
        version="10",
        release="10",
        architecture="AMD64",
    )
    runner = CommandRunner(info, SourceValidator(audit), audit, dry_run=True)
    stream = runner.run_streaming(["winget", "list"])
    lines = []
    try:
        while True:
            lines.append(next(stream))
    except StopIteration as exc:
        result = exc.value

    assert lines == ["[Dry-run] would execute: winget list"]
    assert result.success
    assert result.dry_run


def test_run_streaming_executes_mocked(audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.WINDOWS,
        version="10",
        release="10",
        architecture="AMD64",
    )

    class FakePopen:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.stdout = iter(["line one\n", "line two\n"])

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def poll(self) -> int | None:
            return 0

        def kill(self) -> None:
            return None

    runner = CommandRunner(info, SourceValidator(audit), audit, dry_run=False)
    original_popen = subprocess.Popen
    subprocess.Popen = FakePopen  # type: ignore[misc, assignment]
    try:
        stream = runner.run_streaming(["winget", "list"])
        lines = []
        try:
            while True:
                lines.append(next(stream))
        except StopIteration as exc:
            result = exc.value
    finally:
        subprocess.Popen = original_popen  # type: ignore[misc]

    assert lines == ["line one", "line two"]
    assert result.success
    assert result.stdout == "line one\nline two\n"


def test_linux_apply_streaming_dry_run(audit: AuditLogger) -> None:
    info = OSInfo(
        os_type=OSType.LINUX,
        version="6",
        release="6",
        architecture="x86_64",
        package_manager=PackageManager.APT,
    )
    updater = LinuxUpdater(info, audit_logger=audit, dry_run=True)
    stream = updater.apply_streaming(dry_run=True)
    lines = []
    try:
        while True:
            lines.append(next(stream))
    except StopIteration as exc:
        result = exc.value

    assert len(lines) == 1
    assert "Dry-run" in lines[0]
    assert result.success
    assert result.dry_run
