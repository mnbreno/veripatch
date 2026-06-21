"""Tests for AgentWorker listen loop behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agentmesh.agent.spec import load_agent_spec
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.scheduler import default_agents_dir


@pytest.mark.asyncio
async def test_run_loop_continues_after_idle_timeout() -> None:
    spec = load_agent_spec(default_agents_dir() / "backend-architect.md")
    worker = AgentWorker(spec, InMemoryBus())
    call_count = 0
    handled = AsyncMock()

    async def mock_run_once(**kwargs: object) -> AsyncMock | None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("idle")
        return handled

    with patch.object(worker, "run_once", side_effect=mock_run_once):
        results = await worker.run_loop(max_messages=1)

    assert call_count == 2
    assert results == [handled]


@pytest.mark.asyncio
async def test_run_loop_stops_after_message_limit() -> None:
    spec = load_agent_spec(default_agents_dir() / "backend-architect.md")
    worker = AgentWorker(spec, InMemoryBus())
    message = AsyncMock()
    run_once = AsyncMock(return_value=message)

    with patch.object(worker, "run_once", run_once):
        results = await worker.run_loop(max_messages=2)

    assert len(results) == 2
    assert run_once.await_count == 2
