"""Validated subprocess command runner."""

from __future__ import annotations

import locale
import os
import re
import subprocess
import sys
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any

from veripatch.detection.os_detect import OSInfo
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_SPINNER_CHARS = frozenset({"-", "\\", "|", "/"})


def _subprocess_creationflags() -> int:
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def _subprocess_encoding() -> str:
    if sys.platform == "win32":
        return "utf-8"
    return locale.getpreferredencoding(False) or "utf-8"


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if sys.platform == "win32":
        env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _repair_mojibake(text: str) -> str:
    """Recover UTF-8 text that was decoded as Latin-1/CP1252."""
    if not text or "Ã" not in text:
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text
    if repaired != text and "\ufffd" not in repaired:
        return repaired
    return text


def _looks_like_utf16(raw: bytes) -> bool:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return True
    if len(raw) >= 4 and raw[1] == 0 and raw[3] == 0:
        return True
    return False


def _decode_output_bytes(raw: bytes | str) -> str:
    if isinstance(raw, str):
        return _repair_mojibake(raw)
    if not raw:
        return ""
    candidates: list[str] = []

    if _looks_like_utf16(raw):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                candidates.append(raw.decode(encoding))
            except UnicodeDecodeError:
                continue

    for encoding in (
        "utf-8",
        "utf-8-sig",
        locale.getpreferredencoding(False),
        "cp1252",
        "cp850",
        "latin-1",
    ):
        if not encoding:
            continue
        try:
            candidates.append(raw.decode(encoding))
        except UnicodeDecodeError:
            continue

    if not candidates:
        return raw.decode("utf-8", errors="replace")

    for text in candidates:
        repaired = _repair_mojibake(text)
        if "Ã" not in repaired and "\ufffd" not in repaired:
            return repaired

    return _repair_mojibake(candidates[0])


def _clean_output_line(line: str) -> str:
    cleaned = _ANSI_ESCAPE.sub("", line).strip("\r")
    stripped = _repair_mojibake(cleaned.strip())
    if stripped in _SPINNER_CHARS:
        return ""
    return stripped


@dataclass
class ExecutionResult:
    """Result of running a validated command."""

    success: bool
    dry_run: bool
    command: list[str]
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "message": self.message,
            "metadata": self.metadata,
        }


class CommandRunner:
    """Runs commands only after source validation; supports dry-run mode."""

    DEFAULT_TIMEOUT = 300

    def __init__(
        self,
        os_info: OSInfo,
        validator: SourceValidator | None = None,
        audit_logger: AuditLogger | None = None,
        dry_run: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        subprocess_runner: SubprocessRunner | None = None,
    ) -> None:
        self.os_info = os_info
        self.validator = validator or SourceValidator(audit_logger)
        self.audit = audit_logger or AuditLogger()
        self.dry_run = dry_run
        self.timeout = timeout
        self._subprocess_run = subprocess_runner or subprocess.run

    def run(self, command: list[str], dry_run: bool | None = None) -> ExecutionResult:
        """Validate and execute (or dry-run log) a command."""
        effective_dry_run = self.dry_run if dry_run is None else dry_run
        outcome = self.validator.validate_command(
            command,
            self.os_info.os_type,
            self.os_info.package_manager,
        )
        if not outcome.approved:
            self.audit.log_action(
                "command_blocked",
                {"command": command, "reason": outcome.reason},
            )
            return ExecutionResult(
                success=False,
                dry_run=effective_dry_run,
                command=command,
                message=outcome.reason,
                metadata={"rejected": True},
            )

        if effective_dry_run:
            self.audit.log_action(
                "command_dry_run",
                {"command": command},
            )
            return ExecutionResult(
                success=True,
                dry_run=True,
                command=command,
                message=f"Dry-run: would execute {' '.join(command)}",
            )

        self.audit.log_action("command_execute", {"command": command})
        try:
            completed = self._subprocess_run(
                command,
                capture_output=True,
                text=False,
                timeout=self.timeout,
                check=False,
                env=_subprocess_env(),
                creationflags=_subprocess_creationflags(),
            )
        except subprocess.TimeoutExpired:
            self.audit.log_action(
                "command_timeout",
                {"command": command, "timeout": self.timeout},
            )
            return ExecutionResult(
                success=False,
                dry_run=False,
                command=command,
                message=f"Command timed out after {self.timeout}s",
                metadata={"timeout": self.timeout},
            )
        except OSError as exc:
            self.audit.log_action(
                "command_failed",
                {"command": command, "error": str(exc)},
            )
            return ExecutionResult(
                success=False,
                dry_run=False,
                command=command,
                message=str(exc),
                metadata={"os_error": True},
            )

        stdout = _decode_output_bytes(completed.stdout or b"")
        stderr = _decode_output_bytes(completed.stderr or b"")
        success = completed.returncode == 0
        self.audit.log_action(
            "command_complete",
            {
                "command": command,
                "exit_code": completed.returncode,
                "success": success,
            },
        )
        return ExecutionResult(
            success=success,
            dry_run=False,
            command=command,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            message="Command completed successfully" if success else "Command failed",
        )

    def run_streaming(
        self,
        command: list[str],
        dry_run: bool | None = None,
    ) -> Generator[str, None, ExecutionResult]:
        """Validate and execute a command, yielding output lines in real-time."""
        effective_dry_run = self.dry_run if dry_run is None else dry_run
        outcome = self.validator.validate_command(
            command,
            self.os_info.os_type,
            self.os_info.package_manager,
        )
        if not outcome.approved:
            self.audit.log_action(
                "command_blocked",
                {"command": command, "reason": outcome.reason},
            )
            return ExecutionResult(
                success=False,
                dry_run=effective_dry_run,
                command=command,
                message=outcome.reason,
                metadata={"rejected": True},
            )

        if effective_dry_run:
            self.audit.log_action(
                "command_dry_run",
                {"command": command},
            )
            yield f"[Dry-run] would execute: {' '.join(command)}"
            return ExecutionResult(
                success=True,
                dry_run=True,
                command=command,
                message=f"Dry-run: would execute {' '.join(command)}",
            )

        self.audit.log_action("command_execute", {"command": command})
        stdout_acc: list[str] = []
        process: subprocess.Popen[str] | None = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
                env=_subprocess_env(),
                creationflags=_subprocess_creationflags(),
            )
            if process.stdout:
                for raw_line in process.stdout:
                    stdout_acc.append(raw_line)
                    line = _decode_output_bytes(raw_line.rstrip(b"\r\n"))
                    cleaned = _clean_output_line(line)
                    if cleaned:
                        yield cleaned
            exit_code = process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            if process is not None:
                process.kill()
                process.wait(timeout=5)
            self.audit.log_action(
                "command_timeout",
                {"command": command, "timeout": self.timeout},
            )
            return ExecutionResult(
                success=False,
                dry_run=False,
                command=command,
                message=f"Command timed out after {self.timeout}s",
                metadata={"timeout": self.timeout},
            )
        except OSError as exc:
            if process is not None and process.poll() is None:
                process.kill()
            self.audit.log_action(
                "command_failed",
                {"command": command, "error": str(exc)},
            )
            return ExecutionResult(
                success=False,
                dry_run=False,
                command=command,
                message=str(exc),
                metadata={"os_error": True},
            )

        stdout = _decode_output_bytes(b"".join(stdout_acc))
        success = exit_code == 0
        self.audit.log_action(
            "command_complete",
            {
                "command": command,
                "exit_code": exit_code,
                "success": success,
            },
        )
        return ExecutionResult(
            success=success,
            dry_run=False,
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr="",
            message="Command completed successfully" if success else "Command failed",
        )
