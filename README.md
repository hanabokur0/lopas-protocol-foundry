LoPAS Protocol Foundry is an experimental reference implementation for turning fragmented observations into structured protocol candidates, simulating them across varied scenarios, and selecting both high-performing and unusual designs for real-world proof-of-concept testing.

Observation
→ Proxy
→ Protocol Candidate
→ Simulation
→ Selection
→ PoC Promotion
→ Receipt
→ ProtocolMemory

Raw observations are materials, not instructions.

The foundry does not automate posts, ideas, complaints, or workarounds directly. It first converts them into explicit, inspectable, and testable protocol candidates.

Why This Exists

Most AI automation begins after a workflow has already been defined:

Human-defined workflow
→ AI agent
→ execution

LoPAS Protocol Foundry explores an earlier layer:

Distributed observations
→ reusable structure
→ candidate workflows
→ simulated evaluation
→ limited real-world PoC

The goal is not to ask an LLM for one “best idea.” The goal is to build a traceable pipeline that can:

collect observations from multiple sources;

separate evidence from interpretation;

convert observations into normalized proxies;

generate multiple protocol candidates;

simulate candidates under different conditions;

preserve both elite and rare behavioral types;

route only qualified candidates toward real-world PoCs;

record every transformation as a receipt.

Status

Current stage: v0.1 design and local prototype

The first release is intentionally narrow:

local JSONL/YAML input;

schema validation;

proxy generation;

protocol candidate generation;

synthetic scenario generation;

simulation receipts;

elite, rare, anomaly, and reject selection;

PoC promotion decisions;

one reproducible end-to-end sample run.

External source adapters, production integrations, autonomous execution, and live social-media ingestion are outside the initial scope.

Core Pipeline

flowchart LR
    A[Raw Observations] --> B[Ingest]
    B --> C[Observation]
    C --> D[Proxy Generation]
    D --> E[Proxy Validation]
    E --> F[Protocol Candidate]
    F --> G[Scenario Simulation]
    G --> H[Simulation Receipts]
    H --> I{Selection}
    I --> J[Elite]
    I --> K[Rare]
    I --> L[Anomaly]
    I --> M[Reject]
    J --> N[PoC Promotion Gate]
    K --> N
    L --> O[Investigation Queue]
    N --> P[Shadow Test / Limited PoC]
    P --> Q[Action Receipt]
    Q --> R[ProtocolMemory]

Observation

A source-grounded record of something that happened, was proposed, failed, repeated, or remained unresolved.

Possible sources include public posts, GitHub issues, meeting notes, support logs, incident reports, operator notes, and manually entered examples.

An observation is not yet a recommendation.

Proxy

A normalized intermediate representation that separates reusable structure from the original wording.

Typical fields include:

task type;

friction;

affected actor;

expected effect;

evidence density;

external impact;

reversibility;

uncertainty;

generalizability;

source references.

The proxy acts like an ingot: raw material is refined before entering the crafting process.

Protocol Candidate

A proposed reusable procedure with explicit:

triggers;

required inputs;

preconditions;

ordered steps;

routing rules;

stop conditions;

human-review points;

failure handling;

expected outputs;

provenance.

A generated candidate is not automatically active.

Simulation

Each candidate is tested against multiple synthetic or replayed scenarios.

Scenarios may vary:

user behavior;

missing information;

organizational friction;

conflicting rules;

delayed effects;

adversarial inputs;

operator error;

irreversible consequences;

unusual edge cases.

The output is a structured simulation receipt, not a free-form opinion.

Selection

The foundry does not preserve only one overall winner.

Archive

Purpose

elite

Strong overall performance

rare

High behavioral distance from existing candidates

anomaly

Unusually strong or weak performance under specific conditions

reject

Unsafe, invalid, unsupported, or consistently ineffective

This prevents conventional candidates from crowding out unusual designs that may be valuable in narrow environments.

PoC Promotion

Simulation is not proof.

Candidates may progress through controlled stages:

Level 0: Schema and contradiction checks
Level 1: Synthetic scenario simulation
Level 2: Historical-log replay
Level 3: Shadow mode
Level 4: Limited and reversible PoC
Level 5: Monitored operation

Promotion decisions are recorded in poc_promotion documents.

Repository Structure

lopas-protocol-foundry/
├─ README.md
├─ LICENSE
├─ schemas/
│  ├─ observation.schema.yaml
│  ├─ proxy.schema.yaml
│  ├─ protocol_candidate.schema.yaml
│  ├─ simulation_receipt.schema.yaml
│  └─ poc_promotion.schema.yaml
│
├─ src/
│  ├─ ingest/
│  ├─ proxy/
│  ├─ protocol/
│  ├─ simulation/
│  ├─ selection/
│  └─ routing/
│
├─ prompts/
│  ├─ proxy_generation.md
│  ├─ protocol_generation.md
│  ├─ scenario_generation.md
│  └─ independent_grader.md
│
├─ examples/
│  ├─ meeting_automation/
│  ├─ customer_support/
│  └─ idea_observations/
│
├─ receipts/
│  └─ sample_run/
│
├─ tests/
└─ docs/
   ├─ architecture.md
   ├─ safety-model.md
   └─ poc-lifecycle.md

Minimal Example

Observation

id: obs-001

source:
  type: public_post
  source_id: example-001
  captured_at: 2026-07-26T00:00:00Z

summary: >
  A team reduced meeting preparation time by generating a draft agenda
  from the previous meeting's decisions.

evidence:
  density: low
  references:
    - source_id: example-001
      note: Single anecdotal report

signals:
  repeated: null
  interrupted: false
  avoided: false

