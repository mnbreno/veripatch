"""Asyncio task scheduler for parallel agent execution."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentmesh.agent.brain import Brain, get_brain
from agentmesh.agent.spec import AgentSpec
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.base import MessageBus


@dataclass
class SchedulerResult:
    """Outcome of a scheduled batch."""

    elapsed_seconds: float
    outputs: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Scheduler:
    """Concurrent agent execution with resource limits."""

    def __init__(
        self,
        bus: MessageBus,
        *,
        max_concurrent: int = 4,
        brain: Brain | None = None,
    ) -> None:
        self.bus = bus
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.brain = brain or get_brain()
        self._tasks: list[asyncio.Task[Any]] = []

    async def _run_worker(self, worker: AgentWorker, message_count: int = 1) -> list[Any]:
        async with self.semaphore:
            return await worker.run_loop(max_messages=message_count)

    async def run_agents_parallel(
        self,
        workers: list[AgentWorker],
        *,
        message_count: int = 1,
    ) -> SchedulerResult:
        start = time.perf_counter()
        coros = [self._run_worker(w, message_count) for w in workers]
        results = await asyncio.gather(*coros, return_exceptions=True)
        elapsed = time.perf_counter() - start

        outputs: list[Any] = []
        errors: list[str] = []
        for item in results:
            if isinstance(item, BaseException):
                errors.append(str(item))
            else:
                outputs.append(item)
        return SchedulerResult(elapsed_seconds=elapsed, outputs=outputs, errors=errors)

    async def run_agents_sequential(
        self,
        workers: list[AgentWorker],
        *,
        message_count: int = 1,
    ) -> SchedulerResult:
        start = time.perf_counter()
        outputs: list[Any] = []
        errors: list[str] = []
        for worker in workers:
            try:
                result = await self._run_worker(worker, message_count)
                outputs.append(result)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
        elapsed = time.perf_counter() - start
        return SchedulerResult(elapsed_seconds=elapsed, outputs=outputs, errors=errors)

    async def spawn_terminal_agent(
        self,
        agent_id: str,
        bus_root: Path,
        *,
        brain: str = "scripted",
    ) -> asyncio.subprocess.Process:
        """Spawn a separate terminal process running one agent (FileBus mode)."""
        env = os.environ.copy()
        env["AGENTMESH_BUS_ROOT"] = str(bus_root)
        env["AGENTMESH_BRAIN"] = brain
        cmd = [sys.executable, "-m", "agentmesh.cli", "run", agent_id, "--once"]
        return await asyncio.create_subprocess_exec(*cmd, env=env)

    @staticmethod
    def build_workers(
        specs: dict[str, AgentSpec],
        bus: MessageBus,
        agent_ids: list[str],
        brain: Brain | None = None,
    ) -> list[AgentWorker]:
        brain = brain or get_brain()
        workers = []
        for aid in agent_ids:
            if aid not in specs:
                raise KeyError(f"Unknown agent: {aid}")
            workers.append(AgentWorker(specs[aid], bus, brain))
        return workers


async def register_agents(bus: MessageBus, agent_ids: list[str]) -> None:
    for aid in agent_ids:
        await bus.register_agent(aid)


def default_agents_dir() -> Path:
    return Path(__file__).resolve().parent / "agents"
