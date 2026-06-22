"""Tests for IPC port resolution."""

from __future__ import annotations

from pathlib import Path

from veripatch.ipc.client import resolve_ipc_port


def test_resolve_ipc_port_from_env(monkeypatch) -> None:
    monkeypatch.setenv("VERIPATCH_IPC_PORT", "9999")
    monkeypatch.delenv("VERIPATCH_IPC_PORT_FILE", raising=False)
    assert resolve_ipc_port() == 9999


def test_resolve_ipc_port_invalid_env_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("VERIPATCH_IPC_PORT", "not-a-port")
    assert resolve_ipc_port() is None


def test_resolve_ipc_port_invalid_file_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("VERIPATCH_IPC_PORT", raising=False)
    port_file = tmp_path / "ipc.port"
    port_file.write_text("garbage", encoding="utf-8")
    monkeypatch.setenv("VERIPATCH_IPC_PORT_FILE", str(port_file))
    assert resolve_ipc_port() is None
