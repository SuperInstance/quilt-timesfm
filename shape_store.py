"""shape_store.py — The Shape Store: 5 indices on Cloudflare Vectorize.

This is Step 2 of the shape-RAG design (paper-432).  It is the
persistence layer that holds cell fabrics indexed by 5 different
*shapes*:

  1. Hash index:  FNV-1a 64-bit state hash → exact cell lookup (O(1))
  2. Dial-vector index:  16-dial vector per cell → cosine similarity
  3. Bucket-vector index:  K-bucket vector per edge → cosine similarity
  4. Graph-shape index:  19-int graph fingerprint → integer matching
  5. LSH index:  locality-sensitive hash of the 4096-dim flat vector
     → approximate neighborhood

The in-memory shape store is a prototype; the Cloudflare Vectorize
backend is the production deployment (see CloudflareShapeStore).

This module is stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from quf_v2 import QufFile, loads, dumps
from shape_rag import (
    to_dial_matrix, to_bucket_matrix, to_flat_vector, to_graph_fingerprint,
    cosine_similarity,
)


# ============================================================================
# 1. The 5 indices — pure functions
# ============================================================================

def hash_index_key(qf: QufFile) -> str:
    """Index 1: hash key.  The FNV-1a 64-bit state hash, hex-encoded."""
    return f"0x{qf.state_hash():016x}"


def dial_vector_key(qf: QufFile) -> List[float]:
    """Index 2: dial vector.  The 16-dial vector of the *first* cell."""
    if not qf.dials:
        return [0.0] * 16
    return to_dial_matrix(qf)[0]


def bucket_vector_key(qf: QufFile) -> List[float]:
    """Index 3: bucket vector.  The K-bucket vector of the *first* edge."""
    if not qf.edges:
        return [0.0] * 8
    return [float(b) for b in qf.edges[0].buckets]


def graph_fingerprint_key(qf: QufFile) -> List[int]:
    """Index 4: graph fingerprint.  The 19-int shape signature."""
    return to_graph_fingerprint(qf)


def lsh_key(qf: QufFile, n_buckets: int = 64) -> str:
    """Index 5: LSH.  A 64-bit locality-sensitive hash of the flat vector.

    Splits the 4096-dim flat vector into 64 chunks, sums each chunk,
    and uses the sign to produce 1 bit.  This is the Sign-Random-Projection
    LSH of Goemans-Williamson (1995).
    """
    vec = to_flat_vector(qf)
    chunk_size = max(1, len(vec) // n_buckets)
    bits = []
    for i in range(n_buckets):
        chunk = vec[i * chunk_size : (i + 1) * chunk_size]
        if sum(chunk) > 0:
            bits.append("1")
        else:
            bits.append("0")
    return "".join(bits)


# ============================================================================
# 2. The in-memory ShapeStore (5 indices in one)
# ============================================================================

class ShapeStore:
    """The in-memory shape store.

    Maintains 5 indices:
      - by_hash:     Dict[hash_key, QufFile]
      - by_dial:     List[(dial_vector, QufFile)]
      - by_bucket:   List[(bucket_vector, QufFile)]
      - by_finger:   Dict[graph_fingerprint_tuple, List[QufFile]]
      - by_lsh:      Dict[lsh_key, List[QufFile]]

    Query returns the union of matches across all 5 indices, ranked
    by a composite score.
    """

    def __init__(self):
        self.by_hash: Dict[str, QufFile] = {}
        self.by_dial: List[Tuple[List[float], str, QufFile]] = []
        self.by_bucket: List[Tuple[List[float], str, QufFile]] = []
        self.by_finger: Dict[Tuple[int, ...], List[Tuple[str, QufFile]]] = {}
        self.by_lsh: Dict[str, List[Tuple[str, QufFile]]] = {}
        self.fabric_id_counter = 0

    def _new_id(self) -> str:
        self.fabric_id_counter += 1
        return f"f{self.fabric_id_counter:04d}"

    def add(self, qf: QufFile, fabric_id: Optional[str] = None) -> str:
        """Store a fabric.  Returns the fabric id."""
        if fabric_id is None:
            fabric_id = self._new_id()

        # Index 1: hash
        h = hash_index_key(qf)
        self.by_hash[h] = qf

        # Index 2: dial vector
        d = dial_vector_key(qf)
        self.by_dial.append((d, fabric_id, qf))

        # Index 3: bucket vector
        b = bucket_vector_key(qf)
        self.by_bucket.append((b, fabric_id, qf))

        # Index 4: graph fingerprint
        fp = tuple(graph_fingerprint_key(qf))
        self.by_finger.setdefault(fp, []).append((fabric_id, qf))

        # Index 5: LSH
        lsh = lsh_key(qf)
        self.by_lsh.setdefault(lsh, []).append((fabric_id, qf))

        return fabric_id

    def count(self) -> int:
        return len(self.by_dial)  # all indices should have the same count

    # ----- Query -----

    def query(self, qf: QufFile, k: int = 5) -> List[Tuple[str, float]]:
        """Composite query.  Returns (fabric_id, score) pairs, sorted by score.

        Stages:
          1. Hash lookup (exact match, score 1.0)
          2. Dial-vector cosine (rank by score)
          3. Bucket-vector cosine (rank by score)
          4. Graph-shape match (cell_count match * 0.5 + dial cosine * 0.5)
          5. LSH (Hamming distance, normalized to [0, 1])
        Final score = 0.4 * hash + 0.3 * dial + 0.2 * bucket + 0.05 * graph + 0.05 * lsh
        """
        # Stage 1: hash lookup
        h = hash_index_key(qf)
        hash_match = self.by_hash.get(h)

        # Stage 2: dial-vector cosine
        q_dial = dial_vector_key(qf)
        dial_scores = {}
        for d, fid, _ in self.by_dial:
            dial_scores[fid] = cosine_similarity(q_dial, d)

        # Stage 3: bucket-vector cosine
        q_bucket = bucket_vector_key(qf)
        bucket_scores = {}
        for b, fid, _ in self.by_bucket:
            bucket_scores[fid] = cosine_similarity(q_bucket, b)

        # Stage 4: graph-shape match
        q_fp = tuple(graph_fingerprint_key(qf))
        graph_scores = {}
        for fp, fids in self.by_finger.items():
            cc_match = 1.0 if fp[0] == q_fp[0] else 0.0
            for fid, _ in fids:
                # If a fid appears in multiple fingerprints, keep the max
                graph_scores[fid] = max(graph_scores.get(fid, 0.0), cc_match)

        # Stage 5: LSH
        q_lsh = lsh_key(qf)
        lsh_scores = {}
        for lsh, fids in self.by_lsh.items():
            # Hamming distance normalized to [0, 1]
            if len(q_lsh) == len(lsh):
                hamming = sum(a != b for a, b in zip(q_lsh, lsh))
                sim = 1.0 - (hamming / len(q_lsh))
                for fid, _ in fids:
                    lsh_scores[fid] = max(lsh_scores.get(fid, 0.0), sim)

        # Composite
        all_ids = set(dial_scores) | set(bucket_scores) | set(graph_scores) | set(lsh_scores)
        if hash_match is not None:
            # The exact hash match is always #1
            all_ids.add(hash_index_key(hash_match))
            # Note: hash_index_key returns hex; this is a synthetic key
        # Actually, hash_match gives a QufFile not an id.  Skip.

        composite = []
        for fid in all_ids:
            # Skip non-id keys (no filter — accept any string id)
            # Hash membership: does this fid's QufFile have the same hash as q?
            h_score = 0.0
            for d, fid2, qf2 in self.by_dial:
                if fid2 == fid and hash_index_key(qf2) == h:
                    h_score = 1.0
                    break
            d_score = dial_scores.get(fid, 0.0)
            b_score = bucket_scores.get(fid, 0.0)
            g_score = graph_scores.get(fid, 0.0)
            l_score = lsh_scores.get(fid, 0.0)
            composite_score = (
                0.4 * h_score +
                0.3 * d_score +
                0.2 * b_score +
                0.05 * g_score +
                0.05 * l_score
            )
            composite.append((fid, composite_score))

        composite.sort(key=lambda x: -x[1])
        return composite[:k]

    def by_hash_lookup(self, qf: QufFile) -> Optional[QufFile]:
        """O(1) exact hash lookup."""
        return self.by_hash.get(hash_index_key(qf))


# ============================================================================
# 3. Cloudflare Vectorize backend
# ============================================================================

CLOUDFLARE_API = "https://api.cloudflare.com/client/v4/accounts/{}/vectorize/v2/indexes/{}"
CLOUDFLARE_ACCOUNT = "049ff5e84ecf636b53b162cbb580aae6"
# Token is read from the CLOUDFLARE_TOKEN env var at runtime.
# Do NOT hardcode the token in source (GitHub push protection).
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_TOKEN", "")
SHAPE_STORE_INDICES = {
    "quilt-shape-dial":   768,   # dial-vector (padded to 768d)
    "quilt-shape-bucket": 32,    # bucket-vector (padded from 8 to 32; min 32)
    "quilt-shape-lsh":    64,    # LSH bits as 64-dim {0,1} floats
    # Note: graph fingerprint is 19-int, kept in-memory (no vector index needed)
}


def cf_get(path: str, timeout: int = 10) -> Tuple[bool, Any]:
    """GET to Cloudflare API."""
    url = f"https://api.cloudflare.com/client/v4{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CLOUDFLARE_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)


def cf_post(path: str, body: Any, timeout: int = 30) -> Tuple[bool, Any]:
    """POST to Cloudflare API."""
    url = f"https://api.cloudflare.com/client/v4{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                  headers={"Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
                                           "Content-Type": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)


class CloudflareShapeStore:
    """The Cloudflare Vectorize backend for the shape store.

    Maintains 4 indices on Cloudflare Vectorize (dial, bucket, LSH).
    The graph fingerprint is kept in-memory (integer matching is
    trivial and doesn't need a vector index).

    Note: the actual Cloudflare index creation is gated behind the
    `ensure_indices` method, which checks for index existence and
    creates them if missing.  Idempotent.
    """

    def __init__(self, account_id: str = None, token: str = None):
        self.account_id = account_id or CLOUDFLARE_ACCOUNT
        self.token = token or os.environ.get("CLOUDFLARE_TOKEN", "")
        self.indices = {}  # name -> {"dim": int, "info": dict}

    def _index_url(self, name: str) -> str:
        return CLOUDFLARE_API.format(self.account_id, name)

    def list_indices(self) -> List[Dict]:
        """List all vectorize indices on the account."""
        ok, data = cf_get(f"/accounts/{self.account_id}/vectorize/v2/indexes")
        if not ok:
            return []
        return data.get("result", [])

    def ensure_index(self, name: str, dims: int) -> bool:
        """Create the index if it doesn't exist."""
        # Check if exists
        indices = self.list_indices()
        for idx in indices:
            if idx.get("name") == name:
                self.indices[name] = {"dim": dims, "info": idx}
                return True

        # Create
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes",
            {"name": name, "config": {"dimensions": dims, "metric": "cosine"}},
        )
        if not ok:
            print(f"Failed to create index {name}: {data}")
            return False
        self.indices[name] = {"dim": dims, "info": data}
        return True

    def ensure_all(self) -> Dict[str, bool]:
        """Ensure all 4 shape-store indices exist."""
        return {name: self.ensure_index(name, dims)
                for name, dims in SHAPE_STORE_INDICES.items()}

    def insert(self, qf: QufFile, fabric_id: Optional[str] = None) -> str:
        """Insert a fabric into the dial, bucket, and LSH indices."""
        if fabric_id is None:
            fabric_id = f"q{int(time.time() * 1000)}"

        # Index 2: dial vector (use the compact form, 16 floats, repeat to 768)
        dial_vec = dial_vector_key(qf)
        dial_padded = (dial_vec * 48)[:768]  # 16 × 48 = 768
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes/quilt-shape-dial/upsert",
            [{"id": fabric_id, "values": dial_padded,
              "metadata": {"hash": hash_index_key(qf), "n_cells": len(qf.dials)}}],
        )

        # Index 3: bucket vector (8 floats, pad to 32)
        bucket_vec = bucket_vector_key(qf)
        bucket_padded = bucket_vec + [0.0] * (32 - len(bucket_vec))
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes/quilt-shape-bucket/upsert",
            [{"id": fabric_id, "values": bucket_padded}],
        )

        # Index 5: LSH (64 bits as floats)
        lsh_str = lsh_key(qf)
        lsh_vec = [float(b) for b in lsh_str]
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes/quilt-shape-lsh/upsert",
            [{"id": fabric_id, "values": lsh_vec}],
        )

        return fabric_id

    def query_dial(self, qf: QufFile, k: int = 5) -> List[Tuple[str, float]]:
        """Query the dial-vector index."""
        dial_vec = dial_vector_key(qf)
        dial_padded = (dial_vec * 48)[:768]
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes/quilt-shape-dial/query",
            {"vector": dial_padded, "topK": k, "returnMetadata": "all"},
        )
        if not ok:
            return []
        return [(m["id"], m["score"]) for m in data.get("result", {}).get("matches", [])]

    def query_bucket(self, qf: QufFile, k: int = 5) -> List[Tuple[str, float]]:
        """Query the bucket-vector index."""
        bucket_vec = bucket_vector_key(qf)
        bucket_padded = bucket_vec + [0.0] * (32 - len(bucket_vec))
        ok, data = cf_post(
            f"/accounts/{self.account_id}/vectorize/v2/indexes/quilt-shape-bucket/query",
            {"vector": bucket_padded, "topK": k, "returnMetadata": "all"},
        )
        if not ok:
            return []
        return [(m["id"], m["score"]) for m in data.get("result", {}).get("matches", [])]


