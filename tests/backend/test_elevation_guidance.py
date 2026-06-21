"""Tests for elevation guidance helpers."""

from __future__ import annotations

from unittest.mock import patch

from veripatch.privileges.elevation import get_elevation_guidance, request_elevation


def test_get_elevation_guidance_when_elevated() -> None:
    with patch("veripatch.privileges.elevation.is_elevated", return_value=True):
        guidance = get_elevation_guidance()
    assert guidance["elevated"] is True
    assert "Privileges OK" in str(guidance["message"])


def test_get_elevation_guidance_linux() -> None:
    with patch("veripatch.privileges.elevation.is_elevated", return_value=False):
        with patch("veripatch.privileges.elevation.sys.platform", "linux"):
            guidance = get_elevation_guidance(["veripatch", "--serve"])
    assert guidance["elevated"] is False
    assert "suggested_sudo" in guidance
    assert "suggested_pkexec" in guidance


def test_get_elevation_guidance_windows() -> None:
    with patch("veripatch.privileges.elevation.is_elevated", return_value=False):
        with patch("veripatch.privileges.elevation.sys.platform", "win32"):
            guidance = get_elevation_guidance()
    assert guidance["method"] == "uac_runas"
    assert "suggested" in guidance


def test_request_elevation_when_not_elevated() -> None:
    with patch("veripatch.privileges.elevation.is_elevated", return_value=False):
        with patch("veripatch.privileges.elevation.sys.platform", "linux"):
            assert request_elevation() is False
