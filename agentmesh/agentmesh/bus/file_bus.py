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

    Two-phase message processing: messages are renamed to .processing
    while being read, then deleted after successful delivery. If the
    consumer crashes mid-read, the .processing file can be recovered.
    """

    PROCESSING_SUFFIX = ".processing"

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = Path(root)
        self.inboxes = self.root / "inboxes"
        self.history_path = self.root / "history.jsonl"
        self.inboxes.mkdir(parents=True, exist_ok=True)
        self.history_path.touch(exist_ok=True)
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    def _inbox(self, agent_id: str) -> Path:
        path = self.inboxes / agent_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def register_agent(self, agent_id: str) -> None:
        self._inbox(agent_id)
        self._recover_processing(agent_id)

    def _recover_processing(self, agent_id: str) -> None:
        inbox = self._inbox(agent_id)
        for path in inbox.glob(f"*{self.PROCESSING_SUFFIX}"):
            json_path = path.with_suffix("")
            path.rename(json_path)

    def _append_history(self, message: Message) -> None:
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.to_dict()) + "\n")

    async def send(self, message: Message) -> None:
        message.validate()
        async with self._lock:
            if message.is_expired():
                return
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
            processing = path.with_suffix(self.PROCESSING_SUFFIX)
            path.rename(processing)
            try:
                data = json.loads(processing.read_text(encoding="utf-8"))
                message = Message.from_dict(data)
                if message.is_expired():
                    processing.unlink(missing_ok=True)
                    continue
                if sender != "*" and message.sender != sender:
                    processing.rename(path)
                    continue
                processing.unlink(missing_ok=True)
                return message
            except (json.JSONDecodeError, KeyError):
                processing.unlink(missing_ok=True)
                continue
        return None

    async def receive(self, recipient: str, *, timeout: float = 30.0) -> Message:
        await self.prune_expired()
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            if self._shutdown_event.is_set():
                raise asyncio.CancelledError("Bus is shut down")
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
        return [m for m in messages[-limit:] if not m.is_expired()]

    async def shutdown(self) -> None:
        self._shutdown_event.set()
        await super().shutdown()

    async def prune_expired(self) -> int:
        count = 0
        for inbox_dir in self.inboxes.iterdir():
            if not inbox_dir.is_dir():
                continue
            json_files = list(inbox_dir.glob("*.json"))
            proc_files = list(inbox_dir.glob(f"*{self.PROCESSING_SUFFIX}"))
            for path in json_files + proc_files:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    msg = Message.from_dict(data)
                    if msg.is_expired():
                        path.unlink(missing_ok=True)
                        count += 1
                except (json.JSONDecodeError, KeyError):
                    path.unlink(missing_ok=True)
                    count += 1
        return count
