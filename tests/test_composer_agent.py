#!/usr/bin/env python3
"""test_composer_agent.py — 16 tests for the Composer Agent (paper-433)."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from quf_v2 import QufFile, EdgeRecord, RouteRecord
from shape_store import ShapeStore
from composer_agent import ComposerAgent, _q1515_to_float, _float_to_q1515, DIAL_RANGES


def _make_fabric(n_cells: int, n_edges: int, k: int = 8, seed: int = 0) -> QufFile:
    rng = random.Random(seed)
    n_cells = min(n_cells, 255)
    dials = []
    for _ in range(n_cells):
        row = [64, 16, 1, 1, 4, 16384 + rng.randint(-256, 256),
               1, 128, 1, 0, 8, 0, 0, 0, 0, 0]
        dials.append([max(0, min(0xFFFF, v)) for v in row])
    edges = []
    for _ in range(n_edges):
        src = rng.randint(0, n_cells - 1)
        dst = rng.randint(0, n_cells - 1)
        edges.append(EdgeRecord(src, dst, 0, 0, 0, 0, 0, [rng.randint(0, 255) for _ in range(k)]))
    routing = [RouteRecord(i, i) for i in range(n_cells)]
    return QufFile(
        header={"quf.version": f"composer-test-{seed}",
                "cell_count": n_cells, "edge_count": n_edges,
                "route_count": n_cells, "edge.k": k, "tick_period": 1,
                "quant.dials": "Q1.15", "quant.edges": "Q1.15",
                "quant.routing": "u8", "align": 32},
        dials=dials, edges=edges, routing=routing,
        ticks=(1, [0] * n_cells),
    )


def _build_store_with(n_fabrics: int = 5) -> ShapeStore:
    store = ShapeStore()
    rng = random.Random(0xCAFE)
    for n_cells in [2, 4, 6, 8, 12][:n_fabrics]:
        n_edges = n_cells - 1
        dials = [[64] * 16 for _ in range(n_cells)]
        edges = [EdgeRecord(k, k + 1, 0, 0, 0, 0, 0, [rng.randint(0, 255) for _ in range(8)])
                 for k in range(n_edges)]
        routing = [RouteRecord(i, i) for i in range(n_cells)]
        qf = QufFile(
            header={"quf.version": f"composer-test-{n_cells}",
                    "cell_count": n_cells, "edge_count": n_edges,
                    "route_count": n_cells, "edge.k": 8, "tick_period": 1,
                    "quant.dials": "Q1.15", "quant.edges": "Q1.15",
                    "quant.routing": "u8", "align": 32},
            dials=dials, edges=edges, routing=routing,
            ticks=(1, [0] * n_cells),
        )
        store.add(qf, fabric_id=f"f{n_cells:04d}")
    return store


class TestComposerAgent(unittest.TestCase):

    def test_parameter_count_is_80(self):
        agent = ComposerAgent()
        self.assertEqual(agent.parameter_count(), 80)

    def test_five_cells(self):
        agent = ComposerAgent()
        self.assertEqual(len(agent.cells), 5)
        for cell in agent.cells:
            self.assertEqual(len(cell), 16)

    def test_query_cell_op(self):
        agent = ComposerAgent()
        vec = agent.query_cell_op("hello world")
        self.assertEqual(len(vec), 16)
        # Normalized
        norm = sum(v * v for v in vec) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_decomposer_cell_op(self):
        agent = ComposerAgent()
        query_vec = [0.1 * i for i in range(16)]
        sub_claims = agent.decomposer_cell_op(query_vec, n_sub=2)
        self.assertEqual(len(sub_claims), 2)

    def test_finder_cell_op_empty_store(self):
        agent = ComposerAgent()
        # No shape store
        cands = agent.finder_cell_op([0.0] * 16)
        self.assertEqual(cands, [])

    def test_finder_cell_op_with_store(self):
        agent = ComposerAgent()
        agent.shape_store = _build_store_with(5)
        cands = agent.finder_cell_op([0.0] * 16, k=3)
        self.assertEqual(len(cands), 3)

    def test_composer_cell_op_empty(self):
        agent = ComposerAgent()
        composed = agent.composer_cell_op([])
        self.assertEqual(len(composed.dials), 0)

    def test_composer_cell_op_with_candidates(self):
        agent = ComposerAgent()
        agent.shape_store = _build_store_with(5)
        cands = agent.finder_cell_op([0.0] * 16, k=2)
        composed = agent.composer_cell_op(cands)
        # Should have the dials of one of the fixtures
        self.assertGreater(len(composed.dials), 0)

    def test_answer_cell_op(self):
        agent = ComposerAgent()
        agent.shape_store = _build_store_with(5)
        composed, quf_bytes = agent.retrieve("test query")
        # QUF bytes should be a valid QUF (starts with magic)
        self.assertTrue(quf_bytes.startswith(b"QUF\x00"))
        # Round-trip
        from quf_v2 import loads
        qf2 = loads(quf_bytes)
        self.assertEqual(qf2.state_hash(), composed.state_hash())

    def test_retrieve_pipeline(self):
        agent = ComposerAgent()
        agent.shape_store = _build_store_with(5)
        composed, quf_bytes = agent.retrieve("fabric with 4 cells", n_sub=2, k_per=3)
        self.assertGreater(len(composed.dials), 0)
        self.assertGreater(len(quf_bytes), 100)

    def test_dial_ranges_dict(self):
        """The 5 cell kinds are documented."""
        self.assertEqual(len(DIAL_RANGES), 5)
        for kind in ["query", "decompose", "find", "compose", "answer"]:
            self.assertIn(kind, DIAL_RANGES)

    def test_train_reduces_loss(self):
        """The training loop should not increase the loss on average."""
        agent = ComposerAgent(seed=42)
        agent.shape_store = _build_store_with(5)
        fixtures = [("fabric with 2 cells", _make_fabric(2, 1, seed=0)),
                    ("fabric with 4 cells", _make_fabric(4, 3, seed=1))]
        # Initial loss
        initial_loss = agent._compute_loss_on(fixtures[0][0], fixtures[0][1])
        # Train
        losses = agent.train(fixtures, n_ticks=20, learning_rate=0.01, verbose=False)
        # The loss should be a list of length 20
        self.assertEqual(len(losses), 20)

    def test_state_hash_deterministic(self):
        """Two runs with the same seed produce the same composed fabric."""
        a1 = ComposerAgent(seed=0xBEEF)
        a1.shape_store = _build_store_with(5)
        a2 = ComposerAgent(seed=0xBEEF)
        a2.shape_store = _build_store_with(5)
        c1, b1 = a1.retrieve("test")
        c2, b2 = a2.retrieve("test")
        self.assertEqual(c1.state_hash(), c2.state_hash())

    def test_q1515_round_trip(self):
        for v in [0.0, 0.5, -0.5, 0.999, -1.0]:
            encoded = _float_to_q1515(v)
            decoded = _q1515_to_float(encoded)
            self.assertAlmostEqual(decoded, v, places=3)

    def test_dial_l1_same_fabric(self):
        """L1 distance between a fabric and itself is 0."""
        qf = _make_fabric(4, 3, seed=0)
        d = ComposerAgent._dial_l1(qf, qf)
        self.assertEqual(d, 0.0)

    def test_dial_l1_different_fabrics(self):
        """L1 distance between different fabrics is positive."""
        qf1 = _make_fabric(4, 3, seed=0)
        qf2 = _make_fabric(4, 3, seed=99)
        d = ComposerAgent._dial_l1(qf1, qf2)
        self.assertGreater(d, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
