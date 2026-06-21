"""Official source registry and validation."""

from veripatch.sources.registry import (
    OfficialSource,
    SourceKind,
    get_all_sources,
    get_sources_for_os,
)
from veripatch.sources.validator import SourceValidator, ValidationOutcome, ValidationResult

__all__ = [
    "OfficialSource",
    "SourceKind",
    "SourceValidator",
    "ValidationOutcome",
    "ValidationResult",
    "get_all_sources",
    "get_sources_for_os",
]
