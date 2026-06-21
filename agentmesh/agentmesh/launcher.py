"""Agent launch helpers for in-terminal and external terminal modes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agentmesh.agent.brain import get_brain
from agentmesh.agent.spec import load_agent_spec, load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.file_bus import FileBus
from agentmesh.console import console_print
from agentmesh.paths import apply_runtime_env, ensure_runtime_dirs
from agentmesh.runtime.registry import get_registry
from agentmesh.scheduler import default_agents_dir
from agentmesh.selection import AgentSelection, select_agent_for_intent


def should_spawn_external(*, force_here: bool = False, force_spawn: bool = False) -> bool:
    if force_here:
        return False
    if force_spawn or os.environ.get("AGENTMESH_SPAWN_EXTERNAL") == "1":
        return True
    if os.environ.get("AGENTMESH_IN_TERMINAL") == "1":
        return False
    if os.environ.get("TERM_PROGRAM") == "vscode":
        return False
    return False


def spawn_agent_in_new_terminal(agent_id: str, bus: Path) -> None:
    """Launch agent worker in a separate terminal window."""
    env = os.environ.copy()
    env["AGENTMESH_BUS_ROOT"] = str(bus)
    env["AGENTMESH_FILE_BUS"] = "1"
    run_cmd = [sys.executable, "-m", "agentmesh.cli", "run", agent_id, "--file-bus"]
    joined = subprocess.list2cmdline(run_cmd)

    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", f"AgentMesh: {agent_id}", "cmd", "/k", joined],
            env=env,
            cwd=os.getcwd(),
        )
        return

    if sys.platform == "darwin":
        script = f'tell application "Terminal" to do script "{joined}"'
        subprocess.Popen(["osascript", "-e", script], env=env, cwd=os.getcwd())
        return

    for terminal in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
        try:
            if terminal == "gnome-terminal":
                subprocess.Popen([terminal, "--", *run_cmd], env=env, cwd=os.getcwd())
            elif terminal == "konsole":
                subprocess.Popen([terminal, "-e", *run_cmd], env=env, cwd=os.getcwd())
            else:
                subprocess.Popen([terminal, "-e", joined], env=env, cwd=os.getcwd())
            return
        except OSError:
            continue

    print("Could not open a new terminal. Run manually:")
    print(f"  AGENTMESH_BUS_ROOT={bus} {' '.join(run_cmd)}")


async def run_agent_in_current_terminal(
    agent_id: str,
    *,
    max_messages: int = 100,
) -> int:
    """Run an agent worker in this terminal with FileBus and runtime lock."""
    apply_runtime_env()
    bus_path, _runtime_path = ensure_runtime_dirs()
    spec = load_agent_spec(default_agents_dir() / f"{agent_id}.md")
    bus = FileBus(bus_path)
    await bus.register_agent(spec.agent_id)

    registry = get_registry(known_agents={spec.agent_id})
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
        print(f"Agent {spec.agent_id} listening in this terminal (Ctrl+C to stop)...")
        print(f"FileBus: {bus_path}")
        print(f"Runtime lock PID {runtime_lock.pid}")
        await worker.run_loop(max_messages=max_messages)
    finally:
        registry.release(spec.agent_id)
    return 0


def print_selection(selection: AgentSelection) -> None:
    if selection.skipped:
        console_print(f"Skipped (already running): {', '.join(selection.skipped)}")
    console_print(
        f"Selected: {selection.agent_id} "
        f"({selection.spec.emoji} {selection.spec.name})"
    )
    console_print(f"Reason: {selection.reason}")


async def start_intent(
    intent: str,
    *,
    force_here: bool = False,
    force_spawn: bool = False,
    max_messages: int = 100,
) -> tuple[int, str | None]:
    """
    Select agent for intent and launch it.

    Returns (exit_code, agent_id_if_started_in_terminal).
    When agent starts in current terminal, agent_id is set and caller should exit REPL.
    """
    specs = load_all_agents(default_agents_dir())
    registry = get_registry(known_agents=set(specs.keys()))
    registry.cleanup_stale()

    selection = select_agent_for_intent(intent, specs, registry)
    if selection is None:
        active = sorted(registry.active_agents())
        print(f"All agents for '{intent}' are already running: {', '.join(active) or 'none'}")
        return 1, None

    print_selection(selection)
    bus_path, _ = ensure_runtime_dirs()

    if should_spawn_external(force_here=force_here, force_spawn=force_spawn):
        spawn_agent_in_new_terminal(selection.agent_id, bus_path)
        print(f"Launched {selection.agent_id} in a new terminal (FileBus: {bus_path})")
        return 0, None

    code = await run_agent_in_current_terminal(selection.agent_id, max_messages=max_messages)
    return code, selection.agent_id
