# Design Options

Option A (preferred): Add a minimal handler at routing layer that returns static JSON `{ "status": "ok" }`.

Option B: Add health endpoint that performs lightweight dependency checks (DB ping) — higher complexity.

Decision: Option A — minimal, low risk.
