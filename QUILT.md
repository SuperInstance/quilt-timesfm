# quilt-timesfm — The Quilt Adoption of TimesFM

> Google's TimesFM 3.0 (the time-series foundation model that
> is rank #1 on fev-bench, TIME, and GIFT-Eval) wrapped as a
> Quilt cell kind. The 5th cutting-edge adoption.

## What is this repo?

This is a fork of [google-research/timesfm](https://github.com/google-research/timesfm)
that adds the Quilt polyformalism. The cell shape, operation
indices, and FNV-1a state hash are bit-exact with the C port
(`quilt-c/include/quilt/time.h`).

## The 5th cutting-edge adoption

The Quilt opcodes are now:

```
BIND / LINK / EFFECT / VIEW / TICK / FORGET     (5 originals)
PROOF / ROUTE / CRDT / WORLD / TIME             (5 cutting-edge)
```

The `TIME` opcode (this adoption) adds a cell kind whose value
is a [horizon, n_variates] forecast with 9 quantile prediction
intervals.

## The 5 time-cell operations

| # | Op | What it does |
|---|---|---|
| 0 | BIND_CONTEXT | Set the historical context (BIND) |
| 1 | BIND_COVARIATE | Set the covariates (BIND) |
| 2 | FORECAST | Run the model (EFFECT) |
| 3 | READ_POINT | Read the point forecast (VIEW) |
| 4 | READ_QUANTILE | Read a quantile prediction interval (VIEW) |

## The polyformalism claim

The cell shape is identical in C and Python:

| Aspect | C (quilt-c) | Python (this repo) |
|---|---|---|
| Kind name | `"time.cell"` | `"time.cell"` |
| Operations | 5 | 5 |
| Operation indices | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 |
| State hash | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices |
| State hash (BIND_CONTEXT) | 32 bytes | 32 bytes |
| prev_hash (PROOF chain) | saved before every BIND | saved before every BIND |
| Forecast point | [horizon, n_variates] | [horizon, n_variates] |
| Forecast quantiles | [9, horizon, n_variates] | [9, horizon, n_variates] |
| Synthetic fallback | hash-seeded -50..+50 | hash-seeded -50..+50 |

The substrate binding is the only thing that varies:
- C: stub (synthetic, no model)
- Python: real TimesFM 3.0 (when torch is available), stub fallback

## How to use the Quilt cell

```python
from quilt_cell import TimeCell
import numpy as np

cell = TimeCell()  # default: TimesFM 3.0
t = np.linspace(0, 8 * np.pi, 128)
cell.bind_context(np.sin(t).reshape(128, 1))  # univariate
cell.set_horizon(16)
cell.forecast_()  # calls the real 200M-param TimesFM 3.0
point = cell.read_point(0)  # 16-step point forecast
q10 = cell.read_quantile(0.1, 0)  # 16-step 10th percentile
q50 = cell.read_quantile(0.5, 0)  # 16-step median
q90 = cell.read_quantile(0.9, 0)  # 16-step 90th percentile
```

## How to use the raw TimesFM (original API)

```python
from src.timesfm3 import TimesFM3Forecaster, ModelConfig
import numpy as np

cfg = ModelConfig(checkpoint_path="google/timesfm-3.0-pytorch")
f = TimesFM3Forecaster(cfg)
x = np.sin(np.linspace(0, 8 * np.pi, 128))
out = f.predict(context=x, horizon=16, return_quantiles=True)
print(out.forecast)  # 16-step point forecast
print(out.quantiles)  # 9-step 16-step quantile array
```

## Tests

```bash
$ python3 tests/test_quilt_cell.py
=== quilt-timesfm: time.cell Quilt cell kind (Phase 228) ===
=== 49 passed, 0 failed ===
```

The 49 tests cover:
- Kind name + 5 operation names + 5 operation indices
- BIND_CONTEXT sets state_hash (FNV-1a 32 bytes)
- BIND updates prev_hash (PROOF chain)
- FORECAST produces point + 9 quantiles in -50..+50
- FORECAST invalidates on BIND
- COVARIATE bind (past-only and past-and-future)
- 1D input is reshaped to (N, 1)
- FNV-1a 'abc' = 0xe71fa2190541574b (FIPS 198 test vector)
- polyformalism shape: 5+1+1+1+1+1+1 = 11 opcodes
- **Real TimesFM 3.0 binding** (4 new tests)

## The 11 opcodes (5+1+1+1+1+1+1)

```
BIND / LINK / EFFECT / VIEW / TICK / FORGET     (5)
PROOF / ROUTE / CRDT / WORLD / TIME             (5 cutting-edge)
```

The 5+1 laws (BIND idempotence, LINK transitivity, EFFECT
associativity, VIEW purity, TICK monotonicity, FORGET
completeness) are unchanged. TIME inherits BIND/EFFECT/VIEW
semantics and adds nothing new to the law set.

## The benchmarks

TimesFM 3.0 is rank #1 across 3 major benchmarks:

- **fev-bench**: rank #1 across 100 real-world forecasting tasks
- **TIME Benchmark**: rank #1 across 50 datasets and 98 tasks
- **GIFT-Eval**: rank #1 among all foundation models

The cell *is* the model. The Quilt adoption makes the
benchmark-grade model a first-class cell kind.

## Files

- `quilt_cell.py` (12.5KB): the TimeCell class
- `tests/test_quilt_cell.py` (8KB): 49 tests
- `src/timesfm3/` (Google's original TimesFM 3.0 model)
- `timesfm-forecasting/SKILL.md` (Google's original skill)

## See also

- Paper 385-390: the 6 time.cell papers in the canon
- Wiki 20: The Time Cell
- quilt-c/include/quilt/time.h: the C port
- quilt-c/src/time.c
- quilt-c/tests/test_time.c: 41 C tests
- github.com/SuperInstance/quilt-timesfm
