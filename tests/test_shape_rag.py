#!/usr/bin/env python3
"""test_shape_rag.py — tests for the cell-as-vector projection (Step 1 of F120)."""
from __future__ import annotations

import math
import os
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from quf_v2 import QufFile, EdgeRecord, RouteRecord
from shape_rag import (
    to_dial_matrix, to_bucket_matrix, to_flat_vector, to_graph_fingerprint,
    to_compact_vector, cosine_similarity, dial_matrix_similarity,
    ShapeStore, _q1515_to_float,
)


def _make_fabric(n_cells: int, n_edges: int, k: int = 8, seed: int = 0) -> QufFile:
    """Build a small QufFile with the given dimensions."""
    rng = random.Random(seed)
    n_cells = min(n_cells, 255)
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
        edges.append(EdgeRecord(src, dst, 0, 0, 0, 0, 0, [rng.randint(0, 255) for _ in range(k)]))
    routing = [RouteRecord(i, i) for i in range(n_cells)]
    return QufFile(
        header={
            "quf.version": f"shape-rag-test-{seed}",
            "cell_count": n_cells, "edge_count": n_edges, "route_count": n_cells,
            "edge.k": k, "tick_period": 1,
            "quant.dials": "Q1.15", "quant.edges": "Q1.15",
            "quant.routing": "u8", "align": 32,
        },
        dials=dials, edges=edges, routing=routing,
        ticks=(1, [0] * n_cells),
    )


class TestDialMatrix(unittest.TestCase):

    def test_dial_matrix_dimensions(self):
        qf = _make_fabric(4, 8, seed=1)
        mat = to_dial_matrix(qf)
        self.assertEqual(len(mat), 4)
        for row in mat:
            self.assertEqual(len(row), 16)

    def test_dial_matrix_values_in_range(self):
        """All dial values should be in [-1, 1) after Q1.15 decode."""
        qf = _make_fabric(4, 8, seed=1)
        mat = to_dial_matrix(qf)
        for row in mat:
            for v in row:
                self.assertGreaterEqual(v, -1.0)
                self.assertLess(v, 1.0)


class TestBucketMatrix(unittest.TestCase):

    def test_bucket_matrix_dimensions(self):
        qf = _make_fabric(4, 8, k=8, seed=2)
        mat = to_bucket_matrix(qf)
        self.assertEqual(len(mat), 8)
        for row in mat:
            self.assertEqual(len(row), 8)


class TestFlatVector(unittest.TestCase):

    def test_flat_vector_dim_4096(self):
        qf = _make_fabric(1, 0, seed=3)
        vec = to_flat_vector(qf)
        self.assertEqual(len(vec), 4096)

    def test_flat_vector_pads_to_4096(self):
        """A 1-cell fabric should have 16 nonzero floats max and 4080 zero floats."""
        qf = _make_fabric(1, 0, seed=3)
        vec = to_flat_vector(qf)
        # Some dial slots are intentionally 0 (e.g. tick_period, reserved).
        # The first dial (value) and the THRESH slot are non-zero.
        # Just check that the total nonzero is <= 16 and the count is 4096.
        nonzero = sum(1 for v in vec if v != 0.0)
        self.assertLessEqual(nonzero, 16)
        self.assertGreater(nonzero, 0)
        # The vector dimension is 4096
        self.assertEqual(len(vec), 4096)
        # The first 16 floats correspond to cell 0
        self.assertEqual(len(vec[:16]), 16)

    def test_compact_vector_no_padding(self):
        """to_compact_vector has 16 × N floats, no padding."""
        qf = _make_fabric(4, 0, seed=3)
        vec = to_compact_vector(qf)
        self.assertEqual(len(vec), 4 * 16)


class TestGraphFingerprint(unittest.TestCase):

    def test_fingerprint_has_19_ints(self):
        qf = _make_fabric(4, 8, seed=4)
        fp = to_graph_fingerprint(qf)
        self.assertEqual(len(fp), 19)
        self.assertEqual(fp[0], 4)  # cell_count
        self.assertEqual(fp[1], 8)  # edge_count
        self.assertEqual(fp[2], 8)  # edge.K


class TestSimilarity(unittest.TestCase):

    def test_cosine_self_is_one(self):
        v = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=6)

    def test_cosine_zero_is_zero(self):
        v = [1.0, 0.0, 0.0]
        w = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v, w), 0.0, places=6)

    def test_dial_matrix_self_is_one(self):
        qf = _make_fabric(4, 8, seed=5)
        m = to_dial_matrix(qf)
        self.assertAlmostEqual(dial_matrix_similarity(m, m), 1.0, places=4)

    def test_dial_matrix_symmetric(self):
        qf1 = _make_fabric(4, 8, seed=5)
        qf2 = _make_fabric(4, 8, seed=6)
        m1 = to_dial_matrix(qf1)
        m2 = to_dial_matrix(qf2)
        s1 = dial_matrix_similarity(m1, m2)
        s2 = dial_matrix_similarity(m2, m1)
        self.assertAlmostEqual(s1, s2, places=6)


class TestShapeStore(unittest.TestCase):

    def test_add_and_count(self):
        store = ShapeStore()
        self.assertEqual(store.count(), 0)
        for i in range(3):
            store.add(_make_fabric(2, 2, seed=i), fabric_id=f"f{i}")
        self.assertEqual(store.count(), 3)

    def test_query_returns_self_first(self):
        store = ShapeStore()
        qf = _make_fabric(2, 2, seed=42)
        store.add(qf, fabric_id="self")
        for i in range(5):
            store.add(_make_fabric(2 + i, 2 + i, seed=i), fabric_id=f"other{i}")
        results = store.query(qf, k=3, mode="dial")
        self.assertEqual(results[0][0], "self")
        self.assertAlmostEqual(results[0][1], 1.0, places=4)

    def test_query_modes(self):
        store = ShapeStore()
        qf = _make_fabric(2, 2, seed=42)
        store.add(qf, fabric_id="self")
        for mode in ["flat", "dial", "shape"]:
            results = store.query(qf, k=3, mode=mode)
            self.assertGreater(len(results), 0)
            # self should be top
            self.assertEqual(results[0][0], "self")

    def test_query_k_limit(self):
        store = ShapeStore()
        qf = _make_fabric(2, 2, seed=42)
        for i in range(10):
            store.add(_make_fabric(2 + (i % 4), 2, seed=i), fabric_id=f"f{i}")
        results = store.query(qf, k=3, mode="dial")
        self.assertEqual(len(results), 3)


class TestQ1515Conversion(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(_q1515_to_float(0), 0.0)

    def test_max_positive(self):
        self.assertAlmostEqual(_q1515_to_float(0x7FFF), 0.99997, places=4)

    def test_max_negative(self):
        # 0x8000 is the most negative in Q1.15 two's complement
        self.assertEqual(_q1515_to_float(0x8000), -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
