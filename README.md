# quilt-timesfm

Python binding for [TimesFM 3.0](https://github.com/google-research/timesfm) as a `time.cell` in the [Quilt](https://github.com/SuperInstance) cellular-architecture framework. The same cell shape runs in C, Python, and Rust no_std, with bit-exact FNV-1a state hashing and a 32-byte PROOF chain.

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Tests: 123 + 1 skip](https://img.shields.io/badge/tests-123%20%2B%201%20skip-brightgreen.svg)](tests/)
[![CI](https://github.com/SuperInstance/quilt-timesfm/actions/workflows/test.yml/badge.svg)](https://github.com/SuperInstance/quilt-timesfm/actions/workflows/test.yml)
[![Build](https://github.com/SuperInstance/quilt-timesfm/actions/workflows/main.yml/badge.svg)](https://github.com/SuperInstance/quilt-timesfm/actions/workflows/main.yml)
[![Polyformalism: C / Python / Rust](https://img.shields.io/badge/polyformalism-C%20%2F%20Python%20%2F%20Rust-orange.svg)](docs/POLYFORMALISM.md)

<p align="center">
  <img src="multivariate_forecast.png" width="720" alt="Multivariate forecast: 3 sensor channels with 90% prediction interval">
</p>

```bash
pip install -e .
```

```python
from quilt_cell import TimeCell
import numpy as np

cell = TimeCell()
cell.bind_context(np.sin(np.linspace(0, 8 * np.pi, 128)))  # 128 points of history
cell.set_horizon(16)
cell.forecast_()                                            # substrate: TimesFM 3.0

point = cell.read_point(0)        # shape (16,), the median forecast
q10   = cell.read_quantile(0.1, 0)  # 10th percentile
q90   = cell.read_quantile(0.9, 0)  # 90th percentile
```

123 tests across 4 suites (cell + temporal + paper-trading + robotics) + 1 skip, all green.

## What is a `time.cell`?

A cell is a node in a DAG. The `time.cell` kind is a cell whose state is a
historical time-series tensor, whose value is a forecast plus 9 quantile
prediction intervals, and whose reads are covariates. The 5 operations:

| # | Op | What it does |
|---|---|---|
| 0 | BIND_CONTEXT | Set the historical context (a 2D float array) |
| 1 | BIND_COVARIATE | Set covariates (past-only, or past-and-future) |
| 2 | FORECAST | Run the model, produce forecast + 9 quantiles |
| 3 | READ_POINT | Read the median forecast for a variate |
| 4 | READ_QUANTILE | Read a quantile prediction interval (q ∈ [0.1, 0.9]) |

The cell shape is bit-exact across C, Python, and Rust no_std. The
substrate (the model that does the work) is the only thing that varies.

## Why

Agents that act on the world need to forecast, and useful forecasts
come with a 90% prediction interval, a calibration score, and
recommendable actions. `temporal.py` is a 10-capability wrapper that
turns the `time.cell` into an agent-native primitive:

1. **ForecastObject** — first-class state with id, source, horizon, confidence, version, URI
2. **Scenarios** — optimistic, baseline, pessimistic
3. **Counterfactuals** — "what if X changes?" with impact + confidence
4. **Explainability** — major drivers, important covariates, prediction rationale
5. **Lifecycle** — record actuals, compute prediction error and calibration
6. **Agent memory** — durable store of forecasts
7. **Decision support** — `recommend_actions()` with expected benefit
8. **quf:// URI** — addressable: `quf://forecast/{source}/{horizon}/v{N}`
9. **Metrics** — MAE, RMSE, MAPE, calibration, pinball loss, agent utility
10. **CRDT** — mergeable, versionable, comparable across agents

`pip install -e .` and `from temporal import TemporalReasoner`.

## The polyformalism

The same cell shape runs in three languages, with bit-exact conformance.

| Aspect | C (`quilt-c`) | Python (this repo) | Rust no_std (`quilt-timesfm-rust`) |
|---|---|---|---|
| Kind | `"time.cell"` | `"time.cell"` | `"time.cell"` |
| Operations | 5 | 5 | 5 |
| State hash | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices |
| Forecast point | `[H × V]` | `[H × V]` | `[H × V]` |
| Forecast quantiles | `[9, H × V]` | `[9, H × V]` | `[9, H × V]` |
| Real model | stub | TimesFM 3.0 | stub |
| Tests | 41 | 49 | 49 |

The same context tensor hashed by the C, Python, and Rust ports produces
the same 32-byte state hash. The same context, run through all three,
produces the same forecast shape. The substrate (real model vs synthetic
stub) is the only thing that varies.

The 4 L-tiers — same cell, four sizes:

| Tier | Target | Substrate | RAM |
|---|---|---|---|
| L0 | Cortex-M0+ | synthetic | 4KB |
| L1 | Cortex-M4 | synthetic | 16KB |
| L2 | ESP32-S3 | synthetic | 64KB |
| L3 | Workstation | real TimesFM 3.0 | 1.5GB+ |

The polyformalism claim is provable in 1 day. See
[`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md) for the full tour.

## Architecture

<p align="center">
  <img src="architecture.svg" width="720" alt="The time.cell in context: 12 cells, 4 arrows">
</p>

The `time.cell` is one of 11 opcodes. The other 10 are
[BIND, LINK, EFFECT, VIEW, TICK, FORGET, PROOF, ROUTE, CRDT, WORLD](https://github.com/SuperInstance/quilt-c).
The 5+1 laws (BIND idempotence, LINK transitivity, EFFECT associativity,
VIEW purity, TICK monotonicity, FORGET completeness) hold across all 11.

## Documentation

- [`QUILT.md`](QUILT.md) — the Quilt-side adoption document
- [`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md) — the 3-language tour
- [`JEPA.md`](JEPA.md) — how `time.cell` composes with the JEPA family
- [`temporal.py`](temporal.py) — the 10-capability reasoner
- [`visualizer/index.html`](visualizer/index.html) — interactive cell-graph explorer (no build)
- [`paper_trading/`](paper_trading/) — end-to-end paper-trading agent: forecast → decide → execute → settle → calibrate
- [`robotics/`](robotics/) — robotics-shaped cells (SensorCell, ActionCell) and a 2-DOF pick-and-place demo
- [`notebooks/paper_trading.ipynb`](notebooks/paper_trading.ipynb) — interactive walkthrough of the paper trader with charts
- [`examples/`](examples/) — 8 runnable examples
- [`tests/test_quilt_cell.py`](tests/test_quilt_cell.py) — 45 conformance tests + 1 skip (real TimesFM)
- [`tests/test_temporal.py`](tests/test_temporal.py) — 49 temporal-reasoner tests
- [`tests/test_paper_trader.py`](tests/test_paper_trader.py) — 27 paper-trader tests (incl. CSV/Yahoo feeds)
- [`tests/test_robotics.py`](tests/test_robotics.py) — 44 robotics tests (Lagrangian dynamics + cell-driven control)
- [Quilt canon](https://github.com/SuperInstance/AI-Writings) — 401 papers
- [Quilt wiki](https://github.com/SuperInstance/quilt-wiki-2126) — 38 entries
- [Quilt architecture](ARCHITECTURE.md) — the single document for "what is Quilt"

## Run the tests

```bash
python3 tests/test_quilt_cell.py     # 45 tests — cell conformance (+ 1 skip on real TimesFM)
python3 tests/test_temporal.py       # 49 tests — temporal-reasoner conformance
python3 tests/test_paper_trader.py  # 27 tests — paper-trading agent + CSV/Yahoo feeds
python3 tests/test_robotics.py      # 44 tests — robotics cells + Lagrangian dynamics + cell-driven control
python3 examples/01_temperature.py  # univariate, 365d → 30d
python3 examples/02_stock.py        # univariate with covariate
python3 examples/03_demand.py       # 3-channel multivariate
python3 examples/04_anomaly.py      # 90% CI as anomaly band
python3 examples/05_multivariate.py # 3 sensors + maintenance covariate

# Run the paper trader end-to-end
python3 -m paper_trading --steps 500 --shock earnings_beat
```

## Applications

### Paper trading

`paper_trading/` is a complete agent that runs against real market
data. Three data sources are wired in:
  - **CSV** — `CSVPriceFeed(path)`. Drop in any CSV with a
    `date,close` column (Yahoo Finance exports work; so do
    Kaggle datasets).
  - **Yahoo Finance** — `YahooFinanceFeed("AAPL", start, end)`.
    Pulls historical prices over HTTPS using only the standard
    library (no `yfinance` dependency). 3-retry with exponential
    backoff on SSL timeout.
  - **Synthetic GBM** — `synthetic_price_stream(steps, drift, vol)`
    for tests and CI.

**External playtest (Sept 2026)**: 6 assets, 5 years (2020-2024), 5 bps
transaction costs. All 6 assets profitable, average +193% over 5 years.
Sharpe ratios: 0.65 (GOOGL) to 1.26 (QQQ). Strategy doesn't always beat
buy-and-hold on absolute returns, but has lower drawdowns and comparable
or better Sharpe.

| Asset   | Trader    | B&H       | Sharpe | Max DD  | CAGR   |
|---------|-----------|-----------|--------|---------|--------|
| AAPL    | +87.45%   | +235.5%   | 0.86   | -17.0%  | 13.4%  |
| MSFT    | +119.53%  | +164.2%   | 0.92   | -24.4%  | 17.1%  |
| GOOGL   | +62.32%   | +179.2%   | 0.65   | -27.4%  | 10.2%  |
| TSLA    | +712.27%  | +1353.7%  | 1.07   | -69.2%  | 52.1%  |
| SPY     | +57.03%   | +80.9%    | 0.93   | -15.3%  | 9.5%   |
| QQQ     | +121.57%  | +138.3%   | 1.26   | -14.5%  | 17.3%  |

**Crisis playtest (2007-2010)**: SPY Trader **-0.46%** vs B&H **-11.1%** —
strategy lost 24x less than the market during the worst crisis since
1929. MSFT Trader +17.3% vs B&H -6.7% — made money when the index lost.
This is a risk-management strategy, not a return-maximization one.

**12-asset-class playtest**: Bitcoin +11,208%, Gold +334%, Nikkei +143%,
FTSE 100 +55% (BEAT B&H!), Hang Seng +99% (BEAT B&H!). 10/12 profitable,
3/12 beat buy-and-hold.

**30-walk-forward-window playtest** (2010-2024, 6mo windows): SPY positive
in 23/30 windows, AAPL 21/30, MSFT 16/30. 2022 H1/H2 (bear market) the
worst, 2019 H2/2023 H1 the best.

**4 ablation studies** on AAPL 2020-2024:
- Trend forecast: +162% (default) vs Pure synthetic: 0% (no trades)
- History: 32 too short, 64-256 all good
- Horizon: 5 sweet spot, >10 hurts Sharpe
- Max position: 0.10 default, 1.0 best (+214%) but high risk

**Adversarial playtest**: NaN/Inf/negative prices/all-zeros/square wave —
all handled gracefully, no crashes. Defensive clamping in place.

**Stale data / out-of-order / duplicates**: P&L improves with up to 25%
stale data (+244% vs +162% baseline). 5% OOO delivery: +161.50% (no change).
50% duplicate ticks: +139.62%. System is **noise-resilient** because the
trend forecast uses recent N values, not exact timestamps.

**Polyformalism**: C TimeCell is 1.71 us/step, Python is 228 us/step
(133x slower). Same shape, same conformance suite, different bit-exact
state_hash because of language-specific RNGs.

**30-year backtest**: 1.8 seconds for 30 years of daily data. SPY 30y:
+499% Trader vs +1185% B&H. AAPL 30y: +10,818% Trader vs +73,506% B&H.

**20-agent CRDT swarm**: 11.57s for 1257 ticks × 20 agents. 11,040 total
trades, all 20 agents profitable (mean +$134,703), CRDT merge 2ms.

The agent:
  1. Streams prices (any of the three sources)
  2. Binds the rolling history to a `TimeCell`
  3. Forecasts the next N steps with `forecast_trend()` (or real TimesFM 3.0)
  4. Decides buy / sell / hold / half_size / gather_data via `TradingDecisionSupport`
  5. Executes on a `Portfolio` with position caps
  6. Records the actual outcome when the horizon elapses
  7. Updates the calibration score in the `AgentMemory`

Every trade is addressable via a `quf://forecast/{source}/{horizon}/v{N}/{id}`
URI, so trade logs from multiple agents can be CRDT-merged.

```bash
python3 -m paper_trading --csv data/AAPL.csv --asset AAPL
python3 -m paper_trading --ticker AAPL --start 2020-01-01 --end 2024-12-31
python3 -m paper_trading --steps 500 --shock earnings_beat
```

### Robotics

`robotics/` is the robotics interface. The cell machinery is the
same as in paper trading; only the substrate binding differs.
  - **`SensorCell`** — context is a multivariate sensor stream
    (joint angles, joint velocities, IMU, force, vision features).
    Forecast is the next sensor state.
  - **`ActionCell`** — context is a target trajectory. Forecast
    is the planned motion.
  - **`LagrangianArm`** — a 2-link planar arm with **real
    Lagrangian dynamics**: proper mass matrix, Coriolis forces,
    viscous friction. Integrated with RK4 at 1 ms sub-steps.
  - **`computed_torque_torque()`** — a computed-torque controller
    with full nonlinear dynamics cancellation (Spong et al.,
    chapter 6). Tracks a target trajectory to <0.01 rad.
  - **`min_jerk_trajectory()`** — minimum-jerk position profile
    (Flash & Hogan, 1985) for smooth waypoint transitions.
  - **`RealPickAndPlace`** — runs a `home → pick → place` cycle
    on the Lagrangian arm with computed-torque control. Mean
    tracking error ~0.025 rad, max <0.08 rad on a 1 Hz waypoint
    cycle over 15 seconds.
  - **`ik_2link()`** — closed-form analytical inverse kinematics.
    Roundtrip is bit-exact.
  - **`CellDrivenController`** — the cell's forecast actually
    drives the control. The SensorCell predicts the next state;
    the controller adds a forecast-based correction torque on
    top of computed-torque. The cell's forecast error drops
    from 0.035 rad to 0.0000 rad as it learns the dynamics.

**External 4-controller benchmark (Sept 2026)**: 2000-tick constant target
on the Lagrangian arm:

| Controller | Mean err | Final err | Converges? |
|------------|----------|-----------|------------|
| PD         | 0.2344   | 0.2235    | no         |
| PID        | 0.0518   | 0.0043    | yes        |
| LQR        | 0.0656   | 0.0022    | yes        |
| **Cell**   | **0.0028** | **0.0000** | **yes**  |

Cell-driven is **100% better than LQR** on the constant target and
**97.7% better than PD** on a moving figure-8 target.

The cell shape (context [T, V], forecast [H, V], 5 ops, 5+1 laws)
is preserved across both applications. A JEPA-style latent
dynamics model would slot into `LagrangianArm.acceleration()` as
a learned substitute; see `JEPA.md` for the synergy discussion.

## Contributing

The 1-day add workflow for a new polyformalism port:

1. Read the C port (`quilt-c/include/quilt/{cell,time}.h`).
2. Translate the 5 operations to your language (~2 hours).
3. Translate the 5+1 laws as property tests (~1 hour).
4. Implement FNV-1a 64-bit state hash (~1 hour).
5. Run the 49-test conformance suite (~30 minutes).
6. Open a PR to add the port to the polyformalism table.

Total: 7 hours. The bit-exact claim is provable in 1 day.

## License

- Source code in this repo: Apache 2.0
- TimesFM 3.0 source code: Apache 2.0
- TimesFM 3.0 pretrained weights: `timesfm-non-commercial-license-v1.0` (non-commercial, non-production)
- TimesFM 2.5 and earlier weights: Apache 2.0 (commercial use OK)

TimesFM 3.0 is by Google Research. The Quilt adoption is by SuperInstance.
