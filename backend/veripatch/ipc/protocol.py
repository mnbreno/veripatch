"""JSON-RPC protocol helpers for VeriPatch IPC."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class JsonRpcRequest:
    jsonrpc: str
    method: str
    params: dict[str, Any] | list[Any] | None
    id: int | str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JsonRpcRequest:
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
        )


@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    result: Any = None
    error: dict[str, Any] | None = None
    id: int | str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            payload["error"] = self.error
        else:
            payload["result"] = self.result
        return payload

    def to_line(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


def parse_request_line(line: str) -> JsonRpcRequest:
    data = json.loads(line)
    if not isinstance(data, dict) or "method" not in data:
        raise ValueError("Invalid JSON-RPC request")
    return JsonRpcRequest.from_dict(data)


def make_error(id_: int | str | None, code: int, message: str) -> JsonRpcResponse:
    return JsonRpcResponse(
        id=id_,
        error={"code": code, "message": message},
    )


def make_result(id_: int | str | None, result: Any) -> JsonRpcResponse:
    return JsonRpcResponse(id=id_, result=result)
