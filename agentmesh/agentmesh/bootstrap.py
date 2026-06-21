"""Bootstrap AgentMesh for multi-terminal development."""

from __future__ import annotations

import subprocess
import sys

from agentmesh.paths import ensure_runtime_dirs, find_repo_root
from agentmesh.runtime.registry import get_registry


def run_bootstrap(*, install: bool = True) -> int:
    repo = find_repo_root()
    package_dir = repo / "agentmesh"
    if not (package_dir / "pyproject.toml").is_file():
        print(f"Error: agentmesh package not found under {repo}", file=sys.stderr)
        return 1

    if install:
        print("Installing agentmesh (editable)...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            cwd=package_dir,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

    bus, runtime = ensure_runtime_dirs()
    specs_dir = package_dir / "agentmesh" / "agents"
    known = {p.stem for p in specs_dir.glob("*.md")} if specs_dir.is_dir() else set()
    registry = get_registry(known_agents=known)
    registry.cleanup_stale()

    print()
    print("=" * 60)
    print("  AgentMesh READY for multi-terminal development")
    print("=" * 60)
    print(f"  Repo root:     {repo}")
    print(f"  FileBus:       {bus}")
    print(f"  Runtime locks: {runtime}")
    print()
    print("  Open Cursor integrated terminals manually, then in EACH:")
    print(f"    cd {package_dir.name}")
    print("    agentmesh")
    print("    start development")
    print()
    print("  Or one-liner per terminal:")
    print("    agentmesh start development --here")
    print()
    print("  Verify: agentmesh status")
    print("=" * 60)
    return 0
