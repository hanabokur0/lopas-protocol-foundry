# Routing Stage

The Routing stage combines:

- validated Protocol Candidates;
- one Selection Result;
- optional real-world evidence;

and emits one schema-valid `poc_promotion` decision per candidate.

```bash
python -m src.routing \
  receipts/sample_run/protocol_candidates.yaml \
  receipts/sample_run/selection_results.yaml \
  --output receipts/sample_run/poc_promotions.yaml
```

## Conservative default

Selection performance is not enough for promotion.

The router rechecks:

- archive membership;
- observation count;
- verified source diversity;
- simulation count;
- acceptable simulation rate;
- critical divergences;
- authority scope;
- monitoring;
- rollback or containment;
- human approval.

The current Observation/Proxy/Protocol artifacts do not prove source
diversity, monitoring, rollback, or approval. Without an Evidence Manifest,
those gates remain `unknown` and the candidate routes to `HOLD`.

This is intentional.

## Evidence Manifest

Example:

```yaml
- protocol_candidate_ref: protocol-meeting-preparation-baseline
  source_diversity: 2
  monitoring_defined: true
  rollback_defined: true
  evidence_refs:
    - evidence-meeting-poc-001
  approval:
    approver_ref: protocol-owner-001
    status: approved
    decided_at: 2026-07-26T08:00:00Z
    note: Approved for historical replay only.
```

Run with:

```bash
python -m src.routing \
  protocol_candidates.yaml \
  selection_results.yaml \
  --evidence evidence_manifest.yaml
```

## Decisions

The router emits:

- `PROMOTE`: all blocking gates passed;
- `HOLD`: evidence or approval is incomplete;
- `REVISE`: Selection identified anomaly behavior;
- `REJECT`: candidate or Selection rejected the design;
- `DENY`: candidate intent was explicitly denied.

A `PROMOTE` decision advances only one validation level at a time.

```text
Level 0 → schema and contradiction checks
Level 1 → synthetic simulation
Level 2 → historical replay
Level 3 → shadow mode
Level 4 → limited reversible PoC
Level 5 → monitored operation
```

The CLI defaults to `Level 1 → Level 2`.

## Output validation

Every output is validated against:

```text
schemas/poc_promotion.schema.yaml
```

## Package registration

Because `pyproject.toml` lists packages explicitly, add:

```toml
  "src.routing",
```

under `[tool.setuptools].packages`.
