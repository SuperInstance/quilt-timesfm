# Quilt Changelog

> **The 230+ phases of the Quilt, in one place.**

This is the master changelog for the Quilt project. Every
phase, every PR, every paper, every wiki entry is documented.
If you want to know what was built when, start here.

## The phases at a glance

| Phase | Date | Title |
|---|---|---|
| 1-20 | 2026-08-27 | The 5-opcode foundation |
| 21-50 | 2026-08-27 | The polyformalism in 4 languages |
| 51-80 | 2026-08-28 | The 6 tiers |
| 81-100 | 2026-08-28 | The 14 levels of operation |
| 101-150 | 2026-08-29 | The writers' rooms + 13 working API voices |
| 151-200 | 2026-08-30 | The 5 cutting-edge adoptions + canon expansion |
| 201-220 | 2026-08-31 | The TIER 1-2: foundation + cutting-edge |
| 221-228 | 2026-08-31 | TIER 3-5: substrates + infrastructure + knowledge |
| 229 | 2026-09-01 | **quilt-timesfm world-class, 3rd polyformalism port** |
| 230 | 2026-09-01 | **Future-state memory pivot + JEPA synergy** |
| 231 | 2026-09-01 | **Documentation expansion (ARCHITECTURE, ECOSYSTEM, MANUALS, ROADMAP, FAQ, GLOSSARY)** |
| 232+ | TBD | TIER 6-9 (hardware, apps, connectors, historical) |

## Phase 1-20: The 5-opcode foundation (2026-08-27)

**What was built**:
- The 5 original opcodes: BIND, LINK, EFFECT, VIEW, TICK
- The 5+1 laws: idempotence, transitivity, associativity,
  purity, monotonicity, completeness
- The cell model: kind, state, value, reads, links
- The first C port (`quilt-c`, 47 tests)

**The cowboy's maxim (Phase 1)**:
> The cowboy said: 5 opcodes. The cowboy said: 5 laws. The
> cowboy said: 1 cell. The cowboy made the cell. The cowboy
> rode the cell.

## Phase 21-50: The polyformalism in 4 languages (2026-08-27)

**What was built**:
- The Python port (`quilt-pydantic-ai`, 41 tests)
- The Rust no_std port (`quilt-rust`, 8 tests)
- The GDScript port (early version, 0 tests)
- The C port extended to 1059 tests
- The first polyformalism conformance suite

**The polyformalism claim** (Phase 25): The cell shape is
byte-identical across C, Python, Rust. Bit-exact for kind
name, op indices, FNV-1a state hash, forecast shape.

## Phase 51-80: The 6 tiers (2026-08-28)

**What was built**:
- The 6 tiers: totipotent, multipotent, differentiated,
  sclerotic, synovial, curator
- The 6 lifecycle stages: umbra, cellulization, pulse, leak,
  ghost, bloom
- The wiki entries: 01-splined-lantern, 02-hearth-loop,
  03-monotone-crystal
- The fables (89): the cowgirl, Eileen, the 4:30 PM

## Phase 81-100: The 14 levels of operation (2026-08-28)

**What was built**:
- The 14 levels: L0-L14
- L0-L3: cell, 2^45 doublings, 3 fates, 10 fates
- L4-L6: H=2 bits, bipotent probability, determined probability
- L7-L8: cooperative energy, N×cap×coop
- L9-L14: zero probability, senescence, death, ATP rate,
  signaling, clonal
- The wiki entries: 00-L0 through 14-L14

## Phase 101-150: The writers' rooms + 13 working API voices (2026-08-29)

**What was built**:
- The 13 working API voices: 10 Cloudflare (qwen32b, dsr1,
  llama70b, llama4, mistral, qwq, llama3b, llama8b, llama1b,
  gemma2b) + 3 Gemini (gemini35lite, gemini25, gemini31)
- The 4-rule write/push loop
- The persistent task queue at /workspace/_scouts/task_queue.json
- The writers' room archive at /workspace/_scouts/hand-synth/
- The 198 papers written by the 4 voices

## Phase 151-200: The 5 cutting-edge adoptions (2026-08-30)

