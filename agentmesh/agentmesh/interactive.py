"""Interactive AgentMesh CLI REPL."""

from __future__ import annotations

from agentmesh.agent.spec import load_all_agents
from agentmesh.console import console_print
from agentmesh.launcher import start_intent
from agentmesh.paths import runtime_root
from agentmesh.runtime.registry import get_registry
from agentmesh.scheduler import default_agents_dir
from agentmesh.selection import normalize_intent
from agentmesh.workflows import WORKFLOWS

HELP_TEXT = """
Commands:
  start development   Pick the best free agent and run it in this terminal
  start review        Same selection flow for code/design review
  start docs          Select technical-writer when available
  start ci            Select devops-automator when available
  status              Show running agents (locks + process scan)
  list                List all agents and workflows
  help                Show this help
  quit / exit         Leave the REPL
""".strip()

WELCOME_TEXT = """
AgentMesh ready.
Open additional Cursor terminals and run: agentmesh
In EACH terminal type: start development
Use 'status' to see which agents are already running.
""".strip()


async def handle_start_intent(intent: str) -> int:
    code, _agent_id = await start_intent(intent)
    return code


def handle_status() -> None:
    specs = load_all_agents(default_agents_dir())
    registry = get_registry(known_agents=set(specs.keys()))
    registry.cleanup_stale()

    active = registry.active_agents()
    if not active:
        print("No agents currently running.")
        return

    print("Running agents:")
    for agent_id in sorted(active):
        spec = specs.get(agent_id)
        label = f"{spec.emoji} {spec.name}" if spec else agent_id
        lock = registry.read_lock(agent_id)
        if lock and registry.is_running(agent_id, include_process_scan=False):
            print(f"  {agent_id:25} {label}  PID {lock.pid}  terminal {lock.terminal_session}")
        else:
            print(f"  {agent_id:25} {label}  (detected in process table)")


def handle_list() -> None:
    specs = load_all_agents(default_agents_dir())
    registry = get_registry(known_agents=set(specs.keys()))
    active = registry.active_agents()

    print("Available agents:")
    for aid, spec in specs.items():
        state = "RUNNING" if aid in active else "idle"
        console_print(f"  {aid:25} {spec.emoji} {spec.name:22} [{state}]")
    print("\nWorkflows:")
    for name, wf in WORKFLOWS.items():
        print(f"  {name:25} {wf.get('description', '')}")
    print(f"\nRuntime locks: {runtime_root()}")


async def run_interactive() -> None:
    print(WELCOME_TEXT)
    print()

    while True:
        try:
            line = input("agentmesh> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        lowered = line.lower()
        if lowered in {"quit", "exit", "q"}:
            break
        if lowered == "help":
            print(HELP_TEXT)
            continue
        if lowered == "status":
            handle_status()
            continue
        if lowered == "list":
            handle_list()
            continue

        intent = normalize_intent(line)
        if intent:
            code, agent_id = await start_intent(intent)
            if agent_id is not None:
                break
            if code != 0:
                continue
            continue

        print(f"Unknown command: {line!r}. Type 'help' for options.")
