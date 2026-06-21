"""Source validation module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from veripatch.detection.os_detect import OSType, PackageManager
from veripatch.privileges.audit import AuditLogger
from veripatch.sources.registry import OfficialSource, find_source_by_executable, get_sources_for_os


class ValidationResult(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ValidationOutcome:
    """Result of validating a command against the official source registry."""

    result: ValidationResult
    source: OfficialSource | None
    reason: str
    command: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.result == ValidationResult.APPROVED


class SourceValidator:
    """Validates update commands against the official source registry."""

    def __init__(self, audit_logger: AuditLogger | None = None) -> None:
        self._audit = audit_logger or AuditLogger()

    def validate_command(
        self,
        command: list[str] | tuple[str, ...],
        os_type: OSType,
        package_manager: PackageManager | None = None,
    ) -> ValidationOutcome:
        """Validate that a command uses only an official, approved source."""
        if not command:
            outcome = ValidationOutcome(
                result=ValidationResult.REJECTED,
                source=None,
                reason="Empty command rejected",
                command=tuple(command),
            )
            self._audit.log_rejection(outcome.reason, {"command": list(command)})
            return outcome

        executable = command[0]
        source = find_source_by_executable(executable)

        if source is None:
            outcome = ValidationOutcome(
                result=ValidationResult.REJECTED,
                source=None,
                reason=f"Executable '{executable}' is not in the official source registry",
                command=tuple(command),
            )
            self._audit.log_rejection(outcome.reason, {"command": list(command)})
            return outcome

        if source.os_type != os_type:
            outcome = ValidationOutcome(
                result=ValidationResult.REJECTED,
                source=source,
                reason=(
                    f"Source '{source.id}' is registered for {source.os_type.value}, "
                    f"not {os_type.value}"
                ),
                command=tuple(command),
            )
            self._audit.log_rejection(
                outcome.reason,
                {"command": list(command), "source": source.id},
            )
            return outcome

        allowed_for_os = get_sources_for_os(os_type, package_manager)
        if source not in allowed_for_os:
            outcome = ValidationOutcome(
                result=ValidationResult.REJECTED,
                source=source,
                reason=f"Source '{source.id}' is not approved for this OS configuration",
                command=tuple(command),
            )
            self._audit.log_rejection(
                outcome.reason,
                {"command": list(command), "source": source.id},
            )
            return outcome

        if source.allowed_args_prefixes and len(command) > 1:
            first_arg = command[1]
            if not any(first_arg == prefix or first_arg.startswith(prefix)
                       for prefix in source.allowed_args_prefixes):
                outcome = ValidationOutcome(
                    result=ValidationResult.REJECTED,
                    source=source,
                    reason=(
                        f"Argument '{first_arg}' is not in allowed prefixes "
                        f"for source '{source.id}'"
                    ),
                    command=tuple(command),
                )
                self._audit.log_rejection(
                    outcome.reason,
                    {"command": list(command), "source": source.id},
                )
                return outcome

        outcome = ValidationOutcome(
            result=ValidationResult.APPROVED,
            source=source,
            reason="Command approved against official source registry",
            command=tuple(command),
        )
        self._audit.log_approval(source.id, {"command": list(command)})
        return outcome

