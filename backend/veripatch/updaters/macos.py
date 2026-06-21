"""macOS updater using softwareupdate CLI (stubbed)."""

from __future__ import annotations

from veripatch.updaters.base import UpdateItem, Updater, UpdateResult, UpdateStatus


class MacOSUpdater(Updater):
    """macOS update workflow via softwareupdate and App Store APIs."""

    SOURCE_SOFTWAREUPDATE = "softwareupdate"

    def check(self) -> UpdateResult:
        self.audit.log_action("macos_updater_check", {"stub": True})
        if not self._validate(["softwareupdate", "--list"]):
            return UpdateResult(
                success=False,
                dry_run=True,
                message="softwareupdate source validation failed",
                errors=["Official source validation rejected command"],
            )
        return UpdateResult(
            success=True,
            dry_run=True,
            message="macOS update sources validated (stub)",
        )

    def list_updates(self) -> UpdateResult:
        self.audit.log_action("macos_list_updates", {"stub": True})
        if not self._validate(["softwareupdate", "--list"]):
            return UpdateResult(
                success=False,
                dry_run=True,
                message="Cannot list updates: source validation failed",
                errors=["Rejected non-official command"],
            )
        items = [
            UpdateItem(
                id="macos-stub-1",
                title="[Stub] macOS Security Update",
                source_id=self.SOURCE_SOFTWAREUPDATE,
                status=UpdateStatus.AVAILABLE,
                severity="recommended",
                metadata={"stub": True},
            ),
        ]
        return UpdateResult(
            success=True,
            dry_run=True,
            message="Listed macOS updates (stub)",
            items=items,
        )

    def apply(self, dry_run: bool = True) -> UpdateResult:
        self.audit.log_action("macos_apply_updates", {"dry_run": dry_run, "stub": True})
        if not self._validate(["softwareupdate", "--install", "--all"]):
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
                message="Dry-run: would apply macOS updates via softwareupdate",
                items=[
                    UpdateItem(
                        id="macos-stub-1",
                        title="[Dry-run] macOS Security Update",
                        source_id=self.SOURCE_SOFTWAREUPDATE,
                        status=UpdateStatus.PENDING,
                    )
                ],
            )
        raise NotImplementedError(
            "Real macOS update execution is not yet implemented. Use dry_run=True."
        )
