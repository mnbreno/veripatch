"""Tests for persistent JSON-RPC IPC client."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from veripatch.ipc.client import JsonRpcClient

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
IPC_ENV = {**os.environ, "VERIPATCH_DRY_RUN": "1", "PYTHONPATH": str(BACKEND_DIR)}


@pytest.fixture
def client() -> JsonRpcClient:
    with JsonRpcClient(cwd=str(BACKEND_DIR), env=IPC_ENV) as rpc:
        yield rpc


def test_persistent_session_multiple_calls(client: JsonRpcClient) -> None:
    ping = client.call("ping")
    assert ping["status"] == "ok"

    detected = client.call("detect_os")
    assert "os" in detected

    diagnostics = client.call("diagnostics")
    assert diagnostics["session"]["requests_served"] >= 2


def test_shutdown_ends_session() -> None:
    rpc = JsonRpcClient(cwd=str(BACKEND_DIR), env=IPC_ENV)
    rpc.start()
    result = rpc.call("shutdown")
    assert result["status"] == "shutting_down"
    assert result["requests_served"] >= 1
    rpc.close()
    assert rpc._proc is None
