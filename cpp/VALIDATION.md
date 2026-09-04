# Local validation

Validated in the build environment with GCC 14.2.0 and CMake 3.31.6.

Commands:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Result:

```text
100% tests passed, 0 tests failed out of 1
```

Conservative default run:

```bash
./build/lopas_foundry examples/observations.json \
  --output-dir receipts/default \
  --scenario-count 20
```

Observed promotion: `HOLD` because intent was unconfirmed and no evidence manifest was supplied.

Evidence-qualified Level 2 -> 3 run:

```bash
./build/lopas_foundry examples/observations.json \
  --output-dir receipts/shadow \
  --scenario-count 20 \
  --confirm-intent \
  --evidence examples/evidence.json \
  --current-level 2 \
  --next-level 3 \
  --shadow-bindings examples/adapter_bindings.json
```

Observed promotion: `PROMOTE`.

Observed Shadow receipt:

```text
status: shadowed
external_effects: []
```

The exact generated JSON evidence is retained under `validation/`.
