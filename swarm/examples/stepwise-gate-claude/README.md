# Stepwise Gate Example - Claude Backend

This example demonstrates a complete **Signal + Plan + Build + Gate** SDLC run using the Claude stepwise backend in stub mode.

## Run Details

- **Backend**: `claude-step-orchestrator`
- **Engine**: `claude-step`
- **Mode**: `stub` (simulated execution)
- **Provider**: `anthropic`
- **Flows**: `signal`, `plan`, `build`, `gate`
- **Total Steps**: 32 (6 signal + 8 plan + 12 build + 6 gate)

## Directory Structure

```
stepwise-gate-claude/
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
│   ├── llm/           # 8 transcript files (.jsonl)
│   └── receipts/      # 8 receipt files (.json)
│
├── build/             # Flow 3 artifacts
│   ├── llm/           # 12 transcript files (.jsonl)
│   └── receipts/      # 12 receipt files (.json)
│
└── gate/              # Flow 4 artifacts
    ├── llm/           # 6 transcript files (.jsonl)
    └── receipts/      # 6 receipt files (.json)
```

## Gate Flow Steps

The Gate flow demonstrates the pre-merge quality gate:

| Step | Agent | Purpose |
|------|-------|---------|
| receipt | receipt-checker | Verify build_receipt.json completeness |
| contract | contract-enforcer | Check API changes vs contracts |
| security | security-scanner | Run SAST and secret scans |
| coverage | coverage-enforcer | Verify test coverage thresholds |
| gate_fix | gate-fixer | Apply mechanical fixes only |
| merge_decision | merge-decider | Synthesize into MERGE/BOUNCE/ESCALATE |

## Key Characteristics

The Gate flow is **linear** (no microloops):
- All verification steps run sequentially
- gate-fixer applies mechanical fixes only
- merge-decider produces final verdict

## What to Look For

### 1. Gate Receipt Files
```bash
# View a gate receipt
cat gate/receipts/merge_decision-merge-decider.json

# Check receipt fields
jq '.engine, .mode, .status, .step_id' gate/receipts/*.json
```

### 2. Gate Events
```bash
# See gate flow events
grep '"flow_key":"gate"' events.jsonl | head -10

# Count gate steps
grep '"flow_key":"gate"' events.jsonl | grep '"kind":"step_start"' | wc -l
```

### 3. Build Microloops
```bash
# See routing decisions in build flow (microloops)
grep '"kind":"route_decision"' events.jsonl | grep '"flow_key":"build"' | head -5
```

## Regenerating This Example

```bash
# Generate a fresh run
SWARM_CLAUDE_STEP_ENGINE_MODE=stub uv run swarm/tools/demo_stepwise_run.py \
  --backend claude-step-orchestrator \
  --mode stub \
  --flows signal,plan,build,gate

# Copy to examples (replace run ID)
cp -r swarm/runs/<run-id>/* swarm/examples/stepwise-gate-claude/
```

## Viewing in Flow Studio

```bash
make flow-studio
# Navigate to: http://localhost:5000/?run=stepwise-gate-claude
```

## Related Documentation

- [STEPWISE_BACKENDS.md](../../../docs/STEPWISE_BACKENDS.md) - Stepwise backend overview
- [FLOW_STUDIO.md](../../../docs/FLOW_STUDIO.md) - Flow Studio UI guide
- [gate.yaml](../../config/flows/gate.yaml) - Gate flow step definitions
