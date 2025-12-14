# gh-reporter PR Comment Template Example

This document shows how `gh-reporter` agent would use `mk_flow_link.py` to generate Flow Studio links in PR comments.

## Example 1: Complete Run Report

**Scenario**: All flows complete, no issues

```markdown
## Swarm SDLC Summary for `health-check`

**Run Status**: ✅ All flows complete

[📊 View in Flow Studio](http://localhost:5000/?mode=operator&run=health-check)

### Flow Progress

| Flow | Status | Decision | Link |
|------|--------|----------|------|
| Signal | ✅ Done | ✅ requirements_decision.md | [View](http://localhost:5000/?mode=operator&run=health-check&flow=signal&view=artifacts) |
| Plan | ✅ Done | ✅ work_plan.md | [View](http://localhost:5000/?mode=operator&run=health-check&flow=plan&view=artifacts) |
| Build | ✅ Done | ✅ build_receipt.json | [View](http://localhost:5000/?mode=operator&run=health-check&flow=build&view=artifacts) |
| Gate | ✅ Done | ✅ merge_decision.md | [View](http://localhost:5000/?mode=operator&run=health-check&flow=gate&view=artifacts) |
| Deploy | ✅ Done | ✅ deployment_decision.md | [View](http://localhost:5000/?mode=operator&run=health-check&flow=deploy&view=artifacts) |
| Wisdom | ✅ Done | ✅ feedback_actions.md | [View](http://localhost:5000/?mode=operator&run=health-check&flow=wisdom&view=artifacts) |

---

**How to inspect locally**:
1. Start Flow Studio: `make flow-studio`
2. Click any link above to view flow artifacts
```

---

## Example 2: Partial Run with Issues

**Scenario**: Build flow incomplete, Gate not started

```markdown
## Swarm SDLC Summary for `pr-123-abc123`

**Run Status**: ⚠️ Build incomplete

[📊 View in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123)

### Flow Progress

| Flow | Status | Decision | Link |
|------|--------|----------|------|
| Signal | ✅ Done | ✅ requirements_decision.md | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=signal&view=artifacts) |
| Plan | ✅ Done | ✅ work_plan.md | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=plan&view=artifacts) |
| Build | ⚠️ Partial | ⏳ Missing | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts) |
| Gate | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate) |
| Deploy | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=deploy) |
| Wisdom | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=wisdom) |

### Issues Detected

#### Build Flow - 2 required artifacts missing

**Missing artifacts**:
- `test_summary.md`
- `build_receipt.json`

[🔍 Inspect in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts)

**Steps with missing artifacts**:
- [test_microloop](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&step=test_microloop&view=artifacts&tab=run): Missing `test_summary.md`
- [self_review](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&step=self_review&view=artifacts&tab=run): Missing `build_receipt.json`

### Next Steps

1. ✅ Complete Build flow artifacts
2. ⏳ Run Gate flow for pre-merge validation
3. ⏳ Review receipts before merge

---

**How to inspect locally**:
1. Start Flow Studio: `make flow-studio`
2. Click links above to view flow/step artifacts
3. Fix missing artifacts and re-run Build flow
```

---

## Example 3: Gate Decision Summary

**Scenario**: Gate flow complete with MERGE decision

```markdown
## Gate Decision for `pr-123-abc123`

**Decision**: ✅ MERGE APPROVED

[📊 View Gate artifacts](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&view=artifacts)

### Gate Checks

| Check | Status | Details |
|-------|--------|---------|
| Receipt Audit | ✅ Pass | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=receipt_audit&tab=run) |
| Contract Enforcement | ✅ Pass | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=contract_check&tab=run) |
| Security Scan | ✅ Pass | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=security_scan&tab=run) |
| Coverage Check | ✅ Pass | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=coverage_check&tab=run) |

### Merge Decision

[📄 merge_decision.md](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=merge_decision&tab=run)

**Summary**: All gate checks passed. Code meets quality standards and is ready for merge.

**Next Step**: Merge and deploy → [View Deploy flow](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=deploy)

---

**How to inspect**:
1. Start Flow Studio: `make flow-studio`
2. Review gate decision: [merge_decision.md](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate&step=merge_decision&tab=run)
```

---

## Example 4: Validation Failure Report

**Scenario**: Swarm validation detected issues in flow configs

```markdown
## Swarm Validation Report

**Status**: ❌ FAILED (3 errors)

[📊 View in Flow Studio](http://localhost:5000/?mode=operator&flow=build)

### Issues Detected

#### Flow: build

**Error**: Step `code_microloop` references unknown agent `code-implementor`

- [🔍 Inspect step](http://localhost:5000/?mode=operator&flow=build&step=code_microloop)
- **Fix**: Update agent reference to `code-implementer` or add `code-implementor` to AGENTS.md

#### Flow: gate

**Error**: Missing required artifact `merge_decision.md` in step `merge_decision`

- [🔍 Inspect step](http://localhost:5000/?mode=operator&flow=gate&step=merge_decision&view=artifacts)
- **Fix**: Create `merge_decision.md` artifact or update catalog

---

**Next Steps**:
1. Fix issues listed above
2. Run `make validate-swarm` to verify
3. View updated flows in Flow Studio

**How to inspect**:
```bash
# Start Flow Studio
make flow-studio

