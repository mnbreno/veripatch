# Changelog

All notable changes to this project are documented here.

## [1.1.0] — 2026-06-21

### VeriPatch

- Persistent JSON-RPC sessions with `shutdown` method and request tracking
- Python `JsonRpcClient` for multi-call backend sessions
- **`apply_updates_stream`** RPC with `apply_progress` notifications during apply
- `CommandRunner.run_streaming()` and `Updater.apply_streaming()` for live output
- **`request_elevation`** RPC with platform-specific guidance and optional UAC spawn (Windows)
- `detect_os` includes structured `elevation` guidance when not privileged
- Cross-platform stderr redirect in wxLua IPC client (Linux/macOS/Windows)
- `diagnostics` includes session `requests_served` during persistent sessions

## [1.0.0] — 2026-06-21

### VeriPatch — Stable release

- Real update execution via official CLIs (WinGet, softwareupdate, APT/DNF/Pacman/Zypper)
- `CommandRunner` with source validation, dry-run, timeouts, and audit logging
- Elevation detection with apply gating (confirmation token + admin/root)
- `diagnostics` JSON-RPC method and structured logging (`VERIPATCH_LOG`)
- Headless GUI view-model tests (busted)
- Cross-platform CI: pytest, ruff, mypy, luacheck, busted
- Tightened Pacman flag validation (reject `-S` install; allow combined `-Syu`)
- Expanded test coverage (104 tests): protocol, pacman/dnf/zypper parsers

## [0.2.0] — Prior release

- Real execution infrastructure, elevation, observability, GUI tests

## [0.1.0] — Foundation

- JSON-RPC backend, source registry, wxLua GUI shell, OS detection
