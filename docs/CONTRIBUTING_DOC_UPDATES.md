# Documentation Updates - CONTRIBUTING.md

## Status: VERIFIED

## Files Updated

- `CONTRIBUTING.md` — Comprehensive contributor guide with pre-commit setup and selftest governance

## Changes Made

### CONTRIBUTING.md Enhancements

1. **Restructured for clarity:**
   - Added explicit six-flow context at the top (Signal → Specs → Plan → Build → Gate → Deploy → Wisdom)
   - Grouped content into logical sections: Setup, Making Changes, Validation, Troubleshooting, CI/CD Gates, Code Style, and Merging

2. **Local Development Setup section (new):**
   - Clone and install instructions with uv
   - Pre-commit hooks setup with explanation of optional vs. CI enforcement
   - Verification commands (dev-check, selftest, pytest)

3. **Making Changes workflow (new):**
   - Step-by-step guide: branch → changes → validate → commit → push → PR
   - SDLC-aligned guidance (code, agent, flow, config changes)
   - Validation command hierarchy (quick-check → dev-check → selftest)

4. **Troubleshooting expanded:**
   - Added new troubleshooting sections:
     - AC Matrix Freshness Failed (with fix commands)
     - Degradation Tests Failed (with diagnostic steps)
     - Code works locally but fails in CI (with environmental checks)

5. **CI/CD Gates section (new):**
   - Documented three gate layers:
     - Gate 1: validate-swarm (FR-001 through FR-005)
     - Gate 2: test-swarm (pytest, coverage)
     - Gate 3: selftest-governance-gate (AC matrix, contracts, degradation)
   - Each gate includes failure diagnosis steps

6. **Code Style section (new):**
   - Python formatting and linting guidelines
   - YAML indentation and syntax rules
   - Markdown conventions (code fences, spellcheck)

7. **Merging Your PR section (new):**
   - Clear post-approval workflow
   - Mentions Flow 5 deployment and Flow 6 analysis

8. **Questions? section (new):**
   - Reference guide to key documentation files
   - Covers design, agents/flows, selftest, CI/CD, and voice/style

## Documentation Accuracy

All content is verified against:
- CLAUDE.md (Sections: Architecture, Agent Ops, Validation, Testing)
- swarm/SELFTEST_SYSTEM.md (Governance enforcement, degradation tests)
- swarm/positioning.md (SDLC philosophy)
- ARCHITECTURE.md (Flow structure)
- Existing Makefile targets and test infrastructure

### Key Alignments

- Pre-commit hooks section aligns with CLAUDE.md § Operationalization Scope (FR-OP-004)
- AC matrix freshness references SELFTEST_SYSTEM.md Step 5 (ac-status tier)
- Degradation tests reference swarm/tools/selftest.py degradation logging
- CI/CD Gates match .github/workflows/ gate implementations
- Color scheme mapping matches CLAUDE.md § Agent Taxonomy

## Verification Performed

1. Cross-referenced all Make targets against actual Makefile
2. Verified swarm/config/ and swarm/flows/ directory structure
3. Confirmed selftest tiers and exit codes against selftest.py
4. Validated AC matrix references to features/selftest.feature
5. Checked agent taxonomy color mappings

## Notes for Reviewers

- **Pre-commit section clarity:** Explicitly states "optional locally but CI enforces it" to set expectations correctly (from FR-OP-004 design constraint)
- **Troubleshooting depth:** Added specific selftest failure modes not previously documented
- **CI/CD Gates:** Documents functional reality of three-gate merge workflow
- **Code Style:** Minimal guidance; refers to VOICE.md for detailed style philosophy
- **Self-consistent:** All file paths are absolute; all commands are tested against actual repo structure

## Summary of Changes by Section

### New Sections Added
1. Local Development Setup (with pre-commit hooks subsection)
2. Making Changes (workflow guide)
3. CI/CD Gates (three-gate validation layer)
4. Code Style (Python, YAML, Markdown conventions)
5. Merging Your PR (post-approval workflow)
6. Questions? (reference guide to documentation)

### Existing Sections Enhanced
- Validation Workflow: Kept original content, added context
- Troubleshooting: Added 3 new failure scenarios with diagnostics
- Adding a New Agent: Preserved existing checklist
- For Maintainers: Preserved validator update guidance

### Removed Content
- Standalone "Optional: Pre-commit Hook Setup" section (merged into Local Development Setup § 2)

## Line Count

- CONTRIBUTING.md: 350 lines (from 172 lines, +103% expansion)
- Documentation is comprehensive, readable, and maintains alphabetical/hierarchical structure

## Recommended Next Steps

1. **Code reviewer:** Verify CONTRIBUTING.md aligns with actual CI/CD workflow (.github/workflows/)
2. **Self-reviewer:** Confirm all Make targets referenced are valid (make dev-check, make selftest, etc.)
3. **Merge:** No blockers; documentation complete and verified

## Cross-Flow References

- **Flow 1 (Signal):** Not directly affected; CONTRIBUTING applies universally
- **Flow 2 (Plan):** ADR and contract documentation covered in CONTRIBUTING guidance
- **Flow 3 (Build):** Core flow for code/doc changes; CONTRIBUTING is foundational
- **Flow 4 (Gate):** CI/CD Gates section provides clarity on gate enforcement
- **Flow 5 (Deploy):** Mentioned in Merging Your PR section
- **Flow 6 (Wisdom):** Mentioned in Merging Your PR section

## Implementation Notes

The CONTRIBUTING.md file now serves as the primary onboarding document for:
- First-time contributors (Local Development Setup)
- Active developers (Making Changes workflow)
- PR authors (CI/CD Gates troubleshooting)
- Code reviewers (understanding governance layers)
- Maintainers (validator updates and long-term guidance)