# Click links above to view affected flows/steps
```
```

---

## Implementation Pseudocode for gh-reporter

```python
from swarm.tools.mk_flow_link import FlowStudioLinkGenerator
from swarm.tools.run_inspector import RunInspector

def generate_pr_comment(run_id: str) -> str:
    """Generate PR comment with Flow Studio links."""

    # Initialize tools
    gen = FlowStudioLinkGenerator()
    inspector = RunInspector()

    # Get run status
    run_summary = inspector.get_run_summary(run_id)

    # Start comment
    comment = f"## Swarm SDLC Summary for `{run_id}`\n\n"

    # Add run-level link
    run_link = gen.link(run=run_id, mode="operator")
    comment += f"[📊 View in Flow Studio]({run_link})\n\n"

    # Build flow table
    comment += "### Flow Progress\n\n"
    comment += "| Flow | Status | Decision | Link |\n"
    comment += "|------|--------|----------|------|\n"

    for flow_key, flow_result in run_summary.flows.items():
        # Status emoji
        status_emoji = {
            "done": "✅ Done",
            "in_progress": "⚠️ Partial",
            "not_started": "❌ Not Started"
        }[flow_result.status.value]

        # Decision status
        if flow_result.decision_present:
            decision = f"✅ {flow_result.decision_artifact}"
        elif flow_result.status.value == "not_started":
            decision = "—"
        else:
            decision = "⏳ Missing"

        # Generate flow link
        flow_link = gen.link(
            run=run_id,
            flow=flow_key,
            mode="operator",
            view="artifacts"
        )

        comment += f"| {flow_result.title} | {status_emoji} | {decision} | [View]({flow_link}) |\n"

    # Add issues section if any
    issues = []
    for flow_key, flow_result in run_summary.flows.items():
        for step_id, step_result in flow_result.steps.items():
            if step_result.status != "complete":
                issues.append((flow_key, step_id, step_result))

    if issues:
        comment += "\n### Issues Detected\n\n"

        for flow_key, step_id, step_result in issues:
            comment += f"#### {flow_key.title()} Flow - {step_result.required_total - step_result.required_present} required artifacts missing\n\n"

            # Add step link
            step_link = gen.link(
                run=run_id,
                flow=flow_key,
                step=step_id,
                mode="operator",
                view="artifacts",
                tab="run"
            )
            comment += f"[🔍 Inspect in Flow Studio]({step_link})\n\n"

            # List missing artifacts
            missing_artifacts = [
                a.path for a in step_result.artifacts
                if a.required and a.status == "missing"
            ]
            if missing_artifacts:
                comment += f"**Missing artifacts**:\n"
                for artifact in missing_artifacts:
                    comment += f"- `{artifact}`\n"
                comment += "\n"

    # Add footer
    comment += "---\n\n"
    comment += "**How to inspect locally**:\n"
    comment += "1. Start Flow Studio: `make flow-studio`\n"
    comment += "2. Click any link above to view flow artifacts\n"

    return comment
```

---

## CLI Integration Examples

### Generate links for CI

```bash
# In CI/PR workflow
RUN_ID="pr-${PR_NUMBER}-${COMMIT_SHA:0:7}"

# Generate run link
RUN_LINK=$(uv run swarm/tools/mk_flow_link.py --run "$RUN_ID" --mode operator)

# Generate flow links
BUILD_LINK=$(uv run swarm/tools/mk_flow_link.py --run "$RUN_ID" --flow build --mode operator --view artifacts)
GATE_LINK=$(uv run swarm/tools/mk_flow_link.py --run "$RUN_ID" --flow gate --mode operator --view artifacts)

# Post to PR
gh pr comment "$PR_NUMBER" --body "
Build artifacts: $BUILD_LINK
Gate decision: $GATE_LINK
"
```

### Generate links from validation output

```bash
# Get validation issues with Flow Studio URLs
uv run swarm/tools/validate_swarm.py --json | \
  jq -r '.flows | to_entries[] | select(.value.has_issues) |
    "Flow: \(.key)\nURL: \(.value.flow_studio_url)\n"'
```

---

## Design Notes

1. **All links use `mode=operator`** - Assumes PR viewers want operational view, not authoring
2. **Flow links default to `view=artifacts`** - Shows run artifacts, not abstract flow structure
3. **Step links include `tab=run`** - Opens the run-specific artifact tab by default
4. **Links are localhost by default** - Flow Studio is a local dev tool, not deployed
5. **Footer includes setup instructions** - Reminds users to start Flow Studio locally

---

## Benefits

1. **One-click navigation** - Click link → see artifact in context
2. **Contextual inspection** - Step links show exactly which artifact is missing
3. **Consistent format** - Table layout is scannable and predictable
4. **Actionable** - Each issue includes a direct link to investigate
5. **Low friction** - No need to manually construct URLs or navigate UI