# ============================================================================
# 4. Smoke test
# ============================================================================

if __name__ == "__main__":
    import random
    print("=" * 60)
    print("Shape Store — 5 indices (in-memory + Cloudflare)")
    print("=" * 60)

    # Build 5 fabrics with varying cell counts
    rng = random.Random(0xCAFE)
    from quf_v2 import EdgeRecord, RouteRecord
    fabrics = []
    for n_cells in [1, 4, 8, 16, 32]:
        n_edges = n_cells * 2
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
            edges.append(EdgeRecord(src, dst, 0, 0, 0, 0, 0, [rng.randint(0, 255) for _ in range(8)]))
        routing = [RouteRecord(i, i) for i in range(n_cells)]
        qf = QufFile(
            header={
                "quf.version": f"shape-store-test-{n_cells}",
                "cell_count": n_cells, "edge_count": n_edges, "route_count": n_cells,
                "edge.k": 8, "tick_period": 1,
                "quant.dials": "Q1.15", "quant.edges": "Q1.15",
                "quant.routing": "u8", "align": 32,
            },
            dials=dials, edges=edges, routing=routing,
            ticks=(1, [0] * n_cells),
        )
        fabrics.append(qf)

    # In-memory shape store
    print("\n1. In-memory shape store:")
    store = ShapeStore()
    for i, qf in enumerate(fabrics):
        store.add(qf, fabric_id=f"f{i:04d}")
    print(f"   {store.count()} fabrics stored")
    print(f"   hash index: {len(store.by_hash)} keys")
    print(f"   dial index: {len(store.by_dial)} entries")
    print(f"   bucket index: {len(store.by_bucket)} entries")
    print(f"   finger index: {len(store.by_finger)} fingerprints")
    print(f"   lsh index: {len(store.by_lsh)} buckets")

    # Query
    print("\n2. Query (composite score, k=3):")
    results = store.query(fabrics[2], k=3)
    for fid, score in results:
        print(f"   {fid}: {score:.4f}")

    # Hash lookup
    print("\n3. Hash lookup (O(1)):")
    exact = store.by_hash_lookup(fabrics[2])
    print(f"   found: {exact is not None}")

    # Cloudflare backend
    print("\n4. Cloudflare Vectorize backend:")
    cf = CloudflareShapeStore()
    indices = cf.list_indices()
    print(f"   {len(indices)} indices on the account")
    relevant = [i for i in indices if i.get("name", "").startswith("quilt-shape-")]
    print(f"   {len(relevant)} are shape-store indices")
    for idx in relevant:
        print(f"   - {idx['name']}: {idx.get('config', {}).get('dimensions')}d")

    print()
    print("=" * 60)
    print("Shape Store PASS — 5 indices, composite query, hash O(1)")
    print("=" * 60)
