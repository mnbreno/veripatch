"""Console output helpers for cross-platform CLI."""

from __future__ import annotations

import sys


def configure_console() -> None:
    """Prefer UTF-8 stdout/stderr when the platform supports reconfiguration."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def console_text(text: str) -> str:
    """Return text safe for the active stdout encoding."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def console_print(*args: object, **kwargs: object) -> None:
    """Print with graceful fallback when emoji or other Unicode cannot be encoded."""
    end = str(kwargs.pop("end", "\n") if isinstance(kwargs.get("end"), str) else "\n")
    sep = str(kwargs.pop("sep", " ") if isinstance(kwargs.get("sep"), str) else " ")
    file = kwargs.pop("file", sys.stdout)
    flush = kwargs.pop("flush", False)
    text = console_text(sep.join(str(arg) for arg in args) + end)
    try:
        file.write(text)  # type: ignore[attr-defined,union-attr]
    except UnicodeEncodeError:
        encoding = getattr(file, "encoding", None) or "utf-8"
        file.buffer.write(text.encode(encoding, errors="replace"))  # type: ignore[attr-defined,union-attr]
    if flush:
        flush_fn = getattr(file, "flush", None)
        if flush_fn is not None:
            flush_fn()
