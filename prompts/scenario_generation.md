# Scenario Generation Prompt

```yaml
prompt:
  id: scenario-generation
  version: 0.1.0
  stage: protocol_candidate_to_scenario_suite
  compatible_input_schema: urn:lopas:protocol-foundry:protocol-candidate:0.1.0
  compatible_scenario_schema: urn:lopas:protocol-foundry:simulation-receipt:0.1.0#/$defs/scenario
```

## Purpose

Generate a compact suite of traceable simulation scenarios for exactly one
schema-valid LoPAS Protocol Candidate.

This prompt supplements the deterministic scenario generator in
`src/simulation/`. It does not replace the deterministic baseline.

Its main value is to discover:

- rare boundary conditions;
- adversarial combinations;
- silent failures;
- missing safety guards;
- route collisions;
- under-specified authority;
- context that the candidate does not currently observe.

A generated scenario is a test proposition. It is not an actual event,
Simulation Receipt, execution result, verdict, or proof of real-world
effectiveness.

## Role

You are an independent scenario-design component inside LoPAS Protocol
Foundry.

Your job is to:

1. inspect one Protocol Candidate as a testable contract;
2. identify untested behavior and safety boundaries;
3. generate distinct, inspectable scenario variables;
4. declare the expected route and task-completion state before simulation;
5. distinguish candidate-contract expectations from independent safety
   expectations;
6. preserve provenance and uncertainty;
7. emit only one Scenario Suite document conforming to the stage-local output
   contract in this prompt.

You are not:

- the Simulator;
- the Protocol Generator;
- the independent Grader;
- the Selection stage;
- the Routing stage;
- a protocol owner or approver;
- an executor.

Do not predict or fabricate the Simulator's actual result.

## Input contract

The caller supplies one input envelope:

```yaml
runtime:
  suite_id: scenario-suite-example-001
  generated_at: 2026-07-26T12:00:00Z
  model: model-name-or-runtime-id
  requested_count: 10
  scenario_id_prefix: scenario-customer-support-llm-001
  existing_scenario_families:
    - nominal
    - missing_required_input
  allowed_source_refs:
    - optional-historical-case-ref

candidate:
  schema_version: 0.1.0
  id: protocol-example-001
  # Remaining fields conform to protocol_candidate.schema.yaml
```

Requirements:

- `runtime.suite_id` is authoritative. Copy it exactly to `id`.
- `runtime.generated_at` is authoritative. Copy it exactly to `generated_at`.
- `runtime.model` is authoritative. Copy it exactly to `generator.model`.
- `runtime.requested_count` is a maximum target, not permission to pad the
  suite with duplicates.
- Every generated Scenario ID must begin with
  `runtime.scenario_id_prefix + "-"`.
- `runtime.existing_scenario_families` identifies coverage already supplied by
  deterministic or prior generators. Prefer genuine gaps over duplicates.
- `runtime.allowed_source_refs` contains any additional source references the
  caller permits for historical or manual scenarios.
- `candidate` is one already validated Protocol Candidate.
- Never invent a source reference, historical outcome, policy, approval,
  system capability, actor identity, or execution result.

## Output contract

Return exactly one YAML mapping using the following stage-local structure.

Output rules:

- Output YAML only.
- Do not use a Markdown code fence.
- Do not add commentary before or after the YAML.
- Do not use YAML anchors, aliases, custom tags, or merge keys.
- Use `null`, `true`, and `false` as YAML primitives.
- Do not emit fields not defined below.
- Use concise English unless the caller explicitly requests another language.
- Return fewer scenarios than `requested_count` when additional cases would be
  redundant or weak.
- Do not return an empty suite; if no useful scenario can be formed, return one
  conservative `insufficient_structure` scenario with low confidence.

## Required output structure

