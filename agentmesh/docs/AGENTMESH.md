# AgentMesh

AgentMesh is a standalone asyncio multi-agent system with structured cross-agent messaging, agency-agents-aligned prompt systems, and parallel execution.

## Architecture

- **Scheduler** — asyncio concurrent execution with semaphore-based resource limits
- **MessageBus** — `InMemoryBus` (tests/in-process) and `FileBus` (separate terminal processes)
- **AgentWorker** — parse → brain → format → reply/forward loop
- **PromptSystem** — four prompts per agent (system, input, output, error)
- **Brain** — `ScriptedBrain` (default, offline) or `LLMBrain` (optional)

## Agent Roster

| Agent ID | Role |
|----------|------|
| `backend-architect` | System/API architecture design |
| `code-reviewer` | Security and maintainability review |
| `devops-automator` | CI/CD pipeline design |
| `technical-writer` | Documentation outlines and README sections |
| `reality-checker` | Production readiness gate |

## Communication Protocol

All messages use the `Message` JSON envelope:

```json
{
  "id": "uuid",
  "sender": "backend-architect",
  "recipient": "code-reviewer",
  "type": "request",
  "correlation_id": "workflow-uuid",
  "payload": { "task": "...", "artifacts": {} },
  "context": { "original_task": "...", "prior_sender": "..." },
  "trace": ["prior-message-id"],
  "timestamp": "ISO-8601"
}
```

Message types: `request`, `response`, `data`, `error`.

Routing: directed (`recipient`), broadcast (`*`), history via append-only log.

## Prompt System

Each agent spec ([agents/](agentmesh/agents/)) follows agency-agents structure:

- YAML frontmatter: `name`, `description`, `color`, `emoji`, `vibe`
- Sections: Identity, Core Mission, Critical Rules, Deliverables, Communication Style, Success Metrics

`PromptSystem` derives four runtime prompts ensuring interoperability:

1. **System** — role, constraints, decision boundaries
2. **Input parsing** — normalize inbound messages
3. **Output formatting** — strict JSON contract
4. **Error handling** — communication and validation failures

## CLI Usage

```bash
cd agentmesh
pip install -e ".[dev]"

# Interactive REPL (default when no subcommand)
agentmesh
agentmesh interactive

# Inside the REPL:
#   start development   → auto-pick best free agent, run in this terminal (Cursor)
#   status              → show running agents (lock files + process scan)
#   list / help / quit

# Bootstrap once for multi-terminal dev
agentmesh bootstrap
# Or on Windows: .\scripts\bootstrap-dev.ps1

# One-liner per Cursor terminal (no REPL)
agentmesh start development --here

# List agents and workflows
agentmesh list

# Run single agent (FileBus for separate terminals)
set AGENTMESH_BUS_ROOT=.agentmesh/bus
agentmesh run backend-architect --file-bus --once

# Orchestrate workflow
agentmesh orchestrate design-review-doc
agentmesh orchestrate design-review-doc --file-bus   # dispatch to running FileBus agents
agentmesh orchestrate parallel-ci-check
```

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTMESH_BRAIN` | `scripted` | Brain backend (`scripted` or `llm`) |
| `AGENTMESH_BRAIN_LATENCY_MS` | `0` | Simulated latency for throughput tests |
| `AGENTMESH_LLM_PROVIDER` | `openai` | LLM provider (`openai` / `lmstudio` for OpenAI-compatible APIs; `none` falls back to scripted) |
| `AGENTMESH_LLM_BASE_URL` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API base URL (LM Studio default) |
| `AGENTMESH_LLM_MODEL` | `local-model` | Model id (e.g. `qwen/qwen3.5-9b`) |
| `AGENTMESH_LLM_API_KEY` | `lm-studio` | API key (LM Studio accepts any value) |
| `AGENTMESH_LLM_TIMEOUT` | `300` | Request timeout in seconds (local models can be slow) |
| `AGENTMESH_LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `AGENTMESH_BUS_ROOT` | `<repo>/.agentmesh/bus` | FileBus root directory |
| `AGENTMESH_RUNTIME_ROOT` | `<repo>/.agentmesh/run` | Agent lock files (PID + terminal session) |
| `AGENTMESH_IN_TERMINAL` | — | Force in-terminal launch (`1`) |
| `AGENTMESH_SPAWN_EXTERNAL` | — | Force external terminal spawn (`1`) |
| `AGENTMESH_DRY_RUN` | — | (reserved) |

