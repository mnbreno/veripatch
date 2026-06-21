"""Tests for LLM brain and OpenAI-compatible client."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from agentmesh.agent.brain import LLMBrain, ScriptedBrain, get_brain
from agentmesh.agent.llm_client import chat_completions_sync, extract_json_object
from agentmesh.agent.prompts import PromptSystem
from agentmesh.agent.spec import load_agent_spec
from agentmesh.protocol import Message, MessageType, create_request
from agentmesh.scheduler import default_agents_dir


def test_extract_json_object_raw() -> None:
    assert extract_json_object('{"status": "ok"}') == {"status": "ok"}


def test_extract_json_object_markdown_fence() -> None:
    text = 'Here is output:\n```json\n{"status": "ok", "artifacts": {}}\n```'
    assert extract_json_object(text) == {"status": "ok", "artifacts": {}}


def test_extract_json_object_embedded() -> None:
    text = 'Result: {"status": "ok", "summary": "done"} thanks'
    assert extract_json_object(text)["summary"] == "done"


def test_get_brain_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTMESH_BRAIN", "llm")
    assert isinstance(get_brain(), LLMBrain)


@pytest.mark.asyncio
async def test_llm_brain_openai_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_agent_spec(default_agents_dir() / "backend-architect.md")
    prompts = PromptSystem(spec).build()
    message = create_request("orchestrator", "backend-architect", {"task": "Design auth API"})
    monkeypatch.setenv("AGENTMESH_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AGENTMESH_LLM_BASE_URL", "http://10.5.0.2:1234/v1")
    monkeypatch.setenv("AGENTMESH_LLM_MODEL", "qwen/qwen3.5-9b")

    llm_payload = {
        "status": "ok",
        "agent_id": "backend-architect",
        "summary": "Auth API design complete",
        "artifacts": {"architecture": "JWT + refresh tokens"},
        "next_agent": "code-reviewer",
    }

    async def fake_chat(**kwargs: object) -> str:
        return json.dumps(llm_payload)

    brain = LLMBrain()
    with patch("agentmesh.agent.brain.chat_completions", fake_chat):
        result = await brain.think(spec, prompts, message)

    assert result["status"] == "ok"
    assert result["agent_id"] == "backend-architect"
    assert result["artifacts"]["architecture"] == "JWT + refresh tokens"
    assert result["next_agent"] == "code-reviewer"


@pytest.mark.asyncio
async def test_llm_brain_injects_chain_forward(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_agent_spec(default_agents_dir() / "backend-architect.md")
    prompts = PromptSystem(spec).build()
    message = create_request(
        "orchestrator",
        "backend-architect",
        {"task": "Design auth API", "auto_forward": True},
    )
    monkeypatch.setenv("AGENTMESH_LLM_PROVIDER", "openai")

    llm_payload = {
        "status": "ok",
        "agent_id": "backend-architect",
        "summary": "Done",
        "artifacts": {"architecture": "JWT"},
    }

    async def fake_chat(**kwargs: object) -> str:
        return json.dumps(llm_payload)

    brain = LLMBrain()
    with patch("agentmesh.agent.brain.chat_completions", fake_chat):
        result = await brain.think(spec, prompts, message)

    assert result["next_agent"] == "code-reviewer"
    assert result["forward_payload"]["task"] == "Design auth API"


@pytest.mark.asyncio
async def test_llm_brain_overrides_bad_next_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_agent_spec(default_agents_dir() / "code-reviewer.md")
    prompts = PromptSystem(spec).build()
    message = create_request(
        "backend-architect",
        "code-reviewer",
        {"task": "Review design", "auto_forward": True},
    )
    monkeypatch.setenv("AGENTMESH_LLM_PROVIDER", "openai")

    llm_payload = {
        "status": "ok",
        "agent_id": "code-reviewer",
        "summary": "Reviewed",
        "artifacts": {"review": "ok"},
        "next_agent": "orchestrator",
    }

    async def fake_chat(**kwargs: object) -> str:
        return json.dumps(llm_payload)

    brain = LLMBrain()
    with patch("agentmesh.agent.brain.chat_completions", fake_chat):
        result = await brain.think(spec, prompts, message)

    assert result["next_agent"] == "technical-writer"


@pytest.mark.asyncio
async def test_llm_brain_falls_back_when_provider_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = load_agent_spec(default_agents_dir() / "code-reviewer.md")
    prompts = PromptSystem(spec).build()
    message = create_request("orchestrator", "code-reviewer", {"task": "Review auth module"})
    monkeypatch.setenv("AGENTMESH_LLM_PROVIDER", "none")

    brain = LLMBrain()
    scripted = await ScriptedBrain().think(spec, prompts, message)
    result = await brain.think(spec, prompts, message)
    assert result["status"] == scripted["status"]
    assert result["agent_id"] == scripted["agent_id"]


def test_chat_completions_sync_parses_response() -> None:
    payload = {
        "choices": [{"message": {"content": '{"status":"ok","artifacts":{}}'}}],
    }

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        content = chat_completions_sync(
            base_url="http://10.5.0.2:1234/v1",
            model="qwen/qwen3.5-9b",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert extract_json_object(content)["status"] == "ok"
