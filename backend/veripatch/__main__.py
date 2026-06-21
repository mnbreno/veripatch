"""Entry point for VeriPatch backend JSON-RPC server."""

from __future__ import annotations

import argparse

from veripatch.ipc.server import JsonRpcServer


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriPatch backend JSON-RPC server")
    parser.add_argument(
        "--serve",
        action="store_true",
        default=True,
        help="Start the JSON-RPC server on stdin/stdout (default)",
    )
    args = parser.parse_args()

    if args.serve:
        server = JsonRpcServer()
        server.serve_forever()


if __name__ == "__main__":
    main()
