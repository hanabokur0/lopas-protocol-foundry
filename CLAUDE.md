# CLAUDE.md — lopas-protocol-foundry

Loaded automatically by Claude Code at session start. This is the map. The repo is **v0.1, design-first, and explicitly incomplete** — treat every claim of "implemented" with suspicion until you've actually opened the file.

## One-line summary

Turns fragmented observations into traceable protocol candidates, tests them against declared scenarios via simulation, and promotes only qualified candidates toward limited, reversible real-world PoCs. Simulation is never treated as proof.

## Core pipeline

```
Observation → Proxy → Protocol Candidate → Scenario Suite → Simulation
→ Simulation Record/Receipt → Independent Grading → Selection
→ PoC Promotion Gate → Shadow Test/Limited PoC → Action Receipt → ProtocolMemory
```

Not every arrow above is currently an executable stage — see status table below before assuming a stage runs end-to-end.

## Directory map + implementation status

| Path | Role | v0.1 status | Read when |
|---|---|---|---|
| `schemas/*.yaml` | Contracts between every pipeline stage (observation, proxy, protocol_candidate, simulation_receipt, poc_promotion) | Present, still revisable | Before creating/validating any document at that stage |
| `prompts/*.md` | Stage-local LLM specs: proxy_generation, protocol_generation, scenario_generation, independent_grader | Present | Before generating a Proxy, Candidate, Scenario, or Grade — follow the contract, don't freelance the format |
| `examples/sample_run/` | One inspectable end-to-end trace | Present | To see what a real document at each stage looks like; **not evidence the candidate works in production** |
| `src/{ingest,proxy,protocol,simulation,selection,routing}/` | Runtime modules | Partial and uneven per stage | Check before assuming a stage is executable — many are scaffolding only |
| `receipts/` | Generated/archived run artifacts | Incomplete | — |
| `tests/` | Schema, regression, parity, safety tests | Not yet complete | Don't claim test coverage exists without checking |
| `docs/` | Architecture/safety/lifecycle docs | Planned, not yet added | — |

## Hard rules (from README's explicit safety boundaries — do not soften these)

A Protocol Candidate must **not** be promoted when any of the following hold:
- provenance is missing or fabricated
- evidence and interpretation cannot be separated
- required inputs or authority are unknown
- the route exceeds declared authority
- external impact is high and reversibility is low
- required human review is absent or bypassed
- policy/privacy/legal/rights/ownership ambiguity is unresolved
- simulation coverage is inadequate
- failures may remain silent
- the candidate depends on invented facts

Default status behavior is conservative: `unconfirmed → awaiting confirmation`, `insufficient evidence → hold`. Missing evidence routes to `HOLD`/`REVIEW`/`ESCALATE`/`DENY`, never silent automation.

**This project is explicitly not:** proof that LLM simulation predicts real-world success; a finished autonomous executor; a production scraping system; a replacement for accountable domain experts; a way to bypass consent/policy/review; a universal single-answer optimizer; a stable SDK. Do not describe it as any of these to the user even loosely.

## Quick task recipes

**"Turn this observation into a protocol candidate"** → Observation → `prompts/proxy_generation.md` → Proxy → `prompts/protocol_generation.md` → Candidate. Validate each against its schema before moving to the next stage. Do not skip Proxy and jump straight from raw observation to Candidate.

**"Test this candidate"** → generate a Scenario Suite via `prompts/scenario_generation.md` first (nominal, boundary, adversarial, failure conditions), *then* simulate. The scenario's expected behavior must be declared before simulation, not copied from the candidate's own default route — otherwise the test can't catch missing guards.

**"Grade this run"** → `prompts/independent_grader.md` compares candidate contract vs. scenario expectation vs. simulated actual. The grader does not activate anything or execute externally.

**"Is this ready to promote?"** → check against the 6-level ladder (0 schema checks → 5 monitored operation). A candidate passing simulation (level 1) is nowhere near promotable to real action (level 4+).

## Relationship to other repos in this ecosystem

Part of a wider set alongside `information-compost`, `LoPAS-Open-Translator-Core`, `Verifiable-Capability-Exchange`, `LoPAS-LCA`. No cross-repo wiring exists yet. If a task seems to need a translator/exchange function from another repo, say so explicitly rather than assuming it's already connected here.