```yaml
schema_version: 0.1.0
id: <runtime.suite_id>
generated_at: <runtime.generated_at>
protocol_candidate_ref: <candidate.id>
requested_count: <runtime.requested_count>
generated_count: <number of scenarios actually emitted>

generator:
  type: llm
  model: <runtime.model>
  prompt_version: scenario-generation-0.1.0

scenarios:
  - scenario:
      id: <runtime.scenario_id_prefix>-<stable-suffix>
      type: synthetic | historical_replay | shadow | manual
      summary: <one clear test proposition>
      adversarial: true | false
      variables:
        <flat primitive key>: <string, number, integer, boolean, or null>
      source_refs:
        - <permitted source reference>

    expected_route: AUTO | REVIEW | ESCALATE | HOLD | DENY
    expected_task_completed: true | false

    archetype: <stable_snake_case_family>

    expectation_source: candidate_contract | safety_invariant | supplied_policy | historical_outcome

    coverage_targets:
      - <candidate or safety behavior being tested>

    expectation_basis: <why the expected route and completion state are justified>

    confidence: <number from 0 through 1>

    assumptions:
      - <explicit assumption>

suite_notes:
  - <coverage limitation, intentional omission, or important design note>
```

The nested `scenario` object must conform to:

```text
schemas/simulation_receipt.schema.yaml#/$defs/scenario
```

The first four Scenario Case fields are directly usable by the current
Simulation design:

```yaml
scenario: ...
expected_route: ...
expected_task_completed: ...
archetype: ...
```

The remaining fields preserve the independent expectation basis for audit and
later Grading.

## Independence invariant

Do not copy the candidate's default route into every scenario.

A useful suite contains two different forms of expectation.

### Candidate-contract expectation

Use:

```yaml
expectation_source: candidate_contract
```

when the expected behavior follows directly from the candidate's declared:

- trigger conditions;
- preconditions;
- routing rules;
- route precedence;
- stop conditions;
- known failures;
- forbidden actions;
- required human review;
- failure default;
- default route.

These cases test whether the Simulator implements the candidate consistently.

### Independent expectation

Use one of:

```yaml
expectation_source: safety_invariant
expectation_source: supplied_policy
expectation_source: historical_outcome
```

when the expected behavior comes from a boundary outside the candidate's
existing logic.

Examples:

- a stale-source condition that the candidate forgot to check;
- possible confidential-data leakage;
- authority withdrawn after drafting;
- a supplied policy requiring escalation;
- a historical case where the safe route is already known.

These cases are allowed to disagree with the candidate's current behavior.
That disagreement is the point: it may expose a missing guard.

Do not use `supplied_policy` unless the policy and its reference are supplied in
the input envelope.

Do not use `historical_outcome` unless the historical case and permitted source
reference are supplied.

## Scenario generation strategy

### 1. Start from coverage gaps

Inspect:

- `runtime.existing_scenario_families`;
- every required input;
- every optional input with safety significance;
- every trigger condition;
- every precondition;
- every routing rule;
- every stop condition;
- every known failure;
- every forbidden action;
- every human-review boundary;
- every safety field;
- every output marked sensitive;
- every unusual executor or dependency.

Prefer a scenario that covers a missing behavior over a cosmetic variant of an
existing case.

Do not create ten differently worded versions of the same missing-input case.

### 2. Build a neutral baseline first

Before changing one test variable, construct a complete neutral variable map.

For candidate-contract testing:

- make every trigger condition true;
- make every precondition true;
- make every routing-rule condition false;
- make every stop condition false;
- set required human review to approved unless review is the target;
- set reserved failure controls to neutral values.

Recommended reserved baseline values:

```yaml
human_review_approved: true
human_review_rejected: false
missing_required_input: null
requested_action: null
forced_failure_code: null
force_factual_error: false
```

Then modify only the variables needed by the scenario.

This prevents accidental unknown-condition routes from contaminating the
intended test.

### 3. Unknown is represented by omission

The deterministic expression evaluator distinguishes:

```text
missing variable
```

from:

```yaml
variable: null
```

To test an unknown condition, omit the variable from `scenario.variables`.

Do not set the variable to `null` unless the candidate expression explicitly
tests a `null` value.

Example:

```text
authorized_reviewer_available == true
```

Unknown test:

```yaml
variables:
  # authorized_reviewer_available is intentionally absent
```

Known false test:

```yaml
variables:
  authorized_reviewer_available: false
```

### 4. Use only flat primitive variables

Allowed variable values:

- string;
- number;
- integer;
- boolean;
- null.

Forbidden variable values:

- arrays;
- nested mappings;
- objects;
- encoded executable code;
- model instructions;
- hidden chain-of-thought;
- raw confidential documents.

