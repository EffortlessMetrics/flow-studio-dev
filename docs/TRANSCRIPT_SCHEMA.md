# Transcript and Receipt Schema

> For: Developers building tools that parse LLM execution artifacts (transcripts, receipts) from RUN_BASE.

> **You are here:** Technical reference for transcript/receipt formats. Coming from:
> [Runtime Backends](./RUNTIME_BACKENDS.md) | Jump to:
> [Flow Studio API](./FLOW_STUDIO_API.md)

**See also:**
- [RUNTIME_BACKENDS.md](./RUNTIME_BACKENDS.md) - Backend architecture and event lifecycle
- [FLOW_STUDIO.md](./FLOW_STUDIO.md) - UI documentation

The runtime system writes two types of artifacts during step execution:

1. **Transcripts**: JSONL files containing the raw LLM conversation
2. **Receipts**: JSON files containing execution metadata and token usage

These artifacts enable debugging, auditing, and cost tracking for LLM-driven workflows.

---

## Directory Structure

When a step executes, artifacts are written under `RUN_BASE/<flow_key>/`:

```text
swarm/runs/<run-id>/
  <flow_key>/
    llm/
      <step_id>-<agent_key>-<engine>.jsonl    # Transcript
    receipts/
      <step_id>-<agent_key>.json              # Receipt
```

**Example:**

```text
swarm/runs/run-20251209-143022-abc123/
  build/
    llm/
      context-load-context-loader-claude.jsonl
      impl-loop-code-implementer-claude.jsonl
      impl-loop-code-critic-claude.jsonl
    receipts/
      context-load-context-loader.json
      impl-loop-code-implementer.json
      impl-loop-code-critic.json
```

**Naming Convention:**

| Component | Description | Example |
|-----------|-------------|---------|
| `<step_id>` | Step identifier from flow definition | `context-load`, `impl-loop` |
| `<agent_key>` | Agent key from step assignment | `context-loader`, `code-implementer` |
| `<engine>` | Engine identifier (transcript only) | `claude`, `gemini` |

---

## Transcript Schema (JSONL)

Transcripts are stored as JSONL (JSON Lines) files where each line is a complete JSON object representing one conversation event.

**Location:** `RUN_BASE/<flow_key>/llm/<step_id>-<agent_key>-<engine>.jsonl`

### Message Events

Standard conversation messages between system, user, and assistant:

