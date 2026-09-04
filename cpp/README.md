# LoPAS Protocol Foundry — C++20 Reference Port v0.1

A buildable C++20 reference implementation of the public `hanabokur0/lopas-protocol-foundry` pipeline.

The original Foundry explores the layer before automation: observations become inspectable protocol candidates, candidates are simulated and independently graded, Selection keeps safety/diversity/performance signals separate, and only evidence-qualified candidates may advance toward a no-side-effect Shadow boundary.

This port keeps that conservative shape while moving the runtime core into typed C++.

```text
Observation
  -> Proxy
  -> Protocol Candidate
  -> Scenario Generation
  -> Deterministic Simulation
  -> Independent Grading
  -> Selection
  -> PoC Promotion Gate
  -> Shadow Action Receipt
```

## Why C++

This is not a claim that C++ is inherently better for the Foundry. The goal is to create a small, auditable runtime with:

- C++20 typed domain models (`enum class`, `std::variant`, `std::optional`)
- deterministic routing and gating
- CMake build
- Linux CI
- unit/regression tests
- explicit ownership around JSON parsing
- a path toward Python-vs-C++ golden tests

## Safety invariants preserved

- Route precedence: `DENY > ESCALATE > HOLD > REVIEW > AUTO`
- Unknown or unsupported expressions route to `HOLD`
- Generated candidates begin with `intent_status=unconfirmed`
- Missing promotion evidence routes to `HOLD`
- A Shadow Receipt never invokes adapters and records no external effects

## Requirements

- CMake 3.20+
- C++20 compiler (GCC 12+/Clang 15+ recommended)
- `libjson-c-dev`

Ubuntu/Debian:

```bash
sudo apt-get install -y build-essential cmake libjson-c-dev
```

## Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

## Run the integrated pipeline

Conservative default (candidate intent remains unconfirmed; no evidence):

```bash
./build/lopas_foundry \
  examples/observations.json \
  --output-dir receipts/default \
  --scenario-count 20
```

A human-confirmed run with evidence:

```bash
./build/lopas_foundry \
  examples/observations.json \
  --output-dir receipts/confirmed \
  --scenario-count 20 \
  --confirm-intent \
  --evidence examples/evidence.json \
  --current-level 2 \
  --next-level 3
```

Optional Shadow boundary:

```bash
./build/lopas_foundry \
  examples/observations.json \
  --output-dir receipts/shadow \
  --scenario-count 20 \
  --confirm-intent \
  --evidence examples/evidence.json \
  --current-level 2 \
  --next-level 3 \
  --shadow-bindings examples/adapter_bindings.json
```

Even if promotion succeeds, the Shadow stage emits steps annotated with `external_effect:none` and `external_effects: []`.

## Generated artifacts

```text
01_observations.json
02_proxies.json
03_protocol_candidates.json
04_simulation_receipts.json
05_selection_results.json
06_poc_promotions.json
07_action_receipts.json   # only with --shadow-bindings
```

## C++ structure

```text
include/lopas/
  types.hpp       typed contracts and gates
  expression.hpp  conservative expression evaluator
  foundry.hpp     stage APIs
  io.hpp          JSON boundary
src/
  types.cpp
  expression.cpp
  foundry.cpp
  io.cpp
  main.cpp
tests/
  test_main.cpp
```

## Current compatibility boundary

See `COMPATIBILITY.md` before calling this a full replacement for the Python runtime. v0.1 intentionally proves the C++ execution/gating core first; YAML/schema parity and golden parity tests are the next migration step.
