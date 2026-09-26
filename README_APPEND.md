## Community-health domain adapter example

`examples/community_health/` demonstrates how the Foundry can model a
camera/questionnaire/sensor-to-care-routing workflow while preserving the
current Shadow execution boundary.

The example is synthetic and non-clinical:

- observations are normalized without inventing missing values;
- risk classification is explicitly provisional and non-diagnostic;
- clinician review is mandatory;
- diagnosis, prescription, dispensing, external contact, and real-world routing
  are forbidden;
- the runtime resolves adapter bindings but does not invoke them.

See `examples/community_health/README.md`.

Conceptually:

```text
Observe -> Normalize -> Classify -> Gate -> Human Review
-> Route Proposal -> Verify -> Receipt
```

This is intended as a domain-adapter pattern for future health, agriculture,
education, and public-service integrations — not as evidence that any such
integration is ready for production.
