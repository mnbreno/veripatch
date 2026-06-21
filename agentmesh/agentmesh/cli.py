"""AgentMesh CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from agentmesh.agent.brain import get_brain
from agentmesh.agent.spec import load_agent_spec, load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bootstrap import run_bootstrap
from agentmesh.bus.file_bus import FileBus
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.console import configure_console, console_print
from agentmesh.interactive import handle_status, run_interactive
from agentmesh.launcher import start_intent
from agentmesh.paths import apply_runtime_env, bus_root, ensure_runtime_dirs
from agentmesh.runtime.registry import get_registry
from agentmesh.scheduler import default_agents_dir
from agentmesh.selection import INTENT_AGENT_PRIORITY
from agentmesh.workflows import WORKFLOWS, run_workflow


def _agents_dir() -> Path:
    return default_agents_dir()


def cmd_list(_args: argparse.Namespace) -> int:
    specs = load_all_agents(_agents_dir())
    registry = get_registry(known_agents=set(specs.keys()))
    active = registry.active_agents()
    print("Available agents:")
    for aid, spec in specs.items():
        state = "RUNNING" if aid in active else "idle"
        console_print(f"  {aid:25} {spec.emoji} {spec.name} [{state}]")
    print("\nWorkflows:")
    for name, wf in WORKFLOWS.items():
        print(f"  {name:25} {wf.get('description', '')}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    handle_status()
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    return run_bootstrap(install=not args.no_install)


async def cmd_start(args: argparse.Namespace) -> int:
    force_here = args.here or not args.spawn
    force_spawn = args.spawn
    code, _agent_id = await start_intent(
        args.intent,
        force_here=force_here,
        force_spawn=force_spawn,
        max_messages=args.max_messages,
    )
    return code


async def cmd_run(args: argparse.Namespace) -> int:
    apply_runtime_env()
    spec = load_agent_spec(_agents_dir() / f"{args.agent}.md")
    bus_path = bus_root()
    use_file_bus = args.file_bus or os.environ.get("AGENTMESH_FILE_BUS") == "1"
    bus = FileBus(bus_path) if use_file_bus else InMemoryBus()
    await bus.register_agent(spec.agent_id)

    registry = get_registry(known_agents={spec.agent_id})
    runtime_lock = None
    if use_file_bus:
        registry.cleanup_stale()
        if registry.is_running(spec.agent_id):
            print(
                f"Agent '{spec.agent_id}' is already running in another terminal.",
                file=sys.stderr,
            )
            return 1
        runtime_lock = registry.hold_until_exit(
            spec.agent_id,
            command=f"agentmesh run {spec.agent_id} --file-bus",
        )

    worker = AgentWorker(spec, bus, get_brain())

    try:
        if args.once:
            try:
                result = await worker.run_once(timeout=args.timeout)
                if result:
                    print(result.to_dict())
            except TimeoutError:
                print(f"No message within {args.timeout}s", file=sys.stderr)
                return 1
        else:
            print(f"Agent {spec.agent_id} listening (Ctrl+C to stop)...")
            if runtime_lock:
                print(f"Runtime lock PID {runtime_lock.pid}")
            await worker.run_loop(max_messages=args.max_messages)
    finally:
        if runtime_lock:
            registry.release(spec.agent_id)
    return 0


async def cmd_orchestrate(args: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    if args.file_bus:
        brain = os.environ.get("AGENTMESH_BRAIN", "scripted")
        print(f"FileBus mode: dispatching to running agents (controller brain={brain})")
        print("Ensure agents were started with AGENTMESH_BRAIN=llm for local LLM inference.")
    result = await run_workflow(
        args.workflow,
        file_bus=args.file_bus,
        timeout=args.timeout,
    )
    print(f"Workflow: {result.name}")
    print(f"Correlation: {result.correlation_id}")
    print(f"Steps: {result.steps}")
    print(f"History messages: {result.history_count}")
    if result.final_payload:
        print(f"Final status: {result.final_payload.get('status')}")
        print(f"Final summary: {result.final_payload.get('summary')}")
    elif args.file_bus:
        print(
            "Workflow did not complete. Check `agentmesh status` and LM Studio logs.",
            file=sys.stderr,
        )
    return 0 if result.final_payload else 1


def cmd_interactive(_args: argparse.Namespace) -> int:
    asyncio.run(run_interactive())
    return 0


def main() -> None:
    configure_console()
    if len(sys.argv) == 1:
        cmd_interactive(argparse.Namespace())
        return

    parser = argparse.ArgumentParser(description="AgentMesh multi-agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    interactive_p = sub.add_parser(
        "interactive",
        help="Interactive REPL (also default when no subcommand is given)",
    )
    interactive_p.set_defaults(func=cmd_interactive)

    bootstrap_p = sub.add_parser("bootstrap", help="Prepare AgentMesh for multi-terminal dev")
    bootstrap_p.add_argument(
        "--no-install",
        action="store_true",
        help="Skip pip install -e step",
    )
    bootstrap_p.set_defaults(func=cmd_bootstrap)

    status_p = sub.add_parser("status", help="Show running agents")
    status_p.set_defaults(func=cmd_status)

    list_p = sub.add_parser("list", help="List agents and workflows")
    list_p.set_defaults(func=lambda a: cmd_list(a))

    start_p = sub.add_parser("start", help="Select and launch agent for an intent")
    start_p.add_argument(
        "intent",
        choices=list(INTENT_AGENT_PRIORITY.keys()),
        help="Intent (e.g. development)",
    )
    start_p.add_argument(
        "--here",
        action="store_true",
        help="Run agent in this terminal (default in Cursor/vscode)",
    )
    start_p.add_argument(
        "--spawn",
        action="store_true",
        help="Spawn agent in a new external terminal window",
    )
    start_p.add_argument("--max-messages", type=int, default=100)
    start_p.set_defaults(func=lambda a: asyncio.run(cmd_start(a)))

    run_p = sub.add_parser("run", help="Run a single agent worker")
    run_p.add_argument("agent", help="Agent id (e.g. backend-architect)")
    run_p.add_argument("--once", action="store_true", help="Process one message then exit")
    run_p.add_argument("--file-bus", action="store_true", help="Use FileBus for separate terminals")
    run_p.add_argument("--timeout", type=float, default=60.0)
    run_p.add_argument("--max-messages", type=int, default=100)
    run_p.set_defaults(func=lambda a: asyncio.run(cmd_run(a)))

    orch_p = sub.add_parser("orchestrate", help="Run a predefined workflow")
    orch_p.add_argument("workflow", choices=list(WORKFLOWS.keys()))
    orch_p.add_argument(
        "--file-bus",
        action="store_true",
        help="Dispatch to running FileBus agents (required for multi-terminal LLM mode)",
    )
    orch_p.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="FileBus workflow wait timeout in seconds (default 600)",
    )
    orch_p.set_defaults(func=lambda a: asyncio.run(cmd_orchestrate(a)))

    args = parser.parse_args()
    result = args.func(args)
    if isinstance(result, int):
        sys.exit(result)


if __name__ == "__main__":
    main()
