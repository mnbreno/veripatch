#!/usr/bin/env python3
"""G1: Enforce 100% successful compilation before pipeline progression."""

from __future__ import annotations

import argparse
import compileall
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
GUI = ROOT / "gui"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    backend = root / "backend"
    gui = root / "gui"
    errors: list[str] = []

    if not compileall.compile_dir(str(backend / "veripatch"), quiet=1):
        errors.append("compileall failed for backend/veripatch")

    build = subprocess.run(
        [sys.executable, "-m", "pip", "install", "build", "-q"],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        errors.append(f"pip install build failed: {build.stderr}")

    pkg = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(root / "artifacts-compile-gate")],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    if pkg.returncode != 0:
        errors.append(f"python -m build failed: {pkg.stderr}")

    if shutil.which("luacheck"):
        luacheck = subprocess.run(
            ["luacheck", str(gui)],
            capture_output=True,
            text=True,
        )
        if luacheck.returncode != 0:
            errors.append(f"luacheck failed: {luacheck.stdout}\n{luacheck.stderr}")

    if errors:
        print("COMPILATION GATE FAILED (100% required):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Compilation gate passed (100%).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
