"""Tests for message bus routing, broadcast, and history."""

import pytest

from agentmesh.bus.file_bus import FileBus
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.protocol import BROADCAST, create_request


@pytest.mark.asyncio
async def test_memory_bus_direct_route() -> None:
    bus = InMemoryBus()
    await bus.register_agent("a")
    await bus.register_agent("b")
    msg = create_request("a", "b", {"task": "hello"})
    await bus.send(msg)
    received = await bus.receive("b", timeout=1.0)
    assert received.id == msg.id
    assert received.payload["task"] == "hello"


@pytest.mark.asyncio
async def test_memory_bus_broadcast() -> None:
    bus = InMemoryBus()
    for aid in ("a", "b", "c"):
        await bus.register_agent(aid)
    msg = create_request("a", BROADCAST, {"task": "announce"})
    await bus.broadcast(msg)
    got_b = await bus.receive("b", timeout=1.0)
    got_c = await bus.receive("c", timeout=1.0)
    assert got_b.payload["task"] == "announce"
    assert got_c.payload["task"] == "announce"


@pytest.mark.asyncio
async def test_memory_bus_history() -> None:
    bus = InMemoryBus()
    await bus.register_agent("x")
    await bus.register_agent("y")
    await bus.send(create_request("x", "y", {"task": "one"}))
    hist = await bus.history(limit=10)
    assert len(hist) >= 1


@pytest.mark.asyncio
async def test_file_bus_persistence(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    await bus.register_agent("agent-a")
    await bus.register_agent("agent-b")
    msg = create_request("agent-a", "agent-b", {"task": "file test"})
    await bus.send(msg)
    received = await bus.route("*", "agent-b")
    assert received is not None
    assert received.payload["task"] == "file test"
    hist = await bus.history()
    assert len(hist) == 1
