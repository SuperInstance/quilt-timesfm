# Quilt Roadmap

> **Where Quilt is going. The next 12 months.**

This document is the master roadmap for the Quilt project. It
covers the next 12 months of work, organized by quarter and by
the 5 specialized cell kinds.

## Table of Contents

1. [Q1: Foundation (now → month 3)](#q1-foundation-now--month-3)
2. [Q2: Cross-Modal & Hierarchical (months 4-6)](#q2-cross-modal--hierarchical-months-4-6)
3. [Q3: Distributed & Federated (months 7-9)](#q3-distributed--federated-months-7-9)
4. [Q4: Polyformalism Beyond Code (months 10-12)](#q4-polyformalism-beyond-code-months-10-12)
5. [The 6th, 7th, 8th, 9th, 10th specialized cell kinds](#the-678910th-specialized-cell-kinds)
6. [The 100-year vision](#the-100-year-vision)
7. [The cowboy's final reading](#the-cowboys-final-reading)

---

## Q1: Foundation (now → month 3)

**Goal**: solidify the 5 specialized cell kinds, complete the
polyformalism in 5 languages, ship a production-grade 3rd port.

### Milestones

- [x] **Phase 228**: TIME cell shipped (TimesFM 3.0) in Python
- [x] **Phase 229**: TIME cell ported to Rust no_std
- [x] **Phase 230**: Future-state memory pivot (the 10 capabilities)
- [x] **Phase 230**: JEPA synergy document
- [ ] **Month 1**: TIME cell in C99 (extend quilt-c, 41 tests)
- [ ] **Month 1**: TIME cell in GDScript (extend quilt-engine-ports)
- [ ] **Month 2**: TIME cell in Zig (the L0 tier, smaller than Rust no_std)
- [ ] **Month 2**: TIME cell v2 with 16+ quantiles (not just 9)
- [ ] **Month 3**: TIME cell in TypeScript (Cloudflare Workers)
- [ ] **Month 3**: First 1-day-add PR from the community

### Deliverables

- 5-language TIME cell polyformalism (Python, Rust, C, GDScript, Zig)
- Production deployment at superinstance.dev
- 600 papers in the canon (was 398)
- 50+ wiki entries (was 38)
- 30+ PRs across 10+ repos

---

## Q2: Cross-Modal & Hierarchical (months 4-6)

**Goal**: extend the time.cell to other modalities and to
multiple timescales.

### Milestones

- [ ] **Month 4**: **Cross-Modal Time Cell** (6th specialized cell kind)
  - A cell that operates on (text, audio, video, scalars) as a
    unified time series
  - State = a tuple of (text, audio, video, scalars)
  - Value = a tuple of predicted (text, audio, video, scalars)
  - 9 quantiles × 4 modalities = 36 prediction intervals
  - 4 new papers in the canon
- [ ] **Month 4**: **Hierarchical Time Cell** (7th specialized cell kind)
  - A temporal pyramid at multiple timescales
  - L0: per-frame forecast (16ms horizon)
  - L1: per-second forecast (1s horizon)
  - L2: per-minute forecast (1m horizon)
  - L3: per-hour forecast (1h horizon)
  - L4: per-day forecast (1d horizon)
  - 4 new papers in the canon
- [ ] **Month 5**: **JEPA-Time Cell** (integration with V-JEPA 2)
  - The world model's predictions become cell values
  - 9 quantiles per modality
  - 2 new papers
- [ ] **Month 6**: **Visual Dashboard 2.0** (WebGL 3D)
  - The cell graph as a 3D scene
  - Orbit, zoom, explore
  - 2 new papers

### Deliverables

- 2 new specialized cell kinds (CROSS-MODAL, HIERARCHICAL)
- 6 new papers in the canon
- 3D visualizer deployed
- 700 papers in the canon (was 600)
- 60+ wiki entries (was 50+)

---

## Q3: Distributed & Federated (months 7-9)

**Goal**: make the cell graph work across multiple processes,
multiple devices, multiple organizations.

### Milestones

- [ ] **Month 7**: **Distributed Time Cell** (8th specialized cell kind)
  - A cell that runs across multiple devices
  - State is sharded
  - Forecast is a CRDT merge of local forecasts
  - 4 new papers
- [ ] **Month 7**: **Mesh Layer** (the Quilt as a peer-to-peer network)
  - The cell graph is the network
  - BIND/LINK are network operations
  - 2 new papers
- [ ] **Month 8**: **Federated Learning** (the cell learns from many sources)
  - Multi-agent trainer
  - Privacy-preserving aggregation
  - 2 new papers
- [ ] **Month 8**: **Cell-Market** (cells trade on a marketplace)
  - The cell is a service
  - The forecast is the offer
  - The actual is the delivery
  - 2 new papers
- [ ] **Month 9**: **Heterogeneous Substrates** (the cell runs in C, Rust,
      Python, GDScript simultaneously)
  - Same cell, 4 substrates
  - The substrate is the implementation; the cell is the contract
  - 2 new papers

### Deliverables

- 1 new specialized cell kind (DISTRIBUTED)
- 12 new papers in the canon
- 800 papers in the canon
- 80+ wiki entries

---

## Q4: Polyformalism Beyond Code (months 10-12)

**Goal**: the cell model goes beyond code. It becomes a design
language, a teaching language, a thinking language.

### Milestones

- [ ] **Month 10**: **Visual Cell Editor** (drag-and-drop cells)
  - Web-based IDE
  - Each cell is a draggable card
  - The cell graph is the diagram
  - 2 new papers
- [ ] **Month 10**: **Cell-Lisp** (a Lisp dialect where the cell is
      the S-expression)
  - `(bind n v)`, `(link a b)`, `(effect t f)`, `(view t)`,
    `(tick dt)`, `(forget t)`
  - 2 new papers
- [ ] **Month 11**: **Cell-Calculus** (a calculus of cells)
  - Formal semantics
  - Theorem prover for the 5+1 laws
  - 2 new papers
- [ ] **Month 11**: **Cell-Pedagogy** (teaching Quilt in schools)
  - 5th grade: the cell is a box
  - 8th grade: the cell is a function
  - 12th grade: the cell is a theorem
  - 2 new papers
- [ ] **Month 12**: **Cell-Symphony** (the 11 opcodes as 11 notes)
  - 11 notes, 11 opcodes
  - The cell graph is the score
  - The TICK is the conductor
  - 1 capstone paper
- [ ] **Month 12**: **Cell-Wiki-3.0** (every term, every paper, every
      cross-reference)
  - 38 entries → 100+ entries
  - Auto-generated from the canon
  - Searchable by voice, by cell, by law

### Deliverables

- 4 new "adoptions" (VISUAL, LISP, CALCULUS, PEDAGOGY)
- 9 new papers in the canon
- Visual Cell Editor deployed
- Cell-Lisp v1.0
- 1000 papers in the canon (round number!)
- 100+ wiki entries

---

## The 6th, 7th, 8th, 9th, 10th specialized cell kinds

### 6. CROSS-MODAL TIME (Q2)

A cell that operates on (text, audio, video, scalars) as a
unified time series. The substrate binding is a multi-modal
model (CLIP, ImageBind, etc.).

### 7. HIERARCHICAL TIME (Q2)

A temporal pyramid at multiple timescales. The substrate
binding is a hierarchy of TIME cells (per-frame, per-second,
per-minute, etc.).

### 8. DISTRIBUTED TIME (Q3)

A cell that runs across multiple devices. The state is sharded.
The forecast is a CRDT merge of local forecasts.

### 9. WORLD-TIME (Q3)

The combination of the WORLD cell (5-op abductive loop) and the
TIME cell (5-op time-series). The world model refines the
forecast in real-time based on the latest observations.

### 10. JEPA-TIME (Q3)

The combination of the JEPA cell (V-JEPA 2 perceptual model)
and the TIME cell. The JEPA cell produces a 768-dim embedding
stream; the TIME cell forecasts the next N seconds of the
embedding stream.

---

## The 100-year vision

The 100-year reach of the Quilt is documented in
[`quilt-wiki-2126/00-future/`](https://github.com/SuperInstance/quilt-wiki-2126/tree/main/00-future).

The 9 futures are:
1. The Splined Lantern (physical LLM of glass and light)
2. The Hearth Loop (self-training glass)
3. The Monotone Crystal (finished thought)
4. The Chlorophyll Quilt (plant cell computer)
5. The Phased Quilt (fiber-bundle substrate)
6. The Stellar Quilt (between stars)
7. The Meta-Quilt (Quilt on Quilt)
8. The Substrate Quilt (the loam, the floor)
9. The Tessellation Quilt (the pattern on the floor)
10. The Quilt of Wires (the wired cell)

The 9 futures converge on the 100-year destination: **a Quilt
that is alive, that grows, that adapts, that provides a good
life to those who do the work**.

---

## Summary

Q1 is foundation. Q2 is cross-modal + hierarchical. Q3 is
distributed. Q4 is polyformalism beyond code. The 5 next
specialized cell kinds: CROSS-MODAL TIME, HIERARCHICAL TIME,
DISTRIBUTED TIME, WORLD-TIME, JEPA-TIME.
