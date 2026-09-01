# Examples

Each example is a self-contained Python script that demonstrates one
pattern of the `time.cell`. Run any of them with `python3 <filename>.py`.

| # | File | What it shows |
|---|---|---|
| 01 | [`01_temperature.py`](01_temperature.py) | Univariate forecast. 365 days of synthetic temperature → 30-day forecast with 90% prediction interval. |
| 02 | [`02_stock.py`](02_stock.py) | Univariate with a past-only covariate. 252 trading days of price, with daily volume as the covariate. |
| 03 | [`03_demand.py`](03_demand.py) | Multivariate. 3 correlated demand series (SKUs A, B, C) forecast jointly with shared quantiles. |
| 04 | [`04_anomaly.py`](04_anomaly.py) | Anomaly detection. The 90% prediction interval is the anomaly band; any actual outside the band is a flagged anomaly. |
| 05 | [`05_multivariate.py`](05_multivariate.py) | Multi-variate sensor fusion. 3 sensor channels (temperature, pressure, vibration) with planned maintenance as a past-and-future covariate. |
| 07 | [`07_temporal_reasoner.py`](07_temporal_reasoner.py) | The 5 sections of the `TemporalReasoner`: ForecastObject, scenarios, counterfactuals, lifecycle, decision support. |
| 08 | [`08_agent_utility.py`](08_agent_utility.py) | The `agent_utility` metric. Compares 3 forecast models on the same actuals. |

## The pattern

Every example follows the same 4 steps:

1. **Bind the context** — a 2D float array of shape `[context_len, n_variates]`
2. **(Optional) Bind covariates** — past-only or past-and-future
3. **Set the horizon** and run `cell.forecast_()`
4. **Read the forecast** — `cell.read_point(variate)` for the median, `cell.read_quantile(q, variate)` for a quantile

## What the numbers mean

The `time.cell` produces a point forecast (the median) and 9 quantile
prediction intervals (q=0.1 through q=0.9). The 90% prediction interval
is the band `[q=0.1, q=0.9]`.

If the cell calls real TimesFM 3.0, the numbers are Google's model.
If the cell runs in synthetic mode (no `torch` installed), the numbers
are a deterministic FNV-seeded pattern — same input, same output, no
model needed. The synthetic mode is for tests and for embedded targets
without room for a real model.

## Visual outputs

Examples 01, 03, 04, 05 produce PNGs as side effects:

- `anomaly_detection.png`
- `demand_forecast.png`
- `multivariate_forecast.png`

These are the figures that appear in the README and the visualizer.

## The Rust equivalent

For embedded targets (Cortex-M0+, Cortex-M4, ESP32-S3), the same cell
shape lives in [`quilt-timesfm-rust/examples/06_embed.rs`](https://github.com/SuperInstance/quilt-timesfm-rust/blob/main/examples/06_embed.rs).
Same 5 operations, same FNV-1a state hash, same 9 quantiles. The only
difference is the substrate: the Rust port uses the synthetic
forecast stub (no model in 16KB of RAM).
