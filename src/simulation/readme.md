# Simulation Stage

The Simulation stage creates synthetic scenarios from validated Protocol
Candidates, evaluates the declared routing behavior without executing external
tools, and emits one schema-valid Simulation Receipt per scenario.

```bash
python -m src.simulation \
  receipts/sample_run/protocol_candidates.yaml \
  --output receipts/sample_run/simulation_receipts.yaml
```

By default, each candidate is simulated as many times as declared in:

```yaml
activation:
  required_simulations: 20
```

For a smaller local check:

```bash
python -m src.simulation \
  receipts/sample_run/protocol_candidates.yaml \
  --scenario-count 8
```

## v0.1 behavior

The deterministic baseline:

- validates Protocol Candidate input;
- generates nominal, missing-input, unknown-condition, false-condition,
  human-review, routing-rule, stop-condition, known-failure,
  forbidden-action, and conflicting-route scenarios where applicable;
- supports explicit one-variable comparisons such as
  `status == 'open'`, `flag == true`, and `count > 0`;
- routes unsupported expressions to `HOLD` and records them as failures;
- applies route precedence of `DENY > ESCALATE > HOLD > REVIEW > AUTO`;
- never calls an LLM or external system;
- grades expected and actual routes through a separate deterministic grader;
- validates every output against `schemas/simulation_receipt.schema.yaml`.

Repeated workload variants may be used to reach the declared simulation count.
Raw count is not proof of scenario diversity or real-world effectiveness.
Those judgments belong to later Selection and PoC Promotion stages.

## Package registration

Because `pyproject.toml` currently lists packages explicitly, add:

```toml
  "src.simulation",
```

under `[tool.setuptools].packages`.
