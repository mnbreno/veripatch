"""Tests for apply confirmation gating and elevation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from veripatch.config import APPLY_CONFIRMATION_TOKEN
from veripatch.ipc.server import JsonRpcServer
from veripatch.privileges.audit import AuditLogger
from veripatch.privileges.elevation import request_elevation


def test_apply_requires_confirmation_token() -> None:
    server = JsonRpcServer()
    result = server._handle_apply_updates({"dry_run": False, "confirm": False})
    assert result["success"] is False
    assert "confirm_token" in result["message"]


def test_apply_rejects_wrong_token() -> None:
    server = JsonRpcServer()
    result = server._handle_apply_updates(
        {"dry_run": False, "confirm": True, "confirm_token": "wrong"}
    )
    assert result["success"] is False


@patch("veripatch.ipc.server.is_elevated", return_value=True)
@patch("veripatch.ipc.server.get_updater")
def test_apply_with_valid_token_and_elevation(
    mock_get_updater: object,
    _mock_elevated: object,
) -> None:
    from veripatch.updaters.base import UpdateResult

    class FakeUpdater:
        def apply(self, dry_run: bool = True) -> UpdateResult:
            return UpdateResult(success=True, dry_run=dry_run, message="applied")

    mock_get_updater.return_value = FakeUpdater()
    server = JsonRpcServer()
    result = server._handle_apply_updates(
        {
            "dry_run": False,
            "confirm": True,
            "confirm_token": APPLY_CONFIRMATION_TOKEN,
        }
    )
    assert result["success"] is True


@patch("veripatch.ipc.server.is_elevated", return_value=False)
def test_apply_requires_elevation_when_not_elevated(_mock: object) -> None:
    server = JsonRpcServer()
    result = server._handle_apply_updates(
        {
            "dry_run": False,
            "confirm": True,
            "confirm_token": APPLY_CONFIRMATION_TOKEN,
        }
    )
    assert result["success"] is False
    assert "Elevation" in result["message"]


def test_diagnostics_handler() -> None:
    server = JsonRpcServer()
    result = server._handle_diagnostics({})
    assert "version" in result
    assert "capabilities" in result
    assert "recent_audit_entries" in result


def test_request_elevation_already_elevated(tmp_path: Path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    with patch("veripatch.privileges.elevation.is_elevated", return_value=True):
        assert request_elevation(audit_logger=audit) is True


def test_request_elevation_logs_guidance_on_linux(tmp_path: Path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    with patch("veripatch.privileges.elevation.sys.platform", "linux"):
        with patch("veripatch.privileges.elevation.is_elevated", return_value=False):
            assert request_elevation(audit_logger=audit) is False
    entries = audit.read_entries()
    assert any(e["message"] == "elevation_guidance" for e in entries)