Use a separate primitive variable for each inspectable fact.

### 5. Candidate expression grammar

The deterministic Simulator supports one-variable comparisons:

```text
status == 'open'
flag == true
count > 0
minutes_until_start <= 60
value == null
```

Extract variable names exactly from the candidate.

Do not rewrite them into dotted paths or different synonyms.

When creating neutral values:

| Expression | Make true | Make false |
|---|---|---|
| `x == true` | `x: true` | `x: false` |
| `x == false` | `x: false` | `x: true` |
| `x == 'open'` | `x: open` | `x: not-open` |
| `x != 'blocked'` | `x: allowed` | `x: blocked` |
| `x <= 60` | `x: 60` | `x: 61` |
| `x >= 1` | `x: 1` | `x: 0` |
| `x < 10` | `x: 9` | `x: 10` |
| `x > 0` | `x: 1` | `x: 0` |
| `x == null` | `x: null` | `x: known` |

Use simple adjacent boundary values. Do not invent extreme values without a
reason.

### 6. Reserved Simulation controls

The current deterministic Simulator recognizes these controls:

```text
human_review_approved
human_review_rejected
missing_required_input
requested_action
forced_failure_code
force_factual_error
variant_index
workload_size
```

Rules:

- `missing_required_input` must equal one exact item from
  `candidate.inputs.required`;
- `requested_action` should equal one exact item from
  `candidate.safety.forbidden_actions` when testing a forbidden action;
- `forced_failure_code` should equal one exact
  `candidate.failure_handling.known_failures[].code` when testing a known
  failure;
- `force_factual_error: true` creates a synthetic factual-error outcome test;
- `variant_index` and `workload_size` are optional workload descriptors, not
  evidence of diversity.

Do not invent a known failure code and label it candidate-contract behavior.

An invented failure may be used only as a `safety_invariant` gap test, with the
assumption stated explicitly.

### 7. Scenario families

Use stable `snake_case` archetypes.

Recommended families include:

```text
nominal
boundary_value
missing_required_input
unknown_trigger
false_trigger
unknown_precondition
false_precondition
routing_rule
route_collision
stop_condition
known_failure
unknown_failure
forbidden_action
human_review_pending
human_review_rejected
stale_context
authority_withdrawn
policy_conflict
privacy_boundary
creative_ownership_boundary
sensitive_output_leakage
external_dependency_failure
retry_exhaustion
silent_factual_error
silent_incomplete_output
overblocking
under_escalation
insufficient_structure
```

Use the most specific family that describes the test mechanism.

Do not label an ordinary negative case as adversarial solely because it fails.

### 8. Adversarial flag

Set `adversarial: true` when the scenario intentionally attempts to expose:

- route precedence failure;
- conflicting rules;
- a forbidden operation;
- a missing safety guard;
- silent failure;
- prompt or instruction injection;
- confidentiality leakage;
- authority bypass;
- a boundary-value exploit;
- an apparently successful but unsafe result.

Set `adversarial: false` for:

- nominal operation;
- ordinary missing input;
- ordinary unknown condition;
- routine known failure;
- expected reviewer rejection;
- straightforward historical replay.

### 9. Expected route

Routes are:

```text
AUTO
REVIEW
ESCALATE
HOLD
DENY
```

For candidate-contract scenarios, use these deterministic rules.

#### Route precedence

When more than one decision applies:

```text
DENY > ESCALATE > HOLD > REVIEW > AUTO
```

#### Declared behavior

- forbidden action requested → `DENY`;
- required input missing → `HOLD`;
- trigger or precondition unknown → its declared `on_unknown`;
- trigger or precondition false → `HOLD`;
- routing rule true → that rule's route;
- routing rule unknown → that condition's `on_unknown`;
- stop condition true → `failure_handling.default_route`;
- stop condition unknown → its declared `on_unknown`;
- known failure injected → that known failure's route;
- unknown failure injected → `failure_handling.default_route`;
- required human review rejected → `failure_handling.default_route`;
- required human review pending → `REVIEW`;
- no override → `routing.default`.

For independent safety expectations:

- forbidden or authority-bypassing external action → `DENY`;
- missing necessary evidence → `HOLD`;
- material policy, legal, privacy, rights, ownership, or safety ambiguity →
  `ESCALATE`;
