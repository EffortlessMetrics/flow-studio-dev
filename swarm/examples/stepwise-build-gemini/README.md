# Stepwise Build Example - Gemini Backend

This example demonstrates a complete **Signal + Plan + Build** SDLC run using the Gemini stepwise backend in stub mode.

## Run Details

- **Backend**: `gemini-step-orchestrator`
- **Engine**: `gemini-step`
- **Mode**: `stub` (simulated execution)
- **Flows**: `signal`, `plan`, `build`
- **Total Steps**: 27 (6 signal + 9 plan + 12 build)

## Directory Structure

```
stepwise-build-gemini/
├── spec.json          # Run specification
├── meta.json          # Run metadata (status, timestamps)
├── events.jsonl       # Complete event log (stepwise events)
└── README.md          # This file
```

## Key Characteristics

The Gemini backend uses a **lightweight observability model**:

- **Events only**: No per-step transcripts or receipts
- **Single events.jsonl**: Contains all step_start, step_end, route_decision events
- **Lower storage overhead**: ~44KB vs ~63KB for Claude equivalent

## What to Look For

### 1. Step Events
```bash
# Count step events by type
grep -c '"kind":"step_start"' events.jsonl
grep -c '"kind":"step_end"' events.jsonl
```

### 2. Route Decisions (Microloops)
```bash
# See routing decisions including microloop iterations
grep '"kind":"route_decision"' events.jsonl | head -5
```

### 3. Flow Transitions
```bash
# See flow start/end events
grep '"kind":"run_started"' events.jsonl
grep '"kind":"run_completed"' events.jsonl
```

## Microloop Behavior

This run demonstrates microloop routing in the Build flow:

- **Test microloop**: `author_tests` <-> `critique_tests` (max 3 iterations)
- **Code microloop**: `implement` <-> `critique_code` (max 3 iterations)

In stub mode, receipts don't contain actual critic feedback, so loops hit max_iterations.

## Regenerating This Example

```bash
# Generate a fresh run
SWARM_GEMINI_STUB=1 uv run swarm/tools/demo_stepwise_run.py \
  --backend gemini-step-orchestrator \
  --flows signal,plan,build

# Copy to examples (replace run ID)
cp swarm/runs/<run-id>/* swarm/examples/stepwise-build-gemini/
```

## Viewing in Flow Studio

```bash
make flow-studio
# Navigate to: http://localhost:5000/?run=stepwise-build-gemini
```

## Related Documentation

- [STEPWISE_BACKENDS.md](../../../docs/STEPWISE_BACKENDS.md) - Stepwise backend overview
- [FLOW_STUDIO.md](../../../docs/FLOW_STUDIO.md) - Flow Studio UI guide
- [build.yaml](../../config/flows/build.yaml) - Build flow step definitions
