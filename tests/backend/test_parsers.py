"""Tests for CLI output parsers."""

from __future__ import annotations

from pathlib import Path

from veripatch.execution.parsers import (
    parse_apt_upgradable,
    parse_dnf_check_update,
    parse_pacman_qu,
    parse_softwareupdate_list,
    parse_winget_upgrade,
    parse_zypper_list_updates,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_winget_upgrade() -> None:
    stdout = (FIXTURES / "winget_upgrade.txt").read_text(encoding="utf-8")
    items = parse_winget_upgrade(stdout, "winget")
    assert len(items) >= 2
    assert items[0].source_id == "winget"
    assert "Git" in items[0].title


def test_parse_softwareupdate_list() -> None:
    stdout = (FIXTURES / "softwareupdate_list.txt").read_text(encoding="utf-8")
    items = parse_softwareupdate_list(stdout, "softwareupdate")
    assert len(items) >= 1
    assert "Sonoma" in items[0].title or "macOS" in items[0].title


def test_parse_apt_upgradable() -> None:
    stdout = (FIXTURES / "apt_upgradable.txt").read_text(encoding="utf-8")
    items = parse_apt_upgradable(stdout, "apt")
    assert len(items) == 2
    assert items[0].metadata["package"] == "curl"


def test_parse_dnf_check_update() -> None:
    stdout = "curl.x86_64  8.5.0  updates\nvim.x86_64  9.1  updates\n"
    items = parse_dnf_check_update(stdout, "dnf")
    assert len(items) == 2


def test_parse_pacman_qu() -> None:
    stdout = "curl 8.5.0-1\nvim 9.1.0-1\n"
    items = parse_pacman_qu(stdout, "pacman")
    assert len(items) == 2
    assert "curl" in items[0].title


def test_parse_zypper_list_updates() -> None:
    stdout = (
        "Repository | Name | Current | Available | Arch\n"
        "-----------|------|---------|-----------|-----\n"
        "1 | update | curl | 8.4 | 8.5 | x86_64\n"
    )
    items = parse_zypper_list_updates(stdout, "zypper")
    assert len(items) >= 1
