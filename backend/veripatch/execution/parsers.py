"""CLI output parsers for OS updaters."""

from __future__ import annotations

import re

from veripatch.updaters.base import UpdateItem, UpdateStatus


def parse_winget_upgrade(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `winget upgrade` tabular output into update items."""
    items: list[UpdateItem] = []
    lines = stdout.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("-") or "Name" in line and "Id" in line:
            continue
        parts = re.split(r"\s{2,}", line)
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        pkg_id = parts[1].strip() if len(parts) > 1 else name
        if name.lower() in {"name", "available upgrades"}:
            continue
        items.append(
            UpdateItem(
                id=f"winget-{pkg_id}",
                title=name,
                source_id=source_id,
                status=UpdateStatus.AVAILABLE,
                metadata={"package_id": pkg_id, "raw_line": line},
            )
        )
    return items


def parse_softwareupdate_list(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `softwareupdate --list` output."""
    items: list[UpdateItem] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("*") and not line.startswith("-"):
            continue
        label_match = re.search(r"Label:\s*(.+?)(?:,\s*|$)", line)
        title_match = re.search(r"Title:\s*(.+?)(?:,\s*|$)", line)
        label = (label_match.group(1) if label_match else line.lstrip("*- ")).strip()
        title = (title_match.group(1) if title_match else label).strip()
        items.append(
            UpdateItem(
                id=f"macos-{label}",
                title=title,
                source_id=source_id,
                status=UpdateStatus.AVAILABLE,
                metadata={"label": label},
            )
        )
    if not items and "No new software available" not in stdout:
        if stdout.strip():
            items.append(
                UpdateItem(
                    id="macos-raw",
                    title=stdout.strip()[:120],
                    source_id=source_id,
                    status=UpdateStatus.AVAILABLE,
                    metadata={"raw": True},
                )
            )
    return items


def parse_apt_upgradable(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `apt list --upgradable` output."""
    items: list[UpdateItem] = []
    for line in stdout.splitlines():
        if "upgradable" not in line:
            continue
        pkg = line.split("/", 1)[0].strip()
        if pkg and pkg != "Listing":
            items.append(
                UpdateItem(
                    id=f"apt-{pkg}",
                    title=line.strip()[:120],
                    source_id=source_id,
                    status=UpdateStatus.AVAILABLE,
                    metadata={"package": pkg},
                )
            )
    return items


def parse_dnf_check_update(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `dnf check-update` output."""
    items: list[UpdateItem] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("Last metadata"):
            pkg = parts[0]
            if pkg.endswith(".") or pkg.startswith("="):
                continue
            items.append(
                UpdateItem(
                    id=f"dnf-{pkg}",
                    title=f"{pkg} {parts[1] if len(parts) > 1 else ''}".strip(),
                    source_id=source_id,
                    status=UpdateStatus.AVAILABLE,
                    metadata={"package": pkg},
                )
            )
    return items


def parse_pacman_qu(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `pacman -Qu` output."""
    items: list[UpdateItem] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            pkg, version = parts[0], parts[1]
            items.append(
                UpdateItem(
                    id=f"pacman-{pkg}",
                    title=f"{pkg} -> {version}",
                    source_id=source_id,
                    status=UpdateStatus.AVAILABLE,
                    metadata={"package": pkg, "version": version},
                )
            )
    return items


def parse_zypper_list_updates(stdout: str, source_id: str) -> list[UpdateItem]:
    """Parse `zypper list-updates` output."""
    items: list[UpdateItem] = []
    for line in stdout.splitlines():
        if "|" not in line or line.startswith("---") or "Repository" in line:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 3 and cols[0].isdigit():
            pkg = cols[2] if len(cols) > 2 else cols[1]
            items.append(
                UpdateItem(
                    id=f"zypper-{pkg}",
                    title=pkg,
                    source_id=source_id,
                    status=UpdateStatus.AVAILABLE,
                    metadata={"package": pkg},
                )
            )
    return items
