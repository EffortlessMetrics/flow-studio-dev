"""
Test suite for critical count invariants (v2.3.0).

These tests prevent documentation drift by enforcing that hardcoded counts
in documentation (CLAUDE.md, RELEASE_NOTES, etc.) remain synchronized with
the actual implementation.

Why these invariants matter:
- Selftest step count: Affects CI budgets, parallel execution waves, and
  user expectations about validation coverage.
- Agent count: Affects tooling (gen-adapters), documentation, and model
  distribution tracking.
- Skills count: Affects skill lookup, validation, and agent capabilities.

Authoritative counts for v2.3.0:
- Selftest: 16 steps (1 KERNEL, 13 GOVERNANCE, 2 OPTIONAL)
- Domain agents: 45 (in .claude/agents/*.md)
- Total agents: 48 (3 built-in + 45 domain)
- Skills: 4 (test-runner, auto-linter, policy-runner, heal_selftest)
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Add swarm/tools to path for importing config
sys.path.insert(0, str(REPO_ROOT / "swarm" / "tools"))


# ============================================================================
# Selftest Step Count Invariants
# ============================================================================


class TestSelftestStepInvariants:
    """Verify selftest step counts match documented values."""

    def test_total_steps_is_16(self):
        """
        Selftest has exactly 16 steps.

        This count is documented in:
        - CLAUDE.md (Essential Commands > Selftest)
        - docs/RELEASE_NOTES_2_3_0.md
        - swarm/tools/selftest_config.py docstring

        Changes to this count require updating all documentation.
        """
        from selftest_config import SELFTEST_STEPS

        assert len(SELFTEST_STEPS) == 16, (
            f"Expected 16 selftest steps, got {len(SELFTEST_STEPS)}. "
            "If intentional, update documentation in CLAUDE.md and RELEASE_NOTES."
        )

    def test_kernel_tier_count_is_1(self):
        """
        Exactly 1 KERNEL step (core-checks).

        KERNEL steps block workflow on failure. This is the critical
        fast-path check that must pass before other checks run.
        """
        from selftest_config import SELFTEST_STEPS, SelfTestTier

        kernel_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.KERNEL]
        assert len(kernel_steps) == 1, (
            f"Expected 1 KERNEL step, got {len(kernel_steps)}: "
            f"{[s.id for s in kernel_steps]}"
        )
        assert kernel_steps[0].id == "core-checks", (
            f"Expected KERNEL step to be 'core-checks', got '{kernel_steps[0].id}'"
        )

    def test_governance_tier_count_is_13(self):
        """
        Exactly 13 GOVERNANCE steps.

        GOVERNANCE steps should pass but can warn in degraded mode.
        This count affects parallel execution wave planning.
        """
        from selftest_config import SELFTEST_STEPS, SelfTestTier

        governance_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.GOVERNANCE]
        assert len(governance_steps) == 13, (
            f"Expected 13 GOVERNANCE steps, got {len(governance_steps)}: "
            f"{[s.id for s in governance_steps]}"
        )

    def test_optional_tier_count_is_2(self):
        """
        Exactly 2 OPTIONAL steps.

        OPTIONAL steps are informational only; failures don't affect
        the overall selftest status.
        """
        from selftest_config import SELFTEST_STEPS, SelfTestTier

        optional_steps = [s for s in SELFTEST_STEPS if s.tier == SelfTestTier.OPTIONAL]
        assert len(optional_steps) == 2, (
            f"Expected 2 OPTIONAL steps, got {len(optional_steps)}: "
            f"{[s.id for s in optional_steps]}"
        )

    def test_tier_counts_sum_to_total(self):
        """All tier counts sum to total step count (no missing tiers)."""
        from selftest_config import SELFTEST_STEPS, SelfTestTier

        kernel = len([s for s in SELFTEST_STEPS if s.tier == SelfTestTier.KERNEL])
        governance = len([s for s in SELFTEST_STEPS if s.tier == SelfTestTier.GOVERNANCE])
        optional = len([s for s in SELFTEST_STEPS if s.tier == SelfTestTier.OPTIONAL])

        total = kernel + governance + optional
        assert total == len(SELFTEST_STEPS), (
            f"Tier counts ({kernel} + {governance} + {optional} = {total}) "
            f"don't sum to total steps ({len(SELFTEST_STEPS)})"
        )


# ============================================================================
# Agent Count Invariants
# ============================================================================


class TestAgentCountInvariants:
    """Verify agent counts match documented values."""

    def test_domain_agents_count_is_45(self):
        """
        Exactly 45 domain agent files in .claude/agents/*.md.

        Domain agents are defined in .claude/agents/ with YAML frontmatter.
        This count is documented in:
        - CLAUDE.md (Agent Summary)
        - docs/AGENT_OPS.md

        Changes require updating gen-adapters output expectations.
        """
        agents_dir = REPO_ROOT / ".claude" / "agents"
        agent_files = list(agents_dir.glob("*.md"))

        assert len(agent_files) == 45, (
            f"Expected 45 domain agent files, got {len(agent_files)}. "
            "If intentional, update documentation in CLAUDE.md and AGENT_OPS.md."
        )

    def test_total_agents_is_48(self):
        """
        Total agent count is 48 (3 built-in + 45 domain).

        Built-in agents (explore, plan-subagent, general-subagent) are
        provided by Claude Code and have no local definition files.

        This count is used in:
        - CLAUDE.md (Agent Summary: "Total: 48 agents")
        - Release notes and presentations
        """
        BUILTIN_AGENT_COUNT = 3  # explore, plan-subagent, general-subagent
        agents_dir = REPO_ROOT / ".claude" / "agents"
        domain_agent_count = len(list(agents_dir.glob("*.md")))

        total = BUILTIN_AGENT_COUNT + domain_agent_count
        assert total == 48, (
            f"Expected 48 total agents (3 built-in + 45 domain), got {total} "
            f"(3 built-in + {domain_agent_count} domain)"
        )

    def test_builtin_agents_are_documented(self):
        """Built-in agent names are consistent with documentation."""
        # These are Claude Code built-in agents, not defined in .claude/agents/
        BUILTIN_AGENTS = {"explore", "plan-subagent", "general-subagent"}

        # Verify none of these exist as files (would be a conflict)
        agents_dir = REPO_ROOT / ".claude" / "agents"
        for builtin in BUILTIN_AGENTS:
            agent_file = agents_dir / f"{builtin}.md"
            assert not agent_file.exists(), (
                f"Built-in agent '{builtin}' should NOT have a file in .claude/agents/"
            )


# ============================================================================
# Skills Count Invariants
# ============================================================================


class TestSkillsCountInvariants:
    """Verify skills list matches documented values."""

    def test_skills_list_matches_exactly(self):
        """
        Exactly 4 skills with specific names.

        Skills are global capabilities that agents invoke via frontmatter.
        This list is documented in:
        - CLAUDE.md (Skills vs. Agents)
        - swarm/CLAUDE.md

        Each skill has a SKILL.md file in .claude/skills/<name>/.
        """
        EXPECTED_SKILLS = {"test-runner", "auto-linter", "policy-runner", "heal_selftest"}

        skills_dir = REPO_ROOT / ".claude" / "skills"
        actual_skills = set()

        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                skill_file = skill_path / "SKILL.md"
                if skill_file.exists():
                    actual_skills.add(skill_path.name)

        assert actual_skills == EXPECTED_SKILLS, (
            f"Skills mismatch.\n"
            f"Expected: {sorted(EXPECTED_SKILLS)}\n"
            f"Got: {sorted(actual_skills)}\n"
            f"Missing: {sorted(EXPECTED_SKILLS - actual_skills)}\n"
            f"Extra: {sorted(actual_skills - EXPECTED_SKILLS)}"
        )

    def test_skills_count_is_4(self):
        """
        Exactly 4 skills.

        This is a redundant check with test_skills_list_matches_exactly,
        but provides a clearer error message for count mismatches.
        """
        skills_dir = REPO_ROOT / ".claude" / "skills"
        skill_count = sum(
            1 for skill_path in skills_dir.iterdir()
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists()
        )

        assert skill_count == 4, (
            f"Expected 4 skills, got {skill_count}. "
            "If intentional, update documentation in CLAUDE.md."
        )


# ============================================================================
# Cross-validation Tests
# ============================================================================


class TestCrossValidation:
    """Ensure counts are consistent across different sources."""

    def test_selftest_steps_have_unique_ids(self):
        """All selftest steps have unique IDs."""
        from selftest_config import SELFTEST_STEPS

        ids = [s.id for s in SELFTEST_STEPS]
        assert len(ids) == len(set(ids)), (
            f"Duplicate step IDs found: "
            f"{[id for id in ids if ids.count(id) > 1]}"
        )

    def test_agent_files_are_markdown(self):
        """All agent files in .claude/agents/ are .md files (excluding temp files)."""
        agents_dir = REPO_ROOT / ".claude" / "agents"
        # Exclude common editor temp files: .swp, ~, .bak, etc.
        non_md_files = [
            f.name for f in agents_dir.iterdir()
            if f.is_file()
            and not f.name.endswith(".md")
            and not f.name.startswith(".")  # hidden/temp files
            and not f.name.endswith("~")    # backup files
            and not f.name.endswith(".bak") # backup files
        ]

        assert len(non_md_files) == 0, (
            f"Non-markdown files in .claude/agents/: {non_md_files}"
        )

    def test_no_persistent_hidden_files_in_agents(self):
        """No persistent hidden files in .claude/agents/ (temp editor files allowed)."""
        agents_dir = REPO_ROOT / ".claude" / "agents"
        # Filter out common editor temp files (.swp, .swo, etc.)
        TEMP_FILE_PATTERNS = {".swp", ".swo", ".swn", ".orig", ".bak"}
        hidden_files = [
            f.name for f in agents_dir.iterdir()
            if f.name.startswith(".")
            and not any(f.name.endswith(ext) for ext in TEMP_FILE_PATTERNS)
        ]

        assert len(hidden_files) == 0, (
            f"Persistent hidden files in .claude/agents/: {hidden_files}"
        )
