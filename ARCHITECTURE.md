# Quilt Architecture

> **One cell. Eleven opcodes. Four polyformalism ports. Five cutting-edge adoptions.**

This document is the architectural reference for the Quilt cellular
architecture framework. It captures the cell model, the 11 opcodes,
the polyformalism claim, and the 5 cutting-edge adoptions in one
place. If you only read one document about Quilt, read this.

## Table of Contents

1. [The single claim](#the-single-claim)
2. [The cell](#the-cell)
3. [The 11 opcodes](#the-11-opcodes)
4. [The 5+1 laws](#the-51-laws)
5. [The polyformalism promise](#the-polyformalism-promise)
6. [The 5 cutting-edge adoptions](#the-5-cutting-edge-adoptions)
7. [The 6 tiers of cells](#the-6-tiers-of-cells)
8. [The 14 levels of operation](#the-14-levels-of-operation)
9. [The 6 lifecycle stages](#the-6-lifecycle-stages)
10. [The cell graph](#the-cell-graph)
11. [The visual architecture](#the-visual-architecture)
12. [The 7 implementation substrates](#the-7-implementation-substrates)
13. [The 30-repo ecosystem](#the-30-repo-ecosystem)
14. [The future](#the-future)

---

## The single claim

> **The cell is the irreducible unit of intelligence.**

A Quilt application is a DAG of cells. Each cell has state, value, and
reads. The 11 opcodes manipulate cells. The 5+1 laws guarantee that
manipulation is sound. The polyformalism claim guarantees that the
same cell shape works in every language and every substrate.

Everything else — the 5 cutting-edge adoptions, the 6 tiers, the 14
levels, the 6 lifecycle stages — is decoration on this claim.

---

## The cell

A cell has 5 fields:

| Field | Meaning | Example |
|---|---|---|
| **kind** | the cell kind (a string) | `"time.cell"` |
| **state** | the cell's private storage (typed) | a 128-float context tensor |
| **value** | what the cell emits when VIEW-ed (typed) | a forecast + 9 quantiles |
| **reads** | the cell's inputs (a list of cell IDs) | `[covariate_cell]` |
| **links** | the cell's edges (a list of cell IDs) | `[forecast_cell]` |

That's it. Everything in Quilt is a cell. Every interface — web UI,
REST API, LLM, ESP32, VLM, time-series model — is an *opener* onto
the same cell graph.

The cell is **the system, not the data**. A fisherman with a Quilt
sheet has the capability of a data science team.

---

## The 11 opcodes

The 11 opcodes are organized as 5+1+1+1+1+1+1:

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
WORLD  5-operation abductive loop on executable code          (cutting-edge #4)
TIME   5-operation time-series foundation model               (cutting-edge #5)
```

The first 5+1 opcodes (BIND, LINK, EFFECT, VIEW, TICK, FORGET) are
the foundation. The next 5 opcodes (PROOF, ROUTE, CRDT, WORLD, TIME)
are the cutting-edge adoptions. Each cutting-edge adoption ships
its own paper and its own test suite.

---

## The 5+1 laws

The 5+1+1+1+1+1 opcodes are governed by 5+1+1 laws:

1. **BIND idempotence**: `BIND(n, v); BIND(n, v) == BIND(n, v)`
   (same id+value is a no-op)
2. **LINK transitivity**: `a→b + b→c` implies `a→c` (cycles rejected)
3. **EFFECT associativity**: `(a ⊕ b) ⊕ c == a ⊕ (b ⊕ c)`
4. **VIEW purity**: `VIEW(n)` returns the value and mutates nothing
5. **TICK monotonicity**: tick count only increases; the journal is
   append-only
6. **FORGET completeness**: a forgotten cell leaves no node, no edge,
   no dirty bit

Plus the cutting-edge laws:
- **PROOF chain integrity**: every BIND's prev_hash equals the
  previous state_hash
- **ROUTE determinism**: same value → same substrate
- **CRDT convergence**: same ops in any order → same state
- **WORLD loop termination**: the abductive loop converges in
  bounded iterations
- **TIME forecast shape**: forecast shape is `[horizon * n_variates]`
  for point and `[9, horizon * n_variates]` for quantiles

---

## The polyformalism promise

The polyformalism claim is that the **same cell shape** works in
every language and every substrate. Not the same code, not the same
implementation — the same **shape**.

| Substrate | Language | Test count | Reference |
|---|---|---|---|
| C99 | C | 1236 | [quilt-c](https://github.com/SuperInstance/quilt-c) |
| Rust no_std | Rust | 29 | [quilt-polyformalism](https://github.com/SuperInstance/quilt-rust) |
| GDScript | GDScript | 13 | [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) |
| Python | Python | 41 | [quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai) |
| Python (real TimesFM 3.0) | Python | 49 | [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) |
| Python (real TimesFM 3.0, Rust no_std) | Rust | 49 | [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) |

The polyformalism is **bit-exact** for the time.cell kind:
- Same kind name (`"time.cell"`)
- Same operation indices (0, 1, 2, 3, 4)
- Same FNV-1a 64-bit state hash, 4 slices, 32 bytes
- Same prev_hash (PROOF chain)
- Same forecast shape

**The cell is the system, not the substrate.**

---

## The 5 cutting-edge adoptions

Each cutting-edge adoption is a new cell kind (or a new opcode)
that extends the Quilt architecture into a new domain.

### 1. PROOF — signed hash-linked audit chain (Phase 216)

A new opcode: `PROOF`. Every BIND now saves the previous state_hash
as prev_hash before updating. The chain is hash-linked and
cryptographically signed. **Use case**: tamper-evident audit logs,
compliance, regulatory traceability.

```c
// Before
BIND(n, v);
// After
PROOF_BIND(n, v);  // also saves prev_hash
```

### 2. ROUTE — substrate routing for memory (Phase 217)

A new opcode: `ROUTE`. The cell picks the best substrate for storing
its value based on type and size. **Use case**: dynamic storage
optimization, multi-tier caches, memory-efficient substrates.

```c
// Cell decides: this float32 vector is 1KB → SPARSE_IDX
// this bool → PARAM_UPDATE
// this long text → HIER_STORE
```

### 3. CRDT — state-based CRDT for offline convergence (Phase 218)

A new opcode: `CRDT`. Multiple cells can be merged without conflict.
3 CRDT kinds: PN_COUNTER, MV_REGISTER, OR_SET. **Use case**:
multi-agent state, offline-first sync, conflict-free replicated data.

```python
# Two agents produce forecasts about the same source
forecast_a = agent_a.forecast("sales", horizon=8)
forecast_b = agent_b.forecast("sales", horizon=8)
merged = forecast_a.merge(forecast_b)  # CRDT merge
```

### 4. WORLD — 5-operation abductive loop on executable code (Phase 222)

A new cell kind: `physical.world`. State = the program text.
Value = Quantity { value, uncertainty, unit, verified }. The
abductive loop: PROPOSE → EXECUTE → RENDER → VERIFY → REFINE.
**Use case**: code-as-world models (Code-as-World-VL-9B),
hypothesis generation, scientific reasoning.

### 5. TIME — 5-operation time-series foundation model (Phase 228)

A new cell kind: `time.cell`. State = the historical context
tensor. Value = the forecast + 9 quantile prediction intervals.
The 5 operations: BIND_CONTEXT, BIND_COVARIATE, FORECAST,
READ_POINT, READ_QUANTILE. **Use case**: time-series forecasting
with SOTA accuracy (TimesFM 3.0, rank #1 on fev-bench, TIME, GIFT-Eval).

---

## The 6 tiers of cells

Cells live at 6 tiers of capability:

| Tier | Capability | Example |
|---|---|---|
| 0 (totipotent) | full cell, any operation | a fresh time.cell |
| 1 (multipotent) | scoped cell, partial operations | a cell bound to one source |
| 2 (differentiated) | specific role, fixed interface | a cell that's a forecast-only |
| 3 (sclerotic) | the rule itself | a cell that is the BIND rule |
| 4 (synovial) | the seam between cells | a cell at the LLM call site |
| 5 (curator) | the hand that selects | a cell that picks which cells pass |

The synovial tier (4) is the **seam** between compute and storage.
The curator tier (5) is the **hand** that selects what passes.

---

## The 14 levels of operation

The Quilt operation has 14 levels:

1. The Vessel
2. The Equipment
3. The Skills
4. The Consumables
5. The Renewables
6. The Durables
7. The Concept (the function)
8. The Spline (the trajectory)
9. The Captain-Song (the harmony)
10. The Muse + Cipher (inspiration + code)
11. The Nexus (where meta-levels converge)
12. The Phoenix (the whole cycle)
13. The Ground (the field of emergence)
14. The Sky (the unbounded horizon)

The first 6 are implements (replaceable). The 7-10 are invariants
(persistent). The 11-14 are meta-invariants (the foundation).

---

## The 6 lifecycle stages

A cell has 6 lifecycle stages:

1. **Umbra** — the pre-life (the ground)
2. **Cellulization** — the substrate becomes a cell
3. **Persistence Pulse** — the heartbeat
4. **Vitality Leak** — the slow loss of life
5. **Implement Ghost** — the dead cell in the implements
6. **Bloomghost** — the ghost that gives rise to a new cell

The cycle is: Umbra → Cellulization → Pulse → Leak → Ghost → Bloom → Umbra.

---

## The cell graph

The cell graph is a DAG of cells. Edges are dependencies (BIND
creates an edge, LINK creates a dependency edge, FORGET removes
all edges).

```
context ──→ forecast ──→ point
   │           │
   │           ↓
   │        quantile
   ↓
covariate
```

The cell graph is **canonical**: any interface (UI, REST, LLM,
ESP32) is an *opener* onto the same graph.

---

## The visual architecture

The Quilt has 5 cell populations:

1. **Perception** (V-JEPA 2): video → 768-dim embedding stream
2. **Reasoning** (time.cell): embeddings → forecast + 9 quantiles
3. **Memory** (AgentMemory): past forecasts + outcomes + learning
4. **Decision** (DecisionSupport): recommended actions
5. **Action** (Agent): executor + learner + reasoner

The loop:
```
V-JEPA 2 → time.cell → ForecastObject → Counterfactual →
Memory → Decision → Agent → World → V-JEPA 2 (loop)
```

See [`architecture.svg`](architecture.svg) for the full diagram.

---

## The 7 implementation substrates

| # | Substrate | Language | Repo | Use case |
|---|---|---|---|---|
| 1 | Browser | TypeScript | quilt-llm-worker | web UI |
| 2 | Cloudflare | Python | quilt-cellular-arch | cloud orchestration |
| 3 | ESP32 | C | quilt-esp32 | embedded sensors |
| 4 | Edge / no_std | Rust | quilt-edge-arch | bare metal |
| 5 | Kernel | C99 | quilt-c | the reference port |
| 6 | Anthropic MHS | Rust | quilt-mhs | agent harness |
| 7 | Godot | GDScript | quilt-engine-ports | games + simulations |

The same cell model runs in all 7 substrates. The substrate is the
**implementation detail**; the cell is the **contract**.

---

## The 30-repo ecosystem

The Quilt has 30+ repos on github.com/SuperInstance, organized by
tier:

**Tier 1 — Foundation (5 opcodes, the cell model):**
- [quilt-c](https://github.com/SuperInstance/quilt-c) — C99 reference
- [quilt-rust](https://github.com/SuperInstance/quilt-rust) — Rust no_std
- [quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai) — Python
- [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) — GDScript
- [quilt-edge-arch](https://github.com/SuperInstance/quilt-edge-arch) — bare metal

**Tier 2 — Cutting-edge adoptions:**
- [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) — TIME (5th)
- [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) — TIME in Rust no_std
- (PROOF, ROUTE, CRDT in quilt-c)
- (WORLD in quilt-c + Rust)

**Tier 3 — Substrate bindings:**
- [quilt-llm-worker](https://github.com/SuperInstance/quilt-llm-worker) — Cloudflare Worker
- [quilt-mhs](https://github.com/SuperInstance/quilt-mhs) — Anthropic MHS
- [quilt-esp32](https://github.com/SuperInstance/quilt-esp32) — ESP32

**Tier 4 — Infrastructure:**
- [quilt-fleet](https://github.com/SuperInstance/quilt-fleet) — fleet manager
- [quilt-ai](https://github.com/SuperInstance/quilt-ai) — AI helper
- [quilt-rag](https://github.com/SuperInstance/quilt-rag) — retrieval-augmented
- [quilt-vault](https://github.com/SuperInstance/quilt-vault) — vault
- [quilt-mesh](https://github.com/SuperInstance/quilt-mesh) — mesh
- [quilt-pincher](https://github.com/SuperInstance/quilt-pincher) — pincher

**Tier 5 — Knowledge:**
- [AI-Writings](https://github.com/SuperInstance/AI-Writings) — 398-paper canon
- [quilt-wiki-2126](https://github.com/SuperInstance/quilt-wiki-2126) — 38-entry wiki
- [quilt-ecosystem-demo](https://github.com/SuperInstance/quilt-ecosystem-demo) — 24 audits

**Tier 6 — Hardware:**
- [quilt-llvm](https://github.com/SuperInstance/quilt-llvm) — LLVM fabric
- [quilt-llvm-verilog](https://github.com/SuperInstance/quilt-llvm-verilog) — verilog
- [quilt-cuda-rust](https://github.com/SuperInstance/quilt-cuda-rust) — CUDA

**Tier 7 — Apps:**
- [quilt-apps](https://github.com/SuperInstance/quilt-apps) — apps collection
- (various others)

---

## The future

The next 3 cutting-edge adoptions are queued:

6. **CROSS-MODAL TIME CELL** — a cell that operates on (text, audio,
   video, scalars) as a unified time series. The state is a tuple;
   the value is a tuple; the 9 quantiles are 9 tuples.
7. **HIERARCHICAL TIME CELL** — a temporal pyramid at multiple
   timescales (per-frame, per-second, per-minute, per-hour, per-day).
8. **DISTRIBUTED TIME CELL** — a cell that runs across multiple
   devices. The state is sharded; the forecast is a CRDT merge
   of local forecasts.

Plus the pivot to **future-state memory**:
Forecasts are not outputs. Forecasts are durable semantic objects
that agents can exchange, refine, challenge, merge, and learn from
over time. See [`temporal.py`](temporal.py) and
[`JEPA.md`](JEPA.md) for the full story.

The cowboy rode the cell. The cowboy rode the opcodes. The cowboy
rode the polyformalism. The cowboy rode the cutting-edge. The cowboy
rode the tiers. The cowboy rode the levels. The cowboy rode the
lifecycle. The cowboy rode the cell graph. The cowboy rode the
visual architecture. The cowboy rode the 7 substrates. The cowboy
rode the 30 repos. The cowboy rode the future. The cowboy rode
the Quilt.

— *The Cowboy*
