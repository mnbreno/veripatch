# VeriPatch Knowledge Base Index

The knowledge base stores full context from agent and maintainer work sessions so future sessions can resume without re-discovery.

## Layout

| Path | Purpose |
|------|---------|
| `session-<iso8601>.json` | One record per work session (append-only) |
| `INDEX.md` | This file — catalog and retrieval guide |

## Session record schema

```json
{
  "timestamp": "2026-06-22T16:00:00.000000+00:00",
  "milestone": "v1.3.0-gap-closure",
  "agent": "delegation-manager",
  "summary": "Short outcome statement",
  "artifacts_changed": ["gui/app/ui/view_model.lua"],
  "decisions": ["Keep winget-only apply; label WUA items as informational"],
  "open_items": [],
  "next_steps": []
}
```

## Context transfer workflow

1. **Start of session** — Read this index, [agents/REGISTRY.md](../agents/REGISTRY.md), and the relevant [agents/work/](../agents/work/) doc for the active agent.
2. **During work** — Note decisions, changed paths, and blockers in working notes.
3. **End of session** — Append a new `session-<timestamp>.json` with ISO-8601 UTC `timestamp`.
4. **Cross-agent handoff** — Reference the session filename, agent `full_name` from [registry.json](../agents/registry.json), and milestone `id` in commit trailers (see [../POLICY.md](../POLICY.md)).

## Sessions

| Timestamp | Milestone | Agent | Summary |
|-----------|-----------|-------|---------|
| 2026-06-22T20:30:00.000000+00:00 | v1.3.0-stable | Quinn Morgan — Reality Checker | v1.3.0 stable: branch policy + quality gates enforced, consensus approved |
| 2026-06-22T16:00:00.000000+00:00 | v1.3.0-gap-closure | delegation-manager | Gap-closure plan implemented: accessible UI, elevation flow, governance scaffold |
