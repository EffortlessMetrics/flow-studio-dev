// AUTO-GENERATED from swarm/config/flows.yaml
// Do not edit manually. Run: make gen-flow-constants

import type { FlowKey } from "./domain.js";

/** Canonical flow ordering in SDLC sequence */
export const FLOW_KEYS: FlowKey[] = ["signal", "plan", "build", "gate", "deploy", "wisdom", "stepwise-demo"];

/** Flow key to numeric index (1-6) */
export const FLOW_INDEX: Record<FlowKey, number> = {
  signal: 1,
  plan: 2,
  build: 3,
  gate: 4,
  deploy: 5,
  wisdom: 6,
  "stepwise-demo": 7,
};

/** Flow key to display title */
export const FLOW_TITLES: Record<FlowKey, string> = {
  signal: "Signal",
  plan: "Plan",
  build: "Build",
  gate: "Gate",
  deploy: "Deploy",
  wisdom: "Wisdom",
  "stepwise-demo": "Stepwise",
};

/** Flow key to description */
export const FLOW_DESCRIPTIONS: Record<FlowKey, string> = {
  signal: "Raw input to problem statement, requirements, BDD scenarios, early risk assessment",
  plan: "Requirements to ADR, contracts, observability spec, test/work plans, design validation",
  build: "Implement via adversarial microloops, build code and tests, self-verify, produce receipts",
  gate: "Pre-merge gate, audit receipts, check contracts/security/policy, recommend merge or bounce",
  deploy: "Move approved artifact to production, execute deployment, verify health, create audit trail",
  wisdom: "Analyze artifacts, detect regressions, extract learnings, close feedback loops",
  "stepwise-demo": "A 10-step demo flow for testing stepwise execution backends",
};
