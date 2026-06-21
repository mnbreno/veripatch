"""Pluggable agent brain backends."""

from __future__ import annotations

import asyncio
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Any

from agentmesh.agent.prompts import PromptBundle
from agentmesh.agent.spec import AgentSpec
from agentmesh.protocol import Message


class Brain(ABC):
    """Executes agent reasoning from prompts and inbound message."""

    @abstractmethod
    async def think(
        self,
        spec: AgentSpec,
        prompts: PromptBundle,
        message: Message,
    ) -> dict[str, Any]:
        """Return structured output dict matching the output contract."""


class ScriptedBrain(Brain):
    """Deterministic offline brain with optional simulated latency."""

    def __init__(self, latency_ms: float = 0.0) -> None:
        self.latency_ms = latency_ms

    async def think(
        self,
        spec: AgentSpec,
        prompts: PromptBundle,
        message: Message,
    ) -> dict[str, Any]:
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        task = str(message.payload.get("task", message.context.get("original_task", "unknown")))
        seed = hashlib.sha256(f"{spec.agent_id}:{task}".encode()).hexdigest()[:8]

        artifacts = self._role_artifacts(spec.agent_id, task, message)
        next_agent = self._next_agent(spec.agent_id, message)

        result: dict[str, Any] = {
            "status": "ok",
            "agent_id": spec.agent_id,
            "summary": f"{spec.name} completed: {task[:80]}",
            "artifacts": artifacts,
        }
        if next_agent:
            result["next_agent"] = next_agent
            result["forward_payload"] = {
                "task": task,
                "ctx_seed": seed,
                **{k: v for k, v in message.context.items()},
                "artifacts": artifacts,
            }
        return result

    def _role_artifacts(self, agent_id: str, task: str, message: Message) -> dict[str, Any]:
        prior = message.payload.get("artifacts") or message.context.get("artifacts") or {}
        base = {"task_echo": task, "prior_artifacts": prior}
        role_outputs = {
            "backend-architect": {
                "architecture": f"Design for: {task}",
                "services": ["api", "worker", "store"],
                "api_contract": "openapi-3.1",
            },
            "code-reviewer": {
                "review": "approved_with_notes",
                "findings": ["Add input validation", "Document error paths"],
                "severity": "low",
            },
            "devops-automator": {
                "pipeline": ["lint", "test", "build"],
                "ci_matrix": ["ubuntu", "macos", "windows"],
            },
            "technical-writer": {
                "doc_outline": ["Overview", "Setup", "API", "Testing"],
                "readme_section": f"Documentation for: {task}",
            },
            "reality-checker": {
                "production_ready": True,
                "blockers": [],
                "checklist_passed": 8,
                "checklist_total": 8,
            },
        }
        base.update(role_outputs.get(agent_id, {"output": f"{agent_id} processed task"}))  # type: ignore[call-overload]
        return base

    def _next_agent(self, agent_id: str, message: Message) -> str | None:
        if message.payload.get("final"):
            return None
        chain = {
            "backend-architect": "code-reviewer",
            "code-reviewer": "technical-writer",
            "technical-writer": "reality-checker",
            "devops-automator": "reality-checker",
        }
        return chain.get(agent_id)


class LLMBrain(Brain):
    """Optional LLM adapter (stub — wire to provider via env)."""

    async def think(
        self,
        spec: AgentSpec,
        prompts: PromptBundle,
        message: Message,
    ) -> dict[str, Any]:
        provider = os.environ.get("AGENTMESH_LLM_PROVIDER", "none")
        if provider == "none":
            # Fallback to scripted for offline safety
            return await ScriptedBrain().think(spec, prompts, message)
        raise NotImplementedError(
            f"LLMBrain provider '{provider}' is not configured. Use AGENTMESH_BRAIN=scripted."
        )


def get_brain(name: str | None = None) -> Brain:
    brain_name = (name or os.environ.get("AGENTMESH_BRAIN", "scripted")).lower()
    latency = float(os.environ.get("AGENTMESH_BRAIN_LATENCY_MS", "0"))
    if brain_name == "scripted":
        return ScriptedBrain(latency_ms=latency)
    if brain_name == "llm":
        return LLMBrain()
    raise ValueError(f"Unknown brain: {brain_name}")
