# Positioning: What This Repo Does

This repo implements agentic SDLC flows with receipts and tests. It's designed for teams that want to trade compute for human attention and get audit trails instead of guessing.

## The Core Trade

**Economics**: Compute is cheap and getting cheaper (tokens, wall-clock time, disk). Human attention is expensive and getting more so (Staff engineer focus, context switching, burnout).

So we spend tokens freely to save senior engineer time. That means:

- **Optimize for auditability**, not micro-efficiency. Massive scaffolding and explicit logic beat terse cleverness.
- **Favor verbose receipts** over minimalist diffs. When something breaks, you can trace the decision back to the spec instead of guessing.
- **Measure DevLT** (Dev Lead Time) = the time humans spend actively caring about this change, not total wall-clock.

## How This Works in Practice

**Agents as interns**: They're narrow workers on an assembly line, not autonomous engineers. You give them a slice of context and a clear task. They iterate until critics approve or hit a limit, then hand you receipts.

**Oppositional validation**: The `test-critic` writes harsh reports; the `test-author` makes the fixes. The `code-critic` flags spec violations; the `code-implementer` corrects them. Trust comes from their friction. The receipt of that fight is the trusted artifact.

**Schema gravity**: LLMs drift. Physics pulls them back: contracts, policies, mutation tests, type systems. Success isn't "the LLM understood the spec"; it's "the tests forced compliance." You can't debug vibes, but you can debug "this test failed because the API contract says max_length=255."

**Humans review topology, not vibes**: You don't read every line of agent-generated code. You review the ADR, the test plan, the build receipt, and the critic verdicts. The scaffolding carries the proof; you audit the structure.

**Receipts over speed**: We'd rather spend 10 minutes and produce a 50KB build receipt than finish in 30 seconds with no audit trail. When something fails in production, you want to know *why* the gate let it through.

## Key Principles

### 1. Attention Arbitrage
Spend tokens/time/disk freely if it saves senior engineer attention later. Favor verbose receipts over minimalist diffs.

**Why**: A 50KB build receipt takes 2 minutes to review. Re-reading 300 lines of code to figure out what changed takes 30 minutes.

### 2. Schema Gravity
LLMs drift; physics (contracts, policies, mutation tests) pulls them back. Success is surviving the gravity well; humans review the topology, not vibes.

**Why**: You can't debug vibes. You *can* debug "this test failed because the API contract says max_length=255 and the code returned 256."

### 3. Oppositional Validation
Creation and verification stay separated: author vs critic vs mutator. Trust comes from their friction; the trusted artifact is the receipt of the fight.

**Why**: If the same agent writes and approves code, you're back to "I prompted it and it looks okay." Separation gives you an audit trail of what broke and how it got fixed.

### 4. Narrow Agents, Not Omniscient Engineers
Agents are infinite interns managed via flows, not chat. Give a context slice and a narrow task; accept bounce-backs, fix the brief, rerun.

**Why**: A narrow task with clear success criteria (tests pass, critic approves) is debuggable. "Just implement this feature" is not.

### 5. Volume Buys Clarity
Large PRs are good when scaffolding proves the logic. AI code should be explicit and boring; humans review intent, scaffolding carries proof.

**Why**: A 500-line PR with 200 lines of tests and explicit error handling is easier to review than a 50-line PR where you have to guess what happens on edge cases.

## Factory Model

Think of this as an assembly line:
- **Flows** are the conveyor belt (Signal → Plan → Build → Gate → Operate)
- **Agents** are the robots at each station
- **Schema** (contracts, tests, policies) is the mold that keeps work in bounds
- **Receipts** are QA stamps at each station
- **Humans** are the plant manager who reviews stamps, not every weld

This posture fits platform engineering: you're building a reliable pipeline, not a magic wand.

## Evolution: From Vibe Coding to Vibe Architecting

The shift isn't "stop using AI for code." It's moving from:
- "I prompted it and it looks okay" (vibe coding)

To:
- "I defined the schema/ADR/mutation thresholds, and the swarm ground until it turned green" (vibe architecting)

You still need judgment to set up the gravity well (what contracts? what tests? what thresholds?). But once it's set, agents do the grinding and you review the receipts.

## How This Repo Enforces It

- **Flow 1 (Signal)**: Context slicing + clarified requirements conserve human attention
- **Flow 2 (Plan)**: ADRs, contracts, observability, policy, and test plans build the gravity well
- **Flow 3 (Build)**: Adversarial microloops and mutation prefer receipts over speed
- **Flow 4 (Gate)**: Second verification layer keeps gravity intact before merge
- **Flow 5 (Operate)**: Production signals harden the mold and shorten future DevLT via playbooks

## What This Is Good For

- Platform / DevEx / infra teams automating SDLC
- Staff+ engineers designing CI/CD flows with agent integration
- Teams building or evaluating agentic tooling
- Environments where compute is cheaper than senior engineer time

## What This Isn't Good For

- Small teams or simple projects (this is overkill; just use code completion)
- Environments where compute is expensive or constrained
- Teams that can't review receipts/ADRs/test plans (you still need human judgment)
- Projects where "just ship it" beats "prove it works"
