"""Tests for CLI and interactive REPL helpers."""

import argparse
from unittest.mock import AsyncMock, patch

import pytest

from agentmesh.bootstrap import run_bootstrap
from agentmesh.cli import cmd_bootstrap, cmd_list, cmd_start
from agentmesh.interactive import handle_list, handle_start_intent, handle_status
from agentmesh.launcher import should_spawn_external, start_intent
from agentmesh.paths import ensure_runtime_dirs, find_repo_root
from agentmesh.runtime.registry import get_registry
from agentmesh.selection import normalize_intent


def test_cmd_list_shows_agents(capsys) -> None:
    assert cmd_list(argparse.Namespace()) == 0
    output = capsys.readouterr().out
    assert "backend-architect" in output
    assert "design-review-doc" in output


def test_handle_status_when_idle(capsys) -> None:
    handle_status()
    assert "No agents currently running" in capsys.readouterr().out


def test_handle_list_shows_runtime_root(capsys) -> None:
    handle_list()
    output = capsys.readouterr().out
    assert "backend-architect" in output
    assert "Runtime locks:" in output


def test_normalize_unknown_command() -> None:
    assert normalize_intent("deploy rockets") is None


def test_should_spawn_external_in_vscode(monkeypatch) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.delenv("AGENTMESH_SPAWN_EXTERNAL", raising=False)
    monkeypatch.delenv("AGENTMESH_IN_TERMINAL", raising=False)
    assert should_spawn_external() is False


def test_should_spawn_external_force_here(monkeypatch) -> None:
    monkeypatch.setenv("AGENTMESH_SPAWN_EXTERNAL", "1")
    assert should_spawn_external(force_here=True) is False


@pytest.mark.asyncio
async def test_handle_start_development_spawns_external(capsys, monkeypatch) -> None:
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.setenv("AGENTMESH_SPAWN_EXTERNAL", "1")
    with patch("agentmesh.launcher.spawn_agent_in_new_terminal") as spawn:
        code = await handle_start_intent("development")
    assert code == 0
    spawn.assert_called_once()
    output = capsys.readouterr().out
    assert "Selected:" in output
    assert "backend-architect" in output


@pytest.mark.asyncio
async def test_start_intent_runs_in_terminal_in_vscode(capsys, monkeypatch) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    with patch(
        "agentmesh.launcher.run_agent_in_current_terminal",
        new_callable=AsyncMock,
        return_value=0,
    ) as run_here:
        code, agent_id = await start_intent("development")
    assert code == 0
    assert agent_id == "backend-architect"
    run_here.assert_called_once_with("backend-architect", max_messages=100)


@pytest.mark.asyncio
async def test_cmd_start_development_here(capsys, monkeypatch) -> None:
    with patch(
        "agentmesh.launcher.run_agent_in_current_terminal",
        new_callable=AsyncMock,
        return_value=0,
    ) as run_here:
        args = argparse.Namespace(
            intent="development",
            here=True,
            spawn=False,
            max_messages=50,
        )
        code = await cmd_start(args)
    assert code == 0
    run_here.assert_called_once_with("backend-architect", max_messages=50)


@pytest.mark.asyncio
async def test_handle_start_when_all_agents_busy(capsys) -> None:
    from agentmesh.agent.spec import load_all_agents
    from agentmesh.scheduler import default_agents_dir

    specs = load_all_agents(default_agents_dir())
    with patch("agentmesh.launcher.get_registry") as get_reg:
        registry = get_reg.return_value
        registry.active_agents.return_value = set(specs.keys())
        registry.cleanup_stale.return_value = None
        code = await handle_start_intent("development")
    assert code == 1
    assert "already running" in capsys.readouterr().out.lower()


def test_normalize_review_intent() -> None:
    assert normalize_intent("start review") == "review"


def test_get_registry_singleton_shape() -> None:
    registry = get_registry(known_agents={"backend-architect"})
    assert registry.known_agents == {"backend-architect"}


