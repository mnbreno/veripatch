"""Base updater interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from veripatch.detection.os_detect import OSInfo
from veripatch.execution.runner import CommandRunner, ExecutionResult
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.validator import SourceValidator


class UpdateStatus(StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class UpdateItem:
    """Represents a single available or applied update."""

    id: str
    title: str
    source_id: str
    status: UpdateStatus = UpdateStatus.AVAILABLE
    severity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source_id": self.source_id,
            "status": self.status.value,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class UpdateResult:
    """Result of an update check or apply operation."""

    success: bool
    dry_run: bool
    message: str
    items: list[UpdateItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "message": self.message,
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
        }


class Updater(ABC):
    """Abstract base class for OS-specific updaters."""

    def __init__(
        self,
        os_info: OSInfo,
        validator: SourceValidator | None = None,
        audit_logger: AuditLogger | None = None,
        runner: CommandRunner | None = None,
        dry_run: bool = False,
    ) -> None:
        self.os_info = os_info
        self.validator = validator or SourceValidator()
        self.audit = audit_logger or AuditLogger()
        self.dry_run = dry_run
        self.runner = runner or CommandRunner(
            os_info,
            self.validator,
            self.audit,
            dry_run=dry_run,
        )

    @abstractmethod
    def check(self) -> UpdateResult:
        """Verify update tooling is available."""

    @abstractmethod
    def list_updates(self) -> UpdateResult:
        """List available updates from official sources."""

    @abstractmethod
    def apply(self, dry_run: bool = True) -> UpdateResult:
        """Apply updates. Defaults to dry-run in foundation iteration."""

    @abstractmethod
    def apply_streaming(
        self,
        dry_run: bool = True,
    ) -> Generator[str, None, UpdateResult]:
        """Apply updates and yield progress/log lines."""

    def _validate(self, command: list[str]) -> bool:
        outcome = self.validator.validate_command(
            command,
            self.os_info.os_type,
            self.os_info.package_manager,
        )
        return outcome.approved

    def _yield_command_stream(
        self,
        command: list[str],
        *,
        dry_run: bool,
        validate_cmd: list[str] | None = None,
    ) -> Generator[str, None, ExecutionResult]:
        """Run a validated command via run_streaming, yielding output lines."""
        check_cmd = validate_cmd or command
        if not self._validate(check_cmd):
            return ExecutionResult(
                success=False,
                dry_run=dry_run,
                command=command,
                message="Apply rejected: command not from official source",
                metadata={"rejected": True},
            )

        stream = self.runner.run_streaming(command, dry_run=dry_run)
        try:
            while True:
                yield next(stream)
        except StopIteration as exc:
            result: ExecutionResult = exc.value
            return result
