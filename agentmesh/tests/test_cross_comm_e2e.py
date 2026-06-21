"""End-to-end cross-agent communication tests."""

import pytest

from agentmesh.workflows import run_parallel_workflow, run_sequential_workflow


@pytest.mark.asyncio
async def test_sequential_workflow_three_plus_agents() -> None:
    result = await run_sequential_workflow("design-review-doc")
    assert result.correlation_id
    assert result.history_count >= 4
    assert len(result.steps) >= 3
    assert result.final_payload is not None
    assert result.final_payload.get("status") == "ok"
    assert result.final_payload.get("agent_id") == "reality-checker"


@pytest.mark.asyncio
async def test_parallel_fanout_fanin_workflow() -> None:
    result = await run_parallel_workflow("parallel-ci-check")
    assert result.correlation_id
    assert result.final_payload is not None
    assert "fan-out" in str(result.steps)
    assert "fan-in" in str(result.steps)


@pytest.mark.asyncio
async def test_context_preserved_across_chain() -> None:
    result = await run_sequential_workflow("design-review-doc")
    assert result.final_payload is not None
    artifacts = result.final_payload.get("artifacts", {})
    assert artifacts.get("production_ready") is True
