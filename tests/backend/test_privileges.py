"""Tests for privilege elevation and audit logging."""

from __future__ import annotations

from pathlib import Path

from veripatch.privileges.audit import AuditLogger
from veripatch.privileges.elevation import is_elevated, request_elevation


def test_is_elevated_returns_bool() -> None:
    assert isinstance(is_elevated(), bool)


def test_request_elevation_stub_returns_false() -> None:
    assert request_elevation() is False


def test_audit_logger_append_only(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path=log_path)
    logger.log_action("test_action", {"key": "value"})
    logger.log_approval("winget", {"command": ["winget", "list"]})
    logger.log_rejection("blocked", {"command": ["curl"]})

    entries = logger.read_entries()
    assert len(entries) == 3
    assert entries[0]["event_type"] == "action"
    assert entries[1]["event_type"] == "source_approved"
    assert entries[2]["event_type"] == "source_rejected"
    assert "elevated" in entries[0]


def test_audit_log_persists_across_instances(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.log"
    AuditLogger(log_path=log_path).log_action("first")
    AuditLogger(log_path=log_path).log_action("second")
    entries = AuditLogger(log_path=log_path).read_entries()
    assert len(entries) == 2
