"""Additional registry coverage."""

import os

from agentmesh.runtime.registry import AgentRegistry, get_registry


def test_active_agents_combines_sources(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect", "code-reviewer"})
    registry.acquire("backend-architect")
    active = registry.active_agents()
    assert "backend-architect" in active


def test_hold_until_exit_releases_on_teardown(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    lock = registry.hold_until_exit("backend-architect", command="test")
    assert lock.pid == os.getpid()
    registry.release("backend-architect")
    assert not registry.is_running("backend-architect", include_process_scan=False)


def test_get_registry_default_root() -> None:
    registry = get_registry()
    assert registry.root.name == "run" or "run" in str(registry.root)
