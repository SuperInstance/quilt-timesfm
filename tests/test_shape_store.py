#!/usr/bin/env python3
"""test_shape_store.py — tests for the 5-index shape store (paper-432)."""
from __future__ import annotations

import os
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from quf_v2 import QufFile, EdgeRecord, RouteRecord
from shape_store import (
    ShapeStore, CloudflareShapeStore, hash_index_key, dial_vector_key,
    bucket_vector_key, graph_fingerprint_key, lsh_key, SHAPE_STORE_INDICES,
)
from shape_rag import to_dial_matrix, to_graph_fingerprint


def _make_fabric(n_cells: int, n_edges: int, k: int = 8, seed: int = 0) -> QufFile:
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
            "quf.version": f"shape-store-test-{seed}",
            "cell_count": n_cells, "edge_count": n_edges, "route_count": n_cells,
            "edge.k": k, "tick_period": 1,
            "quant.dials": "Q1.15", "quant.edges": "Q1.15",
            "quant.routing": "u8", "align": 32,
        },
        dials=dials, edges=edges, routing=routing,
        ticks=(1, [0] * n_cells),
    )


class TestIndexKeys(unittest.TestCase):

    def test_hash_key_format(self):
        qf = _make_fabric(1, 0, seed=0)
        key = hash_index_key(qf)
        self.assertTrue(key.startswith("0x"))
        self.assertEqual(len(key), 18)  # 0x + 16 hex chars

    def test_dial_vector_key_dim_16(self):
        qf = _make_fabric(1, 0, seed=0)
        vec = dial_vector_key(qf)
        self.assertEqual(len(vec), 16)

    def test_dial_vector_key_first_cell(self):
        """The dial vector is the first cell's dials (16 floats)."""
        qf = _make_fabric(4, 4, seed=0)
        vec = dial_vector_key(qf)
        expected = to_dial_matrix(qf)[0]
        self.assertEqual(list(vec), expected)

    def test_bucket_vector_key_dim_k(self):
        qf = _make_fabric(1, 1, k=8, seed=0)
        vec = bucket_vector_key(qf)
        self.assertEqual(len(vec), 8)

    def test_graph_fingerprint_key_dim_19(self):
        qf = _make_fabric(4, 4, seed=0)
        fp = graph_fingerprint_key(qf)
        self.assertEqual(len(fp), 19)

    def test_lsh_key_64_bits(self):
        qf = _make_fabric(1, 0, seed=0)
        key = lsh_key(qf)
        self.assertEqual(len(key), 64)
        self.assertTrue(all(c in "01" for c in key))

    def test_lsh_deterministic(self):
        """LSH key is the same for the same fabric."""
        qf1 = _make_fabric(4, 4, seed=0)
        qf2 = _make_fabric(4, 4, seed=0)
        self.assertEqual(lsh_key(qf1), lsh_key(qf2))


class TestShapeStore(unittest.TestCase):

    def test_add_and_count(self):
        store = ShapeStore()
        for i in range(5):
            store.add(_make_fabric(2 + i, 2, seed=i))
        self.assertEqual(store.count(), 5)

    def test_hash_lookup_exact(self):
        """O(1) hash lookup returns the same fabric."""
        store = ShapeStore()
        qf = _make_fabric(2, 2, seed=42)
        store.add(qf, fabric_id="target")
        # Lookup with the same fabric (same seed) should hit
        qf_lookup = _make_fabric(2, 2, seed=42)
        result = store.by_hash_lookup(qf_lookup)
        self.assertIsNotNone(result)
        self.assertEqual(result.state_hash(), qf.state_hash())

    def test_composite_query_returns_self_first(self):
        """Querying for an existing fabric should return it as the top match."""
        store = ShapeStore()
        for i in range(5):
            store.add(_make_fabric(2 + i, 2, seed=i), fabric_id=f"f{i:04d}")
        qf = _make_fabric(3, 2, seed=1)  # fabric f0001
        results = store.query(qf, k=3)
        self.assertEqual(len(results), 3)
        # The top result should be f0001 (exact hash match, score 1.0)
        self.assertEqual(results[0][0], "f0001")
        self.assertAlmostEqual(results[0][1], 1.0, places=4)

    def test_composite_query_k_limit(self):
        store = ShapeStore()
        for i in range(20):
            store.add(_make_fabric(2 + (i % 4), 2, seed=i), fabric_id=f"f{i:04d}")
        results = store.query(_make_fabric(2, 2, seed=0), k=5)
        self.assertEqual(len(results), 5)

    def test_composite_score_weights(self):
        """Hash match should be the heaviest component (0.4)."""
        store = ShapeStore()
        qf = _make_fabric(2, 2, seed=42)
        store.add(qf, fabric_id="self")
        # Add a different fabric
        store.add(_make_fabric(2, 2, seed=99), fabric_id="other")
        results = store.query(qf, k=2)
        # self should be first, with score including 0.4 * 1.0 (hash) + others
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0], "self")


class TestCloudflareShapeStore(unittest.TestCase):

    @unittest.skipUnless(
        os.environ.get("CLOUDFLARE_TOKEN"),
        "CLOUDFLARE_TOKEN not set"
    )
    def test_list_indices(self):
        """List indices should return at least the shape-store indices."""
        cf = CloudflareShapeStore()
        indices = cf.list_indices()
        self.assertIsInstance(indices, list)
        # We created 3 shape-store indices
        relevant = [i for i in indices if i.get("name", "").startswith("quilt-shape-")]
        self.assertGreaterEqual(len(relevant), 3)

    @unittest.skipUnless(
        os.environ.get("CLOUDFLARE_TOKEN"),
        "CLOUDFLARE_TOKEN not set"
    )
    def test_ensure_all_idempotent(self):
        """ensure_all() should be idempotent."""
        cf = CloudflareShapeStore()
        results1 = cf.ensure_all()
        results2 = cf.ensure_all()
        for name, ok1 in results1.items():
            ok2 = results2.get(name)
            self.assertEqual(ok1, ok2)

    def test_constants(self):
        """The 3 cloud indices are correctly configured."""
        self.assertEqual(SHAPE_STORE_INDICES["quilt-shape-dial"], 768)
        self.assertEqual(SHAPE_STORE_INDICES["quilt-shape-bucket"], 32)
        self.assertEqual(SHAPE_STORE_INDICES["quilt-shape-lsh"], 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
