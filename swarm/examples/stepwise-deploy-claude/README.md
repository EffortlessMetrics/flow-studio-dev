# Stepwise Deploy Example (Claude)

Golden example of stepwise SDLC execution through Flow 5 (Deploy).

## Flows Included

- **Signal** (Flow 1): Requirements microloop
- **Plan** (Flow 2): Architecture design
- **Build** (Flow 3): Implementation with test/code microloops
- **Gate** (Flow 4): Pre-merge verification
- **Deploy** (Flow 5): Artifact deployment and verification

## Backend Configuration

- **Backend**: `claude-step-orchestrator`
- **Engine**: `ClaudeStepEngine`
- **Mode**: `stub` (no API calls)
- **Provider**: `anthropic`

## Directory Structure

```
stepwise-deploy-claude/
├── spec.json           # RunSpec with flow_keys and backend
├── meta.json           # RunSummary with status and timestamps
├── events.jsonl        # Complete event stream
├── signal/             # Flow 1 artifacts
│   ├── llm/            # Per-step transcripts
│   └── receipts/       # Per-step execution metadata
├── plan/               # Flow 2 artifacts
├── build/              # Flow 3 artifacts
├── gate/               # Flow 4 artifacts
└── deploy/             # Flow 5 artifacts
    ├── llm/            # 5 transcripts (decide, monitor, smoke, finalize, report)
    └── receipts/       # 5 receipts with routing data
```

## Key Observations

1. **Routing**: All Deploy steps use linear routing (no microloops)
2. **Teaching Notes**: Each step has structured teaching_notes with inputs/outputs/emphasizes/constraints
3. **Event Types**: `step_start`, `step_end`, `route_decision`, `log`

## How to Regenerate

```bash
SWARM_CLAUDE_STEP_ENGINE_MODE=stub uv run swarm/tools/demo_stepwise_run.py \
  --backend claude-step-orchestrator \
  --mode stub \
  --flows signal,plan,build,gate,deploy
```

## Related Examples

- `stepwise-sdlc-claude/`: Full SDLC including Wisdom (Flow 6)
- `stepwise-gate-claude/`: SDLC through Gate only
- `stepwise-build-claude/`: SDLC through Build only
