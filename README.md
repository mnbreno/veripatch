# VeriPatch

**VeriPatch** is a cross-platform desktop utility that applies system and software updates using **only official, verified sources**. It combines a native **wxLua** GUI with a **Python** backend to deliver secure, auditable update workflows on Windows, macOS, and Linux.

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
- Elevated/administrator privileges (required for real updates; stubbed in v0.1.0)

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

This is the **v0.1.0 foundation release**:

- OS detection, source validation, and audit logging are fully implemented
- Update execution is **stubbed** with dry-run support
- Real privileged update execution is planned for a future iteration

## License

MIT — see [LICENSE](LICENSE).
