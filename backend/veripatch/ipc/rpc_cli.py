"""One-shot JSON-RPC CLI for scripts and GUI bridge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from veripatch.ipc.client import SocketJsonRpcClient, get_client


def _load_params(args: argparse.Namespace) -> dict[str, Any]:
    if args.params_file:
        return cast(dict[str, Any], json.loads(Path(args.params_file).read_text(encoding="utf-8")))
    return cast(dict[str, Any], json.loads(args.params))


def run_rpc(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call a VeriPatch JSON-RPC method")
    parser.add_argument("method", help="RPC method name")
    params_group = parser.add_mutually_exclusive_group()
    params_group.add_argument(
        "--params",
        default="{}",
        help="JSON object of RPC params",
    )
    params_group.add_argument(
        "--params-file",
        help="Path to a JSON file containing RPC params",
    )
    parser.add_argument("--host", default=None, help="Backend TCP host")
    parser.add_argument("--port", type=int, default=None, help="Backend TCP port")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print apply_progress lines to stderr (streaming methods)",
    )
    parser.add_argument(
        "--stream-json",
        action="store_true",
        help="Emit raw JSON-RPC lines to stdout (for GUI streaming bridge)",
    )
    args = parser.parse_args(argv)

    try:
        params = _load_params(args)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Invalid RPC params: {exc}", file=sys.stderr)
        return 2

    client = get_client(host=args.host, port=args.port)
    request_id: int | str | None = None
    try:
        if isinstance(client, SocketJsonRpcClient):
            client.connect()
        else:
            client.start()
        request_id = client._request_id + 1

        if args.method == "apply_updates_stream":

            def on_progress(line: str) -> None:
                if args.stream_json:
                    notification = {
                        "jsonrpc": "2.0",
                        "method": "apply_progress",
                        "params": {"line": line},
                    }
                    print(json.dumps(notification, separators=(",", ":")))
                    sys.stdout.flush()
                elif args.stream:
                    print(line, file=sys.stderr)

            result = client.call(args.method, params, on_progress=on_progress)
            if args.stream_json:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
                print(json.dumps(response, separators=(",", ":")))
            else:
                print(json.dumps({"result": result}, separators=(",", ":")))
        else:
            result = client.call(args.method, params)
            if args.stream_json:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
                print(json.dumps(response, separators=(",", ":")))
            else:
                print(json.dumps({"result": result}, separators=(",", ":")))
        return 0
    except RuntimeError as exc:
        if args.stream_json:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(exc)},
            }
            print(json.dumps(response, separators=(",", ":")))
        else:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(run_rpc())
