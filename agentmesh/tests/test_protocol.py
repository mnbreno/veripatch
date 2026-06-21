"""Tests for message protocol."""

from agentmesh.protocol import (
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
