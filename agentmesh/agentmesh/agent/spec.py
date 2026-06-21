"""Agent specification loader."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AgentSpec:
    """Parsed agency-agents-aligned agent definition."""

    agent_id: str
    name: str
    description: str
    color: str = "blue"
    emoji: str = ""
    vibe: str = ""
    body: str = ""
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return self.sections.get("identity", "")

    @property
    def core_mission(self) -> str:
        return self.sections.get("core_mission", "")

    @property
    def critical_rules(self) -> str:
        return self.sections.get("critical_rules", "")

    @property
    def deliverables(self) -> str:
        return self.sections.get("deliverables", "")

    @property
    def communication_style(self) -> str:
        return self.sections.get("communication_style", "")

    @property
    def success_metrics(self) -> str:
        return self.sections.get("success_metrics", "")


_SECTION_MAP = {
    "your identity & memory": "identity",
    "your core mission": "core_mission",
    "critical rules you must follow": "critical_rules",
    "your architecture deliverables": "deliverables",
    "your technical deliverables": "deliverables",
    "your deliverables": "deliverables",
    "your communication style": "communication_style",
    "your success metrics": "success_metrics",
}


def _normalize_heading(title: str) -> str:
    """Strip emoji and normalize heading for section lookup."""
    cleaned = re.sub(r"[^\w\s&]", "", title).strip().lower()
    return _SECTION_MAP.get(cleaned, cleaned.replace(" ", "_"))


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    for line in body.splitlines():
        heading = re.match(r"^##\s+(.+)$", line.strip())
        if heading:
            if current_key is not None:
                sections[current_key] = "\n".join(buffer).strip()
            title = heading.group(1).strip()
            current_key = _normalize_heading(title)
            buffer = []
        else:
            buffer.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(buffer).strip()
    return sections


def load_agent_spec(path: Path) -> AgentSpec:
    """Load an agent markdown file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Agent spec missing frontmatter: {path}")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter in {path}")

    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    agent_id = path.stem

    return AgentSpec(
        agent_id=agent_id,
        name=str(meta.get("name", agent_id)),
        description=str(meta.get("description", "")),
        color=str(meta.get("color", "blue")),
        emoji=str(meta.get("emoji", "")),
        vibe=str(meta.get("vibe", "")),
        body=body,
        sections=_parse_sections(body),
    )


def load_all_agents(agents_dir: Path) -> dict[str, AgentSpec]:
    specs: dict[str, AgentSpec] = {}
    for path in sorted(agents_dir.glob("*.md")):
        spec = load_agent_spec(path)
        specs[spec.agent_id] = spec
    return specs
