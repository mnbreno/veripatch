"""Structured logging for VeriPatch."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_CONFIGURED = False
LOG_DIR = Path(os.environ.get("VERIPATCH_LOG_DIR", ".veripatch"))


def configure_logging(level: str | None = None) -> logging.Logger:
    """Configure root VeriPatch logger from env or argument."""
    global _CONFIGURED
    logger = logging.getLogger("veripatch")
    if _CONFIGURED:
        return logger

    log_level = (level or os.environ.get("VERIPATCH_LOG", "INFO")).upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / "veripatch.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger


def get_logger(name: str = "veripatch") -> logging.Logger:
    """Return a configured logger."""
    configure_logging()
    return logging.getLogger(name)
