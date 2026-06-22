#!/usr/bin/env python3
"""G4: Static analysis — block critical and high severity findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK_SEVERITIES = frozenset({"HIGH", "CRITICAL"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    backend = root / "backend"
    errors: list[str] = []

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]", "bandit", "-q"],
        cwd=backend,
        check=False,
    )

    ruff = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "veripatch", "../tests"],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    if ruff.returncode != 0:
        errors.append(f"ruff check failed:\n{ruff.stdout}\n{ruff.stderr}")

    mypy = subprocess.run(
        [sys.executable, "-m", "mypy", "veripatch"],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    if mypy.returncode != 0:
        errors.append(f"mypy failed:\n{mypy.stdout}\n{mypy.stderr}")

    bandit_json = root / "artifacts-quality-gates" / "bandit.json"
    bandit_json.parent.mkdir(parents=True, exist_ok=True)
    bandit = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "veripatch",
            "-f",
            "json",
            "-o",
            str(bandit_json),
            "-ll",
        ],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    if bandit_json.is_file():
        data = json.loads(bandit_json.read_text(encoding="utf-8"))
        for item in data.get("results", []):
            severity = str(item.get("issue_severity", "")).upper()
            if severity in BLOCK_SEVERITIES:
                errors.append(
                    f"bandit {severity}: {item.get('test_name')} at {item.get('filename')}:{item.get('line_number')}"
                )

    if errors:
        print("STATIC ANALYSIS GATE FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Static analysis gate passed (no critical/high findings).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
