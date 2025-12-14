---
name: Bug Report
about: Report a bug or regression in selftest, validation, or Flow Studio
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

<!-- A clear, concise description of the bug -->

## Steps to Reproduce

1.
2.
3.

## Expected Behavior

<!-- What you expected to happen -->

## Actual Behavior

<!-- What actually happened -->

## Environment

- **OS**: <!-- e.g., macOS 14.2, Ubuntu 22.04, Windows 11 -->
- **Python version**: <!-- e.g., 3.11.5 -->
- **uv version**: <!-- run `uv --version` -->
- **Commit/version**: <!-- run `git rev-parse --short HEAD` -->

## Diagnostic Output

Please run the following and paste the output:

```bash
make selftest-doctor
```

<details>
<summary>selftest-doctor output</summary>

```
<!-- Paste output here -->
```

</details>

## Selftest Status

Please run the following and paste the output:

```bash
make selftest 2>&1 | tail -50
```

<details>
<summary>selftest output (last 50 lines)</summary>

```
<!-- Paste output here -->
```

</details>

## Additional Context

<!-- Any other context, screenshots, or logs that might help -->
