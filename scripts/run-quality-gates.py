#!/usr/bin/env python3
"""Run all mandatory quality gates (G1-G5) locally."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

GATES = [
    ("G1 Compilation (100%)", ["run-compile-gate.py"]),
    ("G2 Unit tests (90%+)", ["run-unit-test-gate.py", "--min-pass-rate", "90"]),
    ("G3 Integration tests", []),  # inline pytest
    ("G4 Static analysis", ["run-static-analysis-gate.py"]),
    ("G5 Governance", ["check-governance-timestamps.py"]),
]


def main() -> int:
    failed: list[str] = []

    for name, script_args in GATES:
        print(f"\n=== {name} ===")
        if name.startswith("G3"):
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"],
                cwd=ROOT / "backend",
                check=False,
            )
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--no-cov"],
                cwd=ROOT,
                env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "backend")},
            )
            if result.returncode != 0:
                failed.append(name)
            continue

        result = subprocess.run([sys.executable, str(SCRIPTS / script_args[0]), *script_args[1:]])
        if result.returncode != 0:
            failed.append(name)

    print("\n" + "=" * 60)
    if failed:
        print("QUALITY GATES FAILED:", ", ".join(failed))
        return 1
    print("All quality gates G1-G5 passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
