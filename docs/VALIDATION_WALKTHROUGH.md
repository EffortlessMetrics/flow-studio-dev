---
title: Validation System Walkthrough
description: Learn how the swarm validator catches mistakes through a realistic scenario
last_updated: 2025-12-01
---

# Validation System Walkthrough

> **For New Contributors**: This document teaches you how the swarm validator works by walking through a realistic task: adding a new agent. You'll encounter common mistakes, see the exact error messages, and learn why each validation check matters.

---

## Table of Contents

1. [Part 1: The Scenario](#part-1-the-scenario)
2. [Part 2: Step-by-Step Walkthrough](#part-2-step-by-step-walkthrough)
3. [Part 3: Understanding the FRs](#part-3-understanding-the-frs)
4. [Part 4: Running Validation Yourself](#part-4-running-validation-yourself)
5. [Part 5: When Validation Fails](#part-5-when-validation-fails)
6. [Part 6: Key Takeaways](#part-6-key-takeaways)
7. [Further Reading](#further-reading)

---

## Part 1: The Scenario

Imagine you're a new contributor to the demo-swarm repo. You've been asked to add a new agent called `incident-responder` to help Flow 4 (Gate) identify critical issues that need emergency escalation.

Your task:
1. Add the agent to `swarm/AGENTS.md` (the registry)
2. Create `.claude/agents/incident-responder.md` (the agent definition)
3. Reference the agent in the appropriate flow spec
4. Run validation to confirm everything is correct

**Here's the problem:** You're going to make realistic mistakes:
- Missing a required field in the registry
- Creating the agent file with the wrong filename format
- Choosing a color that doesn't match the agent's role
- Misspelling the agent name when adding it to a flow
- Using a hardcoded path instead of the `RUN_BASE` placeholder
- Referencing a skill that doesn't exist

Sound familiar? These are the mistakes the validator catches. Let's walk through each one, see the exact error message, and learn how to fix it.

By the end, you'll understand not just "how to fix errors," but *why the validator cares* about each constraint. That's the real power of this system: validation is a teacher, not just a bouncer.

---

## Part 2: Step-by-Step Walkthrough

### Step 1: Add to AGENTS.md (Missing Color Field)

You create an entry in `swarm/AGENTS.md` to register your new agent. Your entry looks like:

```yaml
| incident-responder | gate | verification | [COLOR_MISSING] | project/user | Identify critical issues requiring emergency escalation. |
```

Wait—you forgot to fill in the color! You rush to submit. Let's see what happens when validation runs:

```bash
$ make validate-swarm
```

**Validation Error (FR-002: Frontmatter):**

```
✗ FRONTMATTER: swarm/AGENTS.md:line 92: Agent 'incident-responder'
  has invalid or missing color field
  Fix: Add a valid color from: yellow, purple, green, red, blue, orange, pink, cyan
       Color must match role_family: role_family=verification → color=blue
```

**What went wrong:**

You registered the agent in the table, but the color field is blank. Validation checks that:
1. Every agent in AGENTS.md has a color (required field, not optional)
2. The color matches the semantic role family you chose (`verification` → blue)

The validator looked at the table row, found no color, and caught it immediately.

**Why the validator cares:**

Colors aren't decorative. They're semantic markers tied to role families. The color tells the whole team what kind of agent this is:
- `blue` = verification/checking (security-scanner, mutator, deploy-monitor)
- `green` = implementation/changing code (code-implementer, fixer, repo-operator)
- `red` = critic (test-critic, code-critic)

If a "verification" agent could be any color, swarm navigation becomes confusing. You'd squint at the Flow Studio graph and think "wait, is this agent reviewing or implementing?" The color constraint removes ambiguity.

**The fix:**

Update AGENTS.md to:

```yaml
| incident-responder | gate | verification | blue | project/user | Identify critical issues requiring emergency escalation. |
```

Now run validation again:

```bash
$ make validate-swarm
```

Assuming you've also created the agent file (next step), the AGENTS.md entry should validate. Good!

**Lesson:** Required fields must be present and semantically correct. The validator enforces the schema.

---

### Step 2: Create Agent File (Wrong Filename Format)

Now you create the agent definition file. You name it `.claude/agents/incident_responder.md` (with an underscore).

You write:

```yaml
---
name: incident-responder
description: Identify critical issues requiring emergency escalation
color: blue
model: inherit
---

You are the **Incident Responder**.

## Behavior

1. Review gate outputs
2. Flag critical issues
```

You commit and push. Let's validate:

```bash
$ make validate-swarm
```

**Validation Error (FR-001: Bijection):**

```
✗ BIJECTION: swarm/AGENTS.md:line 92: Agent 'incident-responder' is
  registered but .claude/agents/incident-responder.md does not exist

  Found file .claude/agents/incident_responder.md (underscore)
  Note: Filenames must be kebab-case and match registry key exactly
  Fix: Rename .claude/agents/incident_responder.md →
       .claude/agents/incident-responder.md
```

**What went wrong:**

You created the file with an underscore (`incident_responder`) but registered it with a hyphen (`incident-responder`). The validator checks that:
1. Every agent in AGENTS.md has a corresponding file
2. The filename matches the registry key *exactly* (case-sensitive, kebab-case)
3. No extra files exist without registry entries

You have a bijection (1:1 mapping) error: the registry entry and the file don't correspond.

**Why the validator cares:**

Automation depends on this mapping. When an orchestrator reads AGENTS.md and sees `incident-responder`, it looks for `.claude/agents/incident-responder.md` by name. If the file is `incident_responder.md`, the lookup fails silently, and the agent can't be invoked.

Worse: a developer glancing at the registry might assume the agent exists when it doesn't. The bijection check prevents this silent failure.

**The fix:**

Rename the file:

```bash
mv .claude/agents/incident_responder.md .claude/agents/incident-responder.md
```

Validate again:

```bash
$ make validate-swarm
```

If the frontmatter is valid (name, color, description, model), this step should pass now. Good!

**Lesson:** Filenames are automation contracts. They must match the registry key exactly (kebab-case, no underscores).

---

### Step 3: Color Mismatch (Role Family ↔ Color)

Now assume you created the file correctly, but there's a twist: you second-guessed yourself about the color.

In AGENTS.md, you have:

```yaml
| incident-responder | gate | verification | blue | project/user | Identify critical issues requiring emergency escalation. |
```

But in your agent file (`.claude/agents/incident-responder.md`), you wrote:

```yaml
---
name: incident-responder
description: Identify critical issues requiring emergency escalation
color: green
model: inherit
---
```

Why green? You thought "incident responder sounds like someone making decisions, which is implementation." But verification is the right role family. Let's validate:

```bash
$ make validate-swarm
```

**Validation Error (FR-002b: Color Match):**

```
✗ FRONTMATTER: .claude/agents/incident-responder.md: color 'green'
  does not match expected color 'blue' for role family 'verification'

  AGENTS.md says role_family=verification → color must be blue
  Found: color=green (role family for implementation)

  Fix: Change frontmatter to color: blue
```

**What went wrong:**

The agent file's color doesn't match the role family declared in AGENTS.md. You have a mismatch: the registry says "verification" (blue), but the frontmatter says "green" (implementation). This is a consistency error.

**Why the validator cares:**

The color-to-role-family mapping is the semantic core of the swarm. Colors are deterministic:

- `verification` → `blue` (always)
- `implementation` → `green` (always)
- `critic` → `red` (always)
- `analytics` → `orange` (always)
- `shaping` → `yellow` (always)
- `spec` / `design` → `purple` (always)
- `reporter` → `pink` (exactly one)
- `infra` → `cyan` (built-ins and utilities)

If an agent's color could drift from its role family, the swarm becomes ambiguous. The Flow Studio graph depends on these mappings to display the right visual cues. A "verification" agent showing up as green confuses viewers—they'd expect it to be implementation.

**The fix:**

Update your agent file:

```yaml
---
name: incident-responder
description: Identify critical issues requiring emergency escalation
color: blue
model: inherit
---
```

Validate again:

```bash
$ make validate-swarm
```

Should pass now!

**Lesson:** Color is not a choice; it's derived from role family. The validator enforces the mapping to keep the swarm legible.

---

### Step 4: Agent Reference in Flow (Typo with Suggestion)

Now that your agent is registered and created, you add it to a flow spec. You edit `swarm/flows/flow-gate.md` (Gate) to include it:

```markdown
| gate-fixer | gate | implementation | Apply mechanical fixes → code changes, fix_summary.md. |
| incident-response | gate | verification | Identify critical issues requiring emergency escalation. |
```

Oops! You typed `incident-response` (singular) instead of `incident-responder` (with "er"). Let's validate:

```bash
$ make validate-swarm
```

**Validation Error (FR-003: Flow References):**

```
✗ REFERENCE: swarm/flows/flow-gate.md:line 45: references unknown agent
  'incident-response'

  No agent registered with that name. Did you mean:
    - incident-responder (edit distance: 1) ← best match
    - code-responder (edit distance: 3)
    - incident-analyzer (edit distance: 4)

  Fix: Update reference to 'incident-responder', or register the unknown agent
       in swarm/AGENTS.md and create .claude/agents/incident-responder.md
```

**What went wrong:**

You referenced an agent in the flow spec that doesn't exist in the registry. The validator uses Levenshtein distance (edit distance) to detect typos and suggest corrections. It found "incident-responder" is only 1 character different from "incident-response", so it suggests the fix.

**Why the validator cares:**

Flow specs reference agents by name. If an agent doesn't exist, the orchestrator can't invoke it. The flow breaks silently—the step is defined, but no agent answers the call.

The Levenshtein distance check is clever: it catches typos without requiring exact matches. A 1–2 character difference is almost certainly a typo. The validator catches it and suggests the correction.

**The fix:**

Update the flow spec:

```markdown
| incident-responder | gate | verification | Identify critical issues requiring emergency escalation. |
```

Validate again:

```bash
$ make validate-swarm
```

Should pass!

**Lesson:** Unknown agent references are detected via fuzzy matching. The validator catches typos and suggests corrections.

---

### Step 5: Hardcoded Path (RUN_BASE Placeholder)

Now you update your agent's prompt to write artifacts. In `.claude/agents/incident-responder.md`, you add:

```yaml
## Outputs

- `swarm/runs/my-incident-123/gate/incident_report.md`
```

You hardcoded the artifact path. Let's validate:

```bash
$ make validate-swarm
```

**Validation Error (FR-005: RUN_BASE Paths):**

```
✗ RUNBASE: swarm/flows/flow-gate.md:line 45: contains hardcoded path
  'swarm/runs/my-incident-123/gate/'

  Flow specs must use RUN_BASE placeholders, not hardcoded paths
  Invalid patterns:
    - swarm/runs/<run-id>/ (hardcoded run ID)
    - $RUN_BASE/ (shell variable syntax)
    - {RUN_BASE}/ (template syntax)

  Valid pattern:
    - RUN_BASE/<flow>/ (portable placeholder)

  Fix: Replace with RUN_BASE/gate/incident_report.md
```

**What went wrong:**

You hardcoded the run ID (`my-incident-123`) into the artifact path. The validator scans flow specs for hardcoded paths and rejects them.

**Why the validator cares:**

RUN_BASE is a portable placeholder. It maps to different locations depending on context:
- Local dev: `swarm/runs/ticket-42/`
- CI pipeline: `/tmp/ci-runs/pr-789/`
- Docker container: `/mnt/artifacts/run-abc123/`

If you hardcode `swarm/runs/my-incident-123/`, the agent only works for that one run. The next developer copies the agent and changes the path manually—error-prone. Flow artifacts become repo-specific instead of reusable.

RUN_BASE is the abstraction that makes the swarm portable. The validator enforces it.

**The fix:**

Update your agent definition:

```yaml
## Outputs

- `RUN_BASE/gate/incident_report.md`
```

Validate again:

```bash
$ make validate-swarm
```

Should pass!

**Lesson:** Artifact paths must use RUN_BASE placeholders, not hardcoded run IDs. This keeps flows portable across repos and CI systems.

---

### Step 6: Skill Reference (Missing Skill File)

Finally, you decide your agent should use the `policy-runner` skill to check policies. You update your agent's frontmatter:

```yaml
---
name: incident-responder
description: Identify critical issues requiring emergency escalation
color: blue
model: inherit
skills: [policy-runner, custom-escalation-checker]
---
```

You reference two skills: `policy-runner` (which exists) and `custom-escalation-checker` (which you haven't created yet). Let's validate:

```bash
$ make validate-swarm
```

**Validation Error (FR-004: Skills):**

```
✗ SKILLS: .claude/agents/incident-responder.md: skill 'custom-escalation-checker'
  declared in frontmatter but .claude/skills/custom-escalation-checker/SKILL.md
  does not exist

  Declared skills: [policy-runner, custom-escalation-checker]
  Found skill files:
    - .claude/skills/policy-runner/SKILL.md ✓
    - .claude/skills/custom-escalation-checker/SKILL.md ✗ MISSING

  Fix: Either:
    a) Create .claude/skills/custom-escalation-checker/SKILL.md with valid frontmatter
    b) Remove 'custom-escalation-checker' from agent frontmatter
```

**What went wrong:**

You declared a skill in the agent's frontmatter, but the skill file doesn't exist. The validator checks that every declared skill has a corresponding SKILL.md file.

**Why the validator cares:**

Skills are tools that agents invoke. If a skill is declared but the file doesn't exist, the agent crashes when it tries to use the skill. The validator catches the mismatch up-front, before the agent runs.

Also, declaring a skill is a way to say "I want to use this capability." If the skill doesn't exist, you need to either create it (new capability) or remove the declaration (intent mismatch).

**The fix:**

For now, let's remove the undefined skill. Update your frontmatter:

```yaml
---
name: incident-responder
description: Identify critical issues requiring emergency escalation
color: blue
model: inherit
skills: [policy-runner]
---
```

Validate again:

```bash
$ make validate-swarm
```

Should pass!

Alternatively, if you really wanted the custom skill, you'd create `.claude/skills/custom-escalation-checker/SKILL.md` with proper frontmatter. But for this walkthrough, removing the undefined skill is simpler.

**Lesson:** Skills declared in agent frontmatter must have corresponding SKILL.md files. The validator verifies the mapping.

---

### Final Validation (All Steps Correct)

Now that you've fixed all the mistakes, let's validate the complete agent:

```bash
$ make validate-swarm
```

Expected output:

```
Validation Summary
==================

✓ FR-001 (Bijection): All agents in AGENTS.md have files; all files in .claude/agents/ are registered
✓ FR-002 (Frontmatter): All required fields present; YAML parses correctly
✓ FR-002b (Color): All agent colors match role family (verification→blue)
✓ FR-003 (Flow References): All agents in flow specs exist in registry or are built-ins
✓ FR-004 (Skills): All declared skills have SKILL.md files
✓ FR-005 (RUN_BASE): All flow specs use RUN_BASE placeholders, no hardcoded paths

PASS: 6/6 checks passed
Exit code: 0
```

Congratulations! Your agent is now valid. The next developer can look at the registry and be confident that:
- The file exists
- The frontmatter is correct
- The agent is used in the right flows
- All its skills are available
- All artifact paths are portable

---

## Part 3: Understanding the FRs

The validator enforces six **Functional Requirements (FRs)** that together ensure swarm integrity. Let's understand what each one protects against.

### FR-001: Bijection (1:1 Agent ↔ File Mapping)

**What it checks:**
- Every agent in `swarm/AGENTS.md` has a corresponding `.claude/agents/<key>.md` file
- Every agent file in `.claude/agents/` is registered in AGENTS.md
- Filenames match registry keys exactly (case-sensitive, kebab-case)

**Why it matters:**

The swarm registry is the single source of truth. When the orchestrator reads AGENTS.md, it expects to find the agent file at a deterministic path. If a file is missing, the agent can't be used. If a file exists but isn't registered, it's dead code (the orchestrator won't call it).

The bijection check ensures this 1:1 contract never breaks. No orphaned agents, no missing files.

**Example failure:** You register `foo-bar` in AGENTS.md but create `.claude/agents/foobar.md` (no hyphen). The validator catches it and suggests renaming the file.

### FR-002: Frontmatter (Required Fields & Types)

**What it checks:**
- Required fields present: `name`, `description`, `color`, `model`
- `name` matches filename and registry key
- `model` is valid: `inherit`, `haiku`, `sonnet`, `opus`
- `color` is valid: yellow, purple, green, red, blue, orange, pink, cyan
- YAML parses correctly (proper `---` delimiters, valid indentation)
- `skills` field (if present) is a list

**Why it matters:**

The frontmatter is a contract with Claude Code's agent execution platform. Each field has semantic meaning:
- `name` is the agent's identifier
- `model` determines which Claude model executes the agent
- `color` is metadata for visualization and role classification
- `skills` are global capabilities the agent can invoke

Missing or malformed fields cause runtime errors. The validator catches them before agents run.

**Example failure:** You set `color: unknown-color`. The validator rejects it and lists valid colors.

### FR-002b: Color ↔ Role Family Match

**What it checks:**
- Agent's `color` in frontmatter matches the `role_family` declared in AGENTS.md
- Mapping is deterministic: `verification` → `blue`, `implementation` → `green`, etc.

**Why it matters:**

Colors encode semantic role families. The swarm has 8 role families, each with a canonical color:

| Color | Role Family | Semantic Meaning |
|-------|-------------|------------------|
| yellow | shaping | Front-of-funnel: parsing signal, early clarity |
| purple | spec, design | Specification & architecture contracts |
| green | implementation | Direct repo changes: code, tests, docs, git ops |
| red | critic | Adversarial reviewers (never fix, only critique) |
| blue | verification | Checks, gates, verification, audit, decisions |
| orange | analytics | Cross-flow analysis, risk, learnings, feedback |
| pink | reporter | Human-facing GitHub reporting (exactly one) |
| cyan | infra | Built-in orchestration infrastructure |

If you set `role_family: verification` but `color: green`, the mapping breaks. Developers looking at the Flow Studio graph see green (expects implementation) but the agent is verification (checks/gates). Confusion ensues.

The validator enforces the mapping to keep the swarm legible.

**Example failure:** You register `incident-responder` as `verification` (blue) but set `color: green`. The validator catches the mismatch and tells you to fix it.

### FR-003: Flow References (Unknown Agent Detection)

**What it checks:**
- Every agent referenced in `swarm/flows/flow-*.md` exists in AGENTS.md
- Built-in agents (`explore`, `plan-subagent`, `general-subagent`) are recognized
- Typos are detected via Levenshtein distance (edit distance ≤ 2)
- Up to 3 similar names are suggested for fixes

**Why it matters:**

Flow specs are the blueprints for agent orchestration. If a flow references an agent that doesn't exist, the orchestrator can't invoke it. The step fails silently—no error, just a broken flow.

The Levenshtein distance check is a UX feature: instead of just saying "agent not found," the validator suggests what you probably meant. A 1–2 character difference is almost certainly a typo.

**Example failure:** You type `incident-response` instead of `incident-responder`. The validator suggests `incident-responder` as the best match.

### FR-004: Skills (Declared Skills Have Files)

**What it checks:**
- Every skill listed in an agent's `skills:` frontmatter has a corresponding `.claude/skills/<name>/SKILL.md` file
- Skill file YAML parses correctly

**Why it matters:**

Skills are global capabilities that agents can invoke. If an agent declares a skill but the skill file doesn't exist, the agent crashes at runtime when it tries to use the skill.

The validator prevents this by checking that declared skills are real.

**Example failure:** You add `skills: [custom-checker]` but don't create `.claude/skills/custom-checker/SKILL.md`. The validator catches it and tells you to create the file or remove the skill declaration.

### FR-005: RUN_BASE (Portable Artifact Paths)

**What it checks:**
- Flow specs and agent prompts use `RUN_BASE/<flow>/` placeholders for artifact paths
- No hardcoded paths like `swarm/runs/<run-id>/`
- No malformed placeholders like `$RUN_BASE` or `{RUN_BASE}`

**Why it matters:**

RUN_BASE is a portable abstraction. It maps to different locations in different environments:
- Local dev: `swarm/runs/ticket-42/`
- CI: `/tmp/ci-runs/pr-789/`
- Docker: `/mnt/artifacts/run-abc123/`

If you hardcode a run ID, the agent only works for that one run. The flow becomes repo-specific instead of portable. Copy-pasting the flow to another org requires manual path updates—error-prone.

RUN_BASE keeps flows portable. The validator enforces the abstraction.

**Example failure:** You write `swarm/runs/my-incident/gate/report.md` instead of `RUN_BASE/gate/report.md`. The validator detects the hardcoded path and tells you to use the placeholder.

---

## Part 4: Running Validation Yourself

### Common Commands

**Full validation (all FRs, all files):**

```bash
make validate-swarm
```

or

```bash
uv run swarm/tools/validate_swarm.py
```

Both run the same underlying validator. The Make target is a convenience wrapper.

**Strict mode (enforce design guidelines):**

```bash
make validate-swarm --strict
```

In default mode, certain design guidelines (like "domain agents should omit `tools:` and `permissionMode:` fields") generate warnings. In strict mode, they become hard errors. Use strict mode before merging to enforce the swarm's philosophy: permissions are granted via prompts, not tool denial.

**Incremental validation (only check modified files):**

```bash
uv run swarm/tools/validate_swarm.py --check-modified
```

For large repos, this is faster. It only validates files changed since main branch. Useful during active development when you want quick feedback.

**Debug mode (show timing and steps):**

```bash
uv run swarm/tools/validate_swarm.py --debug
```

Prints timing information for each validation step. Useful if validation is slow or you want to understand what's being checked.

**JSON output (for dashboards/CI):**

```bash
uv run swarm/tools/validate_swarm.py --json | jq .summary
```

Machine-readable JSON with detailed results. Useful for CI systems or dashboards. Exit code is still 0 (pass) or 1 (fail).

### Interpreting Exit Codes

```bash
$ make validate-swarm
$ echo $?
```

- **Exit code 0**: All checks passed. Ready to commit.
- **Exit code 1**: Validation failed (spec/implementation misalignment). Read error messages and fix.
- **Exit code 2**: Fatal error (missing required files, YAML parse errors). Contact the swarm maintainers if you can't fix it.

### Quick Validation Checks

**Before committing, always run:**

```bash
make validate-swarm
```

If you're confident, use strict mode:

```bash
make validate-swarm --strict
```

If validation passes, you're good to commit. The validator has verified all FRs.

**During development, use incremental mode for speed:**

```bash
uv run swarm/tools/validate_swarm.py --check-modified
```

This only checks files you've changed since main. Feedback in < 500ms on typical repos.

### Common CI Integration

In `.github/workflows/`, validation usually runs before merge:

```yaml
- name: Validate swarm
  run: make validate-swarm

- name: Verify tests pass
  run: cargo test --workspace

- name: Check adapters
  run: make check-adapters
```

If any step fails, the PR can't merge. This prevents invalid agents from landing in main.

---

## Part 5: When Validation Fails

Here are the most common validation failures and how to fix them.

### "Bijection Failed: Agent X is registered but file doesn't exist"

**Error message:**
```
✗ BIJECTION: swarm/AGENTS.md:line 42: Agent 'foo-bar' is registered
  but .claude/agents/foo-bar.md does not exist
```

**Root cause:** You added an agent to AGENTS.md but didn't create the corresponding `.claude/agents/foo-bar.md` file.

**How to fix:**
1. Create `.claude/agents/foo-bar.md` with proper frontmatter:
   ```yaml
   ---
   name: foo-bar
   description: One-line description
   color: [color matching role_family]
   model: inherit
   ---

   You are the **Foo Bar**.
   ...
   ```

2. Run validation again:
   ```bash
   make validate-swarm
   ```

**Prevention:** Always create both the registry entry and the file. Use:
```bash
# Register in AGENTS.md
# Create .claude/agents/foo-bar.md
# Run validation immediately
make validate-swarm
```

### "Bijection Failed: File exists but isn't registered"

**Error message:**
```
✗ BIJECTION: .claude/agents/orphaned-agent.md exists but is not
  registered in swarm/AGENTS.md
```

**Root cause:** You created an agent file but forgot to add it to AGENTS.md.

**How to fix:**
1. Add the agent to AGENTS.md:
   ```yaml
   | orphaned-agent | build | [role_family] | [color] | project/user | [description] |
   ```

2. Ensure the `name:` field in the frontmatter matches the filename exactly.

3. Run validation:
   ```bash
   make validate-swarm
   ```

**Prevention:** Always update AGENTS.md first, then create the file. Test immediately.

### "Color Mismatch: color 'X' does not match role family 'Y'"

**Error message:**
```
✗ FRONTMATTER: .claude/agents/foo-bar.md: color 'green' does not
  match expected color 'blue' for role family 'verification'
```

**Root cause:** You registered the agent with `role_family: verification` (which maps to blue) but set `color: green` in the frontmatter.

**How to fix:**
1. Check the canonical color mapping:
   - `shaping` → `yellow`
   - `spec` → `purple`
   - `design` → `purple`
   - `implementation` → `green`
   - `critic` → `red`
   - `verification` → `blue`
   - `analytics` → `orange`
   - `reporter` → `pink`
   - `infra` → `cyan`

2. Update the agent's frontmatter to match:
   ```yaml
   color: blue
   ```

3. Run validation:
   ```bash
   make validate-swarm
   ```

**Prevention:** Check the color mapping before setting the color. The color is not a choice; it's derived from the role family.

### "Unknown Agent Reference: 'X' in flow"

**Error message:**
```
✗ REFERENCE: swarm/flows/flow-build.md:line 12: references unknown agent
  'explor'; did you mean 'explore'?
```

**Root cause:** You referenced an agent in a flow spec that doesn't exist (typo or wrong name).

**How to fix:**
1. Check the suggestion. The validator provides up to 3 suggestions.
2. Use the correct agent name:
   ```markdown
   | explore | flow | shaping | Fast read-only search. |
   ```

3. If the suggestion isn't right, verify the agent exists in AGENTS.md:
   ```bash
   grep "explore" swarm/AGENTS.md
   ```

4. Run validation:
   ```bash
   make validate-swarm
   ```

**Prevention:** Double-check agent names in flow specs. Use a grep to verify the agent exists.

### "Missing Skill File"

**Error message:**
```
✗ SKILLS: .claude/agents/foo-bar.md: skill 'custom-checker' declared
  in frontmatter but .claude/skills/custom-checker/SKILL.md does not exist
```

**Root cause:** You added a skill to the agent's `skills:` field, but the skill file doesn't exist.

**How to fix:**

Option A (remove the skill):
```yaml
skills: []  # or omit the field entirely
```

Option B (create the skill):
```bash
mkdir -p .claude/skills/custom-checker
touch .claude/skills/custom-checker/SKILL.md
```

Then add frontmatter to SKILL.md:
```yaml
---
name: custom-checker
description: Custom checking capability
---

# Custom Checker Skill

...
```

Run validation:
```bash
make validate-swarm
```

**Prevention:** Only declare skills that already exist in `.claude/skills/`. If you're adding a new skill, create both the SKILL.md file and the agent's `skills:` declaration together.

### "Hardcoded Path (RUN_BASE)"

**Error message:**
```
✗ RUNBASE: swarm/flows/flow-build.md:line 45: contains hardcoded path
  'swarm/runs/my-ticket/build/'; should use RUN_BASE placeholder
```

**Root cause:** You hardcoded a run ID into an artifact path instead of using the RUN_BASE placeholder.

**How to fix:**

Change:
```markdown
| agent | flow | role | Writes to swarm/runs/my-ticket/build/report.md |
```

To:
```markdown
| agent | flow | role | Writes to RUN_BASE/build/report.md |
```

Run validation:
```bash
make validate-swarm
```

**Prevention:** Always use `RUN_BASE/<flow>/` in flow specs and agent prompts. Never hardcode `swarm/runs/<run-id>/`.

### "YAML Parse Error"

**Error message:**
```
✗ FRONTMATTER: .claude/agents/foo-bar.md: YAML parse error:
  frontmatter not terminated with '---'
```

**Root cause:** Your frontmatter has a syntax error (missing closing `---`, bad indentation, etc.).

**How to fix:**

Check the frontmatter structure:
```yaml
---
name: foo-bar
description: Description
color: green
model: inherit
---
```

Common mistakes:
- Closing `---` is missing
- Indentation is inconsistent (use spaces, not tabs)
- Field names have typos (e.g., `colour` instead of `color`)
- Quotes are mismatched

Fix the error and run validation:
```bash
make validate-swarm
```

**Prevention:** Use a YAML validator or editor with YAML support. Check frontmatter structure against existing agents.

---

## Part 6: Key Takeaways

After walking through the validator, here's what you should understand:

1. **Validation prevents semantic inconsistencies, not just syntax errors.**
   - The validator doesn't just check "is this YAML valid?" It checks "do these semantic contracts hold?"
   - Bijection, color matching, and RUN_BASE placeholders are all about enforcing invariants that keep the swarm coherent.

2. **Color + role_family mapping keeps the swarm legible.**
   - Colors aren't decorative. They're semantic markers that tell you what kind of agent this is.
   - The validator enforces the mapping so every viewer (human or machine) can understand the agent's role at a glance.

3. **File naming invariants enable automation.**
   - The bijection check ensures that `swarm/AGENTS.md` and `.claude/agents/` stay synchronized.
   - This enables safe automation: the orchestrator can look up agents by name without guessing.

4. **RUN_BASE placeholders make flows portable.**
   - Hardcoded paths tie flows to one repo, one run, one context.
   - RUN_BASE keeps flows reusable across organizations, CI systems, and environments.

5. **The validator is a teaching tool.**
   - Error messages aren't just "you broke something." They explain *why* the constraint exists.
   - Read the error messages carefully. They tell you not just how to fix the problem, but why the problem matters.

6. **Validation catches mistakes before agents run.**
   - It's much faster to fix a typo in AGENTS.md than to debug a failed flow run.
   - Run validation early, often, and before committing. It's your first line of defense.

7. **Required fields and design constraints are not arbitrary.**
   - Every required field (name, color, model, description) has a semantic meaning.
   - Design constraints (no tools/permissionMode on domain agents, RUN_BASE placeholders) protect the swarm's architecture.

The key insight: **The validator is not a barrier. It's a guardrail.** It catches mistakes, suggests fixes, and explains why constraints exist. Use it to learn the swarm's invariants. Once you internalize them, validation becomes invisible—you'll write correct agents the first time.

---

## Further Reading

- **[CLAUDE.md](../CLAUDE.md)** — Complete guide to the swarm architecture, agent taxonomy, and validation reference
- **[swarm/tools/validate_swarm.py](../swarm/tools/validate_swarm.py)** — Validator source code; read this to understand exactly what each FR checks
- **[swarm/AGENTS.md](../swarm/AGENTS.md)** — Agent registry; the source of truth for all domain agents
- **[swarm/flows/flow-*.md](../swarm/flows/)** — Flow specs; see how agents are referenced in practice
- **[swarm/SELFTEST_SYSTEM.md](../swarm/SELFTEST_SYSTEM.md)** — The broader selftest system that includes validation as one layer

---

**Last Updated:** 2025-12-01
**Validator Version:** 1.0.0+
**Questions?** Read the error message from `make validate-swarm`, check this walkthrough for similar errors, then consult CLAUDE.md § Validation.

