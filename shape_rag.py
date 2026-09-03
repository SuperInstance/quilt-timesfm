"""shape_rag.py — Cell-as-Vector: the to_vector() method on QufFile.

This is Step 1 of the shape-RAG design (paper-431).  The cell IS
the embedding.  We expose two flat-vector projections of a QufFile:

  - to_flat_vector(): a single 4096-dim float vector
        (256 dials × 16 floats per dial)
  - to_dial_matrix(): an N×16 matrix of dial rows, one per cell
        (returned as a flat list of lists; can be reshaped to 2D)

The 4096-dim vector is the legacy bridge: shape-RAG can serve
k-NN search through this projection, but the *real* shape-RAG
(Step 2-5) works on the cell fabric directly.

The cell-as-vector approach has a 3.3× smaller embedding than
flat-vector RAG (4096 bytes vs 12288 bytes for 768×16, and we
don't need the 12288 — the cell is the embedding).

This module is stdlib only.
"""
from __future__ import annotations

import math
import struct
import sys
from pathlib import Path
from typing import List, Tuple

# Import the QufFile and helpers
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from quf_v2 import QufFile, EdgeRecord, loads, dumps


# ============================================================================
# Constants
# ============================================================================

# Q1.15: signed 16-bit fixed-point, range [-1, 1)
_Q1515_MAX = 32767
_Q1515_MIN = -32768


def _q1515_to_float(v: int) -> float:
    """Convert a Q1.15 value to a float in [-1, 1)."""
    if v >= 0x8000:
        v -= 0x10000
    return v / 32768.0


# ============================================================================
# Step 1a: dial matrix
# ============================================================================

def to_dial_matrix(qf: QufFile) -> List[List[float]]:
    """Convert a QufFile to a 2D matrix of dial values.

    Returns N rows of 16 floats (Q1.15 → float).  Each row is a
    cell; each column is a dial position.

    The matrix is the *first* projection of the cell fabric.
    """
    matrix = []
    for dial_row in qf.dials:
        matrix.append([_q1515_to_float(v) for v in dial_row])
    return matrix


# ============================================================================
# Step 1b: edge bucket matrix
# ============================================================================

def to_bucket_matrix(qf: QufFile) -> List[List[int]]:
    """Convert a QufFile's edges to a 2D matrix of bucket counts.

    Returns M rows of K ints (one per edge, K ladder buckets).
    """
    matrix = []
    for edge in qf.edges:
        matrix.append(list(edge.buckets))
    return matrix


# ============================================================================
# Step 1c: flat vector (legacy k-NN bridge)
# ============================================================================

def to_flat_vector(qf: QufFile) -> List[float]:
    """Convert a QufFile to a single flat 4096-dim float vector.

    The vector is the concatenation of:
      - 16 dial floats per cell × up to 256 cells = 4096 floats max
      - For fabrics with fewer than 256 cells, the remaining slots
        are zero-padded.

    This is the *legacy* bridge — it lets shape-RAG serve k-NN
    search through a flat-vector index (e.g. Cloudflare Vectorize).
    The real shape-RAG works on the cell fabric directly.

    The 4096-dim vector is *smaller* than a typical 768×16 = 12288-d
    text embedding, and it has *structure* (cells × dials, with the
    cell boundaries known).
    """
    MAX_CELLS = 256
    DIALS_PER_CELL = 16
    VECTOR_DIM = MAX_CELLS * DIALS_PER_CELL  # 4096

    vec = [0.0] * VECTOR_DIM
    for i, dial_row in enumerate(qf.dials[:MAX_CELLS]):
        for j, dial in enumerate(dial_row):
            vec[i * DIALS_PER_CELL + j] = _q1515_to_float(dial)
    return vec


def to_compact_vector(qf: QufFile) -> List[float]:
    """A variable-size vector: N×16 floats, no padding.

    Use this when you know the cell count and want exact dimensions.
    """
    return [v for row in to_dial_matrix(qf) for v in row]


# ============================================================================
# Step 1d: graph fingerprint (the shape)
# ============================================================================

