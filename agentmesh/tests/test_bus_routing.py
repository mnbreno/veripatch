"""Tests for message bus routing, broadcast, and history."""

import asyncio
import json

import pytest

from agentmesh.bus.file_bus import FileBus
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.protocol import BROADCAST, Message, create_request


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
async def test_memory_bus_route_with_sender_filter() -> None:
    bus = InMemoryBus()
    await bus.register_agent("a")
    await bus.register_agent("b")
    msg_a = create_request("a", "b", {"task": "from a"})
    await bus.send(msg_a)
    result = await bus.route("a", "b")
    assert result is not None
    assert result.payload["task"] == "from a"
    msg_c = create_request("c", "b", {"task": "from c"})
    await bus.send(msg_c)
    result = await bus.route("a", "b")
    assert result is None


@pytest.mark.asyncio
async def test_memory_bus_shutdown_raises_cancelled() -> None:
    bus = InMemoryBus()
    await bus.register_agent("a")
    await bus.shutdown()
    with pytest.raises(asyncio.CancelledError):
        await bus.receive("a", timeout=5.0)


@pytest.mark.asyncio
async def test_memory_bus_prune_expired() -> None:
    bus = InMemoryBus()
    await bus.register_agent("a")
    await bus.register_agent("b")
    msg = create_request("a", "b", {"task": "live"})
    await bus.send(msg)
    msg.ttl_seconds = -1
    pruned = await bus.prune_expired()
    assert pruned == 1
    hist = await bus.history()
    assert all(not m.is_expired() for m in hist)


@pytest.mark.asyncio
async def test_memory_bus_bounded_queue_rejects_overflow() -> None:
    bus = InMemoryBus(queue_maxsize=2)
    await bus.register_agent("a")
    await bus.register_agent("b")
    await bus.send(create_request("a", "b", {"task": "m1"}))
    await bus.send(create_request("a", "b", {"task": "m2"}))
    with pytest.raises(asyncio.QueueFull):
        await bus.send(create_request("a", "b", {"task": "m3"}))


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


@pytest.mark.asyncio
async def test_file_bus_shutdown_raises_cancelled(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    await bus.register_agent("a")
    bus._shutdown_event.set()
    with pytest.raises(asyncio.CancelledError):
        await bus.receive("a", timeout=5.0)


@pytest.mark.asyncio
async def test_file_bus_prune_expired(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    await bus.register_agent("a")
    await bus.register_agent("b")
    msg = create_request("a", "b", {"task": "stale"})
    await bus.send(msg)
    assert await bus.route("*", "b") is not None
    msg.ttl_seconds = -1
    inbox = bus._inbox("b")
    (inbox / f"{msg.id}.json").write_text(
        json.dumps(msg.to_dict()), encoding="utf-8",
    )
    pruned = await bus.prune_expired()
    assert pruned >= 1
    result = await bus.route("*", "b")
    assert result is None


@pytest.mark.asyncio
async def test_file_bus_send_skips_expired(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    await bus.register_agent("a")
    await bus.register_agent("b")
    msg = create_request("a", "b", {"task": "too late"})
    msg.ttl_seconds = -1
    await bus.send(msg)
    result = await bus.route("*", "b")
    assert result is None


@pytest.mark.asyncio
async def test_file_bus_recovery_renames_processing(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    inbox = bus._inbox("agent-a")
    msg = create_request("other", "agent-a", {"task": "recover"})
    processing = inbox / f"{msg.id}.json{FileBus.PROCESSING_SUFFIX}"
    processing.write_text(json.dumps(msg.to_dict()), encoding="utf-8")
    bus2 = FileBus(tmp_path / "bus")
    await bus2.register_agent("agent-a")
    result = await bus2.route("*", "agent-a")
    assert result is not None
    assert result.payload["task"] == "recover"


@pytest.mark.asyncio
async def test_memory_bus_history_filters_expired() -> None:
    bus = InMemoryBus()
    await bus.register_agent("a")
    await bus.register_agent("b")
    live = create_request("a", "b", {"task": "live"})
    stale = create_request("a", "b", {"task": "stale"})
    stale.ttl_seconds = -1
    await bus.send(live)
    await bus.send(stale)
    hist = await bus.history(limit=10)
    assert len(hist) == 1
    assert hist[0].payload["task"] == "live"


@pytest.mark.asyncio
async def test_file_bus_history_filters_expired(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    await bus.register_agent("a")
    await bus.register_agent("b")
    live = create_request("a", "b", {"task": "live"})
    await bus.send(live)
    await bus.route("*", "b")
    stale = create_request("a", "b", {"task": "stale"})
    stale.ttl_seconds = -1
    inbox = bus._inbox("b")
    (inbox / f"{stale.id}.json").write_text(
        json.dumps(stale.to_dict()), encoding="utf-8",
    )
    await bus.send(stale)
    hist = await bus.history(limit=10)
    assert all(m.payload["task"] != "stale" for m in hist)


@pytest.mark.asyncio
async def test_memory_bus_start_stop_cleanup() -> None:
    bus = InMemoryBus()
    bus.start_cleanup(interval=0.1)
    assert bus._cleanup_task is not None
    assert not bus._cleanup_task.done()
    await bus.stop_cleanup()
    assert bus._cleanup_task is None


@pytest.mark.asyncio
async def test_memory_bus_start_cleanup_idempotent() -> None:
    bus = InMemoryBus()
    bus.start_cleanup(interval=0.1)
    task1 = bus._cleanup_task
    bus.start_cleanup(interval=0.1)
    assert bus._cleanup_task is task1
    await bus.stop_cleanup()


@pytest.mark.asyncio
async def test_file_bus_start_stop_cleanup(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    bus.start_cleanup(interval=0.1)
    assert bus._cleanup_task is not None
    assert not bus._cleanup_task.done()
    await bus.stop_cleanup()
    assert bus._cleanup_task is None


@pytest.mark.asyncio
async def test_shutdown_stops_cleanup() -> None:
    bus = InMemoryBus()
    bus.start_cleanup(interval=0.1)
    assert bus._cleanup_task is not None
    await bus.shutdown()
    assert bus._cleanup_task is None or bus._cleanup_task.done()
