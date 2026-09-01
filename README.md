# quilt-timesfm

A Python binding for Google's [TimesFM 3.0](https://github.com/google-research/timesfm)
exposed as a `time.cell` in the Quilt cellular-architecture framework.
The same cell shape runs in C, Python, and Rust no_std, with bit-exact
FNV-1a state hashing and a 32-byte PROOF chain.

## What's in this repo

- `quilt_cell.py` — the Python `TimeCell` class. Calls the real TimesFM
  3.0 model when `torch` is available; falls back to a deterministic
  synthetic forecast otherwise (kernel-friendly stub).
- `temporal.py` — a 10-capability wrapper around the cell: forecast
  objects, scenarios, counterfactuals, explainability, lifecycle, agent
  memory, decision support, the `quf://` URI scheme, evaluation metrics,
  and CRDT merging.
- `tests/test_quilt_cell.py` — 49 conformance tests, all green.
- `tests/test_temporal.py` — 49 temporal-reasoner tests, all green.
- `examples/01-08.py` — 8 runnable examples (temperature, stock,
  demand, anomaly, multivariate, embed, temporal reasoner, agent utility).
- `visualizer/index.html` — a 33KB interactive cell-graph explorer.
  Vanilla HTML+Canvas+JS, no build step.
- `docs/POLYFORMALISM.md` — the 3-language tour (C, Python, Rust).
- `JEPA.md` — how the `time.cell` composes with the JEPA family of
  world models.

## The 11 opcodes

```
BIND   write a value to a cell                         (idempotent)
LINK   add a dependency edge                           (transitive, no cycles)
EFFECT apply a registered effect to a cell             (associative, pure)
VIEW   read a cell's value                             (pure)
TICK   advance the engine one step                     (monotonic, journaled)
FORGET tear down a cell                                (complete)

PROOF  signed hash-linked audit chain
ROUTE  substrate routing for memory
CRDT   state-based CRDT for offline convergence
WORLD  5-operation abductive loop on executable code
TIME   5-operation time-series foundation model
```

The 5+1 laws:

- BIND idempotence: `BIND(n, v); BIND(n, v) == BIND(n, v)`
- LINK transitivity: `a→b + b→c` implies `a→c` (cycles rejected)
- EFFECT associativity: `(a ⊕ b) ⊕ c == a ⊕ (b ⊕ c)`
- VIEW purity: `VIEW(n)` returns the value and mutates nothing
- TICK monotonicity: tick count only increases; the journal is append-only
- FORGET completeness: a forgotten cell leaves no node, no edge, no dirty bit

## What is a cell?

| Field | Meaning |
|---|---|
| `kind` | what kind of cell this is (string, e.g. `"time.cell"`) |
| `state` | the cell's private storage (typed) |
| `value` | what the cell emits when VIEW-ed (typed) |
| `reads` | the cell's inputs (a list of other cells) |

A cell-graph is a DAG of cells. TICK advances the graph one step.
BIND writes a value. LINK adds a dependency. EFFECT applies an effect.
VIEW reads. FORGET tears down. The 5 specialized opcodes (PROOF, ROUTE,
CRDT, WORLD, TIME) are additional operations that any cell can perform.

## The `time.cell` kind

A cell whose `kind` is `"time.cell"`. The state is a historical time-series
tensor. The value is a forecast tensor plus 9 quantile prediction
intervals. The reads are covariates (past-only, past-and-future).

### The 5 time-cell operations

| # | Op | What it does |
|---|---|---|
| 0 | BIND_CONTEXT | Set the historical context (a 2D float array) |
| 1 | BIND_COVARIATE | Set the covariates (past-only or past-and-future) |
| 2 | FORECAST | Run the model: produce forecast + 9 quantiles |
| 3 | READ_POINT | Read the point forecast (median quantile) for a variate |
| 4 | READ_QUANTILE | Read a quantile prediction interval (q ∈ [0.1, 0.9]) for a variate |

### The cell shape (bit-exact in C, Python, and Rust)

```c
// C
typedef struct {
    double      *context;          // [context_len, n_variates]
    size_t       context_len;
    size_t       n_variates;
    double      *past_only;        // [context_len, n_past_only_cov]
    size_t       n_past_only_cov;
    double      *past_future;      // [context_len + horizon, n_pf_cov]
    size_t       n_past_future_cov;
    size_t       horizon;
    uint8_t      prev_hash[32];    // FNV-1a 64-bit, 4 slices (PROOF chain)
    uint8_t      state_hash[32];
    quilt_forecast_t forecast;     // { point[horizon, n_variates], quantiles[9, horizon, n_variates] }
} quilt_time_cell_t;
```

