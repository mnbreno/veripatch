"""Prompt system builder aligned with agency-agents patterns."""

from __future__ import annotations

from dataclasses import dataclass

from agentmesh.agent.spec import AgentSpec


@dataclass
class PromptBundle:
    """Four required prompts for each agent."""

    system: str
    input_parsing: str
    output_formatting: str
    error_handling: str


OUTPUT_JSON_SCHEMA = """
{
  "status": "ok|error",
  "agent_id": "<your agent id>",
  "summary": "<one-line summary>",
  "artifacts": { "key": "value" },
  "next_agent": "<optional agent id to forward work>",
  "forward_payload": { "task": "...", "ctx_*": "..." }
}
""".strip()


class PromptSystem:
    """Derives runtime prompts from an AgentSpec."""

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    def build(self) -> PromptBundle:
        return PromptBundle(
            system=self._system_prompt(),
            input_parsing=self._input_parsing_prompt(),
            output_formatting=self._output_formatting_prompt(),
            error_handling=self._error_handling_prompt(),
        )

    def _system_prompt(self) -> str:
        s = self.spec
        return f"""You are {s.name} ({s.agent_id}).

ROLE: {s.description}
VIBE: {s.vibe}

IDENTITY & MEMORY:
{s.identity or s.body[:500]}

CORE MISSION:
{s.core_mission}

CRITICAL RULES (decision boundaries):
{s.critical_rules or "Follow the AgentMesh protocol. Never invent data outside your domain."}

DELIVERABLES:
{s.deliverables or "Structured JSON artifacts for downstream agents."}

COMMUNICATION STYLE:
{s.communication_style or "Be concise, factual, and machine-readable."}

SUCCESS METRICS:
{s.success_metrics or "Produce valid structured output that downstream agents can parse."}

CONSTRAINTS:
- Stay within your role; defer out-of-scope work via next_agent forwarding.
- Preserve correlation_id and context from inbound messages.
- Never break the output JSON contract.
"""

    def _input_parsing_prompt(self) -> str:
        return f"""Parse inbound AgentMesh messages for agent '{self.spec.agent_id}'.

Expected inbound fields:
- type: request | response | data | error
- payload.task: primary work description
- payload.artifacts: prior agent outputs
- context: preserved cross-agent context (original_task, prior_sender, ctx_*)
- correlation_id: workflow trace id
- trace: list of prior message ids

Steps:
1. Validate message type and required payload.task (or artifacts for continuation).
2. Extract task, context, and prior artifacts into a normalized work object.
3. If input is invalid, flag parse_error with a clear reason.
4. If work belongs to another agent, set recommend_forward to that agent id.

Return normalized JSON:
{{ "parsed": true, "task": "...", "artifacts": {{}}, "context": {{}}, "parse_error": null }}
"""

    def _output_formatting_prompt(self) -> str:
        return f"""Format all outputs from {self.spec.name} as strict JSON matching:

{OUTPUT_JSON_SCHEMA}

Rules:
- status must be "ok" on success, "error" on failure
- agent_id must be "{self.spec.agent_id}"
- artifacts must contain role-specific deliverables
- next_agent is optional; set when forwarding work
- forward_payload must include task and any ctx_* fields for downstream agents
"""

    def _error_handling_prompt(self) -> str:
        return f"""When {self.spec.name} encounters errors:

1. Communication failures: emit type=error message with payload.error and payload.details
2. Invalid input: status=error, summary explains missing fields, do not mutate context
3. Out-of-scope requests: status=ok with next_agent set to the correct specialist
4. Never crash silently; always return machine-readable JSON

Error output schema:
{{ "status": "error", "agent_id": "{self.spec.agent_id}",
   "summary": "...", "artifacts": {{ "error_code": "..." }} }}
"""
