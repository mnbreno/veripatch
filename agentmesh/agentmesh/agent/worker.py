"""Agent worker run loop."""

from __future__ import annotations

from typing import Any

from agentmesh.agent.brain import Brain, get_brain
from agentmesh.agent.prompts import PromptSystem
from agentmesh.agent.spec import AgentSpec
from agentmesh.bus.base import MessageBus
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.protocol import (
    Message,
    MessageType,
    create_error,
    create_response,
    forward_request,
)


class AgentWorker:
    """Runs an agent: parse -> brain -> format -> reply."""

    def __init__(
        self,
        spec: AgentSpec,
        bus: MessageBus,
        brain: Brain | None = None,
    ) -> None:
        self.spec = spec
        self.bus = bus
        self.brain = brain or get_brain()
        self.prompts = PromptSystem(spec).build()

    def parse_input(self, message: Message) -> dict[str, Any]:
        """Apply input parsing rules (deterministic validation)."""
        if message.type not in (MessageType.REQUEST, MessageType.RESPONSE, MessageType.DATA):
            return {"parsed": False, "parse_error": f"Unsupported type: {message.type}"}

        task = message.payload.get("task") or message.context.get("original_task")
        if not task and not message.payload.get("artifacts"):
            return {"parsed": False, "parse_error": "Missing task and artifacts"}

        return {
            "parsed": True,
            "task": task or "continue",
            "artifacts": message.payload.get("artifacts", {}),
            "context": message.context,
            "parse_error": None,
        }

    def format_output(self, brain_result: dict[str, Any]) -> dict[str, Any]:
        """Ensure output matches machine-readable contract."""
        required = {"status", "agent_id", "summary", "artifacts"}
        missing = required - set(brain_result.keys())
        if missing:
            return {
                "status": "error",
                "agent_id": self.spec.agent_id,
                "summary": f"Invalid output missing fields: {missing}",
                "artifacts": {"error_code": "FORMAT_ERROR"},
            }
        return brain_result

    async def handle_message(self, message: Message) -> Message | None:
        """Process one inbound message and optionally emit reply/forward."""
        parsed = self.parse_input(message)
        if not parsed.get("parsed"):
            return create_error(
                message,
                self.spec.agent_id,
                str(parsed.get("parse_error", "parse failed")),
            )

        try:
            brain_result = await self.brain.think(self.spec, self.prompts, message)
            formatted = self.format_output(brain_result)
        except Exception as exc:  # noqa: BLE001
            return create_error(
                message,
                self.spec.agent_id,
                str(exc),
                details={"error_code": "BRAIN_FAILURE"},
            )

        if formatted.get("status") == "error":
            return create_response(
                message,
                self.spec.agent_id,
                formatted,
                msg_type=MessageType.ERROR,
            )

        response = create_response(message, self.spec.agent_id, formatted)

        next_agent = formatted.get("next_agent")
        if next_agent and message.payload.get("auto_forward", True):
            forward_payload = formatted.get("forward_payload") or {
                "task": parsed.get("task"),
                "artifacts": formatted.get("artifacts", {}),
            }
            forward_msg = forward_request(
                message,
                self.spec.agent_id,
                str(next_agent),
                forward_payload,
            )
            await self.bus.send(forward_msg)

        return response

    async def run_once(self, *, timeout: float = 30.0) -> Message | None:
        """Wait for one message and handle it."""
        if isinstance(self.bus, InMemoryBus):
            inbound = await self.bus.receive(self.spec.agent_id, timeout=timeout)
        else:
            inbound = await self.bus.receive(self.spec.agent_id, timeout=timeout)
        outbound = await self.handle_message(inbound)
        if outbound is not None:
            await self.bus.send(outbound)
        return outbound

    async def run_loop(self, *, max_messages: int = 100) -> list[Message]:
        """Process up to max_messages, polling until interrupted."""
        results: list[Message] = []
        processed = 0
        while max_messages <= 0 or processed < max_messages:
            try:
                result = await self.run_once(timeout=1.0)
            except TimeoutError:
                continue
            if result is not None:
                results.append(result)
                processed += 1
        return results

    def prompt_audit(self) -> dict[str, Any]:
        """Return prompt bundle for compliance testing."""
        return {
            "agent_id": self.spec.agent_id,
            "system_len": len(self.prompts.system),
            "input_len": len(self.prompts.input_parsing),
            "output_len": len(self.prompts.output_formatting),
            "error_len": len(self.prompts.error_handling),
            "output_schema_valid": "status" in self.prompts.output_formatting,
        }
