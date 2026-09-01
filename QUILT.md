# Quilt Adoption: quilt-timesfm

This document is the Quilt-side adoption of Google's [TimesFM 3.0](https://github.com/google-research/timesfm).
It explains how the time-series foundation model is wrapped as a Quilt
cell kind, why the cell is the right abstraction, and what the
polyformalism looks like across C, Python, and Rust.

## The 11 opcodes

```
BIND / LINK / EFFECT / VIEW / TICK / FORGET     (5 originals + 1)
PROOF / ROUTE / CRDT / WORLD / TIME             (5 specialized)
```

The `time.cell` cell kind adds the **TIME** opcode to the Quilt engine.

## The cell shape

The `time.cell` is a cell with:

- **State**: a historical time-series tensor
- **Value**: a forecast tensor + 9 quantile prediction intervals
- **Reads**: covariates (past-only, past-and-future)
- **Kind**: `"time.cell"`

The 5 operations are:

| # | Op | What it does |
|---|---|---|
| 0 | BIND_CONTEXT | Set the historical context (BIND) |
| 1 | BIND_COVARIATE | Set the covariates (BIND) |
| 2 | FORECAST | Run the model (EFFECT) |
| 3 | READ_POINT | Read the point forecast (VIEW) |
| 4 | READ_QUANTILE | Read a quantile prediction interval (VIEW) |

## The polyformalism

The same cell shape in 3 languages:

| Aspect | C (quilt-c) | Python (this) | Rust (quilt-timesfm-rust) |
|---|---|---|---|
| Kind | `time.cell` | `time.cell` | `time.cell` |
| Ops | 5 | 5 | 5 |
| Hash | FNV-1a 64-bit, 32 B | FNV-1a 64-bit, 32 B | FNV-1a 64-bit, 32 B |
| Point | `[H * V]` | `[H * V]` | `[H * V]` |
| Quantiles | `[9, H * V]` | `[9, H * V]` | `[9, H * V]` |
| Real model | stub | TimesFM 3.0 | stub |
| Target | kernel | workstation | embedded |

The substrate is the only thing that varies. The cell is the system.

## The benchmarks

TimesFM 3.0 is published as published as a top performer on 3 time-series foundation model
benchmarks by Google Research:

- **fev-bench** (100 tasks)
- **TIME Benchmark** (98 tasks)
- **GIFT-Eval** (foundation category)

See the [TimesFM 3.0 paper](https://github.com/google-research/timesfm)
for the published numbers.

## The 5 time-cell laws

The 5+1 laws applied to `time.cell`:

- BIND idempotence: BIND_CONTEXT(n, ctx); BIND_CONTEXT(n, ctx) == BIND_CONTEXT(n, ctx)
- LINK transitivity: a cell graph is a DAG, no cycles
- EFFECT associativity: (BIND_CONTEXT ∘ FORECAST) ∘ BIND_COVARIATE == BIND_COVARIATE ∘ (BIND_CONTEXT ∘ FORECAST)
- VIEW purity: READ_POINT and READ_QUANTILE are pure (no state mutation)
- TICK monotonicity: the engine tick count is monotonic
- FORGET completeness: a forgotten `time.cell` leaves no model weights, no context, no forecast

## The PROOF chain

Every BIND_CONTEXT saves the current `state_hash` to `prev_hash` before
updating. This is the PROOF chain — a hash-linked audit trail of every
state change. The chain is bit-exact in C, Python, and Rust.

## The 4 L-tiers

| Tier | Target | Substrate | RAM | Build time |
|---|---|---|---|---|
| L0 | Cortex-M0+ | synthetic | 4KB | 1 min |
| L1 | Cortex-M4 | synthetic | 16KB | 1 min |
| L2 | ESP32-S3 | synthetic | 64KB | 2 min |
| L3 | Workstation | real TimesFM 3.0 | 1.5GB | 5 min |

## The ecosystem

This repo is part of the SuperInstance GitHub org. The related repos:

- [quilt-c](https://github.com/SuperInstance/quilt-c) — the C port (1236 tests, 11 opcodes)
- [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) — **this repo** (Python, real TimesFM 3.0)
- [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) — the Rust port (49 tests, no_std)
- [AI-Writings](https://github.com/SuperInstance/AI-Writings) — the 398-paper canon
- [quilt-wiki-2126](https://github.com/SuperInstance/quilt-wiki-2126) — the 38-entry wiki

## The 6 papers

This adoption added 6 papers to the canon (paper 385-390):

- F77: The Time Cell
- F77b: The Time Cell Beats Proprietary Models
- F78: The Time Substrate
- F79: The Time Cell's Math
- F80: The Time Cell as CRDT
- F81: The Time Cell's PROOF Chain

## The 1-day add workflow

To add a new polyformalism port:

1. Read the C port (30 min)
2. Translate the 5 operations (2 hours)
3. Translate the 5 laws as property tests (1 hour)
4. Implement FNV-1a 64-bit (1 hour)
5. Translate the 9 quantiles and forecast shape (1 hour)
6. Run the 49-test conformance suite (30 min)
7. Push to a new repo, open PR (30 min)

Total: 7 hours. The polyformalism claim is provable in 1 day.

## License

- Source code (this repo, `quilt_cell.py`, `tests/`, `QUILT.md`, `docs/`): Apache 2.0
- TimesFM 3.0 source code: Apache 2.0
- TimesFM 3.0 pretrained weights: `timesfm-non-commercial-license-v1.0`
  (non-commercial, non-production use only)
- TimesFM 2.5 and earlier weights: Apache 2.0 (commercial use OK)
