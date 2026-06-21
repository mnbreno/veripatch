# VeriPatch Source Validation Policy

VeriPatch exists to apply system updates **only through official, verified channels**. This document defines the allowlist policy enforced at runtime.

## Principles

1. **Official sources only** — No third-party package managers, download sites, or unofficial mirrors
2. **Evidence-based registry** — Every permitted source must map to a documented official update mechanism
3. **Runtime enforcement** — All commands pass through `SourceValidator` before execution
4. **Audit everything** — Approvals and rejections are logged to `.veripatch/audit.log`

## Approved Sources

### Windows

| Source ID | Mechanism | Description |
|-----------|-----------|-------------|
| `windows_update_agent` | WUA COM API | Microsoft Windows Update Agent |
| `winget` | WinGet CLI | Microsoft official package manager |
| `msstore` | Store APIs | Microsoft Store official updates |

**Blocked examples**: Chocolatey, Scoop, Ninite, direct `.exe` downloads from non-Microsoft domains

### macOS

| Source ID | Mechanism | Description |
|-----------|-----------|-------------|
| `softwareupdate` | CLI | Apple built-in `softwareupdate` utility |
| `appstore` | App Store APIs | Mac App Store official updates |

**Blocked examples**: Homebrew, MacPorts, direct DMG downloads from unofficial sites

### Linux

| Source ID | Mechanism | Distros |
|-----------|-----------|---------|
| `apt` | APT | Debian, Ubuntu, Mint, Pop!_OS |
| `dnf` | DNF | Fedora, RHEL, CentOS, Rocky, Alma |
| `pacman` | Pacman | Arch, Manjaro |
| `zypper` | Zypper | openSUSE, SUSE |

**Blocked examples**: Snap (unless added via formal review), Flatpak (unless added via formal review), third-party `.deb`/`.rpm` repositories, `curl | bash` installers

## Validation Rules

1. Command executable must exist in the registry
2. Source must be registered for the detected OS
3. On Linux, source must match the detected package manager
4. CLI arguments must match allowed prefixes for the source
5. Rejected commands are logged and never executed

## Adding New Sources

New sources require:

1. Proof of official vendor documentation
2. Security review PR with updated registry
3. Tests in `tests/backend/test_validator.py`
4. Maintainer approval

Unofficial sources will not be accepted.

## Audit Log Format

Each entry is a JSON line:

```json
{
  "timestamp": "2026-06-21T05:48:00.000000+00:00",
  "event_type": "source_rejected",
  "message": "Executable 'choco' is not in the official source registry",
  "elevated": false,
  "details": {"command": ["choco", "upgrade", "all"]}
}
```

Event types: `source_approved`, `source_rejected`, `action`, `privilege_check`
