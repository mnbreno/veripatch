"""Entry point for VeriPatch backend JSON-RPC server."""

from __future__ import annotations

import argparse
import sys

from veripatch import __version__
from veripatch.ipc.rpc_cli import run_rpc
from veripatch.ipc.server import JsonRpcServer
from veripatch.ipc.socket_server import SocketJsonRpcServer, write_port_file
from veripatch.observability.logging_config import configure_logging


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "rpc":
        sys.exit(run_rpc(sys.argv[2:]))

    parser = argparse.ArgumentParser(description="VeriPatch backend JSON-RPC server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        default=True,
        help="Start the JSON-RPC server on stdin/stdout (default)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Log level (DEBUG, INFO, WARNING, ERROR). Overrides VERIPATCH_LOG.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug JSON-RPC echo logging",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="TCP listen address when --port is set",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Listen on TCP port for persistent IPC (writes .veripatch/ipc.port)",
    )
    parser.add_argument(
        "--write-port-file",
        action="store_true",
        help="Write listen port to .veripatch/ipc.port when using --port",
    )
    args = parser.parse_args()

    configure_logging(args.log_level)

    if args.port is not None:
        if args.write_port_file:
            write_port_file(args.port)
        server = SocketJsonRpcServer(host=args.host, port=args.port, debug=args.debug)
        server.serve_forever()
        return

    if args.serve:
        server = JsonRpcServer(debug=args.debug)
        server.serve_forever()


if __name__ == "__main__":
    main()
