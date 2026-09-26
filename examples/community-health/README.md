# Community Health Adapter — Shadow Example

This example shows how `lopas-protocol-foundry` can represent a community-health
workflow without crossing the repository's current execution boundary.

It is intentionally **not** a medical device, diagnosis system, prescription
system, remote-care service, or production adapter implementation.

## Goal

Represent the following control loop:

```text
Authorized observation
  -> capture-quality check
  -> normalization
  -> provisional risk classification
  -> mandatory clinician review
  -> shadow care-route proposal
  -> Foundry Action Receipt
```

The intended observation sources may include camera images, questionnaires, or
low-cost sensors, but the included fixture contains only synthetic structured
data.

## Safety boundary

This fixture:

- uses synthetic data;
- performs no identity inference from images;
- treats model output as provisional and non-diagnostic;
- requires human clinical review;
- forbids diagnosis, prescription, medication changes, dispensing, provider
  contact, emergency-service contact, and real-world routing;
- fails closed to `HOLD`, `REVIEW`, `ESCALATE`, or `DENY`;
- relies on Foundry Shadow mode, which resolves adapter bindings but does not
  invoke adapters or create external effects.

## Files

- `adapter_bindings.yaml` — action-to-adapter bindings and safety-oriented config.
- `execution_inputs.yaml` — synthetic input bundle.
- `shadow_ready_candidates.yaml` — confirmed synthetic Protocol Candidate.
- `shadow_ready_promotions.yaml` — synthetic Level 3 promotion fixture.

## Run

From the repository root:

```bash
python -m src.execution \
  examples/community_health/shadow_ready_candidates.yaml \
  examples/community_health/shadow_ready_promotions.yaml \
  examples/community_health/adapter_bindings.yaml \
  --inputs examples/community_health/execution_inputs.yaml \
  --output-dir receipts/community_health_shadow \
  --require-ready
```

Expected behavior:

- one Level 3 shadow plan can compile as `READY`;
- every declared action has an enabled adapter binding;
- no adapter is invoked;
- `external_effects` remains empty.

## Why this example exists

The Foundry core is domain-agnostic. Health, agriculture, education, public
services, and other real-world systems can reuse the same pattern:

```text
Observe -> Normalize -> Classify -> Gate -> Human Review
-> Route Proposal -> Verify -> Receipt
```

Domain adapters should supply the schemas, policy rules, evaluators, and
connectors. The Foundry should remain the control and verification plane.

## Before any real clinical integration

A future live implementation would require, at minimum:

1. jurisdiction-specific medical-device and privacy review;
2. validated capture standards and device-quality controls;
3. clinically validated models on the target population;
4. explicit consent, retention, access, and deletion policies;
5. human override and fail-safe procedures;
6. monitoring for distribution shift and silent failure;
7. incident response, rollback, and audit procedures;
8. a separate live adapter runner with explicit capabilities and least privilege.

Do not convert this Shadow fixture into a live medical workflow by simply
enabling an adapter.
