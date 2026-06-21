"""macOS updater using softwareupdate CLI."""

from __future__ import annotations

import shutil
from collections.abc import Generator

from veripatch.execution.parsers import parse_softwareupdate_list
from veripatch.updaters.base import UpdateItem, Updater, UpdateResult, UpdateStatus


class MacOSUpdater(Updater):
    """macOS update workflow via softwareupdate and App Store APIs."""

    SOURCE_SOFTWAREUPDATE = "softwareupdate"

    def _softwareupdate_available(self) -> bool:
        return shutil.which("softwareupdate") is not None

    def check(self) -> UpdateResult:
        self.audit.log_action("macos_updater_check", {})
        if not self._softwareupdate_available():
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="softwareupdate CLI not found",
                errors=["softwareupdate is not available on this system"],
            )
        if not self._validate(["softwareupdate", "--list"]):
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="softwareupdate source validation failed",
                errors=["Official source validation rejected command"],
            )
        result = self.runner.run(["softwareupdate", "--list"])
        return UpdateResult(
            success=result.success or result.dry_run,
            dry_run=result.dry_run,
            message=result.message,
            errors=[] if result.success else [result.stderr or result.message],
        )

    def list_updates(self) -> UpdateResult:
        self.audit.log_action("macos_list_updates", {})
        cmd = ["softwareupdate", "--list"]
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="Cannot list updates: source validation failed",
                errors=["Rejected non-official command"],
            )
        result = self.runner.run(cmd)
        if result.dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=result.message,
                items=[
                    UpdateItem(
                        id="macos-dry-run",
                        title="[Dry-run] macOS updates would be listed",
                        source_id=self.SOURCE_SOFTWAREUPDATE,
                        status=UpdateStatus.AVAILABLE,
                    )
                ],
            )
        items = parse_softwareupdate_list(result.stdout, self.SOURCE_SOFTWAREUPDATE)
        return UpdateResult(
            success=result.success,
            dry_run=False,
            message=f"Listed {len(items)} macOS update(s)",
            items=items,
            errors=[] if result.success else [result.stderr or result.message],
        )

    def apply(self, dry_run: bool = True) -> UpdateResult:
        self.audit.log_action("macos_apply_updates", {"dry_run": dry_run})
        cmd = ["softwareupdate", "--install", "--all"]
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=["Validation failed for softwareupdate --install"],
            )

        result = self.runner.run(cmd, dry_run=dry_run)
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=result.message,
                items=[
                    UpdateItem(
                        id="macos-apply-dry-run",
                        title="[Dry-run] softwareupdate --install --all",
                        source_id=self.SOURCE_SOFTWAREUPDATE,
                        status=UpdateStatus.PENDING,
                    )
                ],
            )

        return UpdateResult(
            success=result.success,
            dry_run=False,
            message=result.message,
            items=[
                UpdateItem(
                    id="macos-applied",
                    title="softwareupdate --install --all executed",
                    source_id=self.SOURCE_SOFTWAREUPDATE,
                    status=UpdateStatus.APPLIED if result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if result.success else [result.stderr or "Apply failed"],
        )

    def apply_streaming(
        self,
        dry_run: bool = True,
    ) -> Generator[str, None, UpdateResult]:
        cmd = ["softwareupdate", "--install", "--all"]
        self.audit.log_action(
            "macos_apply_updates",
            {"dry_run": dry_run, "streaming": True},
        )
        exec_result = yield from self._yield_command_stream(
            cmd,
            dry_run=dry_run,
            validate_cmd=["softwareupdate", "--install"],
        )
        if getattr(exec_result, "metadata", {}).get("rejected"):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=["Validation failed for softwareupdate --install"],
            )
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=exec_result.message,
                items=[
                    UpdateItem(
                        id="macos-apply-dry-run",
                        title="[Dry-run] softwareupdate --install --all",
                        source_id=self.SOURCE_SOFTWAREUPDATE,
                        status=UpdateStatus.PENDING,
                    )
                ],
            )
        return UpdateResult(
            success=exec_result.success,
            dry_run=False,
            message=exec_result.message,
            items=[
                UpdateItem(
                    id="macos-applied",
                    title="softwareupdate --install --all executed",
                    source_id=self.SOURCE_SOFTWAREUPDATE,
                    status=UpdateStatus.APPLIED if exec_result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if exec_result.success else [exec_result.stderr or "Apply failed"],
        )