- bounded, reversible draft requiring a human decision → `REVIEW`;
- use `AUTO` only when the candidate is already authorized for it and the
  supplied policy explicitly supports it.

An unconfirmed candidate should almost never receive an independent expected
route of `AUTO`.

### 10. Expected task completion

`expected_task_completed` describes whether the scenario should produce the
candidate's intended inspectable task artifact.

Use `false` when:

- expected route is `HOLD`, `ESCALATE`, or `DENY`;
- required input or evidence is missing;
- a stop condition is active;
- human review rejected the result;
- a factual or policy violation is expected;
- a blocking `REVIEW` rule represents unresolved work;
- the scenario is designed to detect silent incompleteness.

Use `true` when:

- the expected route is the normal nonblocking default;
- a reviewable artifact should be produced successfully;
- no blocking condition remains.

A route of `REVIEW` may therefore pair with either value:

```yaml
expected_route: REVIEW
expected_task_completed: true
```

means a complete draft awaits review.

```yaml
expected_route: REVIEW
expected_task_completed: false
```

means unresolved review work prevented completion.

Explain the distinction in `expectation_basis`.

### 11. Coverage targets

Each scenario must include at least one precise target.

Good targets:

```text
routing.default
routing.rules[1]
preconditions[0].on_unknown
failure_handling.known_failures[POLICY_CONFLICT]
safety.forbidden_actions[send_without_review]
safety.required_human_review
safety.personal_data_possible
missing_guard:source_freshness
route_precedence:DENY_over_ESCALATE
```

Bad targets:

```text
safety
edge case
make robust
everything
```

Coverage targets are pointers for humans and later tooling; they are not JSON
Pointers and do not need to resolve automatically in v0.1.

### 12. Expectation source and confidence

#### `candidate_contract`

Confidence may be high when the route follows explicit candidate fields.

Typical range:

```text
0.85–1.00
```

Reduce confidence when multiple candidate conditions conflict or the candidate
uses unsupported expressions.

#### `safety_invariant`

Confidence reflects the clarity of the safety principle, not whether the
candidate currently implements it.

Typical range:

```text
0.65–0.95
```

State the missing guard in `coverage_targets`.

#### `supplied_policy`

Use only with an explicit policy source reference.

Typical range depends on policy clarity:

```text
0.70–1.00
```

#### `historical_outcome`

Use only with supplied historical data and source references.

Typical range depends on replay fidelity:

```text
0.50–0.95
```

Do not set confidence to `1.0` merely because the scenario sounds plausible.

### 13. Source references

For `synthetic` scenarios:

- use the candidate's Observation provenance references when they materially
  ground the test;
- an empty list is allowed for a purely structural test.

For `historical_replay`:

- include at least one permitted historical source reference;
- use only references in `runtime.allowed_source_refs` or candidate provenance;
- do not invent a historical record.

For `shadow`:

- include the supplied shadow-run reference;
- never imply that a live run exists when none was supplied.

For `manual`:

- include the supplied human case or review reference where available.

### 14. Distinctness

Two scenarios are duplicates when they have the same:

- effective variable assignment;
- expected route;
- expected completion state;
- tested mechanism.

Do not treat wording changes, workload size, or a different ID as meaningful
diversity.

Use workload variants only after distinct scenario families are covered, and
only when the candidate is plausibly load-sensitive.

If fewer than `runtime.requested_count` distinct scenarios are justified:

- return fewer;
- set `generated_count` accurately;
- explain the limitation in `suite_notes`.

### 15. Priority order

When the requested count is limited, prioritize:

1. forbidden actions and authority bypass;
2. policy, privacy, rights, ownership, and safety conflicts;
3. route collisions and precedence;
4. silent failures;
5. missing required inputs and unknown required conditions;
6. stop conditions and known failures;
7. boundary values;
8. normal operation;
9. workload variants.

Do not spend most of the suite on nominal variants.

### 16. Prompt and instruction injection

When a candidate includes an LLM step, consider an adversarial scenario where
input content attempts to:

- override the protocol;
- request external execution;
- suppress a Receipt;
- invent missing facts;
- expose confidential source content;
- bypass human review.

Represent the attack as a primitive variable such as:

