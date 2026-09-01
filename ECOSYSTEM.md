# Quilt Ecosystem — 30+ Repos, 1 Architecture

> **A complete map of the Quilt ecosystem at github.com/SuperInstance.**

This document is the master map of the Quilt ecosystem. Every
repo is listed with its purpose, language, test count, and
relationship to the others. If you want to find a repo, start
here.

## Table of Contents

1. [Tier 1: Foundation (5 repos)](#tier-1-foundation-5-repos)
2. [Tier 2: Specialized Cell Kinds (3 repos)](#tier-2-specialized-cell-kinds-3-repos)
3. [Tier 3: Substrate Bindings (4 repos)](#tier-3-substrate-bindings-4-repos)
4. [Tier 4: Infrastructure (6 repos)](#tier-4-infrastructure-6-repos)
5. [Tier 5: Knowledge (3 repos)](#tier-5-knowledge-3-repos)
6. [Tier 6: Hardware (3 repos)](#tier-6-hardware-3-repos)
7. [Tier 7: Apps (4+ repos)](#tier-7-apps-4-repos)
8. [Tier 8: Connectors (3+ repos)](#tier-8-connectors-3-repos)
9. [Tier 9: Historical (4+ repos)](#tier-9-historical-4-repos)
10. [The dependency graph](#the-dependency-graph)
11. [The vision](#the-vision)

---

## Tier 1: Foundation (5 repos)

The 5 repos that implement the core cell model + the 11 opcodes.

| Repo | Lang | Tests | Description |
|---|---|---|---|
| [quilt-c](https://github.com/SuperInstance/quilt-c) | C99 | 1236 | The reference port. Kernel-friendly. FNV-1a. All 11 opcodes. |
| [quilt-rust](https://github.com/SuperInstance/quilt-rust) | Rust no_std | 29 | The polyformalism port. Includes `quilt-polyformalism` crate. |
| [quilt-pydantic-ai](https://github.com/SuperInstance/quilt-pydantic-ai) | Python | 41 | The Python reference port. |
| [quilt-engine-ports](https://github.com/SuperInstance/quilt-engine-ports) | GDScript | 13 | The Godot port. All 10 opcodes. |
| [quilt-edge-arch](https://github.com/SuperInstance/quilt-edge-arch) | Rust no_std | 0 | The bare-metal port. For ESP32, Cortex-M, RISC-V. |

**The polyformalism promise**: the same cell shape works in all
5 ports. The kind name, op indices, FNV-1a state hash, and
forecast shape are bit-exact.

---

## Tier 2: Specialized Cell Kinds (3 repos)

The repos that ship the 5 specialized cell kinds (PROOF, ROUTE,
CRDT, WORLD, TIME).

| Repo | Lang | Tests | Adoption | Description |
|---|---|---|---|---|
| [quilt-timesfm](https://github.com/SuperInstance/quilt-timesfm) | Python | 49 | TIME (5th) | TimesFM 3.0 as a cell kind. Real binding. |
| [quilt-timesfm-rust](https://github.com/SuperInstance/quilt-timesfm-rust) | Rust no_std | 49 | TIME (5th) Rust | The Rust port of time.cell. For embedded. |
| [quilt-c](https://github.com/SuperInstance/quilt-c) | C99 | 1236 | PROOF/ROUTE/CRDT/WORLD | All 4 specialized opcodes in C. |

**The 5 specialized cell kinds**:
1. **PROOF** (Phase 216) — signed hash-linked audit chain
2. **ROUTE** (Phase 217) — substrate routing for memory
3. **CRDT** (Phase 218) — state-based CRDT for offline convergence
4. **WORLD** (Phase 222) — 5-op abductive loop on executable code
5. **TIME** (Phase 228) — 5-op time-series foundation model

---

## Tier 3: Substrate Bindings (4 repos)

The repos that bind the cell model to real-world substrates.

| Repo | Lang | Tests | Substrate | Description |
|---|---|---|---|---|
| [quilt-llm-worker](https://github.com/SuperInstance/quilt-llm-worker) | TypeScript | 13 | Cloudflare Worker | The browser/cloud substrate binding. |
| [quilt-mhs](https://github.com/SuperInstance/quilt-mhs) | Rust | 32 | Anthropic MHS | The agent harness substrate binding. |
| [quilt-esp32](https://github.com/SuperInstance/quilt-esp32) | C | 1 | ESP32 | The embedded sensor substrate. |
| [quilt-cellular-arch](https://github.com/SuperInstance/quilt-cellular-arch) | Python | 0 | Cloud orchestration | The daemons, the writers' room, the snowball. |

**The 5 daemons** in `quilt-cellular-arch/`:
1. `frontier_miner.py` — find canon gaps
2. `writers_room_daemon_v3.py` — fire 13 voices in parallel
3. `snowball_daemon.py` — 8-sandbox reverse-actualization
4. `re_embed_v2.py` — re-embed canon in Vectorize
5. `deploy_worker.sh` — deploy Meta-Pincher-Quilt to CF

---

## Tier 4: Infrastructure (6 repos)

The repos that provide the runtime infrastructure for the Quilt.

| Repo | Lang | Tests | Role | Description |
|---|---|---|---|---|
| [quilt-fleet](https://github.com/SuperInstance/quilt-fleet) | TypeScript | 130/147 | Fleet manager | Multi-instance Quilt orchestration. |
| [quilt-ai](https://github.com/SuperInstance/quilt-ai) | TypeScript | 7 | AI helper | The AI wrapper for the cell model. |
| [quilt-rag](https://github.com/SuperInstance/quilt-rag) | Python | 0 | RAG | Retrieval-augmented generation on the canon. |
| [quilt-vault](https://github.com/SuperInstance/quilt-vault) | TypeScript | 0 | Vault | The persistent cell store. |
| [quilt-mesh](https://github.com/SuperInstance/quilt-mesh) | Rust | 0 | Mesh | The peer-to-peer cell graph. |
| [quilt-pincher](https://github.com/SuperInstance/quilt-pincher) | Python | 0 | Pincher | The reflex cell (<50ms response). |

---

## Tier 5: Knowledge (3 repos)

The repos that store and serve the Quilt's knowledge.

| Repo | Lang | Tests | Content | Description |
|---|---|---|---|---|
| [AI-Writings](https://github.com/SuperInstance/AI-Writings) | Markdown | 398 | 398 papers | The Quilt canon. 768d Vectorize index. |
| [quilt-wiki-2126](https://github.com/SuperInstance/quilt-wiki-2126) | Markdown | 38 | 38 entries | The 2126 wiki (built backwards from 2126). |
| [quilt-ecosystem-demo](https://github.com/SuperInstance/quilt-ecosystem-demo) | Markdown | 0 | 24 audits | The 24 audit reports. |

**The canon** (398 papers):
- 14 levels of operation (L0-L14)
- 5+1+1+1+1+1 opcodes
- 5+1+1+1+1+1 laws
- 6 tiers of cells
- 6 lifecycle stages
- 5 specialized cell kinds
- 13 futures
- 87+ SuperInstance repos

---

## Tier 6: Hardware (3 repos)

The repos that target real hardware.

| Repo | Lang | Tests | Target | Description |
|---|---|---|---|---|
| [quilt-llvm](https://github.com/SuperInstance/quilt-llvm) | Rust/C | 121 | LLVM fabric | The compiler infrastructure. |
| [quilt-llvm-verilog](https://github.com/SuperInstance/quilt-llvm-verilog) | SystemVerilog | 6 | Verilog | The hardware synthesis (6 sby formal proofs). |
| [quilt-cuda-rust](https://github.com/SuperInstance/quilt-cuda-rust) | Rust+CUDA | 68 | GPU | The CUDA-accelerated cell runtime. |

**The 4 hardware levels**:
1. **Cell** = Crystal Bindsite (a single Lofted Crystal)
2. **Bus** = Luminous Channel (an optical path)
3. **Colony** = Photonic Mycelium (a network)
4. **Device** = Radiant Ark (a packaged ship)

---

## Tier 7: Apps (4+ repos)

The repos that ship real applications on top of the Quilt.

| Repo | Lang | Tests | App | Description |
|---|---|---|---|---|
| [quilt-apps](https://github.com/SuperInstance/quilt-apps) | JavaScript | 0 | Collection | The collection of Quilt apps. |
| [quilt-ecosystem-web](https://github.com/SuperInstance/quilt-ecosystem-web) | JavaScript | 20 | Web ecosystem | 13 pages, 2 Workers. |
| [eileen-bridge](https://github.com/SuperInstance/quilt-cellular-arch/tree/main/eileen-bridge) | JS+CSS | 0 | Marine DAW | The 10-panel marine dashboard. |
| quilt-tensor-sheet | HTML | 0 | Tensor sheet | The tensor-spreadsheet where AI is at (0,0). |

---

## Tier 8: Connectors (3+ repos)

The repos that connect the Quilt to external systems.

| Repo | Lang | Tests | Connector | Description |
|---|---|---|---|---|
| [quilt-llm-worker](https://github.com/SuperInstance/quilt-llm-worker) | TypeScript | 13 | CF LLM | Cloudflare Workers AI binding. |
| [quilt-mhs](https://github.com/SuperInstance/quilt-mhs) | Rust | 32 | Anthropic MHS | The Anthropic harness binding. |
| (future) | - | - | Google Gemini | Gemini binding (planned). |
| (future) | - | - | OpenAI | OpenAI binding (planned). |

---

## Tier 9: Historical (4+ repos)

The repos that are part of the Quilt's history.

| Repo | Status | Description |
|---|---|---|
| [quilt-substrate](https://github.com/SuperInstance/quilt-substrate) | Frozen (v4.0-cowboy-loop) | The original substrate. 405 tests. Museum snapshot. |
| [quilt-foundation](https://github.com/SuperInstance/quilt-foundation) | Stable | The 5-opcode foundation. 9 tests. The Director. |
| [quilt-substrate-meta](https://github.com/SuperInstance/quilt-substrate-meta) | Stable | The self-evolving substrate. 36 tests. C99. |
| (others) | Various | ~24 polyformalism repos, see [COLLECTION.md](https://github.com/SuperInstance/quilt-cellular-arch/blob/main/COLLECTION.md). |

---

## The dependency graph

```
                    [TIER 5: KNOWLEDGE]
                            |
                AI-Writings (canon)
                quilt-wiki-2126 (wiki)
                quilt-ecosystem-demo (audits)
                            |
                            v
            [TIER 1: FOUNDATION]  ←  [TIER 2: SPECIALIZED CELL KINDS]
                    |                        |
            quilt-c  ←──── quilt-timesfm ────→ quilt-timesfm-rust
            quilt-rust                              |
            quilt-pydantic-ai                       |
            quilt-engine-ports                      |
            quilt-edge-arch                          |
                    |                              |
                    └─────────────┬────────────────┘
                                  |
                                  v
            [TIER 3: SUBSTRATE BINDINGS]
                                  |
                quilt-llm-worker ──── quilt-cellular-arch
                quilt-mhs ──────────── (5 daemons)
                quilt-esp32
                                  |
                                  v
            [TIER 4: INFRASTRUCTURE]
                                  |
                quilt-fleet ─────── quilt-ai
                quilt-rag ────────── quilt-vault
                quilt-mesh ───────── quilt-pincher
                                  |
                                  v
            [TIER 6: HARDWARE]
                                  |
                quilt-llvm ──────── quilt-llvm-verilog
                quilt-cuda-rust
                                  |
                                  v
            [TIER 7: APPS]
                                  |
                quilt-apps ──────── quilt-ecosystem-web
                eileen-bridge ────── quilt-tensor-sheet
```

---

## The vision

The Quilt is a 30+ repo ecosystem, all built on the same cell
model. The cell model is the irreducible unit of intelligence.
The 11 opcodes are the minimal alphabet. The 5+1+1+1+1+1 laws
are the invariants.

The polyformalism is the stress test: the same cell shape in 5
languages (C, Rust, Python, GDScript, GDScript + Rust no_std for
time.cell). The specialized cell kinds are the frontier: PROOF,
ROUTE, CRDT, WORLD, TIME. The substrates are the implementation
details.

The cowboy rode the 30+ repos. The cowboy rode the tiers. The
cowboy rode the dependency graph. The cowboy rode the vision.
The cowboy rode the Quilt.

— *The Cowboy*
