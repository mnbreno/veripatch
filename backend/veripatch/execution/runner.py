"""Validated subprocess command runner."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any

from veripatch.detection.os_detect import OSInfo
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


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
                text=True,
                timeout=self.timeout,
                check=False,
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
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
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
                text=True,
                bufsize=1,
            )
            if process.stdout:
                for line in process.stdout:
                    stdout_acc.append(line)
                    stripped = line.strip()
                    if stripped:
                        yield stripped
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

        stdout = "".join(stdout_acc)
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
