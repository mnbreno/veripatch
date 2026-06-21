"""Intent-based agent selection with availability checks."""

from __future__ import annotations

from dataclasses import dataclass

from agentmesh.agent.spec import AgentSpec
from agentmesh.runtime.registry import AgentRegistry

# Best-fit order for common intents (first available wins).
INTENT_AGENT_PRIORITY: dict[str, list[str]] = {
    "development": [
        "backend-architect",
        "code-reviewer",
        "devops-automator",
        "technical-writer",
        "reality-checker",
    ],
    "review": [
        "code-reviewer",
        "reality-checker",
        "backend-architect",
    ],
    "docs": [
        "technical-writer",
        "backend-architect",
    ],
    "ci": [
        "devops-automator",
        "reality-checker",
    ],
    "release": [
        "reality-checker",
        "devops-automator",
        "code-reviewer",
    ],
}


@dataclass
class AgentSelection:
    agent_id: str
    spec: AgentSpec
    intent: str
    skipped: list[str]
    reason: str


def normalize_intent(text: str) -> str | None:
    normalized = " ".join(text.strip().lower().split())
    aliases = {
        "start development": "development",
        "start dev": "development",
        "dev": "development",
        "develop": "development",
        "start review": "review",
        "start docs": "docs",
        "start ci": "ci",
        "start release": "release",
    }
    if normalized in aliases:
        return aliases[normalized]
    if normalized.startswith("start "):
        candidate = normalized.removeprefix("start ").strip()
        if candidate in INTENT_AGENT_PRIORITY:
            return candidate
    return None


def select_agent_for_intent(
    intent: str,
    specs: dict[str, AgentSpec],
    registry: AgentRegistry,
) -> AgentSelection | None:
    priority = INTENT_AGENT_PRIORITY.get(intent)
    if not priority:
        return None

    active = registry.active_agents()
    skipped: list[str] = []

    for agent_id in priority:
        if agent_id not in specs:
            continue
        if agent_id in active:
            skipped.append(agent_id)
            continue
        spec = specs[agent_id]
        reason = {
            "development": "Primary development and architecture agent",
            "review": "Best suited for code and design review",
            "docs": "Documentation specialist",
            "ci": "CI/CD and automation specialist",
            "release": "Production readiness gatekeeper",
        }.get(intent, "Best match for intent")
        return AgentSelection(
            agent_id=agent_id,
            spec=spec,
            intent=intent,
            skipped=skipped,
            reason=reason,
        )
    return None
