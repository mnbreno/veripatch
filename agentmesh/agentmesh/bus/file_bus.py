"""Filesystem-based message bus for separate terminal processes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agentmesh.bus.base import MessageBus
from agentmesh.protocol import BROADCAST, Message


class FileBus(MessageBus):
    """
    File-based bus: each agent has an inbox directory.
    Messages are JSON files; history is append-only history.jsonl.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.inboxes = self.root / "inboxes"
        self.history_path = self.root / "history.jsonl"
        self.inboxes.mkdir(parents=True, exist_ok=True)
        self.history_path.touch(exist_ok=True)
        self._lock = asyncio.Lock()

    def _inbox(self, agent_id: str) -> Path:
        path = self.inboxes / agent_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def register_agent(self, agent_id: str) -> None:
        self._inbox(agent_id)

    def _append_history(self, message: Message) -> None:
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.to_dict()) + "\n")

    async def send(self, message: Message) -> None:
        message.validate()
        async with self._lock:
            self._append_history(message)
            if message.recipient == BROADCAST:
                for inbox_dir in self.inboxes.iterdir():
                    if inbox_dir.is_dir() and inbox_dir.name != message.sender:
                        target = inbox_dir / f"{message.id}.json"
                        target.write_text(json.dumps(message.to_dict()), encoding="utf-8")
            else:
                target = self._inbox(message.recipient) / f"{message.id}.json"
                target.write_text(json.dumps(message.to_dict()), encoding="utf-8")

    async def route(self, sender: str, recipient: str) -> Message | None:
        inbox = self._inbox(recipient)
        files = sorted(inbox.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            message = Message.from_dict(data)
            if sender != "*" and message.sender != sender:
                continue
            path.unlink(missing_ok=True)
            return message
        return None

    async def receive(self, recipient: str, *, timeout: float = 30.0) -> Message:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            msg = await self.route("*", recipient)
            if msg is not None:
                return msg
            await asyncio.sleep(0.1)
        raise TimeoutError(f"No message for {recipient} within {timeout}s")

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
        if not self.history_path.is_file():
            return []
        lines = self.history_path.read_text(encoding="utf-8").splitlines()
        messages = [Message.from_dict(json.loads(line)) for line in lines if line.strip()]
        return messages[-limit:]
