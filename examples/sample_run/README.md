# Sample Run: Customer Support Stale-Context Gap

This directory contains one synthetic end-to-end trace through the current LoPAS
Protocol Foundry stages.

## What the run demonstrates

A manual Observation describes a support operator checking incomplete requests before
reply preparation. The Proxy normalizes that workaround. The Protocol Generator turns
it into an unconfirmed, review-only Protocol Candidate. The Scenario Generator then
creates a ten-case suite containing contract tests and independent safety challenges.

This run selects the `stale_context` case. The candidate has no source-freshness
condition, so the deterministic Simulator falls through to its default `REVIEW` route
and marks the modeled task complete. The Independent Grader compares that actual result
with the predeclared independent safety expectation of `HOLD`, identifies a missing
freshness guard, and returns `reject` for this candidate version.

The point is not that the simulation proves a real support workflow is unsafe. The point
is that the Foundry can preserve provenance, expose a missing guard, attribute the gap to
the candidate rather than silently blaming the Simulator, and leave an inspectable
Receipt.

## File order

| File | Stage | Purpose |
|---|---|---|
| `00_manifest.yaml` | run index | IDs, order, result, and limitations |
| `01_observation.yaml` | ingest | Source-grounded synthetic observation |
| `02_proxy.yaml` | proxy | Reusable normalized interpretation |
| `03_protocol_candidate.yaml` | protocol | Unconfirmed review-only procedure |
| `04_scenario_suite.yaml` | scenario generation | Ten predeclared tests |
| `05_simulation_record.yaml` | simulation | Blinded pre-grade factual record |
| `06_independent_grade.yaml` | grading | Independent sidecar audit record |
| `07_simulation_receipt.yaml` | receipt merge | Schema-compatible merged receipt |

## Trace

```text
obs-idea-002
  -> proxy-idea-002-llm
  -> protocol-customer-support-llm-001
  -> scenario-customer-support-llm-001-stale-context-gap
  -> simrcpt-customer-support-stale-context-001
  -> grade-customer-support-stale-context-001
```

## Expected and actual behavior

```yaml
expected_route: HOLD
expected_task_completed: false
actual_route: REVIEW
actual_task_completed: true
verdict: reject
```

The mismatch is intentional. This sample shows the Foundry discovering a candidate gap,
not merely confirming a happy path.

## Validation boundary

The Observation, Proxy, Protocol Candidate, Scenario Suite, and Independent Grade are
based on the validated worked examples in the corresponding prompt documents. The final
Simulation Receipt is formed by merging the blinded Simulator record with only the
receipt-compatible fields from the Independent Grade.

This sample stops before Selection, post-grade Routing, and PoC Promotion. Those stages
require aggregate evidence across multiple simulation receipts and explicit promotion
criteria; one synthetic receipt is not enough.
