"""Declarative multi-agent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentmesh.agent.brain import get_brain
from agentmesh.agent.spec import load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.protocol import create_request, new_correlation_id
from agentmesh.scheduler import Scheduler, default_agents_dir, register_agents


@dataclass
class WorkflowResult:
    name: str
    correlation_id: str
    final_payload: dict[str, Any] | None
    history_count: int
    steps: list[str] = field(default_factory=list)


WORKFLOWS: dict[str, dict[str, Any]] = {
    "design-review-doc": {
        "description": (
            "Sequential 4-agent chain: architect -> reviewer -> writer -> reality-checker"
        ),
        "agents": [
            "backend-architect",
            "code-reviewer",
            "technical-writer",
            "reality-checker",
        ],
        "task": "Design and document a message bus API for AgentMesh",
    },
    "parallel-ci-check": {
        "description": "Parallel fan-out: devops + architect, fan-in to reality-checker",
        "parallel": [
            ["devops-automator", "backend-architect"],
            ["reality-checker"],
        ],
        "task": "Validate CI pipeline and architecture for production readiness",
    },
}


async def run_sequential_workflow(name: str, bus: InMemoryBus | None = None) -> WorkflowResult:
    wf = WORKFLOWS[name]
    specs = load_all_agents(default_agents_dir())
    bus = bus or InMemoryBus()
    agent_ids: list[str] = wf["agents"]
    await register_agents(bus, agent_ids + ["scheduler"])

    cid = new_correlation_id()
    brain = get_brain()
    workers = [AgentWorker(specs[aid], bus, brain) for aid in agent_ids]

    # Kick off chain
    first = agent_ids[0]
    kickoff = create_request(
        "scheduler",
        first,
        {"task": wf["task"], "auto_forward": True},
        correlation_id=cid,
    )
    await bus.send(kickoff)

    steps: list[str] = []
    for worker in workers:
        try:
            result = await worker.run_once(timeout=5.0)
            if result:
                steps.append(f"{worker.spec.agent_id}:{result.type.value}")
        except TimeoutError:
            steps.append(f"{worker.spec.agent_id}:timeout")

    history = await bus.history(limit=50)
    final_payload = None
    for msg in reversed(history):
        if msg.correlation_id == cid and msg.type.value == "response":
            final_payload = msg.payload
            break

    return WorkflowResult(
        name=name,
        correlation_id=cid,
        final_payload=final_payload,
        history_count=len(history),
        steps=steps,
    )


async def run_parallel_workflow(name: str, bus: InMemoryBus | None = None) -> WorkflowResult:
    wf = WORKFLOWS[name]
    specs = load_all_agents(default_agents_dir())
    bus = bus or InMemoryBus()
    parallel_groups: list[list[str]] = wf["parallel"]
    all_agents = [aid for group in parallel_groups for aid in group]
    await register_agents(bus, all_agents + ["scheduler"])

    cid = new_correlation_id()
    brain = get_brain("scripted")
    scheduler = Scheduler(bus, max_concurrent=4, brain=brain)

    # Fan-out to first group
    fan_out_ids = parallel_groups[0]
    for aid in fan_out_ids:
        msg = create_request(
            "scheduler",
            aid,
            {"task": wf["task"], "auto_forward": False, "final": False},
            correlation_id=cid,
        )
        await bus.send(msg)

    fan_workers = [AgentWorker(specs[aid], bus, brain) for aid in fan_out_ids]
    await scheduler.run_agents_parallel(fan_workers, message_count=1)

    # Fan-in: send combined task to reality-checker
    fan_in_id = parallel_groups[1][0]
    artifacts = {}
    for msg in await bus.history(limit=20):
        if msg.correlation_id == cid and msg.sender in fan_out_ids:
            artifacts[msg.sender] = msg.payload.get("artifacts", {})

    fin_msg = create_request(
        "scheduler",
        fan_in_id,
        {"task": wf["task"], "artifacts": artifacts, "final": True},
        correlation_id=cid,
    )
    await bus.send(fin_msg)

    fin_worker = AgentWorker(specs[fan_in_id], bus, brain)
    final = await fin_worker.run_once(timeout=5.0)

    return WorkflowResult(
        name=name,
        correlation_id=cid,
        final_payload=final.payload if final else None,
        history_count=len(await bus.history()),
        steps=[f"fan-out:{fan_out_ids}", f"fan-in:{fan_in_id}"],
    )


async def run_workflow(name: str) -> WorkflowResult:
    if name not in WORKFLOWS:
        raise KeyError(f"Unknown workflow: {name}")
    wf = WORKFLOWS[name]
    if "agents" in wf:
        return await run_sequential_workflow(name)
    return await run_parallel_workflow(name)