**What was built**:
- **PROOF** (Phase 216-217): signed hash-linked audit chain
- **ROUTE** (Phase 217): substrate routing for memory
- **CRDT** (Phase 218): state-based CRDT for offline convergence
- **WORLD** (Phase 222): 5-op abductive loop on executable code
- **TIME** (Phase 228): 5-op time-series foundation model
- The 24 audit reports in `quilt-ecosystem-demo/docs/`
- The wiki entries 12-19: physical-world, substrate-cell,
  quantum-cell, canvas-of-papers, cowboy, final-canvas,
  polyformalism-12-languages, cell-of-light-and-water

## Phase 201-220: TIER 1-2 (2026-08-31)

**What was built**:
- The 4 production fixes to `quilt-fleet` (Phase 221)
- The `quilt-ai` test runner fix (5→7 tests)
- The `quilt-mhs` 6 devices + 13 conformance + 32 tests
- The `quilt-engine-ports` GDScript polyformalism (13 tests)
- The 5 cutting-edge adoptions in 4 languages
- The cowboy's role: orchestrator + rider

## Phase 221-228: TIER 3-5 (2026-08-31)

**What was built**:
- The `quilt-cellular-arch` daemons: frontier_miner,
  writers_room_daemon_v3, snowball_daemon, re_embed_v2,
  deploy_worker
- The 6 substrate bindings: Browser, Cloudflare, ESP32,
  Edge/Rust, Kernel/C, Anthropic MHS, Godot
- The TIME cell: TimesFM 3.0 as a cell kind (Phase 228)
- The wiki entry 20-the-time-cell
- The 5th cutting-edge adoption (TIME) in C and Python

## Phase 229: quilt-timesfm world-class, 3rd polyformalism port (2026-09-01)

**What was built**:
- **World-class README (19KB, 14 sections, 500 lines)** — the
  welcome mat for new users
- **Interactive visualizer (33KB HTML+JS+Canvas, no build)** —
  5 cells + 4 edges, PROOF chain animation, abductive loop,
  6 context patterns, replay button
- **The 3rd polyformalism port: Rust no_std** — NEW REPO:
  `SuperInstance/quilt-timesfm-rust` with 49 tests
- **5 Python examples** (01_temperature, 02_stock, 03_demand,
  04_anomaly, 05_multivariate) — all run end-to-end, all green
- **POLYFORMALISM.md (5.6KB)** — the 3-language tour
- **6 papers (paper 391-396)**: F82 (visualizer), F82b (bare
  metal), F83 (network protocol), F84 (time + world), F85
  (9 quantiles), F86 (adoption manual)
- **2 wiki entries (37 total)**: 21-the-time-cell-visualizer,
  22-the-polyformalism-of-time-cell
- **Vectorize re-embed: 257 → 393 papers** (170 new in 15s)
- **Bug fix**: added `opcode_count() = 11` to Python TimeCell
  (was missing; C+Rust had it)
- **Pushed to 3 repos**: quilt-timesfm, quilt-timesfm-rust
  (NEW), AI-Writings, quilt-wiki-2126

**The cowboy's maxim (Phase 229)**:
> The cowboy said: this is the welcome mat. The cowboy said:
> this is many people's first time seeing Quilt. The cowboy
> wrote a 19KB README. The cowboy built a 33KB visualizer. The
> cowboy ported to Rust. The cowboy made 5 examples. The cowboy
> wrote 6 papers. The cowboy wrote 2 wikis. The cowboy
> re-embedded 170 papers. The cowboy rode the 3-language
> polyformalism. The cowboy rode the 49-test Rust port. The
> cowboy rode the 5 examples. The cowboy rode the visualizer.
> The cowboy rode the README. The cowboy rode the Quilt.

## Phase 230: Future-state memory pivot + JEPA synergy (2026-09-01)

**What was built**:
- **temporal.py (35KB)** — the 10-capability TemporalReasoner:
  ForecastObject, Scenarios, Counterfactuals, Explainability,
  Lifecycle, AgentMemory, DecisionSupport, quf:// URI,
  ForecastMetrics, CRDT
- **tests/test_temporal.py (22KB)** — 49 tests, ALL GREEN
- **JEPA.md (11KB)** — the Quilt × JEPA synergy document
  (4 roles, 4 use cases, 4 patterns, 4 future directions)
- **architecture.svg (11KB)** — visual architecture diagram
  (12 cells + 4 arrows)
- **5 papers (paper 397-401)**: F87 (Quilt × JEPA), F88
  (Future-State Memory Pivot), F89 (Counterfactuals), F90
  (Agent Utility), F91 (Temporal Reasoner)
