#!/usr/bin/env python3
"""G2: Enforce minimum unit test pass rate (default 90%)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--min-pass-rate", type=float, default=90.0)
    args = parser.parse_args()
    root = args.root.resolve()
    junit = root / "artifacts-quality-gates" / "unit-junit.xml"
    junit.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"],
        cwd=root / "backend",
        check=False,
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "backend")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/backend/",
            f"--junitxml={junit}",
            "-q",
            "--no-cov",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )

    if not junit.is_file():
        print(f"Unit test gate failed: no junit output\n{result.stdout}\n{result.stderr}", file=sys.stderr)
        return 1

    tree = ET.parse(junit)
    root_el = tree.getroot()
    if root_el.tag == "testsuite":
        suites = [root_el]
    else:
        suites = list(root_el.findall("testsuite"))

    total = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    runnable = max(total - skipped, 0)
    passed = runnable - failures
    rate = (passed / runnable * 100.0) if runnable else 0.0

    print(f"Unit tests: {passed}/{runnable} passed ({rate:.1f}%), skipped={skipped}")

    if rate < args.min_pass_rate:
        print(
            f"UNIT TEST GATE FAILED: pass rate {rate:.1f}% < required {args.min_pass_rate}%",
            file=sys.stderr,
        )
        return 1

    print(f"Unit test gate passed (>={args.min_pass_rate}% pass rate).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
