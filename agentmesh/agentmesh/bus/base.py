"""Abstract message bus interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentmesh.protocol import Message


class MessageBus(ABC):
    """Cross-agent message transport with routing, broadcast, and history."""

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
