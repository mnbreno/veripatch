# VeriPatch

**VeriPatch** is a cross-platform desktop utility that applies system and software updates using **only official, verified sources**. It combines a native **wxLua** GUI with a **Python** backend to deliver secure, auditable update workflows on Windows, macOS, and Linux.

AgentMesh is maintained in a separate private repository and is not part of this project.

## Features

- **Official sources only** — Windows Update Agent, WinGet, Microsoft Store; macOS `softwareupdate` and App Store; Linux APT, DNF, Pacman, Zypper
- **OS detection** — Identifies OS, version, architecture, and Linux distro/package manager
- **Source validation** — Blocks third-party or unofficial update channels with audit logging
- **Native GUI** — wxLua desktop interface with update listing and dry-run apply
- **JSON-RPC backend** — Line-delimited IPC between GUI and Python backend
- **CI/CD** — Cross-platform automated testing on every pull request

## Architecture

```
gui/          wxLua frontend (native widgets)
backend/      Python backend (veripatch package)
tests/        Unit, integration, and GUI validation tests
docs/         Architecture and source policy documentation
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Requirements

- **Python** 3.11+
- **Lua** 5.4+ with **wxLua** (for GUI)
- Elevated/administrator privileges (required for real updates)

## Quick Start

### Backend (CLI / IPC server)

```bash
cd backend
pip install -e ".[dev]"

# Run JSON-RPC server on stdin/stdout
python -m veripatch

# Run tests
pytest ../tests/ -v
```

Example IPC request:

```json
{"jsonrpc":"2.0","method":"detect_os","params":{},"id":1}
```

### GUI

```bash
# Requires wxLua installed for your platform
cd gui
lua main.lua
```

Set `VERIPATCH_PYTHON` to override the Python executable used by the GUI.

## Development Workflow

| Branch    | Purpose                          |
|-----------|----------------------------------|
| `staging` | Active development               |
| `main`    | Stable production releases       |

1. Open issues and assign to a milestone/iteration
2. Create feature branches from `staging`
3. Open pull requests targeting `staging`
4. CI must pass before merge
5. Promote stable releases from `staging` → `main` via PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for iteration governance and contribution guidelines.

## Source Validation Policy

VeriPatch **never** downloads or installs software from unofficial sources. All update commands must pass through the official source registry. See [docs/SOURCE_POLICY.md](docs/SOURCE_POLICY.md).

## Status

**v1.3.0** — stable release (gap-closure, governance policies, mandatory quality gates).

- Cross-platform OS detection (Windows, macOS, Linux with APT/DNF/Pacman/Zypper)
- Official source registry with command validation (blocks unofficial update channels)
- Accessible GUI with tooltips, plain language, and one-click elevation on Windows
- Near-full agent autonomy: commits allowed on `staging`/`main` when G1 compilation passes
- Mandatory CI quality gates G1-G8 (100% compile, 90%+ unit pass, integration, static analysis)

Set `VERIPATCH_DRY_RUN=1` to force dry-run mode for the backend IPC server.

Real apply requires `confirm=true`, `confirm_token=veripatch-confirm-apply`, and elevated privileges.

See [CHANGELOG.md](CHANGELOG.md) for release history.

Stable releases publish a Windows installer after agent consensus validation. See [docs/RELEASE.md](docs/RELEASE.md) for the release process.

## License

MIT — see [LICENSE](LICENSE).
