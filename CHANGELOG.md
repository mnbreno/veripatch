# Changelog

All notable changes to this project are documented here.

## [1.0.0] — 2026-06-21

### VeriPatch — Stable release

- Real update execution via official CLIs (WinGet, softwareupdate, APT/DNF/Pacman/Zypper)
- `CommandRunner` with source validation, dry-run, timeouts, and audit logging
- Elevation detection with apply gating (confirmation token + admin/root)
- `diagnostics` JSON-RPC method and structured logging (`VERIPATCH_LOG`)
- Headless GUI view-model tests (busted)
- Cross-platform CI: pytest, ruff, mypy, luacheck, busted

### AgentMesh — Initial release (0.1.0)

- Asyncio multi-agent system with structured messaging protocol
- Five agency-aligned agents with prompt system and scripted brain
- In-memory and file-based message buses for single- and multi-terminal dev
- Interactive CLI (`start development`, `status`, `orchestrate`)
- Workflows: `design-review-doc`, `parallel-ci-check`
- Windows console encoding fixes and persistent agent listen loop
- Test isolation from developer runtime locks; 75%+ coverage gate
- Tightened Pacman flag validation (reject `-S` install; allow combined `-Syu`)
- Expanded VeriPatch test coverage (104 tests): protocol, pacman/dnf/zypper parsers

## [0.2.0] — Prior release

- Real execution infrastructure, elevation, observability, GUI tests

## [0.1.0] — Foundation

- JSON-RPC backend, source registry, wxLua GUI shell, OS detection