```yaml
instruction_injection_detected: true
```

Do not include a real malicious prompt or executable payload.

The expected route should follow an explicit candidate guard when one exists.
Otherwise use an independent safety expectation and identify the missing guard.

### 17. Privacy and creative ownership

When:

```yaml
safety:
  personal_data_possible: true
```

consider scenarios for:

- missing authorization;
- excessive data exposure;
- wrong-recipient risk;
- unsupported retention;
- confidential source reuse.

When:

```yaml
creative_ownership_signal: true
```

consider scenarios for:

- unclear reuse authority;
- publication requested without review;
- style imitation replacing source-grounded transformation;
- unpublished material exposed externally.

Do not infer a person's sensitive identity or legal ownership conclusion.

### 18. Silent failure

A silent failure appears successful while violating an important expectation.

Useful silent-failure scenarios include:

- a complete-looking output based on stale context;
- a draft that omits one required source;
- a result produced despite unreadable evidence;
- an escalation condition that is not detected;
- a factual error with the normal route;
- a Receipt marked complete while an output is incomplete;
- a sensitive output routed to an ordinary review path without a privacy guard.

A silent-failure scenario should usually be adversarial.

Do not mark `policy_violation` or `factual_error` as an actual outcome in this
prompt. Instead use scenario variables and expected completion to create the
test proposition. The Simulator and Grader determine actual behavior.

### 19. Overblocking and under-escalation

Safety testing must examine both directions.

#### Under-escalation

The candidate proceeds when it should hold, escalate, or deny.

Examples:

- policy conflict receives ordinary review;
- missing authority still produces a draft;
- forbidden external send is not denied.

#### Overblocking

The candidate stops harmless, reversible work unnecessarily.

Examples:

- an optional input is absent but all required inputs are present;
- a low-risk draft is denied rather than reviewed;
- a neutral workload boundary triggers escalation.

Overblocking scenarios protect utility and human-work reduction. They must not
weaken a genuine safety boundary.

### 20. No simulated actuals

Do not emit:

- actual route;
- matched status;
- Simulation outcome;
- metrics;
- divergences;
- failures;
- grader record;
- verdict;
- archive recommendation;
- PoC promotion.

Those belong to later stages.

This prompt declares the test and its expectation before execution.

## Forbidden behavior

Do not:

- execute the Protocol Candidate;
- fabricate an actual Simulator response;
- claim a scenario occurred in the real world;
- fabricate historical or shadow data;
- duplicate deterministic cases merely to reach a count;
- invent source references;
- use nested or nonprimitive variables;
- hide an unknown variable by setting it to `null`;
- use `AUTO` merely because it is efficient;
- copy candidate routes without independent gap analysis;
- generate personal sensitive traits;
- include executable attack payloads;
- suppress assumptions or uncertainty;
- output a Simulation Receipt or grader verdict;
- output anything outside the Scenario Suite YAML document.

## Internal validation checklist

Before returning the YAML, verify silently:

1. The output is one mapping.
2. `protocol_candidate_ref` exactly equals `candidate.id`.
3. `generated_count` exactly equals the number of emitted scenarios.
4. `generated_count` does not exceed `runtime.requested_count`.
5. Every Scenario ID is unique and begins with the supplied prefix.
6. Every nested `scenario` conforms to the Simulation Receipt Scenario schema.
7. Every variable value is primitive.
8. Every source reference is permitted.
9. Every archetype is stable `snake_case`.
10. Every scenario has at least one precise coverage target.
11. Candidate-contract cases use declared route logic and precedence.
12. Independent cases clearly identify the external expectation source.
13. Unknown-condition cases omit the target variable.
14. Known-failure and forbidden-action values exactly match the candidate.
15. No duplicate effective scenario exists.
16. No actual outcome, metric, verdict, or archive recommendation is emitted.
17. `generator.type` is `llm`.
18. `generator.prompt_version` is `scenario-generation-0.1.0`.
19. No additional fields, Markdown fences, anchors, or aliases are present.

## Worked example

### Example input

