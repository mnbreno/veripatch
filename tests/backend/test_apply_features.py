"""Tests for apply feature enhancements."""

from __future__ import annotations

from unittest.mock import patch

from veripatch.detection.os_detect import OSInfo, OSType
from veripatch.ipc.server import JsonRpcServer
from veripatch.updaters.base import UpdateItem, UpdateStatus
from veripatch.updaters.windows import CURSOR_PACKAGE_ID, get_apply_blockers


def test_get_apply_blockers_detects_cursor_update() -> None:
    items = [
        UpdateItem(
            id="winget-cursor",
            title="Cursor",
            source_id="winget",
            status=UpdateStatus.AVAILABLE,
            metadata={"package_id": CURSOR_PACKAGE_ID},
        )
    ]
    with patch("veripatch.updaters.windows.sys.platform", "win32"):
        with patch("veripatch.updaters.windows._cursor_is_running", return_value=True):
            blockers = get_apply_blockers(items)
    assert blockers["cursor_running"] is True
    assert blockers["cursor_update_available"] is True
    assert blockers["cursor_package_id"] == CURSOR_PACKAGE_ID


def test_check_updates_includes_blockers_on_windows() -> None:
    server = JsonRpcServer()
    info = OSInfo(os_type=OSType.WINDOWS, version="10", release="10", architecture="AMD64")
    cursor_item = UpdateItem(
        id="winget-cursor",
        title="Cursor",
        source_id="winget",
        status=UpdateStatus.AVAILABLE,
        metadata={"package_id": CURSOR_PACKAGE_ID},
    )
    list_result = type(
        "Listed",
        (),
        {
            "items": [cursor_item],
            "to_dict": lambda self: {"items": [cursor_item.to_dict()], "success": True},
        },
    )()
    check_result = type(
        "Checked",
        (),
        {"to_dict": lambda self: {"success": True, "message": "ok"}},
    )()

    class FakeUpdater:
        dry_run = False

        def check(self):
            return check_result

        def list_updates(self):
            return list_result

    with patch("veripatch.ipc.server.detect_os", return_value=info):
        with patch("veripatch.ipc.server.get_updater", return_value=FakeUpdater()):
            with patch("veripatch.updaters.windows.sys.platform", "win32"):
                with patch("veripatch.updaters.windows._cursor_is_running", return_value=True):
                    payload = server._handle_check_updates(None)

    assert "blockers" in payload
    assert payload["blockers"]["cursor_running"] is True
    assert payload["blockers"]["cursor_update_available"] is True
