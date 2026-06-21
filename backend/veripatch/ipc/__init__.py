"""IPC module for VeriPatch."""

from veripatch.ipc.client import JsonRpcClient
from veripatch.ipc.protocol import JsonRpcRequest, JsonRpcResponse, make_error, make_result
from veripatch.ipc.server import JsonRpcServer

__all__ = [
    "JsonRpcClient",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcServer",
    "make_error",
    "make_result",
]
