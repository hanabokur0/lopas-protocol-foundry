# Proxy Stage

The Proxy stage converts validated Observation documents into normalized,
inspectable intermediate representations.

```bash
python -m src.proxy \
  receipts/sample_run/observations.yaml \
  --output receipts/sample_run/proxies.yaml
```

The v0.1 baseline is deliberately deterministic:

- one Proxy is generated per Observation;
- task-specific rules provide actors, friction, effects, and classification;
- evidence density, directness, repetition, contradictions, and exclusions
  produce an explicit confidence score;
- source restrictions become constraints;
- external impact and creative-ownership signals become risk hints;
- every interpretation is labeled as interpretation;
- generated output is validated against `schemas/proxy.schema.yaml`.

This baseline is not intended to be semantically complete. It provides a
stable reference output against which future LLM-assisted generators can be
tested.
