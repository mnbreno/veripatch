#!/usr/bin/env python3
"""Validate AgentMesh release consensus before publishing a stable VeriPatch release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_AGENTS = ("devops-automator", "code-reviewer", "reality-checker")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def validate(payload: dict, *, version: str) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    if payload.get("project") != "veripatch":
        errors.append("project must be 'veripatch'")
    if payload.get("version") != version:
        errors.append(f"version must be {version}")
    if not VERSION_RE.match(version):
        errors.append(f"invalid semver: {version}")

    consensus = payload.get("consensus") or {}
    if consensus.get("approved") is not True:
        errors.append("consensus.approved must be true")
    if consensus.get("production_ready") is not True:
        errors.append("consensus.production_ready must be true")
    if consensus.get("blockers"):
        errors.append(f"blockers present: {consensus.get('blockers')}")

    participating = {a.get("agent_id") for a in consensus.get("agents") or []}
    for agent_id in REQUIRED_AGENTS:
        if agent_id not in participating:
            errors.append(f"missing agent verdict: {agent_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release consensus JSON")
    parser.add_argument("--version", required=True, help="Release version (e.g. 1.1.0)")
    parser.add_argument(
        "--file",
        default="",
        help="Consensus JSON path (default: release/consensus/v{version}.json)",
    )
    args = parser.parse_args()

    path = Path(args.file or f"release/consensus/v{args.version}.json")
    if not path.is_file():
        print(f"Consensus file not found: {path}", file=sys.stderr)
        print(
            "Generate with AgentMesh: agentmesh release verify --version "
            f"{args.version} --output {path}",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(payload, version=args.version)
    if errors:
        print("Release consensus validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"Release consensus valid for veripatch {args.version}")
    print(f"  workflow: {payload.get('workflow')}")
    print(f"  correlation: {payload.get('correlation_id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
