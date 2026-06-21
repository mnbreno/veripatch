"""Agent process registry: lock files, PID checks, and terminal process scanning."""

from __future__ import annotations

import atexit
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentmesh.paths import runtime_root as _runtime_root_from_paths


@dataclass
class AgentRuntimeLock:
    agent_id: str
    pid: int
    started_at: str
    command: str
    terminal_session: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentRuntimeLock:
        return cls(
            agent_id=str(data["agent_id"]),
            pid=int(data["pid"]),
            started_at=str(data["started_at"]),
            command=str(data.get("command", "")),
            terminal_session=str(data.get("terminal_session", "")),
        )


def default_runtime_root() -> Path:
    env = os.environ.get("AGENTMESH_RUNTIME_ROOT")
    if env:
        base = Path(env)
        if not base.is_absolute():
            from agentmesh.paths import find_repo_root

            base = find_repo_root() / base
        return base
    return _runtime_root_from_paths()


def _terminal_session_id() -> str:
    if sys.platform == "win32":
        return str(os.environ.get("SESSIONNAME", "console"))
    return str(os.environ.get("TERM_SESSION_ID", os.environ.get("STY", "local")))


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _windows_process_alive(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def _windows_process_alive(pid: int) -> bool:
    import ctypes

    process_query_limited = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


class AgentRegistry:
    """Tracks which agents are running via lock files and process inspection."""

    def __init__(self, root: Path, *, known_agents: set[str] | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.known_agents = known_agents or set()

    def lock_path(self, agent_id: str) -> Path:
        return self.root / f"{agent_id}.lock.json"

    def read_lock(self, agent_id: str) -> AgentRuntimeLock | None:
        path = self.lock_path(agent_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AgentRuntimeLock.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            path.unlink(missing_ok=True)
            return None

    def write_lock(self, lock: AgentRuntimeLock) -> None:
        self.lock_path(lock.agent_id).write_text(
            json.dumps(asdict(lock), indent=2),
            encoding="utf-8",
        )

    def release(self, agent_id: str) -> None:
        self.lock_path(agent_id).unlink(missing_ok=True)

    def cleanup_stale(self) -> None:
        for path in self.root.glob("*.lock.json"):
            agent_id = path.name.removesuffix(".lock.json")
            if not self.is_running(agent_id, include_process_scan=False):
                path.unlink(missing_ok=True)

    def is_running(self, agent_id: str, *, include_process_scan: bool = True) -> bool:
        lock = self.read_lock(agent_id)
        if lock and is_process_alive(lock.pid):
            return True
        if lock:
            self.release(agent_id)

        if include_process_scan:
            return agent_id in self.scan_process_table()
        return False

    def running_from_locks(self) -> set[str]:
        running: set[str] = set()
        for path in self.root.glob("*.lock.json"):
            agent_id = path.name.removesuffix(".lock.json")
            if self.is_running(agent_id, include_process_scan=False):
                running.add(agent_id)
            else:
                path.unlink(missing_ok=True)
        return running

    def scan_process_table(self) -> set[str]:
        """Detect agentmesh run <agent> processes from the OS process table."""
        if os.environ.get("AGENTMESH_SKIP_PROCESS_SCAN") == "1":
            return set()
        if not self.known_agents:
            return set()

        found: set[str] = set()
        current_pid = os.getpid()

        for pid, command in _iter_process_commands():
            if pid == current_pid:
                continue
            if "agentmesh" not in command.lower():
                continue
            if " run " not in command and ".cli run " not in command:
                continue
            for agent_id in self.known_agents:
                if re.search(rf"\brun\s+{re.escape(agent_id)}\b", command):
                    found.add(agent_id)
                    break
        return found

    def active_agents(self) -> set[str]:
        self.cleanup_stale()
        return self.running_from_locks() | self.scan_process_table()

    def acquire(self, agent_id: str, *, command: str = "") -> AgentRuntimeLock:
        existing = self.read_lock(agent_id)
        if existing and is_process_alive(existing.pid):
            raise RuntimeError(
                f"Agent '{agent_id}' is already running (PID {existing.pid})"
            )
        if existing:
            self.release(agent_id)

        lock = AgentRuntimeLock(
            agent_id=agent_id,
            pid=os.getpid(),
            started_at=datetime.now(UTC).isoformat(),
            command=command or f"agentmesh run {agent_id}",
            terminal_session=_terminal_session_id(),
        )
        path = self.lock_path(agent_id)
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(asdict(lock), handle, indent=2)
        except FileExistsError as exc:
            raise RuntimeError(f"Agent '{agent_id}' is already running") from exc
        return lock

    def hold_until_exit(self, agent_id: str, *, command: str = "") -> AgentRuntimeLock:
        lock = self.acquire(agent_id, command=command)

        def _release() -> None:
            if self.read_lock(agent_id) and self.read_lock(agent_id).pid == lock.pid:
                self.release(agent_id)

        atexit.register(_release)
        return lock


def _iter_process_commands() -> list[tuple[int, str]]:
    if sys.platform == "win32":
        return _windows_process_commands()
    return _unix_process_commands()


def _windows_process_commands() -> list[tuple[int, str]]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return _windows_tasklist_fallback()

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return _windows_tasklist_fallback()

    rows = payload if isinstance(payload, list) else [payload]
    commands: list[tuple[int, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = row.get("ProcessId")
        cmd = row.get("CommandLine") or ""
        if pid is not None:
            commands.append((int(pid), str(cmd)))
    return commands


def _windows_tasklist_fallback() -> list[tuple[int, str]]:
    try:
        result = subprocess.run(
            ["wmic", "process", "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    commands: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        if "CommandLine" in line or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) >= 3 and parts[-1].strip().isdigit():
            commands.append((int(parts[-1].strip()), parts[1]))
    return commands


def _unix_process_commands() -> list[tuple[int, str]]:
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    commands: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            commands.append((int(parts[0]), parts[1]))
    return commands


def get_registry(known_agents: set[str] | None = None) -> AgentRegistry:
    return AgentRegistry(default_runtime_root(), known_agents=known_agents)
