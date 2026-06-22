# Taylor Kim — Parallel Scheduler

**Agent ID:** `scheduler`  
**Role:** Parallel Scheduler  
**Last updated:** `2026-06-22T18:00:00.000000+00:00`

## Fast context

Runs parallel agent execution in in-memory AgentMesh workflows. Pseudo-sender for workflow kickoffs when FileBus is not used.

## When to invoke

- `parallel-ci-check` workflow
- Concurrent agent tasks that do not require file-bus persistence
- Local development sessions with `agentmesh start`

## Key repository paths

| Path | Purpose |
|------|---------|
| `agentmesh/agentmesh/scheduler.py` | Parallel execution (private submodule) |
| `agentmesh/agentmesh/workflows.py` | Workflow definitions |
| `.agentmesh/run/*.lock.json` | Running agent PID locks |

## Deliverables

- Parallel workflow execution results
- Kickoff messages as sender `scheduler`
- Workflow correlation IDs for downstream consensus

## Agent relationships

| Direction | Agent |
|-----------|-------|
| Alternative to | Nova Ashford — Workflow Orchestrator (in-memory vs file bus) |
| Schedules | backend-architect, code-reviewer, devops-automator, technical-writer, reality-checker |

## Full specification

[scheduler.md](../scheduler.md)
