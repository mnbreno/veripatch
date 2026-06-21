"""Shared workspace path resolution for multi-terminal AgentMesh."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_MARKER = Path("agentmesh") / "pyproject.toml"


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) until agentmesh/pyproject.toml is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / _REPO_MARKER).is_file():
            return candidate
    return current


def bus_root() -> Path:
    env = os.environ.get("AGENTMESH_BUS_ROOT")
    if env:
        path = Path(env)
        return path if path.is_absolute() else find_repo_root() / path
    return find_repo_root() / ".agentmesh" / "bus"


def runtime_root() -> Path:
    env = os.environ.get("AGENTMESH_RUNTIME_ROOT")
    if env:
        path = Path(env)
        return path if path.is_absolute() else find_repo_root() / path
    return find_repo_root() / ".agentmesh" / "run"


def apply_runtime_env() -> Path:
    """Set default env vars to repo-relative paths and return repo root."""
    root = find_repo_root()
    bus = bus_root()
    runtime = runtime_root()
    os.environ.setdefault("AGENTMESH_BUS_ROOT", str(bus))
    os.environ.setdefault("AGENTMESH_RUNTIME_ROOT", str(runtime))
    return root


def ensure_runtime_dirs() -> tuple[Path, Path]:
    """Create bus and runtime directories; return (bus_root, runtime_root)."""
    apply_runtime_env()
    bus = bus_root()
    runtime = runtime_root()
    (bus / "inboxes").mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)
    return bus, runtime