Proxy

id: proxy-001

observation_refs:
  - obs-001

task:
  type: meeting_preparation

friction:
  - agenda_structure
  - decision_retrieval

proposed_effects:
  - preparation_time_reduction
  - record_consistency_improvement

assessment:
  evidence_density: low
  generalizability: medium
  external_impact: low
  reversibility: high
  interpretation_required: true

Protocol Candidate

id: protocol-meeting-prep-001
version: 0.1.0

trigger:
  event: calendar_event_upcoming
  conditions:
    - minutes_until_start <= 60
    - meeting_type != casual

inputs:
  required:
    - calendar_event
  optional:
    - previous_meeting_receipts
    - project_context

steps:
  - retrieve_previous_decisions
  - identify_unresolved_items
  - generate_draft_agenda
  - generate_note_template
  - request_human_review

routing:
  default: REVIEW
  escalate_when:
    - confidential_context_detected
    - conflicting_decisions_detected

outputs:
  - draft_agenda
  - note_template

provenance:
  observation_refs:
    - obs-001
  proxy_refs:
    - proxy-001

Selection Result

candidate_id: protocol-meeting-prep-001

archive: elite

scores:
  completion: 0.91
  safety: 0.95
  explainability: 0.88
  human_work_reduction: 0.72
  novelty: 0.34

promotion:
  eligible: true
  next_stage: historical_replay
  reason: >
    Strong performance with low external impact, high reversibility,
    and explicit human review before use.

Planned Local Workflow

The v0.1 command-line workflow is expected to follow this shape:

python -m src.ingest examples/idea_observations/input.jsonl
python -m src.proxy receipts/sample_run/observations.yaml
python -m src.protocol receipts/sample_run/proxies.yaml
python -m src.simulation receipts/sample_run/protocol_candidates.yaml
python -m src.selection receipts/sample_run/simulation_receipts.yaml
python -m src.routing receipts/sample_run/selection_results.yaml

The exact CLI may change during implementation. The schemas are intended to remain the stable boundaries between stages.

Design Principles

Evidence before interpretation

Source evidence and model interpretation must remain distinguishable.

Candidates before execution

Generated protocols begin as candidates. Activation requires explicit promotion.

Receipts everywhere

Every meaningful transformation should record:

input references;

rule, prompt, and model versions;

output identifiers;

validation results;

failures;

routing decisions;

timestamps;

promotion status.

Deterministic boundaries

LLMs may generate proposals, but schemas, validation, routing thresholds, and safety gates should be deterministic whenever possible.

Diversity, not only ranking

The system should retain unusual but coherent candidates instead of optimizing solely for average performance.

Reversible first

Early PoCs should prefer low-impact, observable, and reversible operations.

Unknown means hold

Missing evidence or unresolved contradictions should route to HOLD, REVIEW, or ESCALATE, not silent automation.

Safety Boundaries

A protocol should not be promoted when:

provenance is missing;

evidence and interpretation cannot be separated;

external impact is high and reversibility is low;

simulation coverage is inadequate;

the candidate depends on fabricated facts;

the route exceeds declared authority;

required human review is absent;

failures may remain silent or appear only after a delay.

The intended status flow is:

unconfirmed          → awaiting_confirmation
confirmed            → active
rejected             → rejected
denied               → denied
insufficient evidence → hold

See docs/safety-model.md for the planned full model.

What This Project Is Not

LoPAS Protocol Foundry is not:

proof that LLM simulations predict real-world success;

a fully autonomous business-process executor;

a social-media scraping product;

a replacement for domain experts;

a system for copying individual creators' work;

a way to bypass consent, policy, or accountability;

a universal optimizer that produces one correct workflow.

It is a protocol discovery, evaluation, and promotion layer.

Data and Provenance

Recommended practice:

store references instead of unnecessary raw content;

minimize personally identifiable information;

preserve source timestamps and identifiers;

distinguish quotation, summary, and inference;

record model, rule, and prompt versions;

maintain deletion and exclusion paths;

avoid promotion based on one weak observation.

Source adapters should output the common observation schema so downstream stages remain independent of the original platform.

Roadmap

v0.1 — Local Foundry

Core YAML schemas

JSONL/YAML local ingestion

Schema validation

Proxy generation

Protocol candidate generation

Synthetic scenario generation

Independent grading

Elite / rare / anomaly / reject archives

PoC promotion routing

End-to-end sample receipts

Test suite

v0.2 — Replay and Comparison

Historical-log replay

Candidate mutation

Behavioral-distance metrics

Protocol comparison

Divergence reports

Prompt and model version tracking

v0.3 — Adapters and Shadow Mode

GitHub Issues adapter

Generic input adapter

Meeting-log adapter

Support-log adapter

Shadow-mode execution interface

Human review console

Later Exploration

distributed observation sources;

Quality-Diversity search;

multi-model simulation;

domain-specific graders;

protocol registries;

ProtocolMemory feedback loops;

controlled Action Adapter integration.

Contributing

This repository is in an early experimental stage.

Useful contributions include:

schema review;

adversarial scenarios;

deterministic validators;

provenance tooling;

simulation graders;

behavioral-distance metrics;

small reproducible example domains;

safety and promotion-gate tests.

Please keep examples inspectable and do not commit sensitive or personally identifiable data.

License

The project license will be defined in LICENSE.

Until a license is added, no permission is granted to copy, modify, or distribute the repository contents.

One-Sentence Summary

LoPAS Protocol Foundry turns fragmented observations into traceable protocol candidates, tests them in simulation, preserves both strong and unusual designs, and promotes only qualified candidates toward reversible real-world PoCs.
