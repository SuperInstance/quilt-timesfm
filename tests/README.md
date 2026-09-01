# Tests

Two test files cover the cell model and the temporal-reasoner wrapper:

| File | Tests | What it covers |
|---|---|---|
| [`test_quilt_cell.py`](test_quilt_cell.py) | 49 | The 5 cell operations, FNV-1a 64-bit, PROOF chain, polyformalism claim, shape invariants, real TimesFM 3.0 binding (when available) |
| [`test_temporal.py`](test_temporal.py) | 49 | The 10 capabilities of the `TemporalReasoner`: ForecastObject, scenarios, counterfactuals, explainability, lifecycle, agent memory, decision support, `quf://` URI, metrics (incl. agent utility), CRDT |

## Running

```bash
# From the repo root
python3 tests/test_quilt_cell.py     # 49 tests
python3 tests/test_temporal.py       # 49 tests
```

Both files end with `=== 49 passed, 0 failed ===` on a clean checkout.

## What the 49 cell tests cover

The cell tests are a conformance suite for the polyformalism claim. They verify:

- **The kind name is `"time.cell"`** — bit-exact across C, Python, and Rust no_std
- **The 5 operation indices are 0..4** — BIND_CONTEXT, BIND_COVARIATE, FORECAST, READ_POINT, READ_QUANTILE
- **The state hash is FNV-1a 64-bit** — the test vector `FNV-1a("abc") = 0xe71fa2190541574b` is the FIPS 198 reference
- **The PROOF chain records `prev_hash` before every BIND**
- **The forecast shape is `[horizon, n_variates]` for the point and `[9, horizon, n_variates]` for the 9 quantiles**
- **The 11-opcode count is exact** (`BIND / LINK / EFFECT / VIEW / TICK / FORGET / PROOF / ROUTE / CRDT / WORLD / TIME`)

A new polyformalism port passes when these 49 tests pass against the
same context. See [`docs/POLYFORMALISM.md`](../docs/POLYFORMALISM.md) for
the 1-day add workflow.

## What the 49 temporal tests cover

The temporal tests verify the 10 capabilities:

- **ForecastObject** — id, source, timestamp, horizon, confidence, trend, forecast, uncertainty, provenance, URI
- **Scenarios** — optimistic, baseline, pessimistic
- **Counterfactuals** — "what if X changes?" with impact + confidence
- **Explainability** — major drivers, important covariates, prediction rationale
- **Lifecycle** — record outcome, prediction error, calibration score
- **Agent memory** — durable store across `TemporalReasoner` instances
- **Decision support** — `recommend_actions()` with expected benefit + confidence
- **`quf://` URI** — roundtrip, prefix match
- **Metrics** — MAE, RMSE, MAPE, calibration, pinball loss, agent utility
- **CRDT** — merge commutativity, idempotence, version increment

## Other test files (upstream TimesFM)

The remaining test files (`test_torch_layers.py`, `test_torch_utils.py`,
`test_model_loading.py`, `test_base_utils.py`, `test_configs.py`,
`test_force_flip_invariance.py`) are the upstream Google TimesFM tests
that ship with the model source code. They require the `timesfm`
package to be installed and a downloaded model checkpoint.

If you have the full TimesFM stack installed (`pip install timesfm[torch]`),
you can run them. They are not part of the Quilt cell conformance
suite and are not required for the polyformalism claim.

## The polyformalism check

The 49 cell tests are the polyformalism check. If you write a new port
in a new language, port these 49 tests, run them against your new
language's cell, and they all pass — you have a real polyformalism port.

This is what the [`quilt-timesfm-rust`](https://github.com/SuperInstance/quilt-timesfm-rust)
repo proves: 49 tests, all green, no_std, no torch, no model — just
the cell shape and the FNV-1a hash.
