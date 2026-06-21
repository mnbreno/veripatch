"""Integration tests for TCP socket JSON-RPC IPC."""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

from veripatch.ipc.client import SocketJsonRpcClient, get_client, resolve_ipc_port
from veripatch.ipc.socket_server import SocketJsonRpcServer, write_port_file

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
IPC_ENV = {**os.environ, "VERIPATCH_DRY_RUN": "1", "PYTHONPATH": str(BACKEND_DIR)}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def socket_server() -> int:
    port = _free_port()
    server = SocketJsonRpcServer(host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield port


def test_socket_persistent_session(socket_server: int) -> None:
    with SocketJsonRpcClient("127.0.0.1", socket_server) as client:
        ping = client.call("ping")
        assert ping["status"] == "ok"

        detected = client.call("detect_os")
        assert "os" in detected

        diagnostics = client.call("diagnostics")
        assert diagnostics["session"]["requests_served"] >= 2


def test_socket_apply_updates_stream(socket_server: int) -> None:
    progress: list[str] = []
    with SocketJsonRpcClient("127.0.0.1", socket_server) as client:
        result = client.call(
            "apply_updates_stream",
            {"dry_run": True},
            on_progress=progress.append,
        )
    assert progress
    assert result["dry_run"] is True


def test_get_client_uses_socket_when_port_env(monkeypatch: pytest.MonkeyPatch, socket_server: int) -> None:
    monkeypatch.setenv("VERIPATCH_IPC_PORT", str(socket_server))
    client = get_client()
    assert isinstance(client, SocketJsonRpcClient)
    client.connect()
    try:
        assert client.call("ping")["status"] == "ok"
    finally:
        client.close()


def test_resolve_ipc_port_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERIPATCH_IPC_PORT", raising=False)
    port_file = tmp_path / "ipc.port"
    port_file.write_text("9876", encoding="utf-8")
    monkeypatch.setenv("VERIPATCH_IPC_PORT_FILE", str(port_file))
    assert resolve_ipc_port() == 9876


def test_write_port_file(tmp_path: Path) -> None:
    target = tmp_path / "ipc.port"
    write_port_file(8765, str(target))
    assert target.read_text(encoding="utf-8") == "8765"


def test_rpc_cli_over_socket(socket_server: int) -> None:
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "veripatch",
            "rpc",
            "ping",
            "--port",
            str(socket_server),
            "--stream-json",
        ],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_DIR),
        timeout=30,
        env=IPC_ENV,
    )
    assert proc.returncode == 0, proc.stderr
    response = json.loads(proc.stdout.strip())
    assert response["result"]["status"] == "ok"
