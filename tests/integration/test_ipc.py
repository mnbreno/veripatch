"""Integration tests for JSON-RPC IPC server."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


def _run_rpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    request = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": req_id}
    payload = json.dumps(request) + "\n"

    proc = subprocess.run(
        [sys.executable, "-m", "veripatch"],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(BACKEND_DIR),
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    assert lines, "No response from server"
    return json.loads(lines[0])


def test_ipc_ping() -> None:
    response = _run_rpc("ping")
    assert response["result"]["status"] == "ok"


def test_ipc_detect_os() -> None:
    response = _run_rpc("detect_os")
    assert "os" in response["result"]
    assert "elevated" in response["result"]
    assert "os_type" in response["result"]["os"]


def test_ipc_list_sources() -> None:
    response = _run_rpc("list_sources")
    assert "sources" in response["result"]
    assert isinstance(response["result"]["sources"], list)
    assert len(response["result"]["sources"]) >= 1


def test_ipc_check_updates() -> None:
    response = _run_rpc("check_updates")
    assert "check" in response["result"]
    assert "updates" in response["result"]


def test_ipc_apply_updates_dry_run() -> None:
    response = _run_rpc("apply_updates", {"dry_run": True})
    result = response["result"]
    assert result["dry_run"] is True


def test_ipc_unknown_method() -> None:
    response = _run_rpc("nonexistent_method")
    assert "error" in response
    assert response["error"]["code"] == -32601
