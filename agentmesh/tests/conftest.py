"""Shared pytest configuration for AgentMesh."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("AGENTMESH_SKIP_PROCESS_SCAN", "1")

AGENTMESH_DIR = Path(__file__).resolve().parent.parent
if str(AGENTMESH_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTMESH_DIR))


@pytest.fixture(autouse=True)
def isolated_agentmesh_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent from developer runtime locks and FileBus state."""
    runtime = tmp_path / "run"
    bus = tmp_path / "bus"
    runtime.mkdir()
    bus.mkdir()
    monkeypatch.setenv("AGENTMESH_RUNTIME_ROOT", str(runtime))
    monkeypatch.setenv("AGENTMESH_BUS_ROOT", str(bus))
    monkeypatch.setenv("AGENTMESH_SKIP_PROCESS_SCAN", "1")
