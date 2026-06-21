"""Persistent JSON-RPC client for VeriPatch backend IPC."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


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

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
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

        response_line = self._proc.stdout.readline()
        if not response_line.strip():
            raise RuntimeError("Empty response from backend")

        response = json.loads(response_line)
        if "error" in response:
            error = response["error"]
            raise RuntimeError(error.get("message", "RPC error"))
        return response.get("result")

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
