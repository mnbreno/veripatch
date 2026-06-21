"""Tests for agent runtime registry."""

from agentmesh.runtime.registry import AgentRegistry, AgentRuntimeLock, is_process_alive


def test_acquire_and_release(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    lock = registry.acquire("backend-architect", command="test")
    assert lock.agent_id == "backend-architect"
    assert registry.is_running("backend-architect", include_process_scan=False)
    registry.release("backend-architect")
    assert not registry.is_running("backend-architect", include_process_scan=False)


def test_acquire_rejects_duplicate(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    registry.acquire("backend-architect")
    try:
        registry.acquire("backend-architect")
        raised = False
    except RuntimeError:
        raised = True
    finally:
        registry.release("backend-architect")
    assert raised


def test_stale_lock_removed(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    dead_pid = 999999
    registry.write_lock(
        AgentRuntimeLock(
            agent_id="backend-architect",
            pid=dead_pid,
            started_at="old",
            command="dead",
        )
    )
    assert not is_process_alive(dead_pid)
    registry.cleanup_stale()
    assert registry.read_lock("backend-architect") is None


def test_running_from_locks(tmp_path) -> None:
    registry = AgentRegistry(tmp_path, known_agents={"a", "b"})
    registry.acquire("a")
    running = registry.running_from_locks()
    assert running == {"a"}
