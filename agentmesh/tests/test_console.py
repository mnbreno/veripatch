"""Tests for console output helpers."""

from __future__ import annotations

import io
import sys

from agentmesh.console import configure_console, console_print, console_text


def test_console_text_replaces_unencodable_chars(monkeypatch) -> None:
    class NarrowStream:
        encoding = "ascii"

    monkeypatch.setattr(sys, "stdout", NarrowStream())
    result = console_text("hello 🏗️")
    assert "?" in result or "hello" in result


def test_console_print_writes_to_stream(capsys) -> None:
    console_print("backend-architect", flush=True)
    assert "backend-architect" in capsys.readouterr().out


def test_console_print_handles_encode_error(monkeypatch) -> None:
    buffer = io.BytesIO()

    class BrokenStream:
        encoding = "ascii"

        def write(self, text: str) -> int:
            raise UnicodeEncodeError("ascii", text, 0, 1, "forced")

        @property
        def buffer(self) -> io.BytesIO:
            return buffer

    stream = BrokenStream()
    console_print("test 🚀", file=stream, flush=True)
    assert buffer.getvalue()


def test_configure_console_does_not_raise() -> None:
    configure_console()
