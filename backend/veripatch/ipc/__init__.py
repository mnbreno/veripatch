"""IPC module for VeriPatch."""

from veripatch.ipc.protocol import JsonRpcRequest, JsonRpcResponse, make_error, make_result
from veripatch.ipc.server import JsonRpcServer

__all__ = ["JsonRpcRequest", "JsonRpcResponse", "JsonRpcServer", "make_error", "make_result"]
