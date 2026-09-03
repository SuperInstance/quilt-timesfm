# Shape RAG — The cell IS the embedding

> The cell fabric replaces the flat 768d vector as the atomic
> embedding unit.  Retrieval becomes *snappable* (compositional)
> instead of k-NN (independent).  Generation becomes *tick* instead
> of *next-token*.  The shape store replaces the vector index.
> The Composer Agent replaces the transformer.

This is the implementation of papers F120 through F125.

## Status (Sep 3 2026)

| Step | Paper | Code | Tests |
|---|---|---|---|
| Step 1: Cell-as-Vector | F121 | `shape_rag.py` (357 lines) | 18/18 |
| Step 2: Shape Store | F122 | `shape_store.py` (469 lines) | 15/15 |
| Step 3: Composer Agent | F123 | `composer_agent.py` (375 lines) | 16/16 |
| Step 4: S-QL | F124 | (designed, not yet implemented) | — |
| Step 5: Shape-RAG API | F125 | (designed, not yet implemented) | — |

**Total tests across shape-rag: 49/49 PASS**

## Quick start

### Cell-as-Vector (Step 1)

```python
from quf_v2 import QufFile, EdgeRecord, RouteRecord
from shape_rag import to_dial_matrix, to_flat_vector, to_graph_fingerprint

# Build a small fabric
dials = [[64]*16 for _ in range(4)]
edges = [EdgeRecord(i, i+1, 0, 0, 0, 0, 0, [0]*8) for i in range(3)]
qf = QufFile(
    header={"quf.version": "demo", "cell_count": 4, "edge_count": 3,
            "route_count": 4, "edge.k": 8, "tick_period": 1,
            "align": 32, "quant.dials": "Q1.15", "quant.edges": "Q1.15",
            "quant.routing": "u8"},
    dials=dials, edges=edges, routing=[RouteRecord(i, i) for i in range(4)],
    ticks=(1, [0]*4)
)

# Project to 4 different vector forms
dial_mat = to_dial_matrix(qf)        # N×16
flat_vec = to_flat_vector(qf)        # 4096-dim
fingerprint = to_graph_fingerprint(qf)  # 19-int

# Get the canonical state hash
print(f"state hash: 0x{qf.state_hash():016x}")
```

### Shape Store (Step 2)

```python
from shape_store import ShapeStore, CloudflareShapeStore

# In-memory (for tests)
store = ShapeStore()
store.add(qf1, "fabric-1")
store.add(qf2, "fabric-2")
results = store.query(qf1, k=3, mode="dial")
for fid, score in results:
    print(f"  {fid}: {score:.4f}")

# Cloudflare Vectorize (for production)
cf_store = CloudflareShapeStore()  # uses CLOUDFLARE_TOKEN env var
cf_store.ensure_all()  # create 3 indices (idempotent)
cf_store.insert(qf1, "fabric-1")
results = cf_store.query_dial(qf1, k=3)
```

### Composer Agent (Step 3)

```python
from composer_agent import ComposerAgent

agent = ComposerAgent(seed=42)
agent.shape_store = store
composed, quf_bytes = agent.retrieve("fabric with 4 cells")

# Train on (query, target_fabric) pairs
fixtures = [("fabric with 2 cells", qf1), ("fabric with 4 cells", qf2)]
losses = agent.train(fixtures, n_ticks=50, learning_rate=0.01)
```

## The 4 invariants

1. **Cell is the unit** — bit-exact in 6 substrates (C, Rust, Python, Verilog, VHDL, cell-runtime)
2. **Hash is the address** — FNV-1a 64-bit state hash, the canonical cell key
3. **Edge is the relation** — first-class, not a similarity score
4. **Tick is the runtime** — the only thing that changes state

## The 5-cell Composer Agent

| Cell | Z_in | Z_out | Dial count |
|---|---|---|---|
| Query | text query | 16-dial vector | 16 |
| Decomposer | query cell | 1-N sub-claim cells | 16 |
| Finder (×2) | sub-claim | K candidate (id, score) pairs | 16 each |
| Composer | candidates | composed fabric F | 16 |
| Answer | F | F as QUF bytes | 16 |

**Total: 5 cells × 16 dials = 80 parameters** (the new embedding agent)

## The 5 indices of the shape store

| Index | Key | Query |
|---|---|---|
| 1. Hash | FNV-1a 64-bit | exact match (O(1)) |
| 2. Dial | 16-dial vector | cosine similarity |
| 3. Bucket | K-bucket vector (per edge) | cosine similarity |
| 4. Graph-fp | 19-int fingerprint | integer matching |
| 5. LSH | 64-bit Sign-Random-Projection | Hamming distance |

Composite score = 0.4·hash + 0.3·dial + 0.2·bucket + 0.05·fp + 0.05·lsh

## The 6 advantages over flat-vector RAG

| Property | Flat-vector RAG | Shape RAG |
|---|---|---|
| Embedding unit | a 768d point | a cell fabric (≤255 cells) |
| Retrieval | k-NN (independent) | snap (compositional) |
| Generation | next-token | cell tick |
| State | none (stateless) | the cell state (FNV-1a) |
| Cross-substrate | embedding-specific | bit-exact in 6 substrates |
| Structured output | no (text) | yes (fabric) |

## The polyformalism value

The FNV-1a 64-bit state hash is the same value in all 6 substrates:
- 4-cell 4-edge fixture: `0x284816ba66c6e2af`
- 3-cell 2-edge fixture: `0xbbaec330a403c979`

The cell fabric is the inheritance.  The substrate is the projection.  The chart grows.

## Files

```
quilt-timesfm/
├── quf_v2.py            # the QUF reader/writer (Phase 239)
├── shape_rag.py         # Step 1: Cell-as-Vector + in-memory ShapeStore
├── shape_store.py       # Step 2: 5-index shape store (hash/dial/bucket/fp/lsh)
├── composer_agent.py    # Step 3: 5-cell, 80-param Composer Agent
├── SHAPE_RAG_README.md  # this file
├── tests/
│   ├── run_quf_v2_tests.py     # 52 tests
│   ├── test_shape_rag.py       # 18 tests
│   ├── test_shape_store.py     # 15 tests
│   └── test_composer_agent.py  # 16 tests
├── benchmarks/
│   └── benchmark_quf.py        # 100-fuzz + 5×3 cross-substrate matrix
```

## Run all tests

```bash
cd /workspace/quilt-timesfm
python3 tests/run_quf_v2_tests.py     # 52 tests
python3 tests/test_shape_rag.py       # 18 tests
python3 tests/test_shape_store.py     # 15 tests
python3 tests/test_composer_agent.py  # 16 tests
python3 benchmarks/benchmark_quf.py  # 100-fuzz + cross-substrate
```

## References

- F120 / paper-430.md — Shape RAG: the Cell IS the Embedding (design)
- F121 / paper-431.md — Cell-as-Vector (Step 1, 4096-dim flat projection)
- F122 / paper-432.md — The Shape Store: 5 Indices on Cloudflare Vectorize (Step 2)
- F123 / paper-433.md — The Composer Agent: 5 Cells, 80 Parameters, 1 Fabric (Step 3)
- F124 / paper-434.md — S-QL: The Shape Query Language (Step 4, designed)
- F125 / paper-435.md — The Shape-RAG API: 4 Endpoints, 10 Scenarios (Step 5, designed)
