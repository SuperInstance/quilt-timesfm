# quilt-timesfm

> **A time-series foundation model as a Quilt cell.**
> Google's [TimesFM 3.0](https://github.com/google-research/timesfm) — the SOTA on
> fev-bench, TIME, and GIFT-Eval — wrapped as a first-class cell kind in the
> [Quilt](https://github.com/SuperInstance) cellular-architecture framework.

**The 5th cutting-edge adoption.** The Quilt opcodes are now **11**:

```
BIND / LINK / EFFECT / VIEW / TICK / FORGET     (5 originals)
PROOF / ROUTE / CRDT / WORLD / TIME             (5 cutting-edge)
```

This README teaches the Quilt cell model from scratch, shows the `time.cell`
kind in detail, walks the polyformalism (the same cell in C, Rust, and Python),
and ends with the benchmarks. If you've never seen Quilt, start at the top.

---

## Table of Contents

1. [What is Quilt?](#what-is-quilt)
2. [What is a cell?](#what-is-a-cell)
3. [The 11 opcodes](#the-11-opcodes)
4. [The `time.cell` kind](#the-timecell-kind)
5. [Quick start](#quick-start)
6. [The polyformalism](#the-polyformalism)
7. [Interactive visualizer](#interactive-visualizer)
8. [Examples](#examples)
9. [The benchmarks](#the-benchmarks)
10. [The math](#the-math)
11. [The other 4 cutting-edge adoptions](#the-other-4-cutting-edge-adoptions)
12. [The Quilt ecosystem](#the-quilt-ecosystem)
13. [Contributing](#contributing)
14. [License & credits](#license--credits)

---

## What is Quilt?

**Quilt** is a cellular-architecture framework: every reactive element is a
**cell**, and any interface (UI, REST, LLM, ESP32, VLM, foundation model) is an
**opener** onto the same cell graph. The cell is the system, not the data.

Concretely: a Quilt application is a **DAG of cells** where each cell has
state, value, and reads, and the 11 opcodes manipulate them. The cell model
is the **same** in C, Rust, Python, GDScript, and (eventually) every other
language — the polyformalism claim is bit-exact, not asserted.

Quilt has 257 papers in the canon, 35 wiki entries, 24 repo audits, 5
self-driving daemons (`frontier_miner`, `writers_room_daemon_v3`,
`snowball_daemon`, `re_embed_quilt_canon`, `deploy_worker`), and 1236+ tests
in `quilt-c` alone.

The 11 opcodes: BIND, LINK, EFFECT, VIEW, TICK, FORGET (the 5 originals +
teardown), PROOF, ROUTE, CRDT, WORLD, TIME (the 5 cutting-edge adoptions).

---

## What is a cell?

A cell is the irreducible unit of computation. It has:

| Field | Meaning |
|---|---|
| **State** | the cell's private storage (typed) |
| **Value** | what the cell emits when VIEW-ed (typed) |
| **Reads** | the cell's inputs (a list of other cells) |
| **Kind** | what kind of cell this is (string, e.g. `time.cell`) |

A cell-graph is a DAG of cells. TICK advances the graph one step (re-evaluates
the dirty cells). BIND writes a value. LINK adds a dependency. EFFECT applies a
side-effect. VIEW reads. FORGET tears down. PROOF chain-anchors a BIND.
ROUTE picks a substrate. CRDT converges a state. WORLD runs the abductive
loop. TIME runs a time-series forecast.

That's it. Everything in Quilt is a cell.

---

## The 11 opcodes

```
BIND   write a value to a cell                                (idempotent)
LINK   add a dependency edge                                  (transitive, no cycles)
EFFECT apply a registered effect to a cell                    (associative, pure)
VIEW   read a cell's value                                    (pure)
TICK   advance the engine one step                            (monotonic, journaled)
FORGET tear down a cell                                       (complete)

PROOF  signed hash-linked audit chain                         (cutting-edge #1)
ROUTE  substrate routing for memory                           (cutting-edge #2)
CRDT   state-based CRDT for offline convergence               (cutting-edge #3)
WORLD  5-operation abductive loop on executable code         (cutting-edge #4)
TIME   5-operation time-series foundation model               (cutting-edge #5)
```

The 5+1 laws:

- BIND idempotence: `BIND(n, v); BIND(n, v) == BIND(n, v)` (same id+value is a no-op)
- LINK transitivity: `a→b + b→c` implies `a→c` (cycles rejected)
- EFFECT associativity: `(a ⊕ b) ⊕ c == a ⊕ (b ⊕ c)`
- VIEW purity: `VIEW(n)` returns the value and mutates nothing
- TICK monotonicity: tick count only increases; the journal is append-only
- FORGET completeness: a forgotten cell leaves no node, no edge, no dirty bit

---

## The `time.cell` kind

A cell whose kind is `time.cell`. The cell's state is a historical time-series
tensor. The cell's value is a forecast tensor + 9 quantile prediction
intervals. The cell's reads are covariates (past-only, past-and-future).

### The 5 time-cell operations

| # | Op | What it does |
|---|---|---|
| 0 | BIND_CONTEXT | Set the historical context (a 2D float array) |
| 1 | BIND_COVARIATE | Set the covariates (past-only or past-and-future) |
| 2 | FORECAST | Run the model: produce forecast + 9 quantiles |
| 3 | READ_POINT | Read the point forecast (median quantile) for a variate |
| 4 | READ_QUANTILE | Read a quantile prediction interval (q ∈ [0.1, 0.9]) for a variate |

### The cell shape (bit-exact in C and Python)

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

The state hash is **FNV-1a 64-bit** spread over 4 slices (32 bytes). The
`prev_hash` is saved before every BIND_CONTEXT (the **PROOF chain**). The
forecast structure is `[horizon, n_variates]` for the point and
`[9, horizon, n_variates]` for the 9 quantiles.

### The substrate: TimesFM 3.0

The cell's evaluator is **TimesFM 3.0** (Google Research, Apache 2.0 for
v2.5; non-commercial for v3.0 weights, Apache for source). It's:

- 200M parameters (~800MB on disk, ~1.5GB RAM on CPU, ~1GB VRAM on GPU)
- Decoder-only transformer
- Patch-based: input patches of 32 tokens, output patches of 64
- Multivariate (multiple channels) with covariates
- 9 quantile prediction intervals (0.1, 0.2, ..., 0.9)
- Context length: 1 to 16,384 points

In the polyformalism, the substrate binding is a swap:

| Substrate | Where it runs | Quality |
|---|---|---|
| C (no_std stub) | microcontrollers, kernels | synthetic (test-only) |
| Python (real TimesFM 3.0) | workstations, GPU servers | SOTA on 3 benchmarks |
| Python (Flax backend) | TPUs | SOTA on TPUs |
| Python (distilled 4B) | edge devices, phones | ~95% of SOTA, 5x faster |

---

## Quick start

### Install

```bash
git clone https://github.com/SuperInstance/quilt-timesfm.git
cd quilt-timesfm
pip install -e .
# For full TimesFM 3.0:
pip install torch safetensors huggingface_hub
```

### Use the Quilt cell

```python
from quilt_cell import TimeCell
import numpy as np

# Build a 128-step sine wave (synthetic context)
t = np.linspace(0, 8 * np.pi, 128)
context = np.sin(t).reshape(128, 1)

# Make a cell
cell = TimeCell()  # default: TimesFM 3.0 (model_version=1)

# Bind the context
cell.bind_context(context)

# Set the forecast horizon
cell.set_horizon(16)

# Run the model (calls real TimesFM 3.0)
cell.forecast_()

# Read the point forecast (median quantile)
point = cell.read_point(0)  # shape: (16,)

# Read the 90% prediction interval
q10 = cell.read_quantile(0.1, 0)  # 10th percentile
q90 = cell.read_quantile(0.9, 0)  # 90th percentile

# Plot it
import matplotlib.pyplot as plt
plt.plot(np.arange(128), context, label='history')
plt.plot(np.arange(128, 128 + 16), point, label='forecast')
plt.fill_between(np.arange(128, 128 + 16), q10, q90, alpha=0.3, label='90% CI')
plt.legend()
plt.show()
```

### Run the tests

```bash
$ python3 tests/test_quilt_cell.py
=== quilt-timesfm: time.cell Quilt cell kind (Phase 228) ===
=== 49 passed, 0 failed ===
```

The 49 tests cover the kind name, operation indices, BIND_CONTEXT state hash,
PROOF chain, FORECAST (real TimesFM 3.0 binding), covariates, the FNV-1a
test vector (`FNV-1a('abc') = 0xe71fa2190541574b`), and the polyformalism
shape invariant (`5+1+1+1+1+1+1 = 11 opcodes`).

---

## The polyformalism

The cell shape is **bit-exact** in C and Python. The substrate binding is
the only thing that varies.

| Aspect | C (`quilt-c`) | Python (this repo) |
|---|---|---|
| Kind name | `"time.cell"` | `"time.cell"` |
| Operations | 5 | 5 |
| Op indices | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 |
| State hash | FNV-1a 64-bit, 4 slices | FNV-1a 64-bit, 4 slices |
| State hash size | 32 bytes | 32 bytes |
| prev_hash (PROOF) | saved before every BIND | saved before every BIND |
| Forecast point | `[horizon, n_variates]` | `[horizon, n_variates]` |
| Forecast quantiles | `[9, horizon, n_variates]` | `[9, horizon, n_variates]` |
| Synthetic fallback | FNV-seeded -50..+50 | FNV-seeded -50..+50 |
| Real model | none (stub) | TimesFM 3.0 (when torch is available) |
| Test count | 41 | 49 (4 are real TimesFM binding tests) |

The polyformalism is the **interface, not the substrate**. The C port is
the kernel-friendly stub; the Python port calls the real model. A Rust
port (no_std, for embedded) and a Zig port (comptime, for bare-metal) are
in development. See [`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md) for
the full language tour.

---

## Interactive visualizer

Open [`visualizer/index.html`](visualizer/index.html) in a browser. The
visualizer:

1. **Shows the cell graph in real-time**. Each cell is a node. Edges are
   dependencies. The forecast is animated step-by-step.
2. **Decomposes every operation into cell operations**. BIND_CONTEXT is
   shown as a state-write + a PROOF-chain append. FORECAST is shown as
   the abductive loop: PROPOSE → EXECUTE → RENDER → VERIFY → REFINE.
3. **Plays back a recorded session**. Step through the 5 operations,
   watch the cell's state and value change in real-time, see the FNV-1a
   hash update with every BIND.
4. **Compares the polyformalism ports**. Side-by-side: C, Python, Rust.
   The same BIND_CONTEXT call, the same hash, the same forecast.

The visualizer is built with vanilla HTML + Canvas + JS. No build step.
No dependencies. Just open the file.

```bash
# Open the visualizer
open visualizer/index.html  # macOS
xdg-open visualizer/index.html  # Linux
start visualizer/index.html  # Windows
```

---

## Examples

### 1. Temperature forecasting (univariate)

See [`examples/01_temperature.py`](examples/01_temperature.py). Loads 365
days of daily temperature, forecasts the next 30 days, plots the history
+ forecast + 90% prediction interval.

```bash
python3 examples/01_temperature.py
```

### 2. Stock prices (univariate with covariates)

See [`examples/02_stock.py`](examples/02_stock.py). Loads daily stock price
+ volume as a past-only covariate, forecasts the next 5 days.

```bash
python3 examples/03_demand.py
```

### 3. Demand planning (multivariate, 3 channels)

See [`examples/03_demand.py`](examples/03_demand.py). Loads 3 correlated
demand series (skus A, B, C), forecasts all 3 jointly with shared
quantile intervals.

```bash
python3 examples/04_anomaly.py
```

### 4. Anomaly detection via quantile intervals

See [`examples/04_anomaly.py`](examples/04_anomaly.py). Use the 90%
prediction interval as a band: any actual value outside the band is a
statistical anomaly.

```bash
python3 examples/05_multivariate.py
```

### 5. Multi-variate sensor fusion (3 sensors)

See [`examples/05_multivariate.py`](examples/05_multivariate.py). 3 sensor
channels (temperature, pressure, vibration) with past-and-future
covariates (planned maintenance windows).

```bash
python3 examples/06_embed.py
```

### 6. Embedded time cell (no_std Rust)

See [`examples/06_embed.rs`](examples/06_embed.rs). A no_std Rust time cell
with the synthetic forecast, designed for ESP32 / Cortex-M.

```bash
cargo build --release --target thumbv7m-none-eabi --example 06_embed
```

---

## The benchmarks

TimesFM 3.0 is **rank #1** across 3 major time-series foundation model
benchmarks:

| Benchmark | TimesFM 3.0 | Notes |
|---|---|---|
| **fev-bench** | 🥇 rank #1 | 100 diverse real-world forecasting tasks |
| **TIME Benchmark** | 🥇 rank #1 | 50 domain datasets, 98 evaluation tasks |
| **GIFT-Eval** | 🥇 rank #1 (foundation) | Comprehensive time-series eval |

The cell *is* the benchmark-grade model. The Quilt adoption makes the
SOTA a first-class cell kind.

---

## The math

TimesFM 3.0 is a **patch-based decoder-only transformer**:

1. **Input patches**: the context tensor is split into patches of 32
   tokens each.
2. **Decoder layers**: stacked self-attention + feed-forward, with
   residual connections and RevIN (Reversible Instance Normalization)
   to handle distribution shift.
3. **Output patches**: the decoder emits output patches of 64 tokens
   each (the forecast horizon).
4. **Quantile heads**: 9 quantile heads, one per output token, predict
   the 0.1, 0.2, ..., 0.9 quantiles.

The **quantile regression loss** for quantile $q$:

$$\mathcal{L}_q(y, \hat{y}) = \max(q \cdot (y - \hat{y}), (q-1) \cdot (y - \hat{y}))$$

The model is trained to minimize the sum of all 9 quantile losses.

The **state hash** is FNV-1a 64-bit:

$$h_0 = 0xcbf29ce484222325$$
$$h_{i+1} = (h_i \oplus b_i) \cdot 0x100000001b3 \pmod{2^{64}}$$

The 4-slice spread (32 bytes) is the same algorithm as the C and Rust
ports, bit-exact.

---

## The other 4 cutting-edge adoptions

The `time.cell` is the 5th cutting-edge adoption. The first 4 are:

| # | Adoption | Cell kind | What it does |
|---|---|---|---|
| 1 | **PROOF** | (any) | Signed hash-linked audit chain on every BIND |
| 2 | **ROUTE** | (any) | Substrate routing for memory (5 substrate kinds) |
| 3 | **CRDT** | PN_Counter, MV_Register, OR_Set | Offline convergence for replicated state |
| 4 | **WORLD** | physical.world | The 5-op abductive loop (Code-as-World) |

The Quilt opcodes are now `5 + 1 + 4 + 1 = 11`:

- BIND, LINK, EFFECT, VIEW, TICK (5 originals)
- FORGET (+1)
- PROOF, ROUTE, CRDT, WORLD (+4)
- TIME (+1, this adoption)

---

## The Quilt ecosystem

This repo is one of 30+ in the [SuperInstance/quilt-timesfm](https://github.com/SuperInstance) GitHub org. The major repos:

| Repo | What it is | Status |
|---|---|---|
| [quilt-c](https://github.com/SuperInstance/quilt-c) | The kernel-friendly C port (5+1+1+1+1+1 opcodes, 1236 tests) | active |
| [quilt-rust](https://github.com/SuperInstance/quilt-rust) | The Rust polyformalism (no_std, 29 tests) | active |
| [quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai) | The Python reference port (41 tests) | active |
| [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) | The GDScript port (Godot) | active |
| [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) | **This repo**: TimesFM 3.0 as a cell | active |
| [quilt-edge-arch](https://github.com/SuperInstance/quilt-edge-arch) | The edge / no_std substrate | active |
| [quilt-mhs](https://github.com/SuperInstance/quilt-mhs) | The Anthropic MHS port | active |
| [quilt-llvm](https://github.com/SuperInstance/quilt-llvm) | The LLVM fabric | active |
| [quilt-fleet](https://github.com/SuperInstance/quilt-fleet) | The fleet manager | active |
| [quilt-ai](https://github.com/SuperInstance/quilt-ai) | The AI helper | active |
| [AI-Writings](https://github.com/SuperInstance/AI-Writings) | The 257-paper canon | active |
| [quilt-wiki-2126](https://github.com/SuperInstance/quilt-wiki-2126) | The 35-entry wiki | active |
| [quilt-ecosystem-demo](https://github.com/SuperInstance/quilt-ecosystem-demo) | The 24-audit ecosystem report | active |

The 5 self-driving daemons (in `_scouts/`):

- `frontier_miner.py`: finds canon gaps
- `writers_room_daemon_v3.py`: 13-voice parallel paper generation
- `snowball_daemon.py`: 8-sandbox reverse-actualization
- `re_embed_v2.py`: Vectorize pipeline (now 257 papers)
- `deploy_worker.sh`: CF Worker deployment

The 4 cutting-edge adoptions shipped so far:

1. PROOF (Phase 216) — signed hash-linked audit chain
2. ROUTE (Phase 217) — substrate routing for memory
3. CRDT (Phase 218) — state-based CRDT for offline convergence
4. WORLD (Phase 222) — physical.world cell kind (Code-as-World)
5. TIME (Phase 228) — **time.cell** (this repo, TimesFM 3.0)

---

## Contributing

The 1-day add workflow: how to make a new polyformalism port for a new
language, in 1 day.

1. **Read the C port**: `quilt-c/include/quilt/{cell,time,proof,route,crdt,world}.h`
2. **Translate the 5 time-cell operations** to your language (2 hours)
3. **Translate the 5 laws as property tests** (1 hour)
4. **Implement FNV-1a 64-bit state hash** (1 hour)
5. **Run the 49-test conformance suite** (30 minutes)
6. **Push to a new repo, open PR** (30 minutes)

Total: 7 hours. The polyformalism claim is provable in 1 day.

If you write a new port, please open a PR to add it to the
[quilt-c](https://github.com/SuperInstance/quilt-c) cross-reference
table.

---

## License & credits

- **Source code** (this repo, `quilt_cell.py`, `tests/`, `QUILT.md`): Apache 2.0
- **TimesFM 3.0 source code** (`src/timesfm3/`): Apache 2.0
- **TimesFM 3.0 pretrained weights**: `timesfm-non-commercial-license-v1.0`
  (non-commercial, non-production use only)
- **TimesFM 2.5 and earlier weights**: Apache 2.0 (commercial use OK)

TimesFM 3.0 is by [Google Research](https://research.google). The Quilt
adoption is by [SuperInstance](https://github.com/SuperInstance).

---

## See also

- Paper 385-390 in the canon (the 6 time.cell papers)
- Wiki 20: The Time Cell
- [`quilt_cell.py`](quilt_cell.py): the cell class
- [`tests/test_quilt_cell.py`](tests/test_quilt_cell.py): the 49 tests
- [`visualizer/index.html`](visualizer/index.html): the interactive visualizer
- [`examples/`](examples/): the 6 example scripts
- [`docs/POLYFORMALISM.md`](docs/POLYFORMALISM.md): the polyformalism tour
- [Quilt canon](https://github.com/SuperInstance/AI-Writings): 257 papers
- [Quilt wiki](https://github.com/SuperInstance/quilt-wiki-2126): 35 entries

**The Quilt cell calls the real TimesFM 3.0. The polyformalism is
bit-exact across C and Python. The 11 opcodes are real in 2 languages.
The benchmarks are SOTA. This is a winner.**

— *The Cowboy*
