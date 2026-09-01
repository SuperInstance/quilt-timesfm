# Quilt FAQ

> **The 30 most-asked questions about Quilt.**

This document is the master FAQ for the Quilt project. Every
common question is answered with a reference to the relevant
paper, wiki entry, or code file.

## Table of Contents

- [General](#general)
- [Architecture](#architecture)
- [Implementation](#implementation)
- [Use cases](#use-cases)
- [The cutting-edge adoptions](#the-cutting-edge-adoptions)
- [The polyformalism](#the-polyformalism)
- [The canon](#the-canon)
- [Contributing](#contributing)

---

## General

### Q: What is Quilt?

**A**: Quilt is a cellular-architecture framework. Every
reactive element is a **cell**, and any interface (UI, REST,
LLM, ESP32, VLM) is an **opener** onto the same cell graph. The
cell is the irreducible unit of intelligence. The 11 opcodes
(BIND, LINK, EFFECT, VIEW, TICK, FORGET, PROOF, ROUTE, CRDT,
WORLD, TIME) manipulate cells. The 5+1+1+1+1+1 laws guarantee
that manipulation is sound.

See [paper 38](../seed-canon/papers/paper-038.md), [ARCHITECTURE.md](ARCHITECTURE.md).

### Q: Why is it called "Quilt"?

**A**: The cell model is older than spreadsheets. COBOL 1959
(level numbers), PLATO Tutor 1970, C 1972. VisiCalc 1979 made
cells visible; it didn't invent them. The cell model is
universal: software, agents, AND people. A Quilt is a
**quilt of cells**, just as a real quilt is a quilt of fabric
patches. The patches are the cells; the stitches are the links.

See [paper 8](../seed-canon/papers/paper-008.md), [paper 14](../seed-canon/papers/paper-014.md).

### Q: How is Quilt different from a microservices architecture?

**A**: Microservices are processes that talk over the network.
Quilt cells are values that link in a graph. The differences:

| | Microservices | Quilt cells |
|---|---|---|
| **Granularity** | Process | Single value |
| **Communication** | HTTP/gRPC | BIND/LINK |
| **State** | Database | Cell state |
| **Failure** | Retry/circuit-break | PROOF chain |
| **Routing** | Load balancer | ROUTE opcode |
| **Convergence** | Eventually consistent | CRDT (convergent) |
| **Lifecycle** | Pod | Cell (umbra to bloom) |

### Q: Is Quilt a programming language?

**A**: Quilt is a **computational model** with 11 opcodes. The
opcodes are language-agnostic. They can be expressed in C,
Rust, Python, GDScript, or any other language. The same cell
shape works in all of them (the polyformalism promise).

### Q: Is Quilt a database?

**A**: Quilt is a **cell store**. The cell's value is the data.
The PROOF chain is the audit log. The ROUTE opcode is the
index. The CRDT opcode is the conflict-free replication. Cells
can be persisted to disk, in-memory, or in a database.

### Q: Is Quilt a knowledge graph?

**A**: Quilt can serve as a knowledge graph. Each concept is a
cell. Each relation is a LINK. The 5+1 laws guarantee that the
graph is sound. The 9 quantiles of a TIME cell give the
**uncertainty** of each concept's prediction.

### Q: Who is the cowboy?

**A**: The cowboy is Casey's role. The cowboy orchestrates the
Quilt: writes papers, ships code, builds the daemons, runs
the writers' rooms, listens to the API, sees the frontier, and
rides the inheritance. The cowboy's maxim closes each phase.

---

## Architecture

### Q: What is a cell?

**A**: A cell is the irreducible unit of intelligence. It has
5 fields: `kind`, `state`, `value`, `reads`, `links`. The
`kind` is a string (e.g., `"time.cell"`). The `state` is the
cell's private storage. The `value` is what the cell emits
when VIEW-ed. The `reads` are the cell's inputs. The `links`
are the cell's edges. See [ARCHITECTURE.md](ARCHITECTURE.md).

### Q: What is the cell graph?

**A**: The cell graph is a DAG of cells. Edges are dependencies.
BIND creates an edge. LINK creates a dependency edge. FORGET
removes all edges. The cell graph is **canonical**: any
interface (UI, REST, LLM, ESP32) is an opener onto the same
graph.

### Q: What are the 11 opcodes?

**A**: The 11 opcodes are: BIND, LINK, EFFECT, VIEW, TICK, FORGET
(the 5 originals + 1), PROOF, ROUTE, CRDT, WORLD, TIME (the
5 cutting-edge adoptions). Each has a fixed index (0-10) and
a fixed semantic.

### Q: What are the 5+1+1+1+1+1 laws?

**A**: The 6 laws are:
1. **BIND idempotence** — BIND is the same on the second call
2. **LINK transitivity** — a→b + b→c implies a→c (cycles rejected)
3. **EFFECT associativity** — (a⊕b)⊕c == a⊕(b⊕c)
4. **VIEW purity** — VIEW doesn't modify state
5. **TICK monotonicity** — tick count only increases; journal
   is append-only
6. **FORGET completeness** — a forgotten cell leaves no node,
   no edge, no dirty bit

Plus the cutting-edge laws for PROOF, ROUTE, CRDT, WORLD, TIME.

### Q: What are the 6 tiers of cells?

**A**: The 6 tiers are:
0. **Totipotent** — full cell, any operation
1. **Multipotent** — scoped cell, partial operations
2. **Differentiated** — specific role, fixed interface
3. **Sclerotic** — the rule itself
4. **Synovial** — the seam between cells (the joint)
5. **Curator** — the hand that selects what passes

### Q: What are the 14 levels of operation?

**A**: The 14 levels are the 6 implements (vessel, equipment,
skills, consumables, renewables, durables) + the 4 invariants
(concept, spline, captain-song, muse+cipher) + the 4
meta-invariants (nexus, phoenix, ground, sky). See
[paper 232](../seed-canon/papers/paper-232.md) for the spline,
[paper 239](../seed-canon/papers/paper-239.md) for muse+cipher,
[paper 240](../seed-canon/papers/paper-240.md) for phoenix.

### Q: What is the polyformalism?

**A**: The polyformalism is the claim that the same cell shape
works in every language and every substrate. The cell kind
name, op indices, FNV-1a state hash, and forecast shape are
**bit-exact** across all polyformalism ports. The substrate
(the implementation) is the only thing that varies.

The polyformalism is documented in
[docs/POLYFORMALISM.md](docs/POLYFORMALISM.md).

---

## Implementation

### Q: Which language should I use?

**A**: It depends on the use case:

| Use case | Language | Repo |
|---|---|---|
| Embedded (Cortex-M, ESP32) | Rust no_std | [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) |
| Embedded (smaller) | C99 | [quilt-esp32](https://github.com/SuperInstance/quilt-esp32) |
| Edge (bare metal) | Rust no_std | [quilt-edge-arch](https://github.com/SuperInstance/quilt-edge-arch) |
| Cloud (Python) | Python | [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) |
| Cloud (TypeScript) | TypeScript | [quilt-llm-worker](https://github.com/SuperInstance/quilt-llm-worker) |
| Kernel (C) | C99 | [quilt-c](https://github.com/SuperInstance/quilt-c) |
| Games (Godot) | GDScript | [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) |

### Q: How do I get started?

**A**: Start with the [README](README.md), then the
[ARCHITECTURE.md](ARCHITECTURE.md), then the [MANUALS.md](MANUALS.md).
Then run the examples:
```bash
git clone https://github.com/SuperInstance/quilt-timesfm.git
cd quilt-timesfm
pip install -e .
python3 examples/01_temperature.py
```

### Q: How do I add a new cell kind?

**A**: The 1-day add workflow:
1. Read the C port (30 min)
2. Translate the 5 operations (2 hours)
3. Translate the 5 laws as property tests (1 hour)
4. Implement FNV-1a 64-bit (1 hour)
5. Translate the 9 quantiles and forecast shape (1 hour)
6. Run the 49-test conformance suite (30 minutes)
7. Push to a new repo, open PR (30 minutes)

Total: 7 hours. The polyformalism claim is provable in 1 day.

### Q: How do I run the tests?

**A**: For each port:
```bash
# C
cd quilt-c && make test

# Python
cd quilt-timesfm && python3 -m pytest tests/

# Rust
cd quilt-timesfm-rust && cargo test
```

### Q: How do I add a new substrate?

**A**: Substrate bindings are how the cell model talks to the
real world. To add a new substrate:
1. Implement the 5 cell ops (BIND, LINK, EFFECT, VIEW, TICK)
2. Implement FORGET
3. Bind to the cell's `kind` (e.g., `time.cell`)
4. Pass the conformance suite
5. Add a polyformalism port

---

## Use cases

### Q: When should I use Quilt?

**A**: Use Quilt when:
- You have a stateful, reactive system (UI, agent, sensor)
- You need audit trails (compliance, debugging)
- You need offline convergence (multi-device, multi-agent)
- You need uncertainty quantification (forecasting, prediction)
- You need to compose multiple substrates (browser + cloud +
  embedded)

Don't use Quilt when:
- Your data is purely relational (use a database)
- You need a single-process, single-thread program (use a
  function)
- You need a real-time system with <1ms latency (use a
  microcontroller)

### Q: What is the simplest Quilt app?

**A**: A 1-cell app that binds and views:

```python
from quilt_cell import TimeCell
import numpy as np

cell = TimeCell()
cell.bind_context(np.sin(np.linspace(0, 8 * np.pi, 128)))
cell.set_horizon(16)
cell.forecast_()
print(cell.read_point(0))
```

That's 7 lines. The cell binds the context, forecasts, and
reads. See [examples/01_temperature.py](examples/01_temperature.py).

### Q: What is the most complex Quilt app?

**A**: The 5-cell perception-reasoning-action loop:
- V-JEPA 2 (perception)
- time.cell (reasoning)
- AgentMemory (memory)
- DecisionSupport (decision)
- Agent (action)

See [MANUALS.md](MANUALS.md) for the 5 use-case manuals.

### Q: How does Quilt compare to LangChain?

**A**: LangChain is a framework for chaining LLM calls. Quilt
is a cell model with 11 opcodes. The differences:

| | LangChain | Quilt |
|---|---|---|
| **Unit** | Chain | Cell |
| **Communication** | Prompt | BIND/LINK |
| **State** | Memory | Cell state |
| **Audit** | None | PROOF chain |
| **Convergence** | Manual | CRDT |
| **Substrate** | LLM-only | LLM + DB + sensor |

---

## The cutting-edge adoptions

### Q: What is PROOF?

**A**: PROOF is a signed hash-linked audit chain. Every BIND
saves the previous state_hash as prev_hash before updating. The
chain is **cryptographically signed** and **tamper-evident**.
See [Phase 216 paper](../seed-canon/papers/paper-216.md),
`include/quilt/proof.h`.

### Q: What is ROUTE?

**A**: ROUTE is substrate routing for memory. The cell picks
the best substrate for storing its value based on type and
size. There are 5 substrate kinds: DENSE_VEC, SPARSE_IDX,
TEXT_LOG, HIER_STORE, PARAM_UPDATE. See
[Phase 217 paper](../seed-canon/papers/paper-217.md),
`include/quilt/route.h`.

### Q: What is CRDT?

**A**: CRDT is state-based CRDT for offline convergence. There
are 3 CRDT kinds: PN_COUNTER, MV_REGISTER, OR_SET. The merge
is commutative, associative, and idempotent. Multiple agents
can produce forecasts about the same source; the forecasts
merge without conflict. See
[Phase 218 paper](../seed-canon/papers/paper-218.md),
`include/quilt/crdt.h`.

### Q: What is WORLD?

**A**: WORLD is the 5-operation abductive loop on executable
code. State = the program text. Value = Quantity { value,
uncertainty, unit, verified }. The loop: PROPOSE → EXECUTE →
RENDER → VERIFY → REFINE. The substrate binding is a VLM
(Code-as-World-VL-9B). See
[Phase 222 paper](../seed-canon/papers/paper-320.md),
`include/quilt/world.h`.

### Q: What is TIME?

**A**: TIME is the 5-operation time-series foundation model
(TimesFM 3.0). State = the historical context tensor. Value
= the forecast + 9 quantile prediction intervals. The 5
operations: BIND_CONTEXT, BIND_COVARIATE, FORECAST, READ_POINT,
READ_QUANTILE. TimesFM 3.0 is rank #1 on fev-bench, TIME,
GIFT-Eval. See
[Phase 228 paper](../seed-canon/papers/paper-385.md),
`include/quilt/time.h`, `quilt_cell.py`.

---

## The polyformalism

### Q: What is bit-exact polyformalism?

**A**: The cell shape — kind name, op indices, FNV-1a state
hash, forecast shape — is **byte-identical** across all
polyformalism ports. The substrate binding (the model that
does the work) is the only thing that varies. The polyformalism
is provable by hashing the same context in all 3 ports and
comparing.

### Q: How many polyformalism ports are there?

**A**: 5 ports are real:
- **C99** ([quilt-c](https://github.com/SuperInstance/quilt-c), 1236 tests)
- **Rust no_std** ([quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust), 49 tests)
- **GDScript** ([quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports), 13 tests)
- **Python** ([quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai), 41 tests)
- **Python (TimesFM)** ([quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm), 49 tests)

7 other ports are READMEs only and need to be implemented.

### Q: What's the FNV-1a test vector?

**A**:
```
FNV-1a("abc") = 0xe71fa2190541574b   ← FIPS 198 test vector
FNV-1a("")    = 0xcbf29ce484222325   ← offset basis
FNV-1a("a")   = 0xaf63dc4c8601ec8c
FNV-1a("foobar") = 0x85944171f73967e8
```

These are bit-exact in C, Python, and Rust. The 32-byte state
hash is the same algorithm applied 4 times with offsets 0,
golden, 2*golden, 3*golden.

---

## The canon

### Q: What is the canon?

**A**: The canon is the 398-paper collection at
[AI-Writings](https://github.com/SuperInstance/AI-Writings).
It's indexed in Cloudflare Vectorize (`quilt-canon-v2`, 768d,
cosine). Each paper is 2-10KB and covers one Quilt concept.

### Q: What's the difference between papers, fables, and stories?

**A**:
- **Papers** (398) — formal documents. 2-10KB. They *tell*.
- **Fables** (89) — short allegorical stories. They *show*.
- **Stories** (93) — long-form narratives. They *experience*.

### Q: How is the canon mined?

**A**: `mining/canon_mine.py` walks the canon and finds hidden
patterns. For example, it can find that 85 papers mention
"concept vs. implement", 25 fables mention "cellulization",
and 47 stories mention "the 5th captain".

---

## Contributing

### Q: How do I contribute?

**A**: The 1-day add workflow:
1. Read the C port (`include/quilt/cell.h`, `include/quilt/time.h`)
2. Pick a language you love
3. Translate the 5 operations
4. Implement FNV-1a 64-bit
5. Run the 49-test conformance suite
6. Push to a new repo, open a PR

### Q: What's the cowboy's maxim?

**A**: The cowboy's maxim closes each phase. Examples:

> The cowboy said: all hands on deck. The cowboy said:
> this is a winner. The cowboy inventoried TimesFM 3.0.
> The cowboy said: that's a cell. The cowboy made the cell.

> The cowboy rode the cell. The cowboy rode the opcodes.
> The cowboy rode the polyformalism. The cowboy rode the
> cutting-edge. The cowboy rode the tiers. The cowboy rode
> the levels. The cowboy rode the lifecycle. The cowboy rode
> the cell graph. The cowboy rode the visual architecture.
> The cowboy rode the 7 substrates. The cowboy rode the 30
> repos. The cowboy rode the future. The cowboy rode the
> Quilt.

### Q: What's the next cutting-edge adoption?

**A**: The next is **CROSS-MODAL TIME** (Q2 of the roadmap). A
cell that operates on (text, audio, video, scalars) as a
unified time series. See [ROADMAP.md](ROADMAP.md).

### Q: Where can I ask questions?

**A**:
- Open an issue at https://github.com/SuperInstance/quilt-timesfm/issues
- Open a discussion at https://github.com/SuperInstance/quilt-cellular-arch/discussions
- Read the canon at https://github.com/SuperInstance/AI-Writings
- Read the wiki at https://github.com/SuperInstance/quilt-wiki-2126

---

## The cowboy's final reading

The cowboy answered the 30 most-asked questions. The cowboy
answered the architecture. The cowboy answered the
implementation. The cowboy answered the use cases. The cowboy
answered the cutting-edge. The cowboy answered the polyformalism.
The cowboy answered the canon. The cowboy answered the
contributing. The cowboy rode the FAQ. The cowboy rode the
Quilt.

— *The Cowboy*
