"""Tests for runtime configuration helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

from veripatch.config import DEFAULT_APPLY_TIMEOUT_SECONDS, apply_command_timeout


def test_apply_command_timeout_default() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert apply_command_timeout() == DEFAULT_APPLY_TIMEOUT_SECONDS


def test_apply_command_timeout_from_env() -> None:
    with patch.dict(os.environ, {"VERIPATCH_APPLY_TIMEOUT": "900"}):
        assert apply_command_timeout() == 900


def test_apply_command_timeout_minimum() -> None:
    with patch.dict(os.environ, {"VERIPATCH_APPLY_TIMEOUT": "10"}):
        assert apply_command_timeout() == 60
