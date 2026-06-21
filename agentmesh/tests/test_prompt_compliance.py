"""Prompt system compliance audit."""

from agentmesh.agent.prompts import PromptSystem
from agentmesh.agent.spec import load_all_agents
from agentmesh.agent.worker import AgentWorker
from agentmesh.bus.memory_bus import InMemoryBus
from agentmesh.scheduler import default_agents_dir

REQUIRED_SECTIONS = {
    "identity",
    "core_mission",
    "critical_rules",
    "deliverables",
    "communication_style",
    "success_metrics",
}


def test_all_agents_have_frontmatter() -> None:
    specs = load_all_agents(default_agents_dir())
    assert len(specs) == 5
    for _aid, spec in specs.items():
        assert spec.name
        assert spec.description
        assert spec.vibe


def test_all_agents_prompt_bundle_complete() -> None:
    specs = load_all_agents(default_agents_dir())
    for spec in specs.values():
        bundle = PromptSystem(spec).build()
        assert len(bundle.system) > 100
        assert "Parse inbound" in bundle.input_parsing
        assert "status" in bundle.output_formatting
        assert "error" in bundle.error_handling.lower()


def test_all_agents_sections_present() -> None:
    specs = load_all_agents(default_agents_dir())
    for spec in specs.values():
        for section in REQUIRED_SECTIONS:
            assert section in spec.sections, f"{spec.agent_id} missing {section}"


def test_worker_prompt_audit() -> None:
    specs = load_all_agents(default_agents_dir())
    bus = InMemoryBus()
    for spec in specs.values():
        worker = AgentWorker(spec, bus)
        audit = worker.prompt_audit()
        assert audit["output_schema_valid"]
        assert audit["system_len"] > 0
