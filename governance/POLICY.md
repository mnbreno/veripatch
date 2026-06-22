# VeriPatch Agent Governance Policy

This policy governs all agent-assisted work on VeriPatch. It applies to human maintainers and to any AI agent operating in this repository.

## 1. Machine-readable timestamps (audit trail)

Every agent-generated artifact **must** include a precise, machine-readable UTC timestamp in ISO-8601 format (`YYYY-MM-DDTHH:MM:SS.ssssss+00:00`).

### Required on

| Artifact type | Timestamp field | Location |
|---------------|-----------------|----------|
| Knowledge-base session records | `timestamp` | `governance/knowledge-base/session-*.json` |
| Milestone definitions | `start`, `due` | `governance/milestones/*.json` |
| Release consensus | `generated_at` | `release/consensus/v*.json` |
| Cross-agent messages | `timestamp` | `.agentmesh/bus/history.jsonl` (when AgentMesh is used) |
| Governance policy updates | `last_updated` | Front matter in this file |

### Git commit trailer convention

Agent-assisted commits **should** include these trailers in the commit message body:

```
Agent: <agent-id>
Timestamp: <iso8601-utc>
Milestone: <milestone-id>
```

Example:

```
feat(gui): add tooltips to update buttons

Agent: delegation-manager
Timestamp: 2026-06-22T15:30:00.000000+00:00
Milestone: v1.3.0-gap-closure
```

## 2. Time-bound milestones

All project work must be tied to a milestone under `governance/milestones/`. Each milestone file is JSON with:

- `id` — unique milestone identifier
- `goal` — outcome statement
- `start` — ISO-8601 UTC start time
- `due` — ISO-8601 UTC deadline
- `owner_agent` — responsible agent or role
- `exit_criteria` — list of measurable completion checks

Milestones are reviewed at iteration close (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## 3. Shared knowledge base

Full session context is persisted under `governance/knowledge-base/` as append-only JSON records named `session-<timestamp>.json`. See [governance/knowledge-base/INDEX.md](knowledge-base/INDEX.md) for retrieval and context-transfer workflow.

## 4. Delegation agent

Repository workflow rules (PR cadence, commit frequency, issue triage) are defined by **Jordan Hale — Delegation Manager** ([agents/delegation-manager.md](agents/delegation-manager.md)). All agents defer to that agent for repository activity scheduling.

## 5. Agent registry

All agents have hardcoded display names (name + role) in [agents/registry.json](agents/registry.json). Fast context retrieval docs live under [agents/work/](agents/work/). See [agents/REGISTRY.md](agents/REGISTRY.md) for the full roster.

## 6. CI enforcement

`scripts/check-governance-timestamps.py` runs in CI and fails when governance artifacts are missing required timestamps.

## 7. Agent autonomy

VeriPatch is a simple application; agents operate with **near-full autonomy**. Agent-driven commits may target **`staging`**, **`main`**, or any branch without restriction.

**Prerequisite:** changes must pass **G1 compilation (100%)** before commit or merge. Run `python scripts/run-compile-gate.py` or `python scripts/run-quality-gates.py` locally.

Recommended (not blocking): include governance commit trailers (`Agent:`, `Timestamp:`, `Milestone:`) for audit trail.

## 8. Quality gates

All promotion to staging and production requires passing gates G1–G8 documented in [QUALITY_GATES.md](QUALITY_GATES.md), including:

- **G1:** 100% compilation success (blocks pipeline on any failure)
- **G2:** ≥ 90% unit test pass rate
- **G3:** 100% integration test pass
- **G4:** Zero critical/high static analysis findings
- **G6:** Engineering lead manual approval (`staging-promotion` environment)
- **G7:** Release manager manual approval (`production-release` environment)
- **G8:** Agent release consensus JSON

Local verification: `python scripts/run-quality-gates.py`

---

`last_updated`: `2026-06-22T21:00:00.000000+00:00`
