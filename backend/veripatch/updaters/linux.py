"""Linux updater using distro-native package managers."""

from __future__ import annotations

from collections.abc import Generator

from veripatch.detection.os_detect import PackageManager
from veripatch.execution.parsers import (
    parse_apt_upgradable,
    parse_dnf_check_update,
    parse_pacman_qu,
    parse_zypper_list_updates,
)
from veripatch.updaters.base import UpdateItem, Updater, UpdateResult, UpdateStatus

_PM_SOURCE_ID: dict[PackageManager, str] = {
    PackageManager.APT: "apt",
    PackageManager.DNF: "dnf",
    PackageManager.PACMAN: "pacman",
    PackageManager.ZYPPER: "zypper",
}

_PM_CHECK_CMD: dict[PackageManager, list[str]] = {
    PackageManager.APT: ["apt", "list", "--upgradable"],
    PackageManager.DNF: ["dnf", "check-update"],
    PackageManager.PACMAN: ["pacman", "-Qu"],
    PackageManager.ZYPPER: ["zypper", "list-updates"],
}

_PM_APPLY_CMD: dict[PackageManager, list[str]] = {
    PackageManager.APT: ["apt", "upgrade", "-y"],
    PackageManager.DNF: ["dnf", "upgrade", "-y"],
    PackageManager.PACMAN: ["pacman", "-Su", "--noconfirm"],
    PackageManager.ZYPPER: ["zypper", "update", "-y"],
}

_PM_APPLY_VALIDATE: dict[PackageManager, list[str]] = {
    PackageManager.APT: ["apt", "upgrade"],
    PackageManager.DNF: ["dnf", "upgrade"],
    PackageManager.PACMAN: ["pacman", "-Su"],
    PackageManager.ZYPPER: ["zypper", "update"],
}

_PM_PARSER = {
    PackageManager.APT: parse_apt_upgradable,
    PackageManager.DNF: parse_dnf_check_update,
    PackageManager.PACMAN: parse_pacman_qu,
    PackageManager.ZYPPER: parse_zypper_list_updates,
}


class LinuxUpdater(Updater):
    """Linux update workflow via distro-native package managers."""

    def _package_manager(self) -> PackageManager:
        return self.os_info.package_manager or PackageManager.UNKNOWN

    def _source_id(self) -> str:
        return _PM_SOURCE_ID.get(self._package_manager(), "unknown")

    def check(self) -> UpdateResult:
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )
        cmd = _PM_CHECK_CMD[pm]
        self.audit.log_action("linux_updater_check", {"package_manager": pm.value})
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message=f"{pm.value} source validation failed",
                errors=["Official source validation rejected command"],
            )
        result = self.runner.run(cmd)
        return UpdateResult(
            success=result.success or result.dry_run,
            dry_run=result.dry_run,
            message=result.message,
            errors=[] if result.success else [result.stderr or result.message],
        )

    def list_updates(self) -> UpdateResult:
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )
        cmd = _PM_CHECK_CMD[pm]
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=self.dry_run,
                message="Cannot list updates: source validation failed",
                errors=["Rejected non-official command"],
            )
        result = self.runner.run(cmd)
        source_id = self._source_id()
        if result.dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=result.message,
                items=[
                    UpdateItem(
                        id=f"linux-dry-run-{pm.value}",
                        title=f"[Dry-run] {pm.value.upper()} updates would be listed",
                        source_id=source_id,
                        status=UpdateStatus.AVAILABLE,
                    )
                ],
            )
        parser = _PM_PARSER[pm]
        items = parser(result.stdout, source_id)
        return UpdateResult(
            success=result.success,
            dry_run=False,
            message=f"Listed {len(items)} Linux update(s) via {pm.value}",
            items=items,
            errors=[] if result.success else [result.stderr or result.message],
        )

    def apply(self, dry_run: bool = True) -> UpdateResult:
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )
        cmd = _PM_APPLY_CMD[pm]
        self.audit.log_action(
            "linux_apply_updates",
            {"package_manager": pm.value, "dry_run": dry_run},
        )
        if not self._validate(_PM_APPLY_VALIDATE[pm]):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=[f"Validation failed for {pm.value} upgrade command"],
            )

        result = self.runner.run(cmd, dry_run=dry_run)
        source_id = self._source_id()
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=result.message,
                items=[
                    UpdateItem(
                        id=f"linux-apply-dry-run-{pm.value}",
                        title=f"[Dry-run] {pm.value.upper()} system upgrade",
                        source_id=source_id,
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
                    id=f"linux-applied-{pm.value}",
                    title=f"{pm.value.upper()} upgrade executed",
                    source_id=source_id,
                    status=UpdateStatus.APPLIED if result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if result.success else [result.stderr or "Apply failed"],
        )

    def apply_streaming(
        self,
        dry_run: bool = True,
        *,
        skip_package_ids: frozenset[str] | None = None,
        package_ids: frozenset[str] | None = None,
    ) -> Generator[str, None, UpdateResult]:
        _ = skip_package_ids
        _ = package_ids
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )

        cmd = _PM_APPLY_CMD[pm]
        self.audit.log_action(
            "linux_apply_updates",
            {"package_manager": pm.value, "dry_run": dry_run, "streaming": True},
        )
        source_id = self._source_id()
        exec_result = yield from self._yield_command_stream(
            cmd,
            dry_run=dry_run,
            validate_cmd=_PM_APPLY_VALIDATE[pm],
        )
        if getattr(exec_result, "metadata", {}).get("rejected"):
            return UpdateResult(
                success=False,
                dry_run=dry_run,
                message="Apply rejected: command not from official source",
                errors=[f"Validation failed for {pm.value} upgrade command"],
            )
        if dry_run:
            return UpdateResult(
                success=True,
                dry_run=True,
                message=exec_result.message,
                items=[
                    UpdateItem(
                        id=f"linux-apply-dry-run-{pm.value}",
                        title=f"[Dry-run] {pm.value.upper()} system upgrade",
                        source_id=source_id,
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
                    id=f"linux-applied-{pm.value}",
                    title=f"{pm.value.upper()} upgrade executed",
                    source_id=source_id,
                    status=UpdateStatus.APPLIED if exec_result.success else UpdateStatus.FAILED,
                )
            ],
            errors=[] if exec_result.success else [exec_result.stderr or "Apply failed"],
        )