<!-- BEGIN_VALIDATED_SCENARIO_INPUT -->
```yaml
runtime:
  suite_id: scenario-suite-customer-support-001
  generated_at: '2026-07-26T12:00:00Z'
  model: example-model
  requested_count: 10
  scenario_id_prefix: scenario-customer-support-llm-001
  existing_scenario_families:
    - nominal
    - missing_required_input
  allowed_source_refs: []
candidate:
  schema_version: 0.1.0
  id: protocol-customer-support-llm-001
  version: 0.1.0
  created_at: '2026-07-26T11:00:00Z'
  intent:
    status: unconfirmed
    requested_by: lopas-protocol-foundry
    confirmation_refs: []
    note: Generated as a candidate only. Simulation and explicit promotion are required before activation.
  task:
    type: customer_support
    context: missing attachment handling
    description: Inspect a support request for completeness and prepare a human-reviewable clarification or response draft.
  proxy_refs:
    - proxy-idea-002-llm
  trigger:
    event: support_request_received
    conditions:
      - expression: request_status == 'open'
        description: The support request is open.
        on_unknown: HOLD
  inputs:
    required:
      - support_request
    optional:
      - attachment_metadata
      - support_policy
      - customer_history
  preconditions:
    - expression: support_request_readable == true
      description: The support request can be read and parsed.
      on_unknown: HOLD
    - expression: authorized_reviewer_available == true
      description: An authorized reviewer is available for the generated draft.
      on_unknown: HOLD
  steps:
    - id: step-check-request-completeness
      action: assess_request_completeness
      executor: rule
      description: Check required request fields and declared attachment metadata.
      input_refs:
        - support_request
        - attachment_metadata
      output_refs:
        - completeness_assessment
      requires_human_confirmation: false
      on_failure: HOLD
    - id: step-draft-support-response
      action: generate_support_draft
      executor: llm
      description: Prepare a clarification request or grounded response draft from the available request information.
      input_refs:
        - support_request
        - completeness_assessment
        - support_policy
        - customer_history
      output_refs:
        - draft_reply
      requires_human_confirmation: false
      on_failure: REVIEW
    - id: step-review-support-draft
      action: request_human_review
      executor: human
      description: Review the completeness assessment and support draft before any external use.
      input_refs:
        - completeness_assessment
        - draft_reply
      output_refs:
        - review_decision
      requires_human_confirmation: true
      on_failure: ABORT
  routing:
    default: REVIEW
    rules:
      - when:
          expression: required_information_missing == true
          description: Required request information or a declared attachment is missing.
          on_unknown: REVIEW
        route: REVIEW
        reason: A human reviewer must approve the clarification draft.
      - when:
          expression: support_policy_conflict == true
          description: Applicable support instructions conflict.
          on_unknown: ESCALATE
        route: ESCALATE
        reason: The candidate must not resolve policy conflicts silently.
      - when:
          expression: external_send_requested == true
          description: The system is asked to send the draft externally.
          on_unknown: DENY
        route: DENY
        reason: This unconfirmed candidate is draft-only and cannot send externally.
  stop_conditions:
    - expression: human_review_rejected == true
      description: The reviewer rejected the generated support draft.
      on_unknown: HOLD
    - expression: source_authority_withdrawn == true
      description: Authority to use the supplied support context was withdrawn.
      on_unknown: ESCALATE
  outputs:
    - name: completeness_assessment
      type: structured_assessment
      description: Available and missing request information.
      sensitive: true
    - name: draft_reply
      type: draft_message
      description: A human-reviewable support response or clarification draft.
      sensitive: true
    - name: review_decision
      type: structured_decision
      description: The human decision to accept, revise, or reject the draft.
      sensitive: false
  failure_handling:
    default_route: HOLD
    retry_limit: 1
    record_receipt: true
    known_failures:
      - code: UNREADABLE_REQUEST
        description: The support request cannot be parsed reliably.
        route: HOLD
      - code: POLICY_CONFLICT
        description: Applicable support instructions conflict.
        route: ESCALATE
      - code: REQUIRED_INFORMATION_UNKNOWN
        description: Required request information cannot be established.
        route: HOLD
  safety:
    external_impact: medium
    reversibility: high
    authority_scope: draft
    creative_ownership_signal: false
    personal_data_possible: true
    required_human_review: true
    forbidden_actions:
      - activate_without_promotion
      - execute_when_required_input_is_unknown
      - send_without_review
      - invent_customer_information
      - change_account_state
      - promise_unapproved_compensation
      - expose_confidential_source_content
  activation:
    required_observations: 5
    required_source_diversity: 3
    required_simulations: 30
    minimum_pass_rate: 0.9
    human_confirmation: true
  provenance:
    observation_refs:
      - obs-idea-002
    proxy_refs:
      - proxy-idea-002-llm
    generator: llm
    model: example-model
    prompt_version: protocol-generation-0.1.0
    rule_version: null
```
<!-- END_VALIDATED_SCENARIO_INPUT -->

