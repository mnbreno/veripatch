"""Entry point for VeriPatch backend JSON-RPC server."""

from __future__ import annotations

import argparse

from veripatch.ipc.server import JsonRpcServer
from veripatch.observability.logging_config import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriPatch backend JSON-RPC server")
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
    args = parser.parse_args()

    configure_logging(args.log_level)

    if args.serve:
        server = JsonRpcServer(debug=args.debug)
        server.serve_forever()


if __name__ == "__main__":
    main()