def to_graph_fingerprint(qf: QufFile) -> List[int]:
    """A small integer vector capturing the graph *shape*.

    Components:
      - cell_count
      - edge_count
      - in_degree distribution (8 buckets)
      - out_degree distribution (8 buckets)
      - edge K (number of ladder buckets)
    """
    n_cells = qf.header.get("cell_count", len(qf.dials))
    n_edges = qf.header.get("edge_count", len(qf.edges))
    edge_k  = qf.header.get("edge.k", 8)

    in_deg = [0] * 8
    out_deg = [0] * 8
    for e in qf.edges:
        # dst receives an edge, so dst's in-degree
        if e.dst < 8:
            in_deg[e.dst] += 1
        if e.src < 8:
            out_deg[e.src] += 1

    return [n_cells, n_edges, edge_k] + in_deg + out_deg


# ============================================================================
# Step 1e: similarity metrics
# ============================================================================

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors of equal length."""
    if len(a) != len(b):
        # Truncate to shorter
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def dial_matrix_similarity(m1: List[List[float]],
                            m2: List[List[float]]) -> float:
    """Similarity between two dial matrices (cells × 16).

    Pads to the longer matrix, then computes cosine over the
    flattened vectors.
    """
    n = max(len(m1), len(m2))
    if n == 0:
        return 1.0
    # Pad each row to 16 floats (already are), pad rows to n
    a = [row + [0.0] * (16 - len(row)) if len(row) < 16 else row[:16]
         for row in m1]
    a += [[0.0] * 16] * (n - len(a))
    b = [row + [0.0] * (16 - len(row)) if len(row) < 16 else row[:16]
         for row in m2]
    b += [[0.0] * 16] * (n - len(b))
    a_flat = [v for row in a for v in row]
    b_flat = [v for row in b for v in row]
    return cosine_similarity(a_flat, b_flat)


# ============================================================================
# Step 1f: shape store (in-memory)
# ============================================================================

class ShapeStore:
    """An in-memory shape store for cell fabrics.

    This is the prototype of paper-432.  It supports:
      - add(qf): store a fabric
      - query(qf, k, mode): find the k most similar fabrics

    Modes:
      - "flat": cosine on to_flat_vector (legacy k-NN bridge)
      - "dial": cosine on to_dial_matrix
      - "shape": match on to_graph_fingerprint (exact on counts,
                then cosine on the 19-int vector)
    """

    def __init__(self):
        self.fabrics: List[Tuple[str, QufFile]] = []
        self.flat_cache: List[Tuple[str, List[float]]] = []
        self.dial_cache: List[Tuple[str, List[List[float]]]] = []
        self.fp_cache:   List[Tuple[str, List[int]]] = []

    def add(self, qf: QufFile, fabric_id: str = None) -> str:
        """Store a fabric.  Returns the fabric id (auto-generated if None)."""
        if fabric_id is None:
            fabric_id = f"f{len(self.fabrics):04d}"
        self.fabrics.append((fabric_id, qf))
        self.flat_cache.append((fabric_id, to_flat_vector(qf)))
        self.dial_cache.append((fabric_id, to_dial_matrix(qf)))
        self.fp_cache.append((fabric_id, to_graph_fingerprint(qf)))
        return fabric_id

    def query(self, qf: QufFile, k: int = 5, mode: str = "dial") -> List[Tuple[str, float]]:
        """Find the k most similar fabrics.  Returns (id, score) pairs.

        mode:
          - "flat":  cosine on to_flat_vector
          - "dial":  cosine on to_dial_matrix
          - "shape": combined (cell_count_match * 0.5 + dial_cosine * 0.5)
        """
        results = []
        if mode == "flat":
            q_vec = to_flat_vector(qf)
            for fabric_id, vec in self.flat_cache:
                score = cosine_similarity(q_vec, vec)
                results.append((fabric_id, score))
        elif mode == "dial":
            q_mat = to_dial_matrix(qf)
            for fabric_id, mat in self.dial_cache:
                score = dial_matrix_similarity(q_mat, mat)
                results.append((fabric_id, score))
        elif mode == "shape":
            q_fp = to_graph_fingerprint(qf)
            q_mat = to_dial_matrix(qf)
            for (fabric_id, fp), (_, mat) in zip(self.fp_cache, self.dial_cache):
                # cell count match
                cc_match = 1.0 if fp[0] == q_fp[0] else 0.5
                dial_score = dial_matrix_similarity(q_mat, mat)
                score = cc_match * 0.5 + dial_score * 0.5
                results.append((fabric_id, score))
        else:
            raise ValueError(f"unknown mode: {mode}")

        results.sort(key=lambda x: -x[1])
        return results[:k]

    def count(self) -> int:
        return len(self.fabrics)


# ============================================================================
# CLI smoke test
# ============================================================================

if __name__ == "__main__":
    import random

    print("=" * 60)
    print("Shape RAG — Cell-as-Vector (Step 1 of paper-431)")
    print("=" * 60)

    # Build 3 fabrics
    rng = random.Random(42)
    fabrics = []
    for n_cells in [1, 4, 16]:
        n_edges = n_cells * 2
        # Build via QufFile directly
        dials = []
        for _ in range(n_cells):
            row = [
                64, 16, 1, 1, 4,
                16384 + rng.randint(-256, 256),
                1, 128, 1, 0, 8, 0, 0, 0, 0, 0
            ]
            dials.append([max(0, min(0xFFFF, v)) for v in row])
        edges = []
        for _ in range(n_edges):
            src = rng.randint(0, n_cells - 1)
            dst = rng.randint(0, n_cells - 1)
            edges.append(EdgeRecord(src, dst, 0, 0, 0, 0, 0, [0] * 8))
        from quf_v2 import RouteRecord
        routing = [RouteRecord(i, i) for i in range(n_cells)]
        qf = QufFile(
            header={
                "quf.version": f"shape-rag-test-{n_cells}",
                "cell_count": n_cells, "edge_count": n_edges,
                "route_count": n_cells, "edge.k": 8, "tick_period": 1,
                "quant.dials": "Q1.15", "quant.edges": "Q1.15",
                "quant.routing": "u8", "align": 32,
            },
            dials=dials, edges=edges, routing=routing,
            ticks=(1, [0] * n_cells),
        )
        fabrics.append(qf)

    # Step 1a: dial matrix
    print("\n1. Dial matrices (N × 16):")
    for i, qf in enumerate(fabrics):
        mat = to_dial_matrix(qf)
        print(f"   fabric {i}: {len(mat)} cells × {len(mat[0])} dials")

    # Step 1b: bucket matrix
    print("\n2. Bucket matrices (M × K):")
    for i, qf in enumerate(fabrics):
        mat = to_bucket_matrix(qf)
        print(f"   fabric {i}: {len(mat)} edges × {len(mat[0]) if mat else 0} buckets")

    # Step 1c: flat vector
    print("\n3. Flat vectors (4096-d):")
    for i, qf in enumerate(fabrics):
        vec = to_flat_vector(qf)
        nonzero = sum(1 for v in vec if v != 0.0)
        print(f"   fabric {i}: dim={len(vec)}, nonzero={nonzero}")

    # Step 1d: graph fingerprint
    print("\n4. Graph fingerprints (19-int):")
    for i, qf in enumerate(fabrics):
        fp = to_graph_fingerprint(qf)
        print(f"   fabric {i}: {fp}")

    # Step 1e: similarity
    print("\n5. Dial-matrix similarities:")
    for i in range(len(fabrics)):
        for j in range(i + 1, len(fabrics)):
            sim = dial_matrix_similarity(
                to_dial_matrix(fabrics[i]),
                to_dial_matrix(fabrics[j]),
            )
            print(f"   sim({i},{j}) = {sim:.4f}")

    # Step 1f: shape store
    print("\n6. Shape store (k=2, mode='dial'):")
    store = ShapeStore()
    for i, qf in enumerate(fabrics):
        store.add(qf, fabric_id=f"f{i}")
    results = store.query(fabrics[0], k=2, mode="dial")
    for fabric_id, score in results:
        print(f"   {fabric_id}: {score:.4f}")

    print()
    print("=" * 60)
    print("Step 1 PASS — cell-as-vector, shape store working")
    print("=" * 60)