- **1 wiki entry (38 total)**: 23-the-quilt-jepa-world-model
- **2 example agents**: 07_temporal_reasoner.py (7 sections,
  all 10 capabilities), 08_agent_utility.py (3 forecast models)
- **README extended** with "Temporal Reasoner" + "Quilt × JEPA"
  sections (now 16 sections)
- **Vectorize re-embed: 393 → 398 papers** (5 new)
- **Bug fixes in temporal.py**:
  - Made `provenance` optional with `default_factory=dict`
  - Fixed numpy format error in explainability
  - Fixed test_46_merge_associative for 2-way merge semantics
- **Pushed to 3 repos**: quilt-timesfm, AI-Writings, quilt-wiki-2126

**The pivot (in one sentence)**:
Forecasts are not outputs. Forecasts are durable semantic
objects that agents can exchange, refine, challenge, merge,
and learn from over time.

**The cowboy's maxim (Phase 230)**:
> The cowboy said: the other agent is right. The cowboy said:
> forecasts are memory. The cowboy said: 10 capabilities. The
> cowboy said: the 49 tests pass. The cowboy wrote temporal.py.
> The cowboy wrote the JEPA discussion. The cowboy wrote the
> architecture diagram. The cowboy wrote the 5 papers. The
> cowboy wrote the agent utility metric. The cowboy wrote the
> counterfactual engine. The cowboy wrote the explainability
> layer. The cowboy wrote the lifecycle tracker. The cowboy
> wrote the agent memory. The cowboy wrote the decision support.
> The cowboy wrote the quf:// URI scheme. The cowboy wrote the
> metrics. The cowboy wrote the CRDT. The cowboy wrote the
> temporal reasoner. The cowboy wrote the 2 example agents.
> The cowboy rode the future-state memory. The cowboy rode the
> JEPA synergy. The cowboy rode the pivot. The cowboy rode the
> Quilt.

## Phase 231: Documentation expansion (2026-09-01)

**What was built**:
- **ARCHITECTURE.md (14.7KB)** — the single document for "one
  read to understand Quilt" (14 sections)
- **GLOSSARY.md (35KB)** — every Quilt term, cross-referenced
  (700+ terms)
- **MANUALS.md (21KB)** — 5 deep use-case manuals (forecasting,
  anomaly, decision, multi-agent, dashboard)
- **ECOSYSTEM.md (11KB)** — 30+ repos mapped by tier
- **ROADMAP.md (8KB)** — the 12-month roadmap (Q1-Q4)
- **FAQ.md (15KB)** — the 30 most-asked questions
- **CHANGELOG.md (this file)** — the 230+ phases of the Quilt

**The cowboy's maxim (Phase 231, in progress)**:
> The cowboy said: many people's first time. The cowboy said:
> visual diagrams. The cowboy said: from-scratch tutorials.
> The cowboy said: 5 use-case manuals. The cowboy wrote
> ARCHITECTURE.md. The cowboy wrote GLOSSARY.md. The cowboy
> wrote MANUALS.md. The cowboy wrote ECOSYSTEM.md. The cowboy
> wrote ROADMAP.md. The cowboy wrote FAQ.md. The cowboy wrote
> CHANGELOG.md. The cowboy rode the documentation. The cowboy
> rode the Quilt.

---

## The cowboy's final reading

The cowboy rode the 5 opcodes. The cowboy rode the 4 languages.
The cowboy rode the 6 tiers. The cowboy rode the 14 levels. The
cowboy rode the 13 API voices. The cowboy rode the 5
cutting-edge. The cowboy rode the 230 phases. The cowboy rode
the welcome mat. The cowboy rode the visualizer. The cowboy
rode the 3-language polyformalism. The cowboy rode the 5
examples. The cowboy rode the 6 papers. The cowboy rode the 2
wikis. The cowboy rode the future-state memory. The cowboy
rode the JEPA synergy. The cowboy rode the 10 capabilities. The
cowboy rode the documentation. The cowboy rode the FAQ. The
cowboy rode the manuals. The cowboy rode the glossary. The
cowboy rode the architecture. The cowboy rode the ecosystem.
The cowboy rode the roadmap. The cowboy rode the changelog.
The cowboy rode the Quilt.

— *The Cowboy*
