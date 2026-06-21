"""Abstract message bus interface."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from agentmesh.protocol import Message


class MessageBus(ABC):
    """Cross-agent message transport with routing, broadcast, and history."""

    CLEANUP_INTERVAL = 60.0

    def __init__(self) -> None:
        self._cleanup_task: asyncio.Task[Any] | None = None

    @abstractmethod
    async def send(self, message: Message) -> None:
        """Deliver a message to its recipient (or all agents if broadcast)."""

    @abstractmethod
    async def route(self, sender: str, recipient: str) -> Message | None:
        """Receive the next message for an agent, optionally filtered by sender."""

    @abstractmethod
    async def broadcast(self, message: Message) -> None:
        """Send a message to all registered agents."""

    @abstractmethod
    async def history(self, *, limit: int = 100) -> list[Message]:
        """Return recent messages for traceability."""

    async def register_agent(self, agent_id: str) -> None:
        """Optional hook for buses that track agent membership."""
        return None

    async def shutdown(self) -> None:
        """Signal all agents to stop waiting for messages. Cleans up resources."""
        await self.stop_cleanup()
        return None

    async def prune_expired(self) -> int:
        """Remove expired messages from history. Returns count removed."""
        return 0

    def start_cleanup(self, interval: float | None = None) -> None:
        """Start a background task that periodically prunes expired messages."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return
        interval = interval if interval is not None else self.CLEANUP_INTERVAL
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval))

    async def stop_cleanup(self) -> None:
        """Cancel the periodic cleanup task."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self, interval: float) -> None:
        try:
            while True:
                await asyncio.sleep(interval)
                await self.prune_expired()
        except asyncio.CancelledError:
            pass
