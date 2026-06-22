# VeriPatch Agent Registry

Canonical list of agents with **hardcoded display names** (name + role). Machine-readable source: [registry.json](registry.json).

| Full name | Agent ID | Role | Release gate | Work doc |
|-----------|----------|------|--------------|----------|
| Jordan Hale — Delegation Manager | `delegation-manager` | Delegation Manager | — | [work/delegation-manager.md](work/delegation-manager.md) |
| Morgan Chen — Backend Architect | `backend-architect` | Backend Architect | — | [work/backend-architect.md](work/backend-architect.md) |
| Alex Rivera — Code Reviewer | `code-reviewer` | Code Reviewer | **required** | [work/code-reviewer.md](work/code-reviewer.md) |
| Riley Santos — DevOps Automator | `devops-automator` | DevOps Automator | **required** | [work/devops-automator.md](work/devops-automator.md) |
| Casey Brooks — Technical Writer | `technical-writer` | Technical Writer | — | [work/technical-writer.md](work/technical-writer.md) |
| Quinn Morgan — Reality Checker | `reality-checker` | Reality Checker | **required** | [work/reality-checker.md](work/reality-checker.md) |
| Nova Ashford — Workflow Orchestrator | `orchestrator` | Workflow Orchestrator | — | [work/orchestrator.md](work/orchestrator.md) |
| Taylor Kim — Parallel Scheduler | `scheduler` | Parallel Scheduler | — | [work/scheduler.md](work/scheduler.md) |

## Fast retrieval

1. Load [registry.json](registry.json) for IDs, roles, and `work_doc` paths.
2. Open the agent's `work/*.md` file for session context, key paths, and deliverables.
3. Open `spec_doc` (same folder, without `work/`) for full personality and rules.

## Release gate agents

`scripts/validate-release-consensus.py` requires verdicts from:

- Riley Santos — DevOps Automator (`devops-automator`)
- Alex Rivera — Code Reviewer (`code-reviewer`)
- Quinn Morgan — Reality Checker (`reality-checker`)

---

`last_updated`: `2026-06-22T18:00:00.000000+00:00`
