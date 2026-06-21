"""In-memory asyncio message bus for tests and in-process orchestration."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from agentmesh.bus.base import MessageBus
from agentmesh.protocol import BROADCAST, Message


class InMemoryBus(MessageBus):
    """Asyncio queue-based bus with append-only history."""

    def __init__(self, history_limit: int = 1000, queue_maxsize: int = 0) -> None:
        super().__init__()
        self._factory = lambda: asyncio.Queue(maxsize=queue_maxsize)
        self._queues: dict[str, asyncio.Queue[Message]] = defaultdict(self._factory)
        self._events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)
        self._agents: set[str] = set()
        self._history: deque[Message] = deque(maxlen=history_limit)
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    async def register_agent(self, agent_id: str) -> None:
        async with self._lock:
            self._agents.add(agent_id)
            _ = self._queues[agent_id]
            _ = self._events[agent_id]

    async def send(self, message: Message) -> None:
        message.validate()
        async with self._lock:
            if message.is_expired():
                return
            self._history.append(message)
            if message.recipient == BROADCAST:
                for agent_id in self._agents:
                    if agent_id != message.sender:
                        self._queues[agent_id].put_nowait(message)
                        self._events[agent_id].set()
            else:
                self._queues[message.recipient].put_nowait(message)
                self._events[message.recipient].set()

    async def route(self, sender: str, recipient: str) -> Message | None:
        queue = self._queues[recipient]
        try:
            message = queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        if message.sender != sender and sender != "*":
            await queue.put(message)
            return None
        return message

    async def receive(self, recipient: str, *, timeout: float = 30.0) -> Message:
        """Wait for the next message addressed to recipient."""
        queue = self._queues[recipient]
        await self.prune_expired()
        event = self._events[recipient]
        tasks = [
            asyncio.create_task(queue.get()),
            asyncio.create_task(self._shutdown_event.wait()),
        ]
        done, pending = await asyncio.wait(
            tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if self._shutdown_event.is_set():
            raise asyncio.CancelledError("Bus is shut down")
        if not done:
            raise asyncio.TimeoutError(f"No message for {recipient} within {timeout}s")
        result = done.pop().result()
        event.clear()
        return result

    async def broadcast(self, message: Message) -> None:
        broadcast_msg = Message(
            id=message.id,
            sender=message.sender,
            recipient=BROADCAST,
            type=message.type,
            correlation_id=message.correlation_id,
            payload=message.payload,
            context=message.context,
            trace=message.trace,
            timestamp=message.timestamp,
        )
        await self.send(broadcast_msg)

    async def history(self, *, limit: int = 100) -> list[Message]:
        async with self._lock:
            items = list(self._history)
            items = [m for m in items if not m.is_expired()]
        return items[-limit:]

    async def shutdown(self) -> None:
        self._shutdown_event.set()
        await super().shutdown()

    async def prune_expired(self) -> int:
        async with self._lock:
            before = len(self._history)
            self._history = deque(
                (m for m in self._history if not m.is_expired()),
                maxlen=self._history.maxlen,
            )
            return before - len(self._history)
