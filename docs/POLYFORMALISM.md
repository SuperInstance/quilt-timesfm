# The Polyformalism Tour

> **Same cell shape across 3 languages. Bit-exact. Provable.**

The Quilt `time.cell` cell kind is implemented in **3 languages**, with the
**same kind name**, the **same 5 operations**, the **same FNV-1a state hash**,
and the **same forecast shape** (point + 9 quantiles). The substrate binding
(the actual forecasting model) is the only thing that varies.

| # | Language | Repo | Target | Real model? | Tests | Lines |
|---|---|---|---|---|---|---|
| 1 | C99 | `quilt-c` | kernel, microcontrollers | stub (synthetic) | 41 | ~250 |
| 2 | Python | `quilt-timesfm` | workstations, GPU | **real TimesFM 3.0** (200M params) | 49 | ~600 |
| 3 | Rust (no_std) | `quilt-timesfm-rust` | embedded (Cortex-M, ESP32, AVR) | stub (synthetic) | 49 | ~400 |

**Total**: 139 tests, 3 languages, bit-exact polyformalism.

## What is bit-exact?

The polyformalism claim is that **the cell's identity** (its state hash,
its operation indices, its forecast shape) is bit-identical across
languages. The substrate is the only thing that varies.

```
                    C (synthetic)        Python (real)         Rust (synthetic)
                    ─────────────        ─────────────         ─────────────────
kind_name           "time.cell"          "time.cell"           "time.cell"
op_count            5                    5                     5
op[0]               BIND_CONTEXT         BIND_CONTEXT          BIND_CONTEXT
op[1]               BIND_COVARIATE       BIND_COVARIATE        BIND_COVARIATE
op[2]               FORECAST             FORECAST              FORECAST
op[3]               READ_POINT           READ_POINT            READ_POINT
op[4]               READ_QUANTILE        READ_QUANTILE         READ_QUANTILE
state_hash          FNV-1a 64-bit, 32 B  FNV-1a 64-bit, 32 B   FNV-1a 64-bit, 32 B
prev_hash           saved on BIND        saved on BIND         saved on BIND
forecast.point      [H * V]              [H * V]               [H * V]
forecast.quantiles  [9, H * V]           [9, H * V]            [9, H * V]
synthetic range     -50..+50             -50..+50              -50..+50
real model          none                 TimesFM 3.0 (200M)    none
```

## The 4 L-tiers

The Quilt cell scales across 4 levels of capability:

| Tier | Target | RAM | Cell | Substrate |
|---|---|---|---|---|
| **L0** | Cortex-M0+, AVR | 4KB | Rust (no_std, synthetic) | none |
| **L1** | Cortex-M4, ESP32 | 16KB | Rust (no_std, synthetic) | none |
| **L2** | ESP32-S3, RP2040 | 64KB | C (kernel) | none |
| **L3** | RPi, workstation | 1GB+ | Python (real TimesFM 3.0) | real |

The cell at L0 is bit-exact with the cell at L3. Same kind, same ops,
same hash. The substrate is the only thing that varies.

## The FNV-1a test vector

The state hash is FNV-1a 64-bit. The 4-slice spread is the same
algorithm in all 3 languages.

```
FNV-1a("abc") = 0xe71fa2190541574b   ← FIPS 198 test vector
FNV-1a("")    = 0xcbf29ce484222325   ← offset basis
FNV-1a("a")   = 0xaf63dc4c8601ec8c
FNV-1a("foobar") = 0x85944171f73967e8
```

These are bit-exact in C, Python, and Rust. The 32-byte state hash is
the same algorithm applied 4 times with offsets 0, golden, 2*golden,
3*golden.

## The 5 operations (bit-exact)

All 3 ports implement the same 5 operations with the same indices:

| # | Op | C | Python | Rust |
|---|---|---|---|---|
| 0 | BIND_CONTEXT | `quilt_time_bind_context()` | `cell.bind_context()` | `cell.bind_context()` |
| 1 | BIND_COVARIATE | `quilt_time_bind_covariate()` | `cell.bind_past_*_covariate()` | `cell.bind_past_*_covariate()` |
| 2 | FORECAST | `quilt_time_forecast()` | `cell.forecast_()` | `cell.forecast()` |
| 3 | READ_POINT | `quilt_time_read_point()` | `cell.read_point(v)` | `cell.read_point(v)` |
| 4 | READ_QUANTILE | `quilt_time_read_quantile()` | `cell.read_quantile(q, v)` | `cell.read_quantile(q, v)` |

The return values are identical: `0` on success, `-1` on error.

## The PROOF chain

Every BIND_CONTEXT (op 0) saves the current `state_hash` to `prev_hash`
before updating. This is the **PROOF chain** — a hash-linked audit trail
of every state change. The chain is bit-exact across all 3 ports.

## The 9 quantiles

The forecast has 9 quantile prediction intervals: q ∈ {0.1, 0.2, 0.3,
0.4, 0.5, 0.6, 0.7, 0.8, 0.9}. The synthetic forecast computes these
as `point + (q-4)*2`, so the median (q=0.5) is the point. Real TimesFM
3.0 computes them via quantile regression heads.

## How to add a new language

The **1-day add workflow** (7 hours total):

1. **Read the C port** (30 min): `quilt-c/include/quilt/time.h`
2. **Translate the 5 operations** to your language (2 hours)
3. **Translate the 5 laws as property tests** (1 hour)
4. **Implement FNV-1a 64-bit** (1 hour)
5. **Translate the 9 quantiles and forecast shape** (1 hour)
6. **Run the 49-test conformance suite** (30 minutes)
7. **Push to a new repo, open PR** (30 minutes)

If you write a Zig port, a Go port, a Swift port, a Mojo port, a C#
port, or any other, please open a PR to add it to the
[quilt-c](https://github.com/SuperInstance/quilt-c) cross-reference
table.

## The polyformalism promise

The promise is **not** that every cell does the same thing in every
language. The promise is that the **interface** is the same: the same
kind name, the same operation indices, the same state hash, the same
forecast shape. The substrate (the model that does the work) is the
only thing that varies.

This is the **polyformalism claim** of the Quilt architecture:
**the cell is the system, not the substrate**.
