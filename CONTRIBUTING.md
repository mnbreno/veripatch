# Contributing to VeriPatch

Thank you for contributing to VeriPatch. This project enforces strict source validation and structured iteration governance.

## Getting Started

1. Fork the repository and clone locally
2. Install backend dev dependencies: `cd backend && pip install -e ".[dev]"`
3. Run tests: `pytest tests/ -v`
4. Install wxLua for GUI development (optional)

## Development Workflow

| Branch    | Purpose                          |
|-----------|----------------------------------|
| `staging` | Active development and pre-production |
| `main`    | Stable production releases       |

Agents may commit autonomously to **`staging`** or **`main`** when changes **compile successfully** (G1). See [governance/QUALITY_GATES.md](governance/QUALITY_GATES.md) and [governance/POLICY.md](governance/POLICY.md).

## Pull Request Requirements

- All CI checks must pass (pytest, ruff, mypy, luacheck)
- Include tests for new backend logic
- Confirm compliance with [SOURCE_POLICY.md](docs/SOURCE_POLICY.md)
- Use the PR template checklist

## Iteration Governance

Every development cycle (milestone/iteration) follows these rules. The [Delegation Manager agent](governance/agents/delegation-manager.md) defines PR cadence, commit frequency, and issue workflows in detail.

See also [governance/POLICY.md](governance/POLICY.md) for timestamp and knowledge-base requirements.

### 1. Mandatory Issue Triage (Start of Cycle)

At the **start of every development iteration**, maintainers must:

- Review all open issues
- Label and prioritize each issue (`bug`, `enhancement`, `triage`, etc.)
- Assign issues to the current milestone or close as stale/duplicate
- Confirm each issue has clear acceptance criteria

### 2. Issue Resolution Before Iteration Close

Before an iteration/milestone is marked **complete**, every issue assigned to that milestone must be:

- **Resolved** and closed with a linked PR, OR
- **Updated** with a clear progress comment explaining blockers and next steps, OR
- **Closed** with justification (won't fix, duplicate, out of scope)

No issue assigned to an active iteration may remain silently stale.

### 3. Milestone Review

At iteration end:

1. Run milestone review meeting (or async review)
2. Verify all assigned issues meet the criteria above
3. Close the milestone only when all issues are accounted for
4. Document iteration summary in release notes or milestone description
5. Append a timestamped session record to `governance/knowledge-base/` per [governance/knowledge-base/INDEX.md](governance/knowledge-base/INDEX.md)

## Agent-assisted contributions

Agent-generated commits should include governance trailers:

```
Agent: <agent-id>
Timestamp: <iso8601-utc>
Milestone: <milestone-id>
```

CI validates governance artifacts via `scripts/check-governance-timestamps.py`.

## Code Standards

- Python: ruff + mypy (strict typing on public APIs)
- Lua: luacheck
- All privileged actions must write to the audit log
- Never add unofficial update sources to the registry

## Reporting Security Issues

Do not open public issues for security vulnerabilities. Contact maintainers directly.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
