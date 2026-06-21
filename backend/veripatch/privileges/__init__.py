"""Privilege elevation utilities."""

from veripatch.privileges.audit import AuditLogger
from veripatch.privileges.elevation import is_elevated, request_elevation

__all__ = ["AuditLogger", "is_elevated", "request_elevation"]
