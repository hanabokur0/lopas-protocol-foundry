# Compatibility note

This is a C++20 **reference port** of the public LoPAS Protocol Foundry v0.1 design, not a bit-for-bit rewrite of every Python module.

Preserved in this port:

- Observation -> Proxy -> Protocol Candidate -> Simulation/Independent Grading -> Selection -> PoC Promotion -> Shadow Receipt pipeline.
- Conservative route precedence: `DENY > ESCALATE > HOLD > REVIEW > AUTO`.
- Unsupported expressions become `HOLD` rather than being guessed.
- Candidate intent starts `unconfirmed` unless a human explicitly confirms it.
- Selection keeps safety rejection separate from the weighted utility score.
- Selection thresholds mirror the current Python reference values for minimum receipts/families and elite/anomaly/reject boundaries.
- Promotion requires evidence; missing source diversity, monitoring, rollback, authority, or approval produces `HOLD`.
- Shadow execution never performs an external effect and emits `external_effects: []`.

Not yet parity-complete:

- YAML/NDJSON input and repository JSON-Schema validation. This C++ v0.1 accepts JSON observations/evidence/bindings.
- Task-specific Proxy rules and Protocol templates are simplified to a deterministic generic baseline.
- Full synthetic scenario family generation and cross-candidate behavioral-distance graph are simplified.
- Stage-local CLIs are represented by one integrated CLI.
- Historical replay and production integrations remain out of scope, consistent with the upstream project's stated v0.1 scope.

The point of this first port is to provide a buildable, testable C++20 execution core that can be compared against the Python reference in later golden tests.
