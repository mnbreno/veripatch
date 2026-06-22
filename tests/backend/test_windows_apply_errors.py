"""Tests for Windows apply error reporting."""

from __future__ import annotations

from unittest.mock import patch

from veripatch.detection.os_detect import OSInfo, OSType
from veripatch.execution.runner import ExecutionResult
from veripatch.privileges.audit import AuditLogger
from veripatch.updaters.base import UpdateItem, UpdateStatus
from veripatch.updaters.windows import (
    CURSOR_PACKAGE_ID,
    WindowsUpdater,
    _apply_hints,
    _build_apply_message,
    _collect_apply_errors,
    _format_apply_error,
    _summarize_winget_stdout,
)


def test_collect_apply_errors_prefers_installer_failure_over_warning() -> None:
    result = ExecutionResult(
        success=False,
        dry_run=False,
        command=["winget", "upgrade", "--all"],
        exit_code=1,
        stdout=(
            "Não é possível remover o pacote Portátil, pois ele foi modificado; "
            "para substituir essa verificação, use --force\n"
            "O instalador falhou com o código de saída: 1\n"
            "12 pacotes têm números de versão que não podem ser determinados. "
            "Use --include-unknown para ver todos os resultados.\n"
        ),
    )

    errors = _collect_apply_errors(result)

    assert errors[0] == "O instalador falhou com o código de saída: 1"
    assert any("Não é possível remover" in line for line in errors)
    assert not any("12 pacotes" in line for line in errors)


def test_format_apply_error_returns_primary_failure() -> None:
    result = ExecutionResult(
        success=False,
        dry_run=False,
        command=["winget", "upgrade", "--all"],
        exit_code=1,
        stdout="O instalador falhou com o código de saída: 1\n",
    )

    assert _format_apply_error(result) == "O instalador falhou com o código de saída: 1"


def test_summarize_winget_stdout_counts_success_and_failure() -> None:
    stdout = (
        "Instalado com êxito\n"
        "O instalador falhou com o código de saída: 1\n"
    )
    assert _summarize_winget_stdout(stdout) == (1, 1)


def test_build_apply_message_reports_partial_success() -> None:
    result = ExecutionResult(
        success=False,
        dry_run=False,
        command=["winget", "upgrade", "--all"],
        exit_code=1,
        stdout="Instalado com êxito\nO instalador falhou com o código de saída: 1\n",
    )
    assert _build_apply_message(result) == "1 package(s) updated, 1 failed"


def test_apply_hints_suggest_closing_cursor() -> None:
    stdout = (
        "(2/2) Encontrado Cursor [Anysphere.Cursor] Versão 3.8.11\n"
        "O instalador falhou com o código de saída: 1\n"
    )
    hints = _apply_hints(stdout)
    assert len(hints) == 1
    assert "Close Cursor" in hints[0]


def test_apply_streaming_skips_cursor_when_requested(tmp_path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    info = OSInfo(os_type=OSType.WINDOWS, version="10", release="10", architecture="AMD64")
    updater = WindowsUpdater(info, audit_logger=audit, dry_run=False)

    readest_item = UpdateItem(
        id="winget-chrox.Readest",
        title="Readest",
        source_id=WindowsUpdater.SOURCE_WINGET,
        status=UpdateStatus.AVAILABLE,
        metadata={"package_id": "chrox.Readest"},
    )
    cursor_item = UpdateItem(
        id=f"winget-{CURSOR_PACKAGE_ID}",
        title="Cursor (User)",
        source_id=WindowsUpdater.SOURCE_WINGET,
        status=UpdateStatus.AVAILABLE,
        metadata={"package_id": CURSOR_PACKAGE_ID},
    )

    def fake_stream(command, dry_run=False, validate_cmd=None):
        assert command[:4] == ["winget", "upgrade", "--id", "chrox.Readest"]

        def generator():
            yield "Instalado com êxito"
            return ExecutionResult(
                success=True,
                dry_run=False,
                command=command,
                exit_code=0,
                stdout="Instalado com êxito\n",
            )

        return generator()

    with patch.object(
        updater,
        "list_updates",
        return_value=type(
            "Listed",
            (),
            {"items": [readest_item, cursor_item]},
        )(),
    ):
        with patch.object(updater, "_yield_command_stream", side_effect=fake_stream):
            stream = updater.apply_streaming(
                dry_run=False,
                skip_package_ids=frozenset({CURSOR_PACKAGE_ID}),
            )
            lines = []
            try:
                while True:
                    lines.append(next(stream))
            except StopIteration as exc:
                result = exc.value

    assert any("Skipping Cursor" in line for line in lines)
    assert result.success is True
    assert result.summary == {"updated": 1, "skipped": 1, "failed": 0}


def test_apply_streaming_selected_package_ids(tmp_path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    info = OSInfo(os_type=OSType.WINDOWS, version="10", release="10", architecture="AMD64")
    updater = WindowsUpdater(info, audit_logger=audit, dry_run=False)

    def fake_stream(command, dry_run=False, validate_cmd=None):
        assert command[:4] == ["winget", "upgrade", "--id", "chrox.Readest"]

        def generator():
            yield "Instalado com êxito"
            return ExecutionResult(
                success=True,
                dry_run=False,
                command=command,
                exit_code=0,
                stdout="Instalado com êxito\n",
            )

        return generator()

    with patch.object(updater, "_yield_command_stream", side_effect=fake_stream):
        stream = updater.apply_streaming(
            dry_run=False,
            package_ids=frozenset({"chrox.Readest"}),
        )
        try:
            while True:
                next(stream)
        except StopIteration as exc:
            result = exc.value

    assert result.success is True
    assert result.summary == {"updated": 1, "skipped": 0, "failed": 0}


def test_apply_streaming_skip_only_non_cursor_package(tmp_path) -> None:
    audit = AuditLogger(log_path=tmp_path / "audit.log")
    info = OSInfo(os_type=OSType.WINDOWS, version="10", release="10", architecture="AMD64")
    updater = WindowsUpdater(info, audit_logger=audit, dry_run=False)

    firefox_item = UpdateItem(
        id="winget-Mozilla.Firefox",
        title="Firefox",
        source_id=WindowsUpdater.SOURCE_WINGET,
        status=UpdateStatus.AVAILABLE,
        metadata={"package_id": "Mozilla.Firefox"},
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("winget upgrade --all should not run when all packages are skipped")

    with patch.object(
        updater,
        "list_updates",
        return_value=type("Listed", (), {"items": [firefox_item]})(),
    ):
        with patch.object(updater, "_yield_command_stream", side_effect=fail_if_called):
            stream = updater.apply_streaming(
                dry_run=False,
                skip_package_ids=frozenset({"Mozilla.Firefox"}),
            )
            lines = []
            try:
                while True:
                    lines.append(next(stream))
            except StopIteration as exc:
                result = exc.value

    assert any("No packages left to update" in line for line in lines)
    assert result.success is True
    assert result.summary == {"updated": 0, "skipped": 1, "failed": 0}