```python
# Python
@dataclass
class TimeCell:
    context: np.ndarray            # [context_len, n_variates]
    context_len: int
    n_variates: int
    past_only: np.ndarray
    past_future: np.ndarray
    horizon: int
    prev_hash: bytes               # FNV-1a 64-bit, 4 slices
    state_hash: bytes
    forecast: Forecast             # { point, quantiles }
```

The state hash is FNV-1a 64-bit spread over 4 slices (32 bytes). The
`prev_hash` is saved before every `BIND_CONTEXT` (the PROOF chain). The
forecast structure is `[horizon, n_variates]` for the point and
`[9, horizon, n_variates]` for the 9 quantiles.

### The substrate: TimesFM 3.0

The cell's evaluator is **TimesFM 3.0** (Google Research, Apache 2.0
for v2.5; non-commercial for v3.0 weights, Apache for source). It is:

- 200M parameters (~800MB on disk, ~1.5GB RAM on CPU, ~1GB VRAM on GPU)
- Decoder-only transformer
- Patch-based: input patches of 32 tokens, output patches of 64
- Multivariate (multiple channels) with covariates
- 9 quantile prediction intervals (0.1, 0.2, ..., 0.9)
- Context length: 1 to 16,384 points

The substrate binding is swappable:

| Substrate | Where it runs | Behavior |
|---|---|---|
| Python (real TimesFM 3.0) | workstations, GPU servers | calls the real model |
| Python (Flax backend) | TPUs | calls the real model on TPU |
| Python (synthetic fallback) | anywhere | deterministic FNV-seeded stub (test-only) |
| C (synthetic stub) | microcontrollers, kernels | no model; used for tests |
| Rust no_std (synthetic stub) | ESP32, Cortex-M | no model; for embedded tests |

## Quick start

### Install

```bash
git clone https://github.com/SuperInstance/quilt-timesfm.git
cd quilt-timesfm
pip install -e .
# For full TimesFM 3.0:
pip install torch safetensors huggingface_hub
```

### Use the cell

```python
from quilt_cell import TimeCell
import numpy as np

# Build a 128-step sine wave
t = np.linspace(0, 8 * np.pi, 128)
context = np.sin(t).reshape(128, 1)

# Make a cell
cell = TimeCell()

# Bind the context
cell.bind_context(context)

# Set the forecast horizon
cell.set_horizon(16)

# Run the model
cell.forecast_()

# Read the point forecast (median quantile)
point = cell.read_point(0)        # shape: (16,)

# Read the 90% prediction interval
q10 = cell.read_quantile(0.1, 0)  # 10th percentile
q90 = cell.read_quantile(0.9, 0)  # 90th percentile
```

### Run the tests

```bash
python3 tests/test_quilt_cell.py
# === 49 passed, 0 failed ===
```

The 49 tests cover the kind name, operation indices, `BIND_CONTEXT`
state hash, PROOF chain, FORECAST (with real TimesFM 3.0 when available),
covariates, the FNV-1a test vector (`FNV-1a("abc") = 0xe71fa2190541574b`),
and the polyformalism shape invariant (`opcode_count() == 11`).

## The polyformalism

The cell shape is bit-exact across C, Python, and Rust no_std. The
substrate binding is the only thing that varies.

| Aspect | C (`quilt-c`) | Python (this repo) | Rust no_std (`quilt-timesfm-rust`) |
|---|---|---|---|
| Kind name | `"time.cell"` | `"time.cell"` | `"time.cell"` |
| Operations | 5 | 5 | 5 |
| Op indices | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 |
| State hash | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices |
| State hash size | 32 bytes | 32 bytes | 32 bytes |
| `prev_hash` (PROOF) | saved before every BIND | saved before every BIND | saved before every BIND |
| Forecast point | `[horizon, n_variates]` | `[horizon, n_variates]` | `[horizon, n_variates]` |
| Forecast quantiles | `[9, horizon, n_variates]` | `[9, horizon, n_variates]` | `[9, horizon, n_variates]` |
| Synthetic fallback | FNV-seeded -50..+50 | FNV-seeded -50..+50 | FNV-seeded -50..+50 |
| Real model | none (stub) | TimesFM 3.0 (when torch is available) | none (stub) |
| Test count | 41 | 49 (4 are real TimesFM binding tests) | 49 |

