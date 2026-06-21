"""In-memory asyncio message bus for tests and in-process orchestration."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from agentmesh.bus.base import MessageBus
from agentmesh.protocol import BROADCAST, Message


class InMemoryBus(MessageBus):
    """Asyncio queue-based bus with append-only history."""

    def __init__(self, history_limit: int = 1000) -> None:
        self._queues: dict[str, asyncio.Queue[Message]] = defaultdict(asyncio.Queue)
        self._agents: set[str] = set()
        self._history: deque[Message] = deque(maxlen=history_limit)
        self._lock = asyncio.Lock()

    async def register_agent(self, agent_id: str) -> None:
        async with self._lock:
            self._agents.add(agent_id)
            _ = self._queues[agent_id]

    async def send(self, message: Message) -> None:
        message.validate()
        async with self._lock:
            self._history.append(message)
            if message.recipient == BROADCAST:
                for agent_id in self._agents:
                    if agent_id != message.sender:
                        await self._queues[agent_id].put(message)
            else:
                await self._queues[message.recipient].put(message)

    async def route(self, sender: str, recipient: str) -> Message | None:
        queue = self._queues[recipient]
        try:
            message = await asyncio.wait_for(queue.get(), timeout=0.05)
        except TimeoutError:
            return None
        if message.sender != sender and sender != "*":
            # Re-queue if filtered sender doesn't match (simple filter)
            await queue.put(message)
            return None
        return message

    async def receive(self, recipient: str, *, timeout: float = 30.0) -> Message:
        """Wait for the next message addressed to recipient."""
        queue = self._queues[recipient]
        return await asyncio.wait_for(queue.get(), timeout=timeout)

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
        return items[-limit:]
