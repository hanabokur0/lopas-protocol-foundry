# Protocol Stage

The Protocol stage groups validated Proxy documents and creates unconfirmed
Protocol Candidates.

```bash
python -m src.protocol \
  receipts/sample_run/proxies.yaml \
  --output receipts/sample_run/protocol_candidates.yaml
```

The v0.1 baseline follows these rules:

- Proxies are grouped by `classification.cluster_id`, falling back to task type.
- One candidate is generated per cluster.
- Every candidate begins with `intent.status: unconfirmed`.
- The default route is never `AUTO`.
- Task-specific templates are available for meeting preparation and customer
  support.
- Unknown task types use an `observe_only` generic template and default to
  `HOLD`.
- External impact, reversibility, evidence quality, risk hints, and constraints
  determine routing and activation thresholds.
- A candidate may exist with sparse evidence, but it cannot satisfy its own
  activation requirements until enough observations, source diversity, and
  simulations exist.
- Generated output is validated against
  `schemas/protocol_candidate.schema.yaml`.

This stage produces design blueprints. It does not activate or execute them.
