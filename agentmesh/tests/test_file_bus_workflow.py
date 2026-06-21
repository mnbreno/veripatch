"""FileBus workflow dispatch tests."""

import asyncio

import pytest

from agentmesh.agent.brain import ScriptedBrain
from agentmesh.agent.spec import load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.file_bus import FileBus
from agentmesh.scheduler import default_agents_dir
from agentmesh.workflows import run_sequential_workflow_file_bus


@pytest.mark.asyncio
async def test_file_bus_sequential_workflow(tmp_path) -> None:
    bus = FileBus(tmp_path / "bus")
    specs = load_all_agents(default_agents_dir())
    agent_ids = [
        "backend-architect",
        "code-reviewer",
        "technical-writer",
        "reality-checker",
    ]
    brain = ScriptedBrain()
    workers = [AgentWorker(specs[aid], bus, brain) for aid in agent_ids]

    async def run_agents() -> None:
        await asyncio.gather(*[worker.run_loop(max_messages=1) for worker in workers])

    agent_task = asyncio.create_task(run_agents())
    result = await run_sequential_workflow_file_bus(
        "design-review-doc",
        bus=bus,
        timeout=30.0,
        poll_interval=0.2,
    )
    await agent_task

    assert result.final_payload is not None
    assert result.final_payload.get("agent_id") == "reality-checker"
    assert len(result.steps) >= 4
