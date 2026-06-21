"""Linux updater using distro-native package managers (stubbed)."""

from __future__ import annotations

from veripatch.detection.os_detect import PackageManager
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
    PackageManager.APT: ["apt", "upgrade"],
    PackageManager.DNF: ["dnf", "upgrade"],
    PackageManager.PACMAN: ["pacman", "-Su"],
    PackageManager.ZYPPER: ["zypper", "update"],
}


class LinuxUpdater(Updater):
    """Linux update workflow via distro-native package managers."""

    def _package_manager(self) -> PackageManager:
        pm = self.os_info.package_manager or PackageManager.UNKNOWN
        return pm

    def _source_id(self) -> str:
        return _PM_SOURCE_ID.get(self._package_manager(), "unknown")

    def check(self) -> UpdateResult:
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=True,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )
        cmd = _PM_CHECK_CMD[pm]
        self.audit.log_action("linux_updater_check", {"package_manager": pm.value, "stub": True})
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=True,
                message=f"{pm.value} source validation failed",
                errors=["Official source validation rejected command"],
            )
        return UpdateResult(
            success=True,
            dry_run=True,
            message=f"Linux update sources validated via {pm.value} (stub)",
        )

    def list_updates(self) -> UpdateResult:
        pm = self._package_manager()
        if pm == PackageManager.UNKNOWN:
            return UpdateResult(
                success=False,
                dry_run=True,
                message="Unknown Linux package manager",
                errors=["Could not determine distro-native package manager"],
            )
        cmd = _PM_CHECK_CMD[pm]
        if not self._validate(cmd):
            return UpdateResult(
                success=False,
                dry_run=True,
                message="Cannot list updates: source validation failed",
                errors=["Rejected non-official command"],
            )
        items = [
            UpdateItem(
                id=f"linux-stub-{pm.value}",
                title=f"[Stub] {pm.value.upper()} package updates available",
                source_id=self._source_id(),
                status=UpdateStatus.AVAILABLE,
                metadata={"stub": True, "package_manager": pm.value},
            ),
        ]
        return UpdateResult(
            success=True,
            dry_run=True,
            message=f"Listed Linux updates via {pm.value} (stub)",
            items=items,
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
            {"package_manager": pm.value, "dry_run": dry_run, "stub": True},
        )
        if not self._validate(cmd):
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
                message=f"Dry-run: would apply updates via {pm.value}",
                items=[
                    UpdateItem(
                        id=f"linux-stub-{pm.value}",
                        title=f"[Dry-run] {pm.value.upper()} system upgrade",
                        source_id=self._source_id(),
                        status=UpdateStatus.PENDING,
                    )
                ],
            )
        raise NotImplementedError(
            "Real Linux update execution is not yet implemented. Use dry_run=True."
        )
