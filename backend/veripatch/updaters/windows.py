"""Windows updater using official WUA and WinGet sources."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Generator
from typing import Any

from veripatch.execution.parsers import parse_winget_upgrade
from veripatch.execution.runner import ExecutionResult, _decode_output_bytes
from veripatch.updaters.base import UpdateItem, Updater, UpdateResult, UpdateStatus


def _line_priority(line: str) -> int:
    lowered = line.lower()
    if "falhou com o código" in lowered or "failed with exit code" in lowered:
        return 0
    if "não é possível" in lowered or "nao e possivel" in lowered:
        return 1
    if "falhou" in lowered or "failed" in lowered:
        return 2
    if "error" in lowered or "erro" in lowered:
        return 3
    if "cannot" in lowered or "não podem ser determinados" in lowered:
        return 8
    if "include-unknown" in lowered:
        return 9
    if "não" in lowered or "nao" in lowered:
        return 7
    return 5


def _collect_apply_errors(result: ExecutionResult) -> list[str]:
    errors: list[str] = []
    if result.stderr and result.stderr.strip():
        errors.append(result.stderr.strip())

    ranked: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        priority = _line_priority(stripped)
        if priority <= 3:
            ranked.append((priority, stripped))

    ranked.sort(key=lambda item: item[0])
    for _priority, line in ranked:
        if line not in errors:
            errors.append(line)

    if not errors:
        if result.exit_code is not None:
            errors.append(f"WinGet exited with code {result.exit_code}")
        else:
            errors.append(result.message or "Apply failed")
    return errors[:3]


def _format_apply_error(result: ExecutionResult) -> str:
    return _collect_apply_errors(result)[0]


def _summarize_winget_stdout(stdout: str) -> tuple[int, int]:
    successes = 0
    failures = 0
    for line in stdout.splitlines():
        lowered = line.lower()
        if "instalado com êxito" in lowered or "installed successfully" in lowered:
            successes += 1
        elif "instalador falhou" in lowered or "installer failed" in lowered:
            failures += 1
    return successes, failures


def _cursor_is_running() -> bool:
    if sys.platform != "win32":
        return False
    try:
        completed = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/NH"],
            capture_output=True,
            text=False,
            timeout=10,
            check=False,
        )
    except OSError:
        return False
    output = _decode_output_bytes(completed.stdout or b"")
    return "cursor.exe" in output.lower()


def _apply_hints(stdout: str) -> list[str]:
    hints: list[str] = []
    lowered = stdout.lower()
    if "anysphere.cursor" in lowered and (
        "instalador falhou" in lowered or "installer failed" in lowered
    ):
        hints.append(
            "Close Cursor completely, then run Update All again to finish the Cursor upgrade."
        )
    return hints


def _build_apply_message(result: ExecutionResult) -> str:
    successes, failures = _summarize_winget_stdout(result.stdout)
    if failures == 0:
        if successes > 0:
            return f"{successes} package(s) updated successfully"
        return result.message or "Command completed successfully"
    if successes > 0:
        return f"{successes} package(s) updated, {failures} failed"
    return result.message or "Command failed"


def _build_apply_summary(
    stdout: str,
    *,
    skipped: int = 0,
) -> dict[str, int]:
    updated, failed = _summarize_winget_stdout(stdout)
    return {"updated": updated, "skipped": skipped, "failed": failed}


def _finalize_apply_result(
    exec_result: ExecutionResult,
    *,
    skipped_packages: list[str] | None = None,
    skipped_count: int | None = None,
) -> UpdateResult:
    errors = [] if exec_result.success else _collect_apply_errors(exec_result)
    if not exec_result.success:
        for hint in _apply_hints(exec_result.stdout):
            if hint not in errors:
                errors.append(hint)
    skipped = skipped_count if skipped_count is not None else len(skipped_packages or [])
    message = _build_apply_message(exec_result)
    summary = _build_apply_summary(exec_result.stdout, skipped=skipped)
    if skipped_packages:
        labels = ", ".join(skipped_packages)
        message = f"{message}; skipped {labels}"
        skip_hint = (
            f"Skipped {labels}. Close the app completely, then use "
            "'Update Cursor Later' or Update All again."
        )
        if skip_hint not in errors:
            errors.append(skip_hint)
    success = exec_result.success
    if skipped_packages and exec_result.success:
        success = True
    return UpdateResult(
        success=success,
        dry_run=False,
        message=message,
        summary=summary,
        items=[
            UpdateItem(
                id="winget-applied",
                title="WinGet upgrade executed",
                source_id="winget",
                status=UpdateStatus.APPLIED if success else UpdateStatus.FAILED,
            )
        ],
        errors=errors,
    )


def _winget_list_cmd() -> list[str]:
    return [
        "winget",
        "upgrade",
        "--disable-interactivity",
        "--include-unknown",
    ]


def _winget_apply_cmd() -> list[str]:
    return [
        "winget",
        "upgrade",
        "--all",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--include-unknown",
        "--force",
    ]


CURSOR_PACKAGE_ID = "Anysphere.Cursor"


def get_apply_blockers(items: list[UpdateItem] | None = None) -> dict[str, Any]:
    """Return client-facing apply blockers for Windows."""
    blockers: dict[str, Any] = {}
    if sys.platform != "win32":
        return blockers
    blockers["cursor_running"] = _cursor_is_running()
    blockers["cursor_package_id"] = CURSOR_PACKAGE_ID
    if items:
        blockers["cursor_update_available"] = any(
            item.metadata.get("package_id") == CURSOR_PACKAGE_ID for item in items
        )
    return blockers


def _winget_upgrade_id_cmd(package_id: str) -> list[str]:
    return [
        "winget",
        "upgrade",
        "--id",
        package_id,
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--include-unknown",
        "--force",
    ]


class WindowsUpdater(Updater):
    """Windows update workflow via WUA COM and WinGet."""

    SOURCE_WUA = "windows_update_agent"
    SOURCE_WINGET = "winget"

    def _cursor_running(self) -> bool:
        return _cursor_is_running()

    def _winget_available(self) -> bool:
        return shutil.which("winget") is not None

    def _list_wua_updates(self) -> list[UpdateItem]:
        """Optional WUA COM path when pywin32 is available."""
        try:
            import win32com.client  # type: ignore[import-untyped]
            from win32com import com_error  # type: ignore[import-untyped]
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
        except (com_error, AttributeError, OSError):
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
            cmd = _winget_list_cmd()
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
        cmd = _winget_apply_cmd()
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

        return _finalize_apply_result(result)

    def _list_winget_package_ids(self, skip: set[str]) -> list[str]:
        listed = self.list_updates()
        package_ids: list[str] = []
        for item in listed.items:
            if item.source_id != self.SOURCE_WINGET:
                continue
            package_id = item.metadata.get("package_id")
            if package_id and package_id not in skip:
                package_ids.append(str(package_id))
        return package_ids

    def _apply_selected_packages(
        self,
        package_ids: list[str],
        *,
        dry_run: bool,
    ) -> Generator[str, None, ExecutionResult]:
        combined_stdout: list[str] = []
        exit_code = 0
        success = True

        for package_id in package_ids:
            cmd = _winget_upgrade_id_cmd(package_id)
            yield f"[VeriPatch] Updating {package_id}..."
            exec_result = yield from self._yield_command_stream(
                cmd,
                dry_run=dry_run,
                validate_cmd=["winget", "upgrade", "--id"],
            )
            combined_stdout.append(exec_result.stdout)
            if exec_result.exit_code:
                exit_code = exec_result.exit_code
            if not exec_result.success:
                success = False

        return ExecutionResult(
            success=success,
            dry_run=dry_run,
            command=_winget_upgrade_id_cmd(package_ids[0]) if package_ids else _winget_apply_cmd(),
            exit_code=exit_code,
            stdout="\n".join(part for part in combined_stdout if part),
            message="Command completed successfully" if success else "Command failed",
        )

    def apply_streaming(
        self,
        dry_run: bool = True,
        *,
        skip_package_ids: frozenset[str] | None = None,
        package_ids: frozenset[str] | None = None,
    ) -> Generator[str, None, UpdateResult]:
        skip = set(skip_package_ids or ())
        skipped_labels: list[str] = []
        for package_id in skip:
            if package_id == CURSOR_PACKAGE_ID:
                skipped_labels.append("Cursor")
            else:
                skipped_labels.append(package_id)

        self.audit.log_action(
            "windows_apply_updates",
            {
                "dry_run": dry_run,
                "streaming": True,
                "skip": sorted(skip),
                "package_ids": sorted(package_ids) if package_ids else [],
            },
        )

        if package_ids is not None:
            target_ids = [pid for pid in package_ids if pid not in skip]
            skipped_count = len(package_ids) - len(target_ids)
            if dry_run:
                yield f"[Dry-run] would update: {', '.join(target_ids) or 'none'}"
                return UpdateResult(
                    success=True,
                    dry_run=True,
                    message=f"Dry-run: would update {len(target_ids)} package(s)",
                    summary={"updated": 0, "skipped": skipped_count, "failed": 0},
                    items=[
                        UpdateItem(
                            id="winget-apply-dry-run",
                            title="[Dry-run] WinGet selected upgrades",
                            source_id=self.SOURCE_WINGET,
                            status=UpdateStatus.PENDING,
                        )
                    ],
                )
            if not target_ids:
                yield "[VeriPatch] No packages selected for update."
                return UpdateResult(
                    success=False,
                    dry_run=False,
                    message="No packages selected for update",
                    summary={"updated": 0, "skipped": skipped_count, "failed": 0},
                    errors=["Select at least one package or remove skip rules."],
                    items=[],
                )
            yield f"[VeriPatch] Updating {len(target_ids)} selected package(s)..."
            exec_result = yield from self._apply_selected_packages(
                target_ids,
                dry_run=dry_run,
            )
            return _finalize_apply_result(
                exec_result,
                skipped_packages=skipped_labels or None,
                skipped_count=skipped_count,
            )

        if skip and not dry_run:
            package_ids_to_apply = self._list_winget_package_ids(skip)
            if package_ids_to_apply:
                if CURSOR_PACKAGE_ID in skip:
                    yield (
                        "[VeriPatch] Skipping Cursor and updating other packages."
                    )
                exec_result = yield from self._apply_selected_packages(
                    package_ids_to_apply,
                    dry_run=dry_run,
                )
                return _finalize_apply_result(
                    exec_result,
                    skipped_packages=skipped_labels or None,
                    skipped_count=len(skip),
                )
            if CURSOR_PACKAGE_ID in skip:
                yield "[VeriPatch] Only Cursor has updates and it was skipped."
                return UpdateResult(
                    success=False,
                    dry_run=False,
                    message="Cursor update skipped",
                    summary={"updated": 0, "skipped": 1, "failed": 0},
                    errors=[
                        "Close Cursor completely, then use 'Update Cursor Later'."
                    ],
                    items=[],
                )

        cmd = _winget_apply_cmd()
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
        return _finalize_apply_result(exec_result)
