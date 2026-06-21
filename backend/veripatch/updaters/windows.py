"""Windows updater using official WUA and WinGet sources."""

from __future__ import annotations

import shutil
from collections.abc import Generator

from veripatch.execution.parsers import parse_winget_upgrade
from veripatch.updaters.base import UpdateItem, Updater, UpdateResult, UpdateStatus


class WindowsUpdater(Updater):
    """Windows update workflow via WUA COM and WinGet."""

    SOURCE_WUA = "windows_update_agent"
    SOURCE_WINGET = "winget"

    def _winget_available(self) -> bool:
        return shutil.which("winget") is not None

    def _list_wua_updates(self) -> list[UpdateItem]:
        """Optional WUA COM path when pywin32 is available."""
        try:
            import win32com.client  # type: ignore[import-untyped]
        except ImportError:
            return []

        items: list[UpdateItem] = []
        try:
            session = win32com.client.Dispatch("Microsoft.Update.Session")
            searcher = session.CreateUpdateSearcher()
            result = searcher.Search("IsInstalled=0")
            for i in range(result.Updates.Count):
                update = result.Updates.Item(i)
                title = str(update.Title)
                update_id = str(update.Identity.UpdateID)
                items.append(
                    UpdateItem(
                        id=f"wua-{update_id[:16]}",
                        title=title,
                        source_id=self.SOURCE_WUA,
                        status=UpdateStatus.AVAILABLE,
                        severity="important",
                        metadata={"update_id": update_id},
                    )
                )
        except Exception:  # noqa: BLE001 - COM may be unavailable in CI
            return []
        return items

    def check(self) -> UpdateResult:
        self.audit.log_action("windows_updater_check", {})
        if self._winget_available():
            return UpdateResult(
                success=True,
                dry_run=self.dry_run,
                message="WinGet is available",
            )
        wua_items = self._list_wua_updates()
        if wua_items:
            return UpdateResult(
                success=True,
                dry_run=self.dry_run,
                message="Windows Update Agent available",
            )
        return UpdateResult(
            success=False,
            dry_run=self.dry_run,
            message="Neither winget nor WUA COM available",
            errors=["Install WinGet or ensure Windows Update Agent is accessible"],
        )

    def list_updates(self) -> UpdateResult:
        self.audit.log_action("windows_list_updates", {})
        items: list[UpdateItem] = []

        if self._winget_available():
            cmd = ["winget", "upgrade", "--disable-interactivity"]
            if self._validate(cmd):
                result = self.runner.run(cmd)
                if result.dry_run:
                    items.append(
                        UpdateItem(
                            id="winget-dry-run",
                            title="[Dry-run] WinGet upgrades would be listed",
                            source_id=self.SOURCE_WINGET,
                            status=UpdateStatus.AVAILABLE,
                        )
                    )
                elif result.success:
                    items.extend(parse_winget_upgrade(result.stdout, self.SOURCE_WINGET))

        items.extend(self._list_wua_updates())

        return UpdateResult(
            success=True,
            dry_run=self.dry_run,
            message=f"Listed {len(items)} Windows update(s)",
            items=items,
        )

    def apply(self, dry_run: bool = True) -> UpdateResult:
        self.audit.log_action("windows_apply_updates", {"dry_run": dry_run})
        cmd = [
            "winget",
            "upgrade",
            "--all",
            "--disable-interactivity",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        if not self._validate(["winget", "upgrade", "--all"]):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=["Validation failed for winget upgrade"],
            )

        result = self.runner.run(cmd, dry_run=dry_run)
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=result.message,
                items=[
                    UpdateItem(
                        id="winget-apply-dry-run",
                        title="[Dry-run] WinGet upgrade --all",
                        source_id=self.SOURCE_WINGET,
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
                    id="winget-applied",
                    title="WinGet upgrade --all executed",
                    source_id=self.SOURCE_WINGET,
                    status=UpdateStatus.APPLIED if result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if result.success else [result.stderr or "Apply failed"],
        )

    def apply_streaming(
        self,
        dry_run: bool = True,
    ) -> Generator[str, None, UpdateResult]:
        cmd = [
            "winget",
            "upgrade",
            "--all",
            "--disable-interactivity",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        self.audit.log_action("windows_apply_updates", {"dry_run": dry_run, "streaming": True})
        exec_result = yield from self._yield_command_stream(
            cmd,
            dry_run=dry_run,
            validate_cmd=["winget", "upgrade", "--all"],
        )

        if getattr(exec_result, "metadata", {}).get("rejected"):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=["Validation failed for winget upgrade"],
            )
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=exec_result.message,
                items=[
                    UpdateItem(
                        id="winget-apply-dry-run",
                        title="[Dry-run] WinGet upgrade --all",
                        source_id=self.SOURCE_WINGET,
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
                    id="winget-applied",
                    title="WinGet upgrade --all executed",
                    source_id=self.SOURCE_WINGET,
                    status=UpdateStatus.APPLIED if exec_result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if exec_result.success else [exec_result.stderr or "Apply failed"],
        )
