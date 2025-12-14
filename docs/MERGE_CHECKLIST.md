# Pre-Merge Checklist

> **Purpose:** A single-page checklist for PR authors and reviewers.
> Use this before clicking "Merge" to ensure nothing is missed.

---

## For PR Authors

### Before Requesting Review

- [ ] **Local validation passes**: `make validate-swarm`
- [ ] **Tests pass locally**: `uv run pytest tests/ -v --tb=short`
- [ ] **No lint errors**: `ruff check swarm/` and `black --check swarm/`
- [ ] **Selftest passes**: `make kernel-smoke` (quick) or `make selftest` (full)

### Code Quality

- [ ] **No hardcoded paths**: Use `RUN_BASE/` for run artifacts
- [ ] **No secrets committed**: Check `.env`, credentials, API keys
- [ ] **Type hints added**: For new Python functions
- [ ] **Docstrings added**: For public functions and classes

### Documentation

- [ ] **CHANGELOG.md updated**: For user-facing changes
- [ ] **Docs updated**: If behavior changed or new features added
- [ ] **Agent registry synced**: If agents added/removed

### Test Coverage

- [ ] **Tests added**: For new functionality
- [ ] **No new xfails without reason**: Document why with issue link
- [ ] **No new skips without condition**: Use `@pytest.mark.skipif` with real condition

---

## For Reviewers

### CI Status

- [ ] **Gate 1 (validate-swarm)**: Green checkmark
- [ ] **Gate 2 (test-swarm)**: Green checkmark
- [ ] **Gate 3 (selftest-governance-gate)**: Green checkmark

### Code Review

- [ ] **Logic is correct**: Code does what it claims
- [ ] **No obvious bugs**: Edge cases handled
- [ ] **No security issues**: No injection, no secrets
- [ ] **Style is consistent**: Follows existing patterns

### Documentation Review

- [ ] **PR description is clear**: Explains what and why
- [ ] **Breaking changes noted**: If any
- [ ] **Related issues linked**: If applicable

---

## Gate Failure Quick Reference

| Gate | Local Command | Common Fix |
|------|---------------|------------|
| validate-swarm | `make validate-swarm` | Sync AGENTS.md with .claude/agents/ |
| test-swarm | `uv run pytest tests/` | Fix failing tests |
| selftest-governance | `make selftest-doctor` | Update step counts or AC matrix |

---

## Merge Decision Tree

```
All 3 gates green?
├── YES → Has review approval?
│         ├── YES → Safe to merge
│         └── NO  → Request review
└── NO  → Which gate failed?
          ├── Gate 1 → Run `make validate-swarm` locally
          ├── Gate 2 → Run `uv run pytest tests/` locally
          └── Gate 3 → Run `make selftest-doctor`
```

---

## After Merge

1. Monitor CI/CD for deployment success
2. Check Flow 6 (Wisdom) for regression reports
3. Close related issues if fixed

---

## See Also

- [DEFINITION_OF_DONE.md](./DEFINITION_OF_DONE.md): Full DoD documentation
- [CI_TROUBLESHOOTING.md](./CI_TROUBLESHOOTING.md): CI issue resolution
