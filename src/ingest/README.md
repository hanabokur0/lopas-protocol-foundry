# Ingest Stage

The ingest stage accepts structured Observation documents in:

- `.jsonl` / `.ndjson`
- `.json`
- `.yaml` / `.yml`

It validates each record against `schemas/observation.schema.yaml`.

```bash
python -m src.ingest \
  examples/idea_observations/input.jsonl \
  --output receipts/sample_run/observations.yaml
```

Outputs:

- validated observation list;
- a separate validation receipt;
- exit code `0` on success;
- exit code `2` when records fail schema validation;
- exit code `1` for parsing, schema-loading, or I/O failures.

Use `--allow-invalid` to retain valid records from a mixed batch. Invalid
records are never written into the validated output.
