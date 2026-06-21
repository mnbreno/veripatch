"""Tests for observability and diagnostics."""

from __future__ import annotations

from veripatch.observability.diagnostics import get_capabilities, get_diagnostics


def test_get_capabilities_includes_version() -> None:
    caps = get_capabilities()
    assert "veripatch" in caps
    assert "python" in caps


def test_get_diagnostics_structure() -> None:
    diag = get_diagnostics()
    assert "version" in diag
    assert "os" in diag
    assert "elevated" in diag
    assert "capabilities" in diag
    assert "official_sources" in diag
    assert isinstance(diag["recent_audit_entries"], list)
