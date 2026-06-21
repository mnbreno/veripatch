"""Tests for JSON-RPC protocol helpers."""

from __future__ import annotations

import json

import pytest

from veripatch.ipc.protocol import (
    JsonRpcRequest,
    JsonRpcResponse,
    make_error,
    make_result,
    parse_request_line,
)


class TestJsonRpcRequest:
    def test_from_dict_full(self) -> None:
        req = JsonRpcRequest.from_dict(
            {"jsonrpc": "2.0", "method": "ping", "params": {}, "id": 1}
        )
        assert req.jsonrpc == "2.0"
        assert req.method == "ping"
        assert req.params == {}
        assert req.id == 1

    def test_from_dict_minimal(self) -> None:
        req = JsonRpcRequest.from_dict({"method": "ping"})
        assert req.jsonrpc == "2.0"
        assert req.method == "ping"
        assert req.params is None
        assert req.id is None

    def test_from_dict_with_list_params(self) -> None:
        req = JsonRpcRequest.from_dict(
            {"method": "some_method", "params": [1, 2, 3]}
        )
        assert req.params == [1, 2, 3]


class TestJsonRpcResponse:
    def test_to_dict_with_result(self) -> None:
        resp = JsonRpcResponse(id=1, result={"status": "ok"})
        data = resp.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["result"] == {"status": "ok"}
        assert "error" not in data

    def test_to_dict_with_error(self) -> None:
        resp = JsonRpcResponse(id=1, error={"code": -32601, "message": "not found"})
        data = resp.to_dict()
        assert data["error"]["code"] == -32601
        assert "result" not in data

    def test_to_dict_with_null_id(self) -> None:
        resp = JsonRpcResponse(id=None, error={"code": -32600, "message": "bad"})
        data = resp.to_dict()
        assert data["id"] is None

    def test_to_line_result(self) -> None:
        resp = JsonRpcResponse(id=1, result="ok")
        line = resp.to_line()
        parsed = json.loads(line)
        assert parsed["result"] == "ok"

    def test_to_line_error(self) -> None:
        resp = JsonRpcResponse(id=1, error={"code": -32601, "message": "bad"})
        line = resp.to_line()
        parsed = json.loads(line)
        assert parsed["error"]["code"] == -32601

    def test_to_line_compact(self) -> None:
        """Verify separators produce compact JSON (no spaces)."""
        resp = JsonRpcResponse(id=1, result="ok")
        line = resp.to_line()
        assert " " not in line


class TestParseRequestLine:
    def test_valid_request(self) -> None:
        req = parse_request_line('{"method":"ping","id":1}')
        assert req.method == "ping"
        assert req.id == 1

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            parse_request_line("not json")

    def test_missing_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            parse_request_line('{"jsonrpc":"2.0"}')

    def test_not_a_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            parse_request_line('["list"]')


class TestHelpers:
    def test_make_error(self) -> None:
        resp = make_error(1, -32601, "Method not found")
        assert resp.id == 1
        assert resp.error == {"code": -32601, "message": "Method not found"}
        assert resp.result is None

    def test_make_error_null_id(self) -> None:
        resp = make_error(None, -32600, "Bad")
        assert resp.id is None
        assert resp.error["code"] == -32600

    def test_make_result(self) -> None:
        resp = make_result(1, {"done": True})
        assert resp.id == 1
        assert resp.result == {"done": True}
        assert resp.error is None

    def test_make_result_none(self) -> None:
        resp = make_result(1, None)
        assert resp.result is None
