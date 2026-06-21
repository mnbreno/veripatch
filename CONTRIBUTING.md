# Contributing to VeriPatch

Thank you for contributing to VeriPatch. This project enforces strict source validation and structured iteration governance.

## Getting Started

1. Fork the repository and clone locally
2. Install backend dev dependencies: `cd backend && pip install -e ".[dev]"`
3. Run tests: `pytest tests/ -v`
4. Install wxLua for GUI development (optional)

## Branch Strategy

- **`staging`** — All feature development merges here first
- **`main`** — Production/stable releases only; no direct pushes

Create feature branches from `staging` and open PRs targeting `staging`.

## Pull Request Requirements

- All CI checks must pass (pytest, ruff, mypy, luacheck)
- Include tests for new backend logic
- Confirm compliance with [SOURCE_POLICY.md](docs/SOURCE_POLICY.md)
- Use the PR template checklist

## Iteration Governance

Every development cycle (milestone/iteration) follows these rules:

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

## Code Standards

- Python: ruff + mypy (strict typing on public APIs)
- Lua: luacheck
- All privileged actions must write to the audit log
- Never add unofficial update sources to the registry

## Reporting Security Issues

Do not open public issues for security vulnerabilities. Contact maintainers directly.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