def test_scan_process_table_detects_agent(tmp_path, monkeypatch) -> None:
    from agentmesh.runtime.registry import AgentRegistry

    monkeypatch.delenv("AGENTMESH_SKIP_PROCESS_SCAN", raising=False)
    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    monkeypatch.setattr(
        "agentmesh.runtime.registry._iter_process_commands",
        lambda: [(9998, "python -m agentmesh.cli run backend-architect --file-bus")],
    )
    found = registry.scan_process_table()
    assert "backend-architect" in found


@pytest.mark.asyncio
async def test_cmd_run_rejects_duplicate_file_bus(tmp_path, monkeypatch) -> None:
    from agentmesh.cli import cmd_run
    from agentmesh.runtime.registry import AgentRegistry

    monkeypatch.setenv("AGENTMESH_BUS_ROOT", str(tmp_path / "bus"))
    monkeypatch.setenv("AGENTMESH_RUNTIME_ROOT", str(tmp_path / "run"))
    registry = AgentRegistry(tmp_path / "run", known_agents={"backend-architect"})
    registry.acquire("backend-architect")

    args = argparse.Namespace(
        agent="backend-architect",
        once=False,
        file_bus=True,
        timeout=1.0,
        max_messages=1,
    )
    code = await cmd_run(args)
    assert code == 1


def test_handle_status_shows_running_agent(capsys, tmp_path) -> None:
    from agentmesh.runtime.registry import AgentRegistry, AgentRuntimeLock

    registry = AgentRegistry(tmp_path, known_agents={"backend-architect"})
    registry.write_lock(
        AgentRuntimeLock(
            agent_id="backend-architect",
            pid=__import__("os").getpid(),
            started_at="now",
            command="test",
            terminal_session="console",
        )
    )
    with patch("agentmesh.interactive.get_registry", return_value=registry):
        handle_status()
    output = capsys.readouterr().out
    assert "backend-architect" in output
    assert "PID" in output


def test_find_repo_root() -> None:
    root = find_repo_root()
    assert (root / "agentmesh" / "pyproject.toml").is_file()


def test_ensure_runtime_dirs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTMESH_BUS_ROOT", str(tmp_path / "bus"))
    monkeypatch.setenv("AGENTMESH_RUNTIME_ROOT", str(tmp_path / "run"))
    bus, runtime = ensure_runtime_dirs()
    assert bus.is_dir()
    assert runtime.is_dir()
    assert (bus / "inboxes").is_dir()


def test_bootstrap_no_install(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agentmesh" / "agentmesh" / "agents").mkdir(parents=True)
    (tmp_path / "agentmesh" / "pyproject.toml").write_text("[project]\nname='agentmesh'\n")
    monkeypatch.setenv("AGENTMESH_BUS_ROOT", str(tmp_path / ".agentmesh" / "bus"))
    monkeypatch.setenv("AGENTMESH_RUNTIME_ROOT", str(tmp_path / ".agentmesh" / "run"))
    code = run_bootstrap(install=False)
    assert code == 0
    assert "READY" in capsys.readouterr().out


def test_cmd_bootstrap_no_install(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agentmesh" / "agentmesh" / "agents").mkdir(parents=True)
    (tmp_path / "agentmesh" / "pyproject.toml").write_text("[project]\nname='agentmesh'\n")
    args = argparse.Namespace(no_install=True)
    code = cmd_bootstrap(args)
    assert code == 0


@pytest.mark.asyncio
async def test_run_agent_in_current_terminal(tmp_path, monkeypatch) -> None:
    from agentmesh.launcher import run_agent_in_current_terminal

    monkeypatch.setenv("AGENTMESH_BUS_ROOT", str(tmp_path / "bus"))
    monkeypatch.setenv("AGENTMESH_RUNTIME_ROOT", str(tmp_path / "run"))
    with patch("agentmesh.launcher.AgentWorker") as worker_cls:
        worker_cls.return_value.run_loop = AsyncMock(return_value=[])
        code = await run_agent_in_current_terminal("backend-architect", max_messages=5)
    assert code == 0
    worker_cls.return_value.run_loop.assert_called_once_with(max_messages=5)

