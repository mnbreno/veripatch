"""Message protocol for cross-agent communication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    DATA = "data"
    ERROR = "error"


BROADCAST = "*"


@dataclass
class Message:
    """Structured envelope for all cross-agent communication."""

    id: str
    sender: str
    recipient: str
    type: MessageType
    correlation_id: str
    payload: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)
    trace: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.type.value,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "context": self.context,
            "trace": self.trace,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            id=str(data["id"]),
            sender=str(data["sender"]),
            recipient=str(data["recipient"]),
            type=MessageType(str(data["type"])),
            correlation_id=str(data["correlation_id"]),
            payload=dict(data.get("payload") or {}),
            context=dict(data.get("context") or {}),
            trace=list(data.get("trace") or []),
            timestamp=str(data.get("timestamp") or ""),
        )

    def validate(self) -> None:
        if not self.id:
            raise ValueError("Message id is required")
        if not self.sender:
            raise ValueError("Message sender is required")
        if not self.recipient:
            raise ValueError("Message recipient is required")
        if not self.correlation_id:
            raise ValueError("Message correlation_id is required")
        if self.type not in MessageType:
            raise ValueError(f"Invalid message type: {self.type}")


def new_message_id() -> str:
    return str(uuid.uuid4())


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def create_request(
    sender: str,
    recipient: str,
    payload: dict[str, Any],
    *,
    correlation_id: str | None = None,
    context: dict[str, Any] | None = None,
    trace: list[str] | None = None,
) -> Message:
    cid = correlation_id or new_correlation_id()
    msg = Message(
        id=new_message_id(),
        sender=sender,
        recipient=recipient,
        type=MessageType.REQUEST,
        correlation_id=cid,
        payload=payload,
        context=dict(context or {}),
        trace=list(trace or []),
    )
    msg.validate()
    return msg


def create_response(
    request: Message,
    sender: str,
    payload: dict[str, Any],
    *,
    msg_type: MessageType = MessageType.RESPONSE,
) -> Message:
    trace = list(request.trace) + [request.id]
    context = preserve_context(request, payload)
    msg = Message(
        id=new_message_id(),
        sender=sender,
        recipient=request.sender,
        type=msg_type,
        correlation_id=request.correlation_id,
        payload=payload,
        context=context,
        trace=trace,
    )
    msg.validate()
    return msg


def create_error(
    request: Message,
    sender: str,
    error: str,
    *,
    details: dict[str, Any] | None = None,
) -> Message:
    payload = {"error": error, "details": details or {}}
    return create_response(request, sender, payload, msg_type=MessageType.ERROR)


def preserve_context(source: Message, new_payload: dict[str, Any]) -> dict[str, Any]:
    """Merge prior context with new payload fields for downstream agents."""
    merged = dict(source.context)
    merged["prior_sender"] = source.sender
    merged["prior_message_id"] = source.id
    if "task" in source.payload and "task" not in new_payload:
        merged.setdefault("original_task", source.payload["task"])
    merged.update({k: v for k, v in new_payload.items() if k.startswith("ctx_")})
    return merged


def forward_request(
    source: Message,
    sender: str,
    recipient: str,
    payload: dict[str, Any],
) -> Message:
    """Forward work to another agent while preserving correlation and context."""
    trace = list(source.trace) + [source.id]
    context = preserve_context(source, payload)
    msg = Message(
        id=new_message_id(),
        sender=sender,
        recipient=recipient,
        type=MessageType.REQUEST,
        correlation_id=source.correlation_id,
        payload=payload,
        context=context,
        trace=trace,
    )
    msg.validate()
    return msg
