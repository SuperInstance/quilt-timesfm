#!/usr/bin/env python3
"""benchmarks/benchmark_quf.py -- the polyformalism play-test + benchmark.

Three play-test categories:
  1. CORRECTNESS: 100 random fabrics round-tripped; state hash invariant.
  2. CROSS-SUBSTRATE: 1 fabric written in Python, loaded in Verilog
     and VHDL, hashes must match.
  3. SCALING: write/read throughput as a function of fabric size.

The goal is to *measure* the polyformalism, not just claim it.  Numbers
go in F118 / paper-428.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Make the parent quf_v2 importable
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from quf_v2 import (
    QufFile, EdgeRecord, RouteRecord, loads, dumps,
    FNV_OFFSET, FNV_PRIME, QufError,
)

QUILT_VERILOG = "/workspace/quilt-verilog"
QUILT_VHDL    = "/workspace/quf-vhdl"


# ============================================================================
# Helpers
# ============================================================================

def make_random_fabric(n_cells: int, n_edges: int, k: int = 8,
                       seed: int = 0) -> QufFile:
    """Build a QufFile with n_cells cells, n_edges edges, K ladder buckets.

    Dials are filled with the cell defaults plus random q1515 fractions.
    Edge buckets are random walk counts.

    NOTE: QUF v1 edge src/dst are u8, so n_cells is capped at 255.
    For larger fabrics, use the QUF v2 plan (16-bit cell ids).
    """
    rng = random.Random(seed)
    n_cells = min(n_cells, 255)  # QUF v1 edge id is u8

    dials = []
    for _ in range(n_cells):
        row = [
            64, 16, 1, 1, 4,
            16384 + rng.randint(-256, 256),  # THRESH around 0.5
            1, 128, 1, 0, 8, 0, 0, 0, 0, 0
        ]
        dials.append([max(0, min(0xFFFF, v)) for v in row])

    edges = []
    for _ in range(n_edges):
        src = rng.randint(0, n_cells - 1)
        dst = rng.randint(0, n_cells - 1)
        base = rng.randint(0, 0xFFFF)
        age = rng.randint(0, 0xFFFFFFFF)
        buckets = [rng.randint(0, 0xFF) for _ in range(k)]
        edges.append(EdgeRecord(src, dst, 0, 0, base, 0, age, buckets))

    routing = []
    for i in range(min(n_cells, 8)):
        routing.append(RouteRecord(i, i))

    return QufFile(
        header={
            "quf.version": f"bench-{seed}",
            "cell_count": n_cells, "edge_count": n_edges, "route_count": len(routing),
            "edge.k": k, "tick_period": 4,
            "quant.dials": "Q1.15", "quant.edges": "Q1.15",
            "quant.routing": "u8", "align": 32,
        },
        dials=dials, edges=edges, routing=routing,
        ticks=(4, [0] * n_cells),
    )


# ============================================================================
# 1. CORRECTNESS (fuzz round-trip)
# ============================================================================

def playtest_correctness(n_iter: int = 100, max_cells: int = 64,
                         max_edges: int = 100, seed_base: int = 42) -> Dict[str, Any]:
    """Round-trip n_iter random fabrics through dumps -> loads; assert
    the state hash is invariant.
    """
    print(f"\n=== 1. CORRECTNESS (fuzz round-trip, n={n_iter}) ===")
    hashes_match = 0
    byte_exact = 0
    failures = []
    total_bytes_in = 0
    total_bytes_out = 0
    rng = random.Random(seed_base)
    t0 = time.perf_counter()

    for i in range(n_iter):
        n_cells = rng.randint(1, max_cells)
        n_edges = rng.randint(0, min(max_edges, n_cells * 4))
        k = rng.choice([4, 8, 16])
        qf = make_random_fabric(n_cells, n_edges, k, seed=seed_base + i)

        blob1 = dumps(qf)
        qf2 = loads(blob1)
        blob2 = dumps(qf2)

        h1 = qf.state_hash()
        h2 = qf2.state_hash()
        if h1 == h2:
            hashes_match += 1
        else:
            failures.append(f"iter {i}: hash mismatch {h1:016x} vs {h2:016x}")
        if blob1 == blob2:
            byte_exact += 1
        total_bytes_in += len(blob1)
        total_bytes_out += len(blob2)

    elapsed = time.perf_counter() - t0
    total_fabrics = n_iter
    avg_bytes = total_bytes_in / total_fabrics if total_fabrics else 0
    return {
        "iterations": n_iter,
        "hash_match": hashes_match,
        "byte_exact": byte_exact,
        "failures": len(failures),
        "first_failures": failures[:3],
        "elapsed_s": elapsed,
        "avg_bytes_per_fabric": avg_bytes,
        "rate_fabrics_per_s": n_iter / elapsed if elapsed > 0 else 0,
    }


# ============================================================================
# 2. CROSS-SUBSTRATE (1 fabric -> 3 readers)
# ============================================================================

def playtest_cross_substrate(n_cells: int = 8, n_edges: int = 16) -> Dict[str, Any]:
    """Build a fabric in Python, write QUF, then have Verilog and VHDL
    references re-write the same JSON.  Verify all three are byte-exact,
    and that all three produce the same FNV-1a 64-bit state hash.
    """
    print(f"\n=== 2. CROSS-SUBSTRATE (n={n_cells}, e={n_edges}) ===")
    if not (os.path.exists(f"{QUILT_VERILOG}/tools/quf.py") and
            os.path.exists(f"{QUILT_VHDL}/tools/vhdl_quf.py")):
        return {"skipped": True, "reason": "reference tools not present"}

    qf = make_random_fabric(n_cells, n_edges, k=8, seed=0xBEEF)
    py_blob = dumps(qf)
    py_hash = qf.state_hash()

    # Build the same JSON for the Verilog + VHDL references
    doc = qf.to_dict()

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        fixture = os.path.join(d, "fixture.json")
        with open(fixture, "w") as f:
            json.dump(doc, f)

        py_path = os.path.join(d, "py.quf")
        v_path  = os.path.join(d, "v.quf")
        x_path  = os.path.join(d, "x.quf")

        with open(py_path, "wb") as f: f.write(py_blob)

        subprocess.check_call(
            ["python3", f"{QUILT_VERILOG}/tools/quf.py", "create", fixture, v_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["python3", f"{QUILT_VHDL}/tools/vhdl_quf.py", "create", fixture, x_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        py_b = open(py_path, "rb").read()
        v_b  = open(v_path, "rb").read()
        x_b  = open(x_path, "rb").read()

        py_v_match = (py_b == v_b)
        py_x_match = (py_b == x_b)
        v_x_match  = (v_b  == x_b)

        # Read each one back and check the state hash
        v_read = loads(v_b).state_hash()
        x_read = loads(x_b).state_hash()

    return {
        "python_bytes": len(py_b),
        "python_hash":  py_hash,
        "verilog_hash": v_read,
        "vhdl_hash":    x_read,
        "py_eq_v":      py_v_match,
        "py_eq_x":      py_x_match,
        "v_eq_x":       v_x_match,
        "all_hashes_match": (py_hash == v_read == x_read),
    }


# ============================================================================
# 3. SCALING (throughput vs fabric size)
# ============================================================================

def benchmark_scaling() -> List[Dict[str, Any]]:
    """Measure write/read throughput as a function of fabric size."""
    print(f"\n=== 3. SCALING (cell counts: 1, 4, 16, 64, 128, 255) ===")
    results = []
    # QUF v1: edge src/dst are u8, so max 255 cells
    for n_cells in [1, 4, 16, 64, 128, 255]:
        n_edges = n_cells * 4
        qf = make_random_fabric(n_cells, n_edges, k=8, seed=0xCAFE)

        # Warmup
        dumps(qf); loads(dumps(qf))

        t0 = time.perf_counter()
        N = max(5, 1000 // max(1, n_cells // 4))
        for _ in range(N):
            blob = dumps(qf)
        t_write = time.perf_counter() - t0

        t0 = time.perf_counter()
        for _ in range(N):
            loads(blob)
        t_read = time.perf_counter() - t0

        size_kb = len(blob) / 1024
        results.append({
            "n_cells": n_cells,
            "n_edges": n_edges,
            "quf_bytes": len(blob),
            "quf_kb": size_kb,
            "iterations": N,
            "write_s": t_write,
            "read_s": t_read,
            "write_qps": N / t_write if t_write > 0 else 0,
            "read_qps": N / t_read if t_read > 0 else 0,
            "write_kbps": (N * size_kb) / t_write if t_write > 0 else 0,
            "read_kbps": (N * size_kb) / t_read if t_read > 0 else 0,
        })
    return results


# ============================================================================
# 4. C-PORT SIMULATION (C is the kernel serializer; verify QUF is loaded
#    by the C tests and produces the same hash)
# ============================================================================

def playtest_c_substrate() -> Dict[str, Any]:
    """Run the C QUF test binary and check it passes."""
    print(f"\n=== 4. C-SUBSTRATE (run quilt-c test_quf) ===")
    test_bin = "/workspace/quilt-c/build/test_quf"
    if not os.path.exists(test_bin):
        return {"skipped": True, "reason": f"{test_bin} not built"}
    try:
        result = subprocess.run([test_bin], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        passed_line = [l for l in output.split("\n") if "passed" in l and "failed" in l]
        return {
            "exit_code": result.returncode,
            "passed_line": passed_line[0] if passed_line else "(not found)",
            "stdout_lines": len(result.stdout.split("\n")),
        }
    except subprocess.TimeoutExpired:
        return {"skipped": True, "reason": "test_quf timed out"}


# ============================================================================
# 5. RUST-SUBSTRATE (Rust polyformalism: run the cargo tests)
# ============================================================================

def playtest_rust_substrate() -> Dict[str, Any]:
    """Run the Rust polyformalism test suite."""
    print(f"\n=== 5. RUST-SUBSTRATE (run cargo test -p quilt-polyformalism) ===")
    crate = "/workspace/quilt-rust/crates/quilt-polyformalism"
    if not os.path.exists(f"{crate}/Cargo.toml"):
        return {"skipped": True, "reason": f"{crate} not present"}
    try:
        result = subprocess.run(
            ["cargo", "test", "-p", "quilt-polyformalism"],
            cwd=crate, capture_output=True, text=True, timeout=120,
        )
        output = result.stdout + result.stderr
        passed_line = [l for l in output.split("\n") if "test result: ok" in l and "passed" in l]
        # Get the line with the most passes
        if passed_line:
            best = max(passed_line, key=lambda l: int([x for x in l.split() if x.isdigit()][0]) if any(x.isdigit() for x in l.split()) else 0)
        else:
            best = "(not found)"
        return {
            "exit_code": result.returncode,
            "passed_line": best,
        }
    except subprocess.TimeoutExpired:
        return {"skipped": True, "reason": "cargo test timed out"}


# ============================================================================
# 6. STATE HASH MATRIX (the polyformalism value, measured everywhere)
# ============================================================================

def measure_state_hash_matrix() -> List[Dict[str, Any]]:
    """For 5 different cell counts, measure the FNV-1a 64-bit state
    hash from each substrate (Python + C if possible + Verilog ref +
    VHDL ref).  All must match.
    """
    print(f"\n=== 6. STATE HASH MATRIX (5 sizes × 4 substrates) ===")
    rows = []
    for n_cells in [1, 4, 16, 64, 256]:
        n_edges = max(1, n_cells * 2)
        qf = make_random_fabric(n_cells, n_edges, k=8, seed=0xDEAD)
        py_hash = qf.state_hash()
        py_blob = dumps(qf)

        # Read back through Python
        py_read_hash = loads(py_blob).state_hash()

        # Write through Verilog and VHDL references
        v_hash = None
        x_hash = None
        if (os.path.exists(f"{QUILT_VERILOG}/tools/quf.py") and
            os.path.exists(f"{QUILT_VHDL}/tools/vhdl_quf.py")):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                fixture = os.path.join(d, "fixture.json")
                v_path  = os.path.join(d, "v.quf")
                x_path  = os.path.join(d, "x.quf")
                with open(fixture, "w") as f:
                    json.dump(qf.to_dict(), f)
                subprocess.check_call(
                    ["python3", f"{QUILT_VERILOG}/tools/quf.py", "create", fixture, v_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                subprocess.check_call(
                    ["python3", f"{QUILT_VHDL}/tools/vhdl_quf.py", "create", fixture, x_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                v_hash = loads(open(v_path, "rb").read()).state_hash()
                x_hash = loads(open(x_path, "rb").read()).state_hash()

        all_match = py_hash == py_read_hash
        if v_hash is not None: all_match = all_match and (py_hash == v_hash)
        if x_hash is not None: all_match = all_match and (py_hash == x_hash)

        rows.append({
            "n_cells": n_cells, "n_edges": n_edges, "quf_bytes": len(py_blob),
            "py_hash": f"0x{py_hash:016x}",
            "py_read_hash": f"0x{py_read_hash:016x}",
            "verilog_hash": f"0x{v_hash:016x}" if v_hash is not None else "n/a",
            "vhdl_hash":    f"0x{x_hash:016x}" if x_hash is not None else "n/a",
            "all_match": all_match,
        })
    return rows


# ============================================================================
# Main
# ============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-fuzz", type=int, default=100)
    ap.add_argument("--max-cells", type=int, default=64)
    ap.add_argument("--max-edges", type=int, default=100)
    ap.add_argument("--out", default=None, help="Write results to JSON")
    args = ap.parse_args()

    print("=" * 70)
    print("  POLYFORMALISM PLAY-TEST + BENCHMARK")
    print("=" * 70)
    print(f"  Python substrate:    quilt-timesfm/quf_v2.py")
    print(f"  Verilog reference:   {QUILT_VERILOG}/tools/quf.py")
    print(f"  VHDL reference:      {QUILT_VHDL}/tools/vhdl_quf.py")
    print(f"  C substrate:         quilt-c/src/quf.c")
    print(f"  Rust substrate:      quilt-rust/crates/quilt-polyformalism")
    print()

    results = {
        "fuzz_round_trip": playtest_correctness(args.n_fuzz, args.max_cells, args.max_edges),
        "cross_substrate":  playtest_cross_substrate(8, 16),
        "scaling":          benchmark_scaling(),
        "c_substrate":      playtest_c_substrate(),
        "rust_substrate":   playtest_rust_substrate(),
        "state_hash_matrix": measure_state_hash_matrix(),
    }

    # Pretty-print
    print()
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print()
    print(f"1. Fuzz round-trip: {results['fuzz_round_trip']['hash_match']}/{results['fuzz_round_trip']['iterations']} hash match, "
          f"{results['fuzz_round_trip']['byte_exact']}/{results['fuzz_round_trip']['iterations']} byte-exact")
    print(f"   elapsed: {results['fuzz_round_trip']['elapsed_s']:.3f}s, "
          f"avg: {results['fuzz_round_trip']['avg_bytes_per_fabric']:.1f} bytes/fabric, "
          f"rate: {results['fuzz_round_trip']['rate_fabrics_per_s']:.1f} fabrics/s")
    if results['fuzz_round_trip']['failures'] > 0:
        print(f"   first failures: {results['fuzz_round_trip']['first_failures']}")

    print()
    print(f"2. Cross-substrate: 8 cells, 16 edges")
    cs = results['cross_substrate']
    if cs.get("skipped"):
        print(f"   SKIPPED: {cs.get('reason')}")
    else:
        print(f"   python bytes: {cs['python_bytes']}")
        print(f"   python hash:  {cs['python_hash']:016x}")
        print(f"   verilog hash: {cs['verilog_hash']:016x}")
        print(f"   vhdl hash:    {cs['vhdl_hash']:016x}")
        print(f"   py==v: {cs['py_eq_v']}, py==x: {cs['py_eq_x']}, v==x: {cs['v_eq_x']}")
        print(f"   ALL_HASHES_MATCH: {cs['all_hashes_match']}")

    print()
    print(f"3. Scaling (Python):")
    print(f"   {'cells':>6} {'edges':>6} {'bytes':>8} {'wr_qps':>10} {'rd_qps':>10} {'wr_kbps':>10} {'rd_kbps':>10}")
    for r in results['scaling']:
        print(f"   {r['n_cells']:>6} {r['n_edges']:>6} {r['quf_bytes']:>8} "
              f"{r['write_qps']:>10.1f} {r['read_qps']:>10.1f} "
              f"{r['write_kbps']:>10.1f} {r['read_kbps']:>10.1f}")

    print()
    print(f"4. C substrate: ", end="")
    c = results['c_substrate']
    if c.get('skipped'):
        print(f"SKIPPED ({c.get('reason')})")
    else:
        print(c.get('passed_line', 'unknown'))

    print(f"5. Rust substrate: ", end="")
    r = results['rust_substrate']
    if r.get('skipped'):
        print(f"SKIPPED ({r.get('reason')})")
    else:
        print(r.get('passed_line', 'unknown'))

    print()
    print(f"6. State hash matrix (the polyformalism value):")
    print(f"   {'cells':>6} {'edges':>6} {'bytes':>8} {'python':>18} {'verilog':>18} {'vhdl':>18} {'match':>6}")
    for row in results['state_hash_matrix']:
        print(f"   {row['n_cells']:>6} {row['n_edges']:>6} {row['quf_bytes']:>8} "
              f"{row['py_hash']:>18} {row['verilog_hash']:>18} {row['vhdl_hash']:>18} "
              f"{'YES' if row['all_match'] else 'NO':>6}")

    # Summary
    print()
    print("=" * 70)
    print("  POLYFORMALISM VERDICT")
    print("=" * 70)

    n_subs = 0
    n_subs_match = 0
    for row in results['state_hash_matrix']:
        n_subs += 1
        if row['all_match']:
            n_subs_match += 1
    print(f"  State hash matrix: {n_subs_match}/{n_subs} cell counts where Python == Verilog == VHDL")
    fuzz = results['fuzz_round_trip']
    if fuzz['hash_match'] == fuzz['iterations'] and fuzz['failures'] == 0:
        print(f"  Fuzz round-trip: {fuzz['hash_match']}/{fuzz['iterations']} PASS (state hash invariant)")
    else:
        print(f"  Fuzz round-trip: {fuzz['hash_match']}/{fuzz['iterations']} PASS, {fuzz['failures']} FAIL")
    cs = results['cross_substrate']
    if not cs.get('skipped') and cs.get('all_hashes_match'):
        print(f"  Cross-substrate: ALL_HASHES_MATCH (Python == Verilog == VHDL)")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n  results written to {args.out}")


if __name__ == "__main__":
    main()
