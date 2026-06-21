"""JSON-RPC server for VeriPatch backend IPC."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from veripatch.detection.os_detect import detect_os
from veripatch.ipc.protocol import (
    JsonRpcRequest,
    make_error,
    make_result,
    parse_request_line,
)
from veripatch.privileges.elevation import is_elevated
from veripatch.sources.registry import get_sources_for_os
from veripatch.updaters import get_updater

Handler = Callable[[dict[str, Any] | list[Any] | None], Any]

METHOD_NOT_FOUND = -32601
INVALID_REQUEST = -32600
INTERNAL_ERROR = -32603


class JsonRpcServer:
    """Line-delimited JSON-RPC server over stdin/stdout."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {
            "detect_os": self._handle_detect_os,
            "list_sources": self._handle_list_sources,
            "check_updates": self._handle_check_updates,
            "apply_updates": self._handle_apply_updates,
            "ping": self._handle_ping,
        }

    def _handle_ping(self, _params: dict[str, Any] | list[Any] | None) -> dict[str, str]:
        return {"status": "ok"}

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
        updater = get_updater(info)
        check_result = updater.check()
        list_result = updater.list_updates()
        return {
            "check": check_result.to_dict(),
            "updates": list_result.to_dict(),
        }

    def _handle_apply_updates(self, params: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        dry_run = True
        if isinstance(params, dict):
            dry_run = bool(params.get("dry_run", True))
        info = detect_os()
        updater = get_updater(info)
        result = updater.apply(dry_run=dry_run)
        return result.to_dict()

    def handle_request(self, request: JsonRpcRequest) -> dict[str, Any]:
        handler = self._handlers.get(request.method)
        if handler is None:
            msg = f"Method not found: {request.method}"
            return make_error(request.id, METHOD_NOT_FOUND, msg).to_dict()

        try:
            result = handler(request.params)
            return make_result(request.id, result).to_dict()
        except NotImplementedError as exc:
            return make_error(request.id, INTERNAL_ERROR, str(exc)).to_dict()
        except Exception as exc:  # noqa: BLE001 - surface to IPC client
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
            sys.stdout.write(
                __import__("json").dumps(response_dict, separators=(",", ":")) + "\n"
            )
            sys.stdout.flush()
