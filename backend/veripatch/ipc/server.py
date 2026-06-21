"""JSON-RPC server for VeriPatch backend IPC."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from typing import Any

from veripatch.config import APPLY_CONFIRMATION_TOKEN
from veripatch.detection.os_detect import detect_os
from veripatch.ipc.protocol import (
    JsonRpcRequest,
    make_error,
    make_result,
    parse_request_line,
)
from veripatch.observability.diagnostics import get_diagnostics
from veripatch.observability.logging_config import get_logger
from veripatch.privileges.audit import AuditLogger
from veripatch.privileges.elevation import is_elevated, request_elevation
from veripatch.sources.registry import get_sources_for_os
from veripatch.updaters import get_updater

Handler = Callable[[dict[str, Any] | list[Any] | None], Any]

METHOD_NOT_FOUND = -32601
INVALID_REQUEST = -32600
INTERNAL_ERROR = -32603


def _env_dry_run() -> bool:
    return os.environ.get("VERIPATCH_DRY_RUN", "").lower() in ("1", "true", "yes")


INVALID_PARAMS = -32602


class JsonRpcServer:
    """Line-delimited JSON-RPC server over stdin/stdout."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.audit = AuditLogger()
        self.log = get_logger("veripatch.ipc")
        self.request_count = 0
        self._shutdown_requested = False
        self._handlers: dict[str, Handler] = {
            "detect_os": self._handle_detect_os,
            "list_sources": self._handle_list_sources,
            "check_updates": self._handle_check_updates,
            "apply_updates": self._handle_apply_updates,
            "diagnostics": self._handle_diagnostics,
            "ping": self._handle_ping,
            "shutdown": self._handle_shutdown,
        }

    def _handle_ping(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, str]:
        return {"status": "ok"}

    def _handle_shutdown(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        self._shutdown_requested = True
        return {"status": "shutting_down", "requests_served": self.request_count + 1}

    def _handle_detect_os(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        info = detect_os()
        return {
            "os": info.to_dict(),
            "elevated": is_elevated(),
        }

    def _handle_list_sources(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        info = detect_os()
        sources = get_sources_for_os(info.os_type, info.package_manager)
        return {
            "sources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "kind": s.kind.value,
                    "executable": s.executable,
                    "description": s.description,
                }
                for s in sources
            ]
        }

    def _handle_check_updates(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        info = detect_os()
        updater = get_updater(info, audit_logger=self.audit, dry_run=_env_dry_run())
        check_result = updater.check()
        list_result = updater.list_updates()
        return {
            "check": check_result.to_dict(),
            "updates": list_result.to_dict(),
        }

    def _handle_diagnostics(self, params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        limit = 20
        if isinstance(params, dict) and "audit_limit" in params:
            limit = int(params["audit_limit"])
        return get_diagnostics(
            self.audit,
            audit_limit=limit,
            session={"requests_served": self.request_count},
        )

    def _handle_apply_updates(self, params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        dry_run = True
        confirm = False
        confirm_token = ""
        if isinstance(params, dict):
            dry_run = bool(params.get("dry_run", True))
            confirm = bool(params.get("confirm", False))
            confirm_token = str(params.get("confirm_token", ""))

        if not dry_run:
            if not confirm or confirm_token != APPLY_CONFIRMATION_TOKEN:
                self.audit.log_action("apply_rejected", {"reason": "missing_confirmation"})
                return {
                    "success": False,
                    "dry_run": False,
                    "message": (
                        "Real apply requires confirm=true and "
                        f"confirm_token='{APPLY_CONFIRMATION_TOKEN}'"
                    ),
                    "errors": ["Confirmation token required for non-dry-run apply"],
                    "items": [],
                }
            if not is_elevated():
                request_elevation(audit_logger=self.audit)
                self.audit.log_privilege_check(required=True, granted=False)
                return {
                    "success": False,
                    "dry_run": False,
                    "message": "Elevation required. Re-run VeriPatch as administrator/root.",
                    "errors": ["Insufficient privileges for apply"],
                    "items": [],
                }

        info = detect_os()
        updater = get_updater(info, audit_logger=self.audit, dry_run=_env_dry_run())
        result = updater.apply(dry_run=dry_run)
        return result.to_dict()

    def handle_request(self, request: JsonRpcRequest) -> dict[str, Any]:
        if self.debug:
            self.log.debug("RPC request: %s", request.method)

        handler = self._handlers.get(request.method)
        if handler is None:
            msg = f"Method not found: {request.method}"
            return make_error(request.id, METHOD_NOT_FOUND, msg).to_dict()

        try:
            result = handler(request.params)
            if self.debug:
                self.log.debug("RPC response for %s: %s", request.method, result)
            return make_result(request.id, result).to_dict()
        except NotImplementedError as exc:
            return make_error(request.id, INTERNAL_ERROR, str(exc)).to_dict()
        except Exception as exc:  # noqa: BLE001 - surface to IPC client
            self.log.exception("RPC error in %s", request.method)
            return make_error(request.id, INTERNAL_ERROR, str(exc)).to_dict()

    def serve_forever(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = parse_request_line(line)
            except (ValueError, KeyError) as exc:
                response = make_error(None, INVALID_REQUEST, str(exc))
                sys.stdout.write(response.to_line() + "\n")
                sys.stdout.flush()
                continue

            response_dict = self.handle_request(request)
            sys.stdout.write(json.dumps(response_dict, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            self.request_count += 1
            if self._shutdown_requested:
                break
