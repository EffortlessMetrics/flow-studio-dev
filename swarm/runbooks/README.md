# Swarm Runbooks

Implementation playbooks for system work. Each `*.md` file is a focused,
step-by-step guide for humans and AI tools.

## What belongs here

**Runbooks** are versioned implementation guides for specific slices of work:

- Selftest / governance improvements
- Flow Studio features and fixes
- Contract tightening work
- Cross-cutting system changes

**NOT runbooks** (use other locations):

- Flow artifacts → `swarm/runs/<run-id>/` (gitignored, transient)
- Flow specs → `swarm/flows/` (abstract role definitions)
- Agent definitions → `.claude/agents/` (provider-specific adapters)
- General docs → `docs/` (external-facing documentation)

## Conventions

1. **One runbook per implementation slice**
   - Small, focused scope
   - Can reference other runbooks for dependencies

2. **Standard structure:**
   ```markdown
   # Runbook: <Title>

   **Branch**: `feature-branch-name`

   ## Goal
   What this work achieves.

   ## Constraints
   Boundaries and requirements that must be respected.

   ## Invariants (Don't Break These)
   What must NOT break during implementation.

   ## Technical Steps
   Numbered implementation steps with code examples.

   ## Success Criteria
   How to verify the work is complete.

   ## Dependencies
   What must be in place before starting this work.

   ## Files to Modify
   - Existing files that need changes

   ## Files to Create
   - New files this work introduces
   ```

3. **Keep runbooks provider-agnostic**
   - No `.claude/`-specific paths for core logic
   - Any AI tool or human should be able to follow

4. **Reference tests explicitly**
   - Name the test files that pin behavior
   - Include example `pytest` commands

## Index

| Runbook | Area | Status |
|---------|------|--------|
| [10min-health-check.md](10min-health-check.md) | Validation | Active |
| [selftest-flowstudio-fastpath.md](selftest-flowstudio-fastpath.md) | Flow Studio | Active |
| [ui-layout-review.md](ui-layout-review.md) | UX Review | Active |

## Usage

Humans and AI tools use these runbooks to:

1. **Plan work** — understand scope before starting
2. **Track progress** — check off steps as completed
3. **Verify completion** — run success criteria checks
4. **Review PRs** — compare implementation against runbook

When starting a new implementation slice, create a runbook first. This trades
a few minutes of planning for clarity throughout the work.
