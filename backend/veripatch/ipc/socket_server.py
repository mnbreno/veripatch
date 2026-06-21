"""TCP socket JSON-RPC server for persistent GUI/tooling connections."""

from __future__ import annotations

import json
import socket
import threading
from typing import TextIO

from veripatch.ipc.protocol import make_error, parse_request_line
from veripatch.ipc.server import INVALID_REQUEST, JsonRpcServer

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class SocketJsonRpcServer:
    """Line-delimited JSON-RPC server accepting TCP connections."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        debug: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.debug = debug

    def serve_forever(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)
        try:
            while True:
                conn, _addr = sock.accept()
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True,
                )
                thread.start()
        finally:
            sock.close()

    def _handle_connection(self, conn: socket.socket) -> None:
        with conn:
            reader = conn.makefile("r", encoding="utf-8")
            writer = conn.makefile("w", encoding="utf-8")
            server = JsonRpcServer(debug=self.debug)
            self._serve_session(server, reader, writer)

    def _serve_session(
        self,
        server: JsonRpcServer,
        reader: TextIO,
        writer: TextIO,
    ) -> None:
        for raw_line in reader:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = parse_request_line(line)
            except (ValueError, KeyError) as exc:
                response = make_error(None, INVALID_REQUEST, str(exc))
                writer.write(response.to_line() + "\n")
                writer.flush()
                continue

            response_dict = server.handle_request(request, writer=writer)
            writer.write(json.dumps(response_dict, separators=(",", ":")) + "\n")
            writer.flush()
            server.request_count += 1
            if server._shutdown_requested:
                break


def write_port_file(port: int, path: str | None = None) -> None:
    """Write listen port for clients (default .veripatch/ipc.port)."""
    from pathlib import Path

    target = Path(path) if path else Path(".veripatch") / "ipc.port"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(port), encoding="utf-8")