```json
{"timestamp": "2025-12-09T14:30:22.123456Z", "role": "system", "content": "You are the code-implementer agent..."}
{"timestamp": "2025-12-09T14:30:22.234567Z", "role": "user", "content": "Implement the health check endpoint..."}
{"timestamp": "2025-12-09T14:30:25.456789Z", "role": "assistant", "content": "I'll implement the health check endpoint..."}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with timezone (Z suffix) |
| `role` | string | Yes | Message role: `system`, `user`, `assistant` |
| `content` | string | Yes | Message text content |

### Tool Events

Tool invocations include additional fields for tool name, input, and output:

```json
{"timestamp": "2025-12-09T14:30:26.123456Z", "role": "tool", "tool_name": "Read", "tool_input": {"file_path": "/path/to/file.py"}, "content": "# file contents..."}
{"timestamp": "2025-12-09T14:30:27.234567Z", "role": "tool", "tool_name": "Write", "tool_input": {"file_path": "/path/to/new.py", "content": "..."}, "tool_output": "File written successfully"}
{"timestamp": "2025-12-09T14:30:28.345678Z", "role": "tool", "tool_name": "Bash", "tool_input": {"command": "cargo test"}, "tool_output": "running 5 tests\ntest result: ok"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp with timezone |
| `role` | string | Yes | Always `tool` for tool events |
| `tool_name` | string | Yes | Tool identifier: `Read`, `Write`, `Bash`, `Glob`, `Grep`, etc. |
| `tool_input` | object | Yes | Tool-specific input parameters |
| `content` | string | No | For Read tools, the file contents |
| `tool_output` | string | No | Tool execution result or error |

### Complete Transcript Example

```jsonl
{"timestamp": "2025-12-09T14:30:22.000000Z", "role": "system", "content": "Executing step impl-loop with agent code-implementer"}
{"timestamp": "2025-12-09T14:30:22.100000Z", "role": "user", "content": "Step role: Implement code changes based on test requirements"}
{"timestamp": "2025-12-09T14:30:23.200000Z", "role": "assistant", "content": "I'll read the test requirements first."}
{"timestamp": "2025-12-09T14:30:23.300000Z", "role": "tool", "tool_name": "Read", "tool_input": {"file_path": "swarm/runs/run-123/build/test_summary.md"}, "content": "# Test Summary\n..."}
{"timestamp": "2025-12-09T14:30:24.400000Z", "role": "assistant", "content": "Now I'll implement the health endpoint."}
{"timestamp": "2025-12-09T14:30:24.500000Z", "role": "tool", "tool_name": "Write", "tool_input": {"file_path": "src/health.py", "content": "def health():\n    return {'status': 'ok'}"}, "tool_output": "File written"}
{"timestamp": "2025-12-09T14:30:25.600000Z", "role": "assistant", "content": "Implementation complete. Running tests to verify."}
{"timestamp": "2025-12-09T14:30:25.700000Z", "role": "tool", "tool_name": "Bash", "tool_input": {"command": "pytest tests/test_health.py"}, "tool_output": "1 passed"}
{"timestamp": "2025-12-09T14:30:26.800000Z", "role": "assistant", "content": "[STUB] Completed step impl-loop. In production, this would contain the actual Claude response."}
```

---

## Receipt Schema (JSON)

Receipts are JSON files containing execution metadata, timing, and token usage for a step execution.

**Location:** `RUN_BASE/<flow_key>/receipts/<step_id>-<agent_key>.json`

### Schema Definition

```json
{
  "engine": "claude-step",
  "model": "claude-sonnet-4-20250514",
  "step_id": "impl-loop",
  "flow_key": "build",
  "run_id": "run-20251209-143022-abc123",
  "agent_key": "code-implementer",
  "started_at": "2025-12-09T14:30:22.000000Z",
  "completed_at": "2025-12-09T14:30:26.800000Z",
  "duration_ms": 4800,
  "status": "succeeded",
  "tokens": {
    "prompt": 12500,
    "completion": 3200,
    "total": 15700
  },
  "transcript_path": "llm/impl-loop-code-implementer-claude.jsonl"
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `engine` | string | Yes | Engine identifier: `claude-step`, `gemini-step` |
| `model` | string | Yes | Model identifier or `claude-stub` for stub mode |
| `step_id` | string | Yes | Step identifier from flow definition |
| `flow_key` | string | Yes | Flow key: `signal`, `plan`, `build`, `gate`, `deploy`, `wisdom` |
| `run_id` | string | Yes | Unique run identifier |
| `agent_key` | string | Yes | Agent key assigned to this step |
| `started_at` | string | Yes | ISO 8601 start timestamp |
| `completed_at` | string | Yes | ISO 8601 completion timestamp |
| `duration_ms` | integer | Yes | Execution duration in milliseconds |
| `status` | string | Yes | Execution status: `succeeded` or `failed` |
| `tokens` | object | Yes | Token usage breakdown |
| `tokens.prompt` | integer | Yes | Input/prompt token count |
| `tokens.completion` | integer | Yes | Output/completion token count |
| `tokens.total` | integer | Yes | Total token count |
| `transcript_path` | string | Yes | Relative path to transcript file from `RUN_BASE/<flow_key>/` |

### Status Values

| Status | Description |
|--------|-------------|
| `succeeded` | Step completed successfully |
| `failed` | Step encountered an error |

---

## Parsing Examples

### Python: Reading Transcripts

```python
import json
from pathlib import Path

def read_transcript(run_base: Path, flow_key: str, step_id: str, agent_key: str, engine: str) -> list:
    """Read transcript entries from a JSONL file."""
    transcript_path = run_base / flow_key / "llm" / f"{step_id}-{agent_key}-{engine}.jsonl"

    entries = []
    with transcript_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

# Usage
run_base = Path("swarm/runs/run-20251209-143022-abc123")
transcript = read_transcript(run_base, "build", "impl-loop", "code-implementer", "claude")

for entry in transcript:
    print(f"[{entry['role']}] {entry.get('content', '')[:100]}...")
```

### Python: Reading Receipts

```python
import json
from pathlib import Path

def read_receipt(run_base: Path, flow_key: str, step_id: str, agent_key: str) -> dict:
    """Read receipt JSON for a step execution."""
    receipt_path = run_base / flow_key / "receipts" / f"{step_id}-{agent_key}.json"

    with receipt_path.open("r", encoding="utf-8") as f:
        return json.load(f)

# Usage
run_base = Path("swarm/runs/run-20251209-143022-abc123")
receipt = read_receipt(run_base, "build", "impl-loop", "code-implementer")

print(f"Duration: {receipt['duration_ms']}ms")
print(f"Tokens: {receipt['tokens']['total']}")
print(f"Status: {receipt['status']}")
```

### JavaScript: Parsing in Flow Studio

```javascript
async function loadTranscript(runId, flowKey, stepId, agentKey, engine) {
  const url = `/api/runs/${runId}/transcript/${flowKey}/${stepId}/${agentKey}/${engine}`;
  const response = await fetch(url);
  const text = await response.text();

  return text
    .split('\n')
    .filter(line => line.trim())
    .map(line => JSON.parse(line));
}

async function loadReceipt(runId, flowKey, stepId, agentKey) {
  const url = `/api/runs/${runId}/receipt/${flowKey}/${stepId}/${agentKey}`;
  const response = await fetch(url);
  return response.json();
}
```

---

## Stub Mode Behavior

When engines run in stub mode (for testing), they generate synthetic transcripts and receipts:

**Stub Transcript:**
```jsonl
{"timestamp": "2025-12-09T14:30:22.000000Z", "role": "system", "content": "Executing step impl-loop with agent code-implementer"}
{"timestamp": "2025-12-09T14:30:22.000000Z", "role": "user", "content": "Step role: Implement code changes..."}
{"timestamp": "2025-12-09T14:30:22.100000Z", "role": "assistant", "content": "[STUB] Completed step impl-loop. In production, this would contain the actual Claude response."}
```

**Stub Receipt:**
```json
{
  "engine": "claude-step",
  "model": "claude-stub",
  "step_id": "impl-loop",
  "flow_key": "build",
  "run_id": "run-20251209-143022-abc123",
  "agent_key": "code-implementer",
  "started_at": "2025-12-09T14:30:22.000000Z",
  "completed_at": "2025-12-09T14:30:22.100000Z",
  "duration_ms": 100,
  "status": "succeeded",
  "tokens": {
    "prompt": 0,
    "completion": 0,
    "total": 0
  },
  "transcript_path": "llm/impl-loop-code-implementer-claude.jsonl"
}
```

Stub mode is indicated by:
- `model: "claude-stub"` in receipts
- `[STUB]` prefix in assistant messages
- Zero token counts

---

## Integration with Flow Studio

Flow Studio uses transcripts and receipts to display:

1. **Step Timeline**: Shows message sequence with timestamps
2. **Tool Usage**: Highlights tool invocations and outputs
3. **Cost Tracking**: Aggregates token usage across steps
4. **Debugging**: Allows inspection of full conversation history

The Flow Studio API exposes these artifacts via:

| Endpoint | Description |
|----------|-------------|
| `GET /api/runs/<id>/transcripts` | List available transcripts for a run |
| `GET /api/runs/<id>/receipts` | List available receipts for a run |

See [FLOW_STUDIO_API.md](./FLOW_STUDIO_API.md) for complete API reference.

---

## See Also

- **[RUNTIME_BACKENDS.md](./RUNTIME_BACKENDS.md)**: Backend architecture
- **[FLOW_STUDIO.md](./FLOW_STUDIO.md)**: UI documentation
- **[FLOW_STUDIO_API.md](./FLOW_STUDIO_API.md)**: REST API reference
- **[swarm/runtime/engines.py](../swarm/runtime/engines.py)**: Engine implementations
