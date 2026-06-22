"""Persistent JSON-RPC client for VeriPatch backend IPC."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

from veripatch.config import apply_command_timeout

_STREAMING_METHODS = frozenset({"apply_updates_stream"})


class JsonRpcClient:
    """Line-delimited JSON-RPC client over a persistent backend subprocess."""

    def __init__(
        self,
        executable: str | None = None,
        args: list[str] | None = None,
        cwd: str | os.PathLike[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.executable = executable or sys.executable
        self.args = args or ["-m", "veripatch"]
        self.cwd = cwd
        self.env = env
        self.timeout = timeout
        self._proc: subprocess.Popen[str] | None = None
        self._request_id = 0

    def start(self) -> None:
        if self._proc is not None:
            return
        run_env = os.environ.copy()
        if self.env:
            run_env.update(self.env)
        self._proc = subprocess.Popen(
            [self.executable, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.cwd,
            env=run_env,
        )

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> Any:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("Client not started; call start() first")

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._request_id,
        }
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

        if method == "apply_updates_stream":
            return self._read_stream_response(
                self._proc.stdout,
                self._request_id,
                on_progress,
            )

        response_line = self._proc.stdout.readline()
        if not response_line.strip():
            raise RuntimeError("Empty response from backend")

        response = json.loads(response_line)
        if "error" in response:
            error = response["error"]
            raise RuntimeError(error.get("message", "RPC error"))
        return response.get("result")

    @staticmethod
    def _read_stream_response(
        readable: IO[str],
        request_id: int,
        on_progress: Callable[[str], None] | None = None,
    ) -> Any:
        while True:
            response_line = readable.readline()
            if not response_line.strip():
                raise RuntimeError("Empty response from backend")
            response = json.loads(response_line)
            if response.get("method") == "apply_progress":
                if on_progress:
                    on_progress(str(response.get("params", {}).get("line", "")))
                continue
            if response.get("id") == request_id:
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(error.get("message", "RPC error"))
                return response.get("result")
            if response.get("result") is not None or response.get("error") is not None:
                raise RuntimeError(
                    f"Unexpected RPC response id {response.get('id')} "
                    f"(expected {request_id})"
                )

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.poll() is None:
                self.call("shutdown")
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            pass
        finally:
            if self._proc.stdin:
                self._proc.stdin.close()
            try:
                self._proc.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)
            self._proc = None

    def __enter__(self) -> JsonRpcClient:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class SocketJsonRpcClient:
    """JSON-RPC client over a TCP connection to a running backend server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        timeout: float = 120.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._reader: IO[str] | None = None
        self._writer: IO[str] | None = None
        self._request_id = 0

    def connect(self) -> None:
        if self._sock is not None:
            return
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self._sock = sock
        self._reader = sock.makefile("r", encoding="utf-8")
        self._writer = sock.makefile("w", encoding="utf-8")

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> Any:
        if self._writer is None or self._reader is None:
            raise RuntimeError("Client not connected; call connect() first")

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._request_id,
        }

        extended_timeout = method in _STREAMING_METHODS
        try:
            if extended_timeout and self._sock is not None:
                self._sock.settimeout(float(apply_command_timeout()) + 30.0)
            self._writer.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._writer.flush()

            if method == "apply_updates_stream":
                return JsonRpcClient._read_stream_response(
                    self._reader,
                    self._request_id,
                    on_progress,
                )
        finally:
            if extended_timeout and self._sock is not None:
                self._sock.settimeout(self.timeout)

        response_line = self._reader.readline()
        if not response_line.strip():
            raise RuntimeError("Empty response from backend")
        response = json.loads(response_line)
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "RPC error"))
        return response.get("result")

    def close(self) -> None:
        try:
            if self._writer is not None:
                self._writer.close()
            if self._reader is not None:
                self._reader.close()
            if self._sock is not None:
                self._sock.close()
        finally:
            self._writer = None
            self._reader = None
            self._sock = None

    def __enter__(self) -> SocketJsonRpcClient:
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def resolve_ipc_port() -> int | None:
    """Resolve TCP port from env or .veripatch/ipc.port."""
    env_port = os.environ.get("VERIPATCH_IPC_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            return None
    port_file = os.environ.get("VERIPATCH_IPC_PORT_FILE", ".veripatch/ipc.port")
    if os.path.isfile(port_file):
        try:
            return int(Path(port_file).read_text(encoding="utf-8").strip())
        except ValueError:
            return None
    return None


def get_client(
    *,
    host: str | None = None,
    port: int | None = None,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
) -> JsonRpcClient | SocketJsonRpcClient:
    """Return a socket client when port is configured, else stdio subprocess client."""
    resolved_port = port if port is not None else resolve_ipc_port()
    resolved_host = host or os.environ.get("VERIPATCH_IPC_HOST", "127.0.0.1")
    if resolved_port:
        return SocketJsonRpcClient(resolved_host, resolved_port)
    return JsonRpcClient(cwd=cwd, env=env)