## Cursor multi-terminal development

1. **Bootstrap once** (from repo root or `agentmesh/`):
   ```powershell
   cd agentmesh
   agentmesh bootstrap
   ```
2. **Open 5 Cursor integrated terminals** manually (`Terminal → New Terminal`).
3. **In each terminal**:
   ```
   cd agentmesh
   agentmesh
   start development
   ```
   Or use the one-liner: `agentmesh start development --here`
4. **Expected agent assignment** (first available wins):

| Terminal order | Agent selected |
|----------------|----------------|
| 1st | backend-architect |
| 2nd | code-reviewer |
| 3rd | devops-automator |
| 4th | technical-writer |
| 5th | reality-checker |

5. **Verify** from any terminal: `agentmesh status`
6. **Optional**: use a 6th terminal as controller:
   ```powershell
   agentmesh orchestrate design-review-doc --file-bus
   ```
   Use `--file-bus` when agents are running in separate terminals. Without it, `orchestrate` runs an in-process workflow and **does not** call your running agents or local LLM.

In Cursor/VS Code integrated terminals (`TERM_PROGRAM=vscode`), `start development` runs the agent **in that same terminal** by default. Use `--spawn` or `AGENTMESH_SPAWN_EXTERNAL=1` to open external windows instead.

## Local LLM (LM Studio)

Use an OpenAI-compatible local server (LM Studio, Ollama, etc.) as the agent brain:

```powershell
cd agentmesh
$env:AGENTMESH_BRAIN = "llm"
$env:AGENTMESH_LLM_PROVIDER = "openai"
$env:AGENTMESH_LLM_BASE_URL = "http://10.5.0.2:1234/v1"
$env:AGENTMESH_LLM_MODEL = "qwen/qwen3.5-9b"
$env:AGENTMESH_LLM_API_KEY = "lm-studio"

agentmesh start development --here
```

Start all five dev agents against LM Studio (Windows):

```powershell
.\scripts\start-llm-development.ps1
```

Optional overrides:

```powershell
.\scripts\start-llm-development.ps1 -BaseUrl "http://10.5.0.2:1234/v1" -Model "qwen/qwen3.5-9b"
```

## Workflows

- **design-review-doc** — Sequential chain: architect → reviewer → writer → reality-checker (4 agents)
- **parallel-ci-check** — Fan-out (devops + architect) → fan-in (reality-checker)

## Testing

```bash
cd agentmesh
pytest tests/ -v --cov=agentmesh --cov-fail-under=75
```

### Test Results (Success Criteria)

| Test Suite | Validates |
|------------|-----------|
| `test_scheduler_parallel` | Parallel execution faster than sequential; semaphore limits concurrency |
| `test_bus_routing` | Directed routing, broadcast, history (memory + file bus) |
| `test_cross_comm_e2e` | 4-agent sequential chain + parallel fan-out/fan-in with context preservation |
| `test_prompt_compliance` | All 5 agents: frontmatter, sections, four prompts, JSON contract |
| `test_protocol` | Message validation, context preservation, forwarding |

## Separate Terminal Mode

For true multi-terminal operation on Windows:

```powershell
# Terminal 1
$env:AGENTMESH_BUS_ROOT = ".agentmesh/bus"
agentmesh run backend-architect --file-bus

# Terminal 2
agentmesh run code-reviewer --file-bus

# Terminal 3 — orchestrate
agentmesh orchestrate design-review-doc
```

Each agent process reads/writes JSON files under `.agentmesh/bus/inboxes/` with full history in `history.jsonl`.
