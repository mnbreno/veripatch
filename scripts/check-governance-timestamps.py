#!/usr/bin/env python3
"""Validate governance artifacts carry machine-readable timestamps."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _is_iso8601(value: str) -> bool:
    if not ISO8601_RE.match(value):
        return False
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def _require_timestamp(data: dict[str, object], field: str, errors: list[str], path: Path) -> None:
    raw = data.get(field)
    if not isinstance(raw, str) or not _is_iso8601(raw):
        errors.append(f"{path}: missing or invalid '{field}' timestamp")


def check_milestones(root: Path, errors: list[str]) -> None:
    milestone_dir = root / "governance" / "milestones"
    if not milestone_dir.is_dir():
        errors.append(f"{milestone_dir}: directory missing")
        return
    files = sorted(milestone_dir.glob("*.json"))
    if not files:
        errors.append(f"{milestone_dir}: no milestone files found")
        return
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("start", "due"):
            _require_timestamp(data, field, errors, path)
        if not data.get("goal"):
            errors.append(f"{path}: missing 'goal'")
        if not data.get("exit_criteria"):
            errors.append(f"{path}: missing 'exit_criteria'")


def check_knowledge_base(root: Path, errors: list[str]) -> None:
    kb_dir = root / "governance" / "knowledge-base"
    index = kb_dir / "INDEX.md"
    if not index.is_file():
        errors.append(f"{index}: missing knowledge-base index")
    sessions = sorted(kb_dir.glob("session-*.json"))
    if not sessions:
        errors.append(f"{kb_dir}: no session records found")
        return
    for path in sessions:
        data = json.loads(path.read_text(encoding="utf-8"))
        _require_timestamp(data, "timestamp", errors, path)
        if not data.get("summary"):
            errors.append(f"{path}: missing 'summary'")


def check_release_consensus(root: Path, errors: list[str]) -> None:
    consensus_dir = root / "release" / "consensus"
    if not consensus_dir.is_dir():
        return
    for path in sorted(consensus_dir.glob("v*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        _require_timestamp(data, "generated_at", errors, path)


def check_policy(root: Path, errors: list[str]) -> None:
    policy = root / "governance" / "POLICY.md"
    if not policy.is_file():
        errors.append(f"{policy}: missing governance policy")
        return
    text = policy.read_text(encoding="utf-8")
    if "last_updated" not in text:
        errors.append(f"{policy}: missing last_updated timestamp")

    for required in ("QUALITY_GATES.md",):
        path = root / "governance" / required
        if not path.is_file():
            errors.append(f"{path}: missing required governance document")
        elif "last_updated" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: missing last_updated timestamp")


def check_agent_registry(root: Path, errors: list[str]) -> None:
    registry_path = root / "governance" / "agents" / "registry.json"
    if not registry_path.is_file():
        errors.append(f"{registry_path}: missing agent registry")
        return

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    _require_timestamp(data, "last_updated", errors, registry_path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        errors.append(f"{registry_path}: 'agents' must be a non-empty list")
        return

    for entry in agents:
        if not isinstance(entry, dict):
            errors.append(f"{registry_path}: agent entry must be an object")
            continue
        agent_id = entry.get("id")
        full_name = entry.get("full_name")
        role = entry.get("role")
        work_doc = entry.get("work_doc")
        if not agent_id or not full_name or not role:
            errors.append(f"{registry_path}: agent missing id, full_name, or role")
            continue
        if role not in full_name:
            errors.append(f"{registry_path}: full_name must include role for {agent_id}")
        if not work_doc:
            errors.append(f"{registry_path}: agent {agent_id} missing work_doc")
            continue
        work_path = root / str(work_doc)
        if not work_path.is_file():
            errors.append(f"{work_path}: missing work documentation for {agent_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    check_policy(root, errors)
    check_agent_registry(root, errors)
    check_milestones(root, errors)
    check_knowledge_base(root, errors)
    check_release_consensus(root, errors)

    if errors:
        print("Governance timestamp validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Governance timestamp validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
