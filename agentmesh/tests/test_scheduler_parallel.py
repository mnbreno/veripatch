"""Parallel vs sequential scheduler throughput tests."""

import pytest

from agentmesh.agent.brain import ScriptedBrain
from agentmesh.agent.spec import load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.protocol import create_request
from agentmesh.scheduler import Scheduler, default_agents_dir, register_agents


@pytest.mark.asyncio
async def test_parallel_faster_than_sequential() -> None:
    specs = load_all_agents(default_agents_dir())
    agent_ids = list(specs.keys())[:4]
    bus = InMemoryBus()
    await register_agents(bus, agent_ids + ["scheduler"])

    brain = ScriptedBrain(latency_ms=50.0)
    workers = [AgentWorker(specs[aid], bus, brain) for aid in agent_ids]

    for aid in agent_ids:
        payload = {"task": f"work-{aid}", "auto_forward": False}
        await bus.send(create_request("scheduler", aid, payload))

    sched = Scheduler(bus, max_concurrent=4, brain=brain)
    parallel = await sched.run_agents_parallel(workers, message_count=1)
    assert not parallel.errors

    bus2 = InMemoryBus()
    await register_agents(bus2, agent_ids + ["scheduler"])
    workers2 = [AgentWorker(specs[aid], bus2, brain) for aid in agent_ids]
    for aid in agent_ids:
        payload = {"task": f"work-{aid}", "auto_forward": False}
        await bus2.send(create_request("scheduler", aid, payload))

    sequential = await sched.run_agents_sequential(workers2, message_count=1)
    assert not sequential.errors

    # Parallel should complete meaningfully faster with 4 agents @ 50ms each
    assert parallel.elapsed_seconds < sequential.elapsed_seconds * 0.85


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency() -> None:
    bus = InMemoryBus()
    specs = load_all_agents(default_agents_dir())
    agent_ids = list(specs.keys())
    await register_agents(bus, agent_ids + ["scheduler"])

    brain = ScriptedBrain(latency_ms=30.0)
    workers = [AgentWorker(specs[aid], bus, brain) for aid in agent_ids]
    sched = Scheduler(bus, max_concurrent=2, brain=brain)

    for aid in agent_ids:
        await bus.send(create_request("scheduler", aid, {"task": "x", "auto_forward": False}))

    result = await sched.run_agents_parallel(workers, message_count=1)
    assert len(result.outputs) == len(agent_ids)
