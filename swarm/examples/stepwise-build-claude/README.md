# Stepwise Build Example - Claude Backend

This example demonstrates a complete **Signal + Plan + Build** SDLC run using the Claude stepwise backend in stub mode.

## Run Details

- **Backend**: `claude-step-orchestrator`
- **Engine**: `claude-step`
- **Mode**: `stub` (simulated execution)
- **Provider**: `none` (stub mode)
- **Flows**: `signal`, `plan`, `build`
- **Total Steps**: 27 (6 signal + 9 plan + 12 build)

## Directory Structure

```
stepwise-build-claude/
├── spec.json          # Run specification
├── meta.json          # Run metadata (status, timestamps)
├── events.jsonl       # Complete event log
├── README.md          # This file
│
├── signal/            # Flow 1 artifacts
│   ├── llm/           # 6 transcript files (.jsonl)
│   └── receipts/      # 6 receipt files (.json)
│
├── plan/              # Flow 2 artifacts
│   ├── llm/           # 9 transcript files (.jsonl)
│   └── receipts/      # 9 receipt files (.json)
│
└── build/             # Flow 3 artifacts
    ├── llm/           # 12 transcript files (.jsonl)
    └── receipts/      # 12 receipt files (.json)
```

## Key Characteristics

The Claude backend uses a **rich observability model**:

- **Per-step transcripts**: JSONL files with conversation history
- **Per-step receipts**: JSON files with execution metadata
- **Full token tracking**: (zeros in stub mode)
- **Higher observability**: Enables detailed debugging and replay

## What to Look For

### 1. Transcript Files
```bash
# View a transcript from the Build flow
cat build/llm/author_tests-test-author-claude.jsonl | head -5

# Count transcripts per flow
ls signal/llm/*.jsonl | wc -l  # 6 steps
ls plan/llm/*.jsonl | wc -l    # 9 steps
ls build/llm/*.jsonl | wc -l   # 12 steps
```

### 2. Receipt Files
```bash
# View a receipt with execution metadata
cat build/receipts/author_tests-test-author.json

# Check receipt fields
jq '.engine, .mode, .status' build/receipts/author_tests-test-author.json
```

### 3. Route Decisions (Microloops)
```bash
# See routing decisions in events
grep '"kind":"route_decision"' events.jsonl | jq -c '{from: .payload.from_step, to: .payload.to_step, reason: .payload.reason}'
```

## Microloop Behavior

This run demonstrates microloop routing in the Build flow:

- **Test microloop**: `author_tests` <-> `critique_tests` (max 3 iterations)
- **Code microloop**: `implement` <-> `critique_code` (max 3 iterations)

In stub mode, receipts don't contain actual critic status fields, so loops hit max_iterations.

## Receipt Schema

Each receipt contains:
```json
{
  "engine": "claude-step",
  "mode": "stub",
  "provider": "none",
  "model": "claude-stub",
  "step_id": "author_tests",
  "flow_key": "build",
  "run_id": "run-xxx",
  "agent_key": "test-author",
  "started_at": "...",
  "completed_at": "...",
  "duration_ms": 0,
  "status": "succeeded",
  "tokens": {"prompt": 0, "completion": 0, "total": 0},
  "transcript_path": "llm/author_tests-test-author-claude.jsonl"
}
```

## Regenerating This Example

```bash
# Generate a fresh run
SWARM_CLAUDE_STEP_ENGINE_MODE=stub uv run swarm/tools/demo_stepwise_run.py \
  --backend claude-step-orchestrator \
  --mode stub \
  --flows signal,plan,build

# Copy to examples (replace run ID)
cp -r swarm/runs/<run-id>/* swarm/examples/stepwise-build-claude/
```

## Viewing in Flow Studio

```bash
make flow-studio
# Navigate to: http://localhost:5000/?run=stepwise-build-claude
```

## Differences from Gemini Backend

| Aspect | Claude | Gemini |
|--------|--------|--------|
| Transcripts | Yes (per-step) | No |
| Receipts | Yes (per-step) | No |
| Log Events | Yes | No |
| Token Tracking | Yes | No |
| Observability | Rich | Minimal |

## Related Documentation

- [STEPWISE_BACKENDS.md](../../../docs/STEPWISE_BACKENDS.md) - Stepwise backend overview
- [FLOW_STUDIO.md](../../../docs/FLOW_STUDIO.md) - Flow Studio UI guide
- [build.yaml](../../config/flows/build.yaml) - Build flow step definitions
