"""Tests for message protocol."""

from agentmesh.protocol import (
    BROADCAST,
    Message,
    MessageType,
    create_request,
    create_response,
    forward_request,
    preserve_context,
)


def test_create_request_validates() -> None:
    msg = create_request("scheduler", "backend-architect", {"task": "design API"})
    assert msg.type == MessageType.REQUEST
    assert msg.recipient == "backend-architect"


def test_preserve_context_carries_task() -> None:
    req = create_request("scheduler", "a", {"task": "original"})
    resp = create_response(req, "a", {"summary": "done"})
    ctx = preserve_context(resp, {"ctx_extra": "value"})
    assert ctx.get("original_task") == "original"
    assert ctx["prior_sender"] == "a"


def test_forward_request_preserves_correlation() -> None:
    req = create_request("scheduler", "backend-architect", {"task": "t"})
    fwd = forward_request(req, "backend-architect", "code-reviewer", {"task": "review"})
    assert fwd.correlation_id == req.correlation_id
    assert fwd.recipient == "code-reviewer"
    assert req.id in fwd.trace


def test_message_ttl_default_not_expired() -> None:
    msg = create_request("a", "b", {"task": "no ttl"})
    assert msg.ttl_seconds is None
    assert not msg.is_expired()


def test_message_ttl_expired() -> None:
    msg = create_request("a", "b", {"task": "expired"})
    msg.ttl_seconds = -1
    assert msg.is_expired()


def test_message_ttl_serialization() -> None:
    msg = create_request("a", "b", {"task": "ttl serial"})
    msg.ttl_seconds = 300
    data = msg.to_dict()
    assert data["ttl_seconds"] == 300
    restored = Message.from_dict(data)
    assert restored.ttl_seconds == 300
    assert not restored.is_expired()


def test_message_from_dict_missing_ttl() -> None:
    data = {
        "id": "m1",
        "sender": "a",
        "recipient": "b",
        "type": "request",
        "correlation_id": "cid-1",
        "payload": {},
    }
    msg = Message.from_dict(data)
    assert msg.ttl_seconds is None


def test_broadcast_constant() -> None:
    assert BROADCAST == "*"


def test_message_with_broadcast_recipient() -> None:
    msg = create_request("a", BROADCAST, {"task": "all"})
    assert msg.recipient == "*"
