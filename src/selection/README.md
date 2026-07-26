# Selection Stage

The Selection stage aggregates schema-valid Simulation Receipts and preserves
performance, diversity, and unusual behavior as separate signals.

```bash
python -m src.selection \
  receipts/sample_run/simulation_receipts.yaml \
  --output receipts/sample_run/selection_results.yaml
```

## Archives

A candidate may belong to more than one positive archive:

- `elite`: strong aggregate performance with sufficient scenario coverage;
- `rare`: behavior is distant from its nearest candidate and novelty is high;
- `anomaly`: scenario-specific variation or unsupported behavior requires study;
- `reject`: unsafe or critically divergent behavior.

`reject` is exclusive and always takes precedence. A candidate can be both
`elite` and `rare`; this is intentional. The result therefore records:

```yaml
classification:
  primary_archive: elite
  archive_memberships:
    - elite
    - rare
```

Candidates that meet none of the archive conditions receive:

```yaml
primary_archive: none
archive_memberships: []
```

They remain available for later evidence collection but are not promoted by
Selection.

## v0.1 evaluation

The deterministic baseline calculates:

- acceptable, pass, revise, reject, and inconclusive rates;
- mean and dispersion for safety, completion, explainability,
  human-work reduction, novelty, and confidence;
- route distribution and route-mismatch rate;
- policy violations, factual errors, failures, and critical divergences;
- scenario-family coverage;
- behavioral distance to the nearest candidate.

The overall utility score never overrides explicit safety rejection rules.

## Mixed simulation runs

Receipts from different `run_id` values are rejected by default:

```bash
python -m src.selection simulation_receipts.yaml
```

Cross-run aggregation must be intentional:

```bash
python -m src.selection \
  simulation_receipts.yaml \
  --allow-mixed-runs
```

## Output contract

`selection_results.yaml` is currently a stage-local contract enforced by
Python. It is not one of the five original repository-level JSON Schemas.
The later Routing stage consumes this document and produces a
`poc_promotion` decision.

## Package registration

Because `pyproject.toml` lists packages explicitly, add:

```toml
  "src.selection",
```

under `[tool.setuptools].packages`.
