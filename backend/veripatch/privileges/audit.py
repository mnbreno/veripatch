"""Privilege elevation detection and audit logging."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from veripatch.privileges.elevation import is_elevated


class AuditLogger:
    """Append-only audit trail for privileged and validation actions."""

    def __init__(self, log_path: Path | None = None) -> None:
        self._log_path = log_path or Path(".veripatch") / "audit.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        return self._log_path

    def _write(self, event_type: str, message: str, details: dict[str, Any] | None = None) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "message": message,
            "elevated": is_elevated(),
            "details": details or {},
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def log_approval(self, source_id: str, details: dict[str, Any] | None = None) -> None:
        self._write("source_approved", f"Approved source: {source_id}", details)

    def log_rejection(self, reason: str, details: dict[str, Any] | None = None) -> None:
        self._write("source_rejected", reason, details)

    def log_action(self, action: str, details: dict[str, Any] | None = None) -> None:
        self._write("action", action, details)

    def log_privilege_check(self, required: bool, granted: bool) -> None:
        self._write(
            "privilege_check",
            f"Required={required}, granted={granted}",
            {"required": required, "granted": granted},
        )

    def read_entries(self) -> list[dict[str, Any]]:
        if not self._log_path.is_file():
            return []
        entries: list[dict[str, Any]] = []
        for line in self._log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries
