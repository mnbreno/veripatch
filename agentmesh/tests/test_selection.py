"""Tests for agent selection."""

import os

from agentmesh.agent.spec import load_all_agents
from agentmesh.runtime.registry import AgentRegistry, AgentRuntimeLock, is_process_alive
from agentmesh.scheduler import default_agents_dir
from agentmesh.selection import normalize_intent, select_agent_for_intent


def test_normalize_start_development() -> None:
    assert normalize_intent("start development") == "development"
    assert normalize_intent("  START development  ") == "development"


def test_select_development_prefers_backend_architect(tmp_path) -> None:
    specs = load_all_agents(default_agents_dir())
    registry = AgentRegistry(tmp_path, known_agents=set(specs.keys()))
    selection = select_agent_for_intent("development", specs, registry)
    assert selection is not None
    assert selection.agent_id == "backend-architect"


def test_select_skips_running_agent(tmp_path) -> None:
    specs = load_all_agents(default_agents_dir())
    registry = AgentRegistry(tmp_path, known_agents=set(specs.keys()))
    registry.write_lock(
        AgentRuntimeLock(
            agent_id="backend-architect",
            pid=os.getpid(),
            started_at="now",
            command="agentmesh run backend-architect",
        )
    )
    selection = select_agent_for_intent("development", specs, registry)
    assert selection is not None
    assert selection.agent_id == "code-reviewer"
    assert "backend-architect" in selection.skipped


def test_select_none_when_all_busy(tmp_path) -> None:
    specs = load_all_agents(default_agents_dir())
    registry = AgentRegistry(tmp_path, known_agents=set(specs.keys()))
    for aid in specs:
        registry.write_lock(
            AgentRuntimeLock(
                agent_id=aid,
                pid=os.getpid(),
                started_at="now",
                command=f"agentmesh run {aid}",
            )
        )
    selection = select_agent_for_intent("development", specs, registry)
    assert selection is None


def test_is_process_alive_current_pid() -> None:
    assert is_process_alive(os.getpid()) is True
    assert is_process_alive(999999) is False