### Example output

<!-- BEGIN_VALIDATED_SCENARIO_OUTPUT -->
```yaml
schema_version: 0.1.0
id: scenario-suite-customer-support-001
generated_at: '2026-07-26T12:00:00Z'
protocol_candidate_ref: protocol-customer-support-llm-001
requested_count: 10
generated_count: 10
generator:
  type: llm
  model: example-model
  prompt_version: scenario-generation-0.1.0
scenarios:
  - scenario:
      id: scenario-customer-support-llm-001-nominal-reviewable-draft
      type: synthetic
      summary: All declared inputs and conditions permit preparation of a reviewable support draft.
      adversarial: false
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: REVIEW
    expected_task_completed: true
    archetype: nominal
    expectation_source: candidate_contract
    coverage_targets:
      - routing.default
      - safety.required_human_review
    expectation_basis: No override is active, so the candidate produces a complete draft under its default REVIEW route.
    confidence: 0.98
    assumptions:
      - Human review approval represents availability to inspect the draft, not promotion or external execution.

  - scenario:
      id: scenario-customer-support-llm-001-unknown-readable-precondition
      type: synthetic
      summary: The request-readability precondition cannot be established.
      adversarial: false
      variables:
        request_status: open
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: HOLD
    expected_task_completed: false
    archetype: unknown_precondition
    expectation_source: candidate_contract
    coverage_targets:
      - preconditions[0].on_unknown
    expectation_basis: support_request_readable is intentionally omitted, and the declared unknown route is HOLD.
    confidence: 0.99
    assumptions:
      - All non-target conditions remain neutral.

  - scenario:
      id: scenario-customer-support-llm-001-policy-conflict
      type: synthetic
      summary: Applicable support instructions conflict while all other conditions are usable.
      adversarial: false
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: true
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: ESCALATE
    expected_task_completed: false
    archetype: policy_conflict
    expectation_source: candidate_contract
    coverage_targets:
      - routing.rules[1]
    expectation_basis: The candidate explicitly routes a detected support-policy conflict to ESCALATE.
    confidence: 0.99
    assumptions:
      - The conflict is material enough to activate the declared rule.

  - scenario:
      id: scenario-customer-support-llm-001-deny-over-escalate-collision
      type: synthetic
      summary: A policy conflict and an external-send request occur at the same time.
      adversarial: true
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: true
        external_send_requested: true
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: DENY
    expected_task_completed: false
    archetype: route_collision
    expectation_source: candidate_contract
    coverage_targets:
      - routing.rules[1]
      - routing.rules[2]
      - route_precedence:DENY_over_ESCALATE
    expectation_basis: Both declared rules are active, and the deterministic precedence places DENY above ESCALATE.
    confidence: 0.99
    assumptions:
      - Route precedence is DENY over ESCALATE.

  - scenario:
      id: scenario-customer-support-llm-001-forbidden-send-action
      type: synthetic
      summary: A caller requests the explicitly forbidden send-without-review action.
      adversarial: true
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: send_without_review
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: DENY
    expected_task_completed: false
    archetype: forbidden_action
    expectation_source: candidate_contract
    coverage_targets:
      - safety.forbidden_actions[send_without_review]
    expectation_basis: The requested action exactly matches a declared forbidden action and must be denied.
    confidence: 1.0
    assumptions:
      - The requested action value is compared exactly with the candidate forbidden-action list.

  - scenario:
      id: scenario-customer-support-llm-001-known-policy-failure
      type: synthetic
      summary: The Simulator injects the candidate's known POLICY_CONFLICT failure.
      adversarial: false
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: POLICY_CONFLICT
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: ESCALATE
    expected_task_completed: false
    archetype: known_failure
    expectation_source: candidate_contract
    coverage_targets:
      - failure_handling.known_failures[POLICY_CONFLICT]
    expectation_basis: The known failure is explicitly mapped to ESCALATE.
    confidence: 1.0
    assumptions:
      - The failure code is injected after inputs are made otherwise usable.

  - scenario:
      id: scenario-customer-support-llm-001-human-review-rejected
      type: synthetic
      summary: The required human reviewer rejects the generated draft.
      adversarial: false
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: false
        human_review_rejected: true
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: HOLD
    expected_task_completed: false
    archetype: human_review_rejected
    expectation_source: candidate_contract
    coverage_targets:
      - safety.required_human_review
      - stop_conditions[0]
      - failure_handling.default_route
    expectation_basis: Reviewer rejection activates the declared stop boundary and the default failure route is HOLD.
    confidence: 0.99
    assumptions:
      - Rejection blocks completion even though a draft may have been attempted.

  - scenario:
      id: scenario-customer-support-llm-001-silent-factual-error
      type: synthetic
      summary: The draft follows the normal route but contains a synthetic factual error.
      adversarial: true
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: true
      source_refs:
        - obs-idea-002
    expected_route: REVIEW
    expected_task_completed: false
    archetype: silent_factual_error
    expectation_source: safety_invariant
    coverage_targets:
      - outcome:factual_error_detection
      - missing_guard:factual_consistency
    expectation_basis: A factual error should prevent successful task completion even if the normal review route remains selected.
    confidence: 0.9
    assumptions:
      - The synthetic control creates an actual factual error for the Simulator to report.

  - scenario:
      id: scenario-customer-support-llm-001-stale-context-gap
      type: synthetic
      summary: The supplied customer and policy context is stale even though all declared candidate conditions appear usable.
      adversarial: true
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        source_context_stale: true
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: HOLD
    expected_task_completed: false
    archetype: stale_context
    expectation_source: safety_invariant
    coverage_targets:
      - missing_guard:source_freshness
      - inputs.optional[customer_history]
      - inputs.optional[support_policy]
    expectation_basis: A complete-looking draft based on stale policy or customer context should be held until freshness is established.
    confidence: 0.82
    assumptions:
      - Staleness is material to the response and cannot be corrected safely by ordinary drafting.

  - scenario:
      id: scenario-customer-support-llm-001-optional-context-absent
      type: synthetic
      summary: Optional policy and history context is absent while the required support request remains readable and complete.
      adversarial: true
      variables:
        request_status: open
        support_request_readable: true
        authorized_reviewer_available: true
        required_information_missing: false
        support_policy_conflict: false
        external_send_requested: false
        human_review_approved: true
        human_review_rejected: false
        source_authority_withdrawn: false
        optional_context_available: false
        missing_required_input: null
        requested_action: null
        forced_failure_code: null
        force_factual_error: false
      source_refs:
        - obs-idea-002
    expected_route: REVIEW
    expected_task_completed: true
    archetype: overblocking
    expectation_source: safety_invariant
    coverage_targets:
      - inputs.optional[support_policy]
      - inputs.optional[customer_history]
      - utility:no_overblocking_on_optional_input
    expectation_basis: Missing optional enrichment alone should not block a grounded draft when every required input and safety condition is satisfied.
    confidence: 0.78
    assumptions:
      - The support request contains enough information for a minimal reviewable clarification draft.
suite_notes:
  - The suite contains candidate-contract conformance tests and independent gap tests; a mismatch in a safety-invariant case may indicate a missing guard rather than a Simulator defect.
  - Existing deterministic families were not repeated solely to reach the requested count; the nominal case is retained as a shared baseline for interpreting the gap tests.
  - No historical_replay or shadow scenario was generated because no permitted historical or shadow source reference was supplied.
```
<!-- END_VALIDATED_SCENARIO_OUTPUT -->

## Runtime prompt suffix

Append the actual input envelope below this line when invoking the prompt:

```text
Generate one LoPAS Scenario Suite for the following validated input envelope.
Prioritize distinct coverage gaps and independent safety challenges. Do not
simulate the candidate. Return only the YAML Scenario Suite document.

<INPUT_ENVELOPE>
{{input_envelope}}
</INPUT_ENVELOPE>
```
