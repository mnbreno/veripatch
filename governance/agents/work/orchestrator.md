# Nova Ashford — Workflow Orchestrator

**Agent ID:** `orchestrator`  
**Role:** Workflow Orchestrator  
**Last updated:** `2026-06-22T18:00:00.000000+00:00`

## Fast context

Dispatches multi-agent workflows over the AgentMesh file bus. Sends kickoff messages to specialist agents and routes responses. Pseudo-sender in FileBus mode (not a long-running worker process).

## When to invoke

- Starting `design-review-doc` or `veripatch-release-gate` workflows
- Routing tasks between specialist agents
- Correlating cross-agent message chains via `correlation_id`

## Key repository paths

| Path | Purpose |
|------|---------|
| `.agentmesh/bus/history.jsonl` | Append-only message audit log |
| `.agentmesh/bus/inboxes/` | Per-agent message inboxes |
| `agentmesh/` | AgentMesh package (private submodule) |
| `governance/agents/registry.json` | Agent roster |

## Deliverables

- Workflow kickoff messages with `correlation_id`
- Task routing to specialist agents
- Trace chains preserved in bus `history.jsonl`

## Agent relationships

| Direction | Agent |
|-----------|-------|
| Dispatches to | All specialist agents |
| Defers scheduling to | Jordan Hale — Delegation Manager |
| Parallel runs via | Taylor Kim — Parallel Scheduler |

## Message conventions

- Every message includes ISO-8601 `timestamp`
- `context.prior_sender` and `context.original_task` preserved across hops
- `trace` array links message IDs for audit

## Full specification

[orchestrator.md](../orchestrator.md)