The polyformalism is the interface, not the substrate. The C and Rust
ports are kernel-friendly stubs; the Python port calls the real model.
See [`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md) for the full tour
including the 4 L-tiers (Cortex-M0+, Cortex-M4, ESP32-S3, Workstation).

### The 4 L-tiers

The same `time.cell` runs at four sizes:

| Tier | Target | Substrate | RAM |
|---|---|---|---|
| L0 | Cortex-M0+ | synthetic | 4KB |
| L1 | Cortex-M4 | synthetic | 16KB |
| L2 | ESP32-S3 | synthetic | 64KB |
| L3 | Workstation | real TimesFM 3.0 | 1.5GB+ |

The 5 operations, the 9 quantiles, the FNV-1a state hash, and the
forecast shape are the same at all four tiers. Only the substrate
binding changes.

## The Temporal Reasoner

`temporal.py` is a 10-capability wrapper around the cell. It treats
forecasts as durable semantic objects (not just outputs), so agents
can exchange, refine, challenge, merge, and learn from them over time.

| # | Capability | What it does |
|---|---|---|
| 1 | ForecastObject | First-class state: id, source, timestamp, horizon, confidence, trend, forecast, uncertainty, provenance, version, URI |
| 2 | Scenarios | Multiple futures: optimistic, baseline, pessimistic (with assumptions + probabilities) |
| 3 | Counterfactuals | "What if X changes?" with impact + confidence bounds |
| 4 | Explainability | Major drivers, important covariates, uncertainty sources, prediction rationale |
| 5 | Lifecycle | Record actuals, compute prediction error and calibration |
| 6 | Agent memory | Durable store of forecasts; learn from history |
| 7 | Decision support | `recommend_actions()` with expected benefit + confidence |
| 8 | quf:// URI | Addressable: `quf://forecast/{source}/{horizon}/v{version}` |
| 9 | Metrics | MAE, RMSE, MAPE, calibration, pinball loss, agent utility |
| 10 | CRDT | Mergeable, versionable, comparable across agents |

### Quick example

```python
from quilt_cell import TimeCell
from temporal import TemporalReasoner
import numpy as np

cell = TimeCell()
cell.bind_context(np.sin(np.linspace(0, 8 * np.pi, 128)))
tr = TemporalReasoner(cell)

# Forecast → produces a ForecastObject
fo = tr.forecast_object("sales", horizon=8)
print(fo.uri)                       # quf://forecast/sales/8/v1
print(fo.prediction_rationale)

# Scenarios
scs = tr.scenarios(3)               # optimistic, baseline, pessimistic

# Counterfactual
cf = tr.counterfactual("context_mean", 0.20)
# → {"impact_total": 0.50, "ci_low": 0.12, "ci_high": 0.56, "confidence": 0.80}

# Record outcome
fo_updated = tr.record_outcome(fo, [v + 0.1 for v in fo.forecast])

# Recommend actions
actions = tr.recommend_actions(fo_updated)
```

### Tests

```bash
python3 tests/test_temporal.py
# === 49 passed, 0 failed ===
```

### See also

- [`temporal.py`](temporal.py): the 10-capability implementation
- [`tests/test_temporal.py`](tests/test_temporal.py): the 49 tests
- [`examples/07_temporal_reasoner.py`](examples/07_temporal_reasoner.py)
- [`JEPA.md`](JEPA.md)

## The Quilt × JEPA composition

The Quilt `time.cell` is a temporal primitive for scalar and
multivariate time series. The JEPA family (V-JEPA 2, I-JEPA, A-JEPA,
M-JEPA) is a world model for high-dimensional sensory data. The two
compose into a perception-reasoning-action loop:

```
V-JEPA 2            Time Cell            Agent
(perception)        (reasoning)          (action)

video ──→ embedding ──→ state ──→ forecast ──→ decision
frames     (768d)       (32B)    (9 quantiles) (action)
```

The 4 roles of the `time.cell` in a JEPA world model:

1. Compression of JEPA embeddings (768-d → 32-byte cell state)
2. Uncertainty quantification for JEPA outputs (9 quantiles)
3. Counterfactual reasoning on JEPA states ("what if?")
4. Memory of past predictions (durable, addressable, learnable)

The 4 use cases: robotics, autonomous driving, video understanding,
time-series foundation models. See [`JEPA.md`](JEPA.md) for the full
discussion.

## Interactive visualizer

Open [`visualizer/index.html`](visualizer/index.html) in a browser.
The visualizer:

1. Renders the cell graph in real time. Each cell is a node, edges
   are dependencies, the forecast is animated step by step.
2. Decomposes every operation into cell operations. `BIND_CONTEXT` is
   shown as a state-write plus a PROOF-chain append. `FORECAST` is
   shown as the abductive loop: PROPOSE → EXECUTE → RENDER → VERIFY
   → REFINE.
3. Plays back a recorded session. Step through the 5 operations,
   watch the cell's state and value change, see the FNV-1a hash
   update with every BIND.
4. Compares the polyformalism ports side-by-side. The same
   `BIND_CONTEXT` call, the same hash, the same forecast.

The visualizer is vanilla HTML + Canvas + JS. No build step. No
dependencies. Just open the file.

```bash
open visualizer/index.html         # macOS
xdg-open visualizer/index.html     # Linux
start visualizer/index.html        # Windows
```

## Examples

### 1. Temperature forecasting (univariate)

[`examples/01_temperature.py`](examples/01_temperature.py) — 365 days of
daily temperature, 30-day forecast, 90% prediction interval.

### 2. Stock prices (univariate with covariates)

[`examples/02_stock.py`](examples/02_stock.py) — daily stock price plus
volume as a past-only covariate, 5-day forecast.

### 3. Demand planning (multivariate, 3 channels)

[`examples/03_demand.py`](examples/03_demand.py) — 3 correlated demand
series (SKUs A, B, C), joint forecast with shared quantile intervals.

### 4. Anomaly detection via quantile intervals

[`examples/04_anomaly.py`](examples/04_anomaly.py) — use the 90%
prediction interval as a band; any actual value outside the band is a
statistical anomaly.

### 5. Multi-variate sensor fusion (3 sensors)

[`examples/05_multivariate.py`](examples/05_multivariate.py) — 3 sensor
channels (temperature, pressure, vibration) with past-and-future
covariates (planned maintenance windows).

### 6. Embedded time cell (no_std Rust)

[`examples/06_embed.rs`](examples/06_embed.rs) — a no_std Rust time cell
with the synthetic forecast, for ESP32 / Cortex-M.

```bash
cargo build --release --target thumbv7m-none-eabi --example 06_embed
```

### 7. Temporal reasoner demo

[`examples/07_temporal_reasoner.py`](examples/07_temporal_reasoner.py) —
7 sections showing all 10 capabilities of `TemporalReasoner`.

### 8. Agent utility comparison

[`examples/08_agent_utility.py`](examples/08_agent_utility.py) — compare
3 forecast models with the `agent_utility` metric.

## The math

TimesFM 3.0 is a patch-based decoder-only transformer:

1. Input patches: the context tensor is split into patches of 32
   tokens each.
2. Decoder layers: stacked self-attention + feed-forward, with
   residual connections and RevIN (Reversible Instance Normalization)
   to handle distribution shift.
3. Output patches: the decoder emits output patches of 64 tokens
   each (the forecast horizon).
4. Quantile heads: 9 quantile heads, one per output token, predict
   the 0.1, 0.2, ..., 0.9 quantiles.

The quantile regression loss for quantile $q$:

$$\mathcal{L}_q(y, \hat{y}) = \max(q \cdot (y - \hat{y}), (q-1) \cdot (y - \hat{y}))$$

The model is trained to minimize the sum of all 9 quantile losses.

The state hash is FNV-1a 64-bit:

$$h_0 = 0xcbf29ce484222325$$
$$h_{i+1} = (h_i \oplus b_i) \cdot 0x100000001b3 \pmod{2^{64}}$$

The 4-slice spread (32 bytes) is the same algorithm as the C and Rust
ports, bit-exact.

## The other 4 specialized opcodes

The `time.cell` is one of 5 specialized opcodes. The other 4 are:

| # | Opcode | What it does |
|---|---|---|
| 1 | PROOF | Signed hash-linked audit chain on every BIND |
| 2 | ROUTE | Substrate routing for memory (5 substrate kinds) |
| 3 | CRDT | Offline convergence for replicated state (PN_Counter, MV_Register, OR_Set) |
| 4 | WORLD | The 5-op abductive loop (Code-as-World) |

The opcodes are `5 + 1 + 4 + 1 = 11`:

- BIND, LINK, EFFECT, VIEW, TICK (5 originals)
- FORGET (+1)
- PROOF, ROUTE, CRDT, WORLD (+4)
- TIME (+1, this repo)

## The Quilt ecosystem

This repo is one of 30+ in the SuperInstance GitHub org.

| Repo | What it is |
|---|---|
| [quilt-c](https://github.com/SuperInstance/quilt-c) | The kernel-friendly C port (11 opcodes, 1236 tests) |
| [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) | The Rust no_std port of `time.cell` (49 tests) |
| [quilt-rust](https://github.com/SuperInstance/quilt-rust) | The Rust polyformalism crate (29 tests) |
| [quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai) | The Python reference port (41 tests) |
| [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) | The GDScript port (Godot) |
| [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) | This repo: TimesFM 3.0 as a cell (49 tests) |
| [quilt-edge-arch](https://github.com/SuperInstance/quilt-edge-arch) | The edge / no_std substrate |
| [quilt-mhs](https://github.com/SuperInstance/quilt-mhs) | The Anthropic MHS port |
| [quilt-llvm](https://github.com/SuperInstance/quilt-llvm) | The LLVM fabric |
| [quilt-fleet](https://github.com/SuperInstance/quilt-fleet) | The fleet manager |
| [quilt-ai](https://github.com/SuperInstance/quilt-ai) | The AI helper |
| [AI-Writings](https://github.com/SuperInstance/AI-Writings) | The 398-paper canon |
| [quilt-wiki-2126](https://github.com/SuperInstance/quilt-wiki-2126) | The 38-entry wiki |
| [quilt-ecosystem-demo](https://github.com/SuperInstance/quilt-ecosystem-demo) | The 24-audit ecosystem report |

The 5 self-driving daemons (in `quilt-cellular-arch/_scouts/`):

- `frontier_miner.py` — finds canon gaps
- `writers_room_daemon_v3.py` — 13-voice parallel paper generation
- `snowball_daemon.py` — 8-sandbox reverse-actualization
- `re_embed_v2.py` — Vectorize pipeline (398 papers)
- `deploy_worker.sh` — CF Worker deployment

## Contributing

The 1-day add workflow: how to make a new polyformalism port for a new
language, in 1 day.

1. Read the C port: `quilt-c/include/quilt/{cell,time,proof,route,crdt,world}.h`
2. Translate the 5 time-cell operations to your language (2 hours)
3. Translate the 5 laws as property tests (1 hour)
4. Implement FNV-1a 64-bit state hash (1 hour)
5. Run the 49-test conformance suite (30 minutes)
6. Push to a new repo, open PR (30 minutes)

Total: 7 hours. The polyformalism claim is provable in 1 day.

If you write a new port, please open a PR to add it to the
[quilt-c](https://github.com/SuperInstance/quilt-c) cross-reference
table.

## License & credits

- **Source code** (this repo, `quilt_cell.py`, `tests/`, `QUILT.md`): Apache 2.0
- **TimesFM 3.0 source code** (`src/timesfm3/`): Apache 2.0
- **TimesFM 3.0 pretrained weights**: `timesfm-non-commercial-license-v1.0`
  (non-commercial, non-production use only)
- **TimesFM 2.5 and earlier weights**: Apache 2.0 (commercial use OK)

TimesFM 3.0 is by Google Research. The Quilt adoption is by SuperInstance.

## See also

- Paper 385-390 in the canon (the 6 time.cell papers)
- Wiki 20: The Time Cell
- [`quilt_cell.py`](quilt_cell.py) — the cell class
- [`temporal.py`](temporal.py) — the 10-capability reasoner
- [`tests/test_quilt_cell.py`](tests/test_quilt_cell.py) — 49 tests
- [`tests/test_temporal.py`](tests/test_temporal.py) — 49 tests
- [`visualizer/index.html`](visualizer/index.html) — interactive visualizer
- [`examples/`](examples/) — 8 runnable examples
- [`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md) — the polyformalism tour
- [Quilt canon](https://github.com/SuperInstance/AI-Writings) — 398 papers
- [Quilt wiki](https://github.com/SuperInstance/quilt-wiki-2126) — 38 entries
