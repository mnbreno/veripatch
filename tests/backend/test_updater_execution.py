"""Additional tests for updaters with mocked subprocess execution."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from veripatch.detection.os_detect import OSInfo, OSType, PackageManager
from veripatch.execution.runner import CommandRunner
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator
from veripatch.updaters.linux import LinuxUpdater
from veripatch.updaters.macos import MacOSUpdater
from veripatch.updaters.windows import WindowsUpdater

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _fake_runner_factory(stdout: str, returncode: int = 0):
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    return fake_run


def test_windows_list_parses_winget_output(tmp_path: Path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    stdout = (FIXTURES / "winget_upgrade.txt").read_text(encoding="utf-8")
    info = OSInfo(os_type=OSType.WINDOWS, version="10", release="10", architecture="AMD64")
    validator = SourceValidator(audit)
    runner = CommandRunner(
        info, validator, audit, dry_run=False, subprocess_runner=_fake_runner_factory(stdout)
    )
    updater = WindowsUpdater(info, validator, audit, dry_run=False)
    updater.runner = runner
    with patch.object(updater, "_winget_available", return_value=True):
        result = updater.list_updates()
    assert result.success
    assert len(result.items) >= 2


def test_macos_list_parses_softwareupdate(tmp_path: Path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    stdout = (FIXTURES / "softwareupdate_list.txt").read_text(encoding="utf-8")
    info = OSInfo(os_type=OSType.MACOS, version="14", release="23", architecture="arm64")
    validator = SourceValidator(audit)
    runner = CommandRunner(
        info, validator, audit, dry_run=False, subprocess_runner=_fake_runner_factory(stdout)
    )
    updater = MacOSUpdater(info, validator, audit, dry_run=False)
    updater.runner = runner
    with patch.object(updater, "_softwareupdate_available", return_value=True):
        result = updater.list_updates()
    assert result.success
    assert len(result.items) >= 1


def test_linux_list_parses_apt(tmp_path: Path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    stdout = (FIXTURES / "apt_upgradable.txt").read_text(encoding="utf-8")
    info = OSInfo(
        os_type=OSType.LINUX,
        version="6",
        release="6",
        architecture="x86_64",
        package_manager=PackageManager.APT,
    )
    validator = SourceValidator(audit)
    runner = CommandRunner(
        info, validator, audit, dry_run=False, subprocess_runner=_fake_runner_factory(stdout)
    )
    updater = LinuxUpdater(info, validator, audit, dry_run=False)
    updater.runner = runner
    result = updater.list_updates()
    assert result.success
    assert len(result.items) == 2
