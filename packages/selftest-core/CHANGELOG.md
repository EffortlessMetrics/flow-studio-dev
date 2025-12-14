# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-12-01

### Added

- Core runner infrastructure with `SelfTestRunner`, `Step`, and `StepResult` classes
- Three-tier validation system: KERNEL, GOVERNANCE, and OPTIONAL tiers
- YAML-based configuration loading for step definitions
- Doctor diagnostics via `SelfTestDoctor` for separating harness issues from service issues
- CLI entrypoint with `selftest` command supporting multiple modes
- Reporter system with JSON output (`--json-v2`) and console formatting
- Degraded mode support allowing GOVERNANCE failures when KERNEL passes
- Strict mode enforcement via `--strict` flag
- Plan mode (`--plan`) for showing execution plan without running steps
- Step filtering by tier and name
- Exit code contract: 0 (pass), 1 (failure), 2 (config error)

[Unreleased]: https://github.com/EffortlessMetrics/flow-studio/compare/selftest-core-v0.1.0...HEAD
[0.1.0]: https://github.com/EffortlessMetrics/flow-studio/releases/tag/selftest-core-v0.1.0
