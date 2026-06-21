"""IPC module for VeriPatch."""

from veripatch.ipc.client import JsonRpcClient, SocketJsonRpcClient, get_client
from veripatch.ipc.protocol import JsonRpcRequest, JsonRpcResponse, make_error, make_result
from veripatch.ipc.server import JsonRpcServer
from veripatch.ipc.socket_server import SocketJsonRpcServer

__all__ = [
    "JsonRpcClient",
    "SocketJsonRpcClient",
    "SocketJsonRpcServer",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcServer",
    "get_client",
    "make_error",
    "make_result",
]
