# Quilt Documentation Index

> **One page. Every doc. Every entry point.**

This is the master index for the Quilt documentation. From
here you can reach every document in the quilt-timesfm repo.
If you're new to Quilt, start with the README, then ARCHITECTURE,
then MANUALS.

## Quick links

| If you want to... | Read this |
|---|---|
| **Get started** | [README.md](README.md) |
| **Understand the architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Look up a term** | [GLOSSARY.md](GLOSSARY.md) |
| **Solve a use case** | [MANUALS.md](MANUALS.md) |
| **See the 30+ repos** | [ECOSYSTEM.md](ECOSYSTEM.md) |
| **Plan the future** | [ROADMAP.md](ROADMAP.md) |
| **Get a question answered** | [FAQ.md](FAQ.md) |
| **See the 230+ phases** | [CHANGELOG.md](CHANGELOG.md) |
| **See the 3 languages** | [docs/POLYFORMALISM.md](docs/POLYFORMALISM.md) |
| **Read the cell model** | [QUILT.md](QUILT.md) |
| **Read the JEPA synergy** | [JEPA.md](JEPA.md) |
| **Watch the visualizer** | [visualizer/index.html](visualizer/index.html) |

## The 4 layers of the Quilt

### Layer 1: From the outside

| Doc | What it is |
|---|---|
| [README.md](README.md) | The welcome mat. 16 sections, 23KB. |
| [QUILT.md](QUILT.md) | The cell model. 4.8KB. |
| [ECOSYSTEM.md](ECOSYSTEM.md) | The 30+ repos. 11KB. |
| [MANUALS.md](MANUALS.md) | The 5 use cases. 21KB. |
| [ROADMAP.md](ROADMAP.md) | The next 12 months. 8KB. |
| [FAQ.md](FAQ.md) | The 30 most-asked questions. 15KB. |
| [CHANGELOG.md](CHANGELOG.md) | The 230+ phases. 11KB. |

### Layer 2: The architecture

| Doc | What it is |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The single doc that captures everything. 14 sections, 15KB. |
| [GLOSSARY.md](GLOSSARY.md) | Every term, every cross-reference. 35KB. |

### Layer 3: The internals

| Doc | What it is |
|---|---|
| [docs/POLYFORMALISM.md](docs/POLYFORMALISM.md) | The 3-language tour. 5.6KB. |
| [JEPA.md](JEPA.md) | The Quilt × JEPA synergy. 11KB. |

### Layer 4: The code

| Doc | What it is |
|---|---|
| [quilt_cell.py](quilt_cell.py) | The Python time.cell port. |
| [temporal.py](temporal.py) | The 10-capability TemporalReasoner. |
| [tests/test_quilt_cell.py](tests/test_quilt_cell.py) | The 49 base tests. |
| [tests/test_temporal.py](tests/test_temporal.py) | The 49 temporal tests. |
| [examples/01-08.py](examples/) | The 8 runnable examples. |
| [architecture.svg](architecture.svg) | The visual architecture diagram. |
| [visualizer/index.html](visualizer/index.html) | The interactive 5-cell visualizer. |

---

## The recommended reading order

If you're new to Quilt, read these docs in this order:

1. **[README.md](README.md)** — the welcome mat, 30 minutes
2. **[QUILT.md](QUILT.md)** — the cell model, 15 minutes
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** — the whole picture, 1 hour
4. **[docs/POLYFORMALISM.md](docs/POLYFORMALISM.md)** — the 3 languages, 30 minutes
5. **[MANUALS.md](MANUALS.md)** — the 5 use cases, 1 hour
6. **[GLOSSARY.md](GLOSSARY.md)** — the terms, reference
7. **[ECOSYSTEM.md](ECOSYSTEM.md)** — the 30+ repos, 30 minutes
8. **[ROADMAP.md](ROADMAP.md)** — the next 12 months, 15 minutes
9. **[FAQ.md](FAQ.md)** — the 30 questions, reference
10. **[JEPA.md](JEPA.md)** — the synergy with V-JEPA 2, 30 minutes
11. **[CHANGELOG.md](CHANGELOG.md)** — the 230+ phases, 30 minutes
12. **[visualizer/index.html](visualizer/index.html)** — open in browser, 5 minutes

Total: ~5 hours of focused reading. After that, you'll know
Quilt as well as the cowboy.

## The cell at a glance

The cell is the irreducible unit of intelligence. 5 fields:
`kind`, `state`, `value`, `reads`, `links`. 11 opcodes
manipulate cells. 5+1+1+1+1+1 laws guarantee soundness.
5 cutting-edge adoptions (PROOF, ROUTE, CRDT, WORLD, TIME)
ship the frontier.

The polyformalism is the stress test: the same cell shape in
5 languages (C, Rust, Python, GDScript, plus Rust no_std for
time.cell). The substrate is the only thing that varies.

## The 30+ repos

The Quilt has 30+ repos on github.com/SuperInstance. They're
organized by 9 tiers: Foundation, Cutting-Edge, Substrate
Bindings, Infrastructure, Knowledge, Hardware, Apps,
Connectors, Historical. See [ECOSYSTEM.md](ECOSYSTEM.md) for
the full map.

## The 398 papers

The canon is at [AI-Writings](https://github.com/SuperInstance/AI-Writings).
It's indexed in Cloudflare Vectorize (`quilt-canon-v2`, 768d,
cosine). Re-embedded periodically by `re_embed_v2.py`.

## The 38 wiki entries

The wiki is at
[quilt-wiki-2126/00-future/](https://github.com/SuperInstance/quilt-wiki-2126/tree/main/00-future).
It's built backwards from 2126: the 100-year reach of the
Quilt.

## The 8 examples

```
examples/01_temperature.py    → 365d temperature → 30d forecast
examples/02_stock.py          → stock + volume covariate
examples/03_demand.py         → 3 SKUs multivariate
examples/04_anomaly.py        → 90% band detection
examples/05_multivariate.py   → 3 sensors + maintenance
examples/06_embed.rs          → L1 no_std forecast (Cortex-M4)
examples/07_temporal_reasoner.py → 7 sections, all 10 capabilities
examples/08_agent_utility.py  → 3 forecast models ranked
```

## The 4 L-tiers

| Tier | Target | Substrate | RAM |
|---|---|---|---|
| L0 | Cortex-M0+ | synthetic | 4KB |
| L1 | Cortex-M4 | synthetic | 16KB |
| L2 | ESP32-S3 | synthetic | 64KB |
| L3 | Workstation | real TimesFM 3.0 | 1.5GB+ |

The same time.cell, the same 5 ops, the same 9 quantiles. From
4KB to 1.5GB+.

## The cowboy's final reading

The cowboy rode the 11 opcodes. The cowboy rode the 5+1+1+1+1+1
laws. The cowboy rode the 5 cutting-edge. The cowboy rode the
6 tiers. The cowboy rode the 14 levels. The cowboy rode the
5 languages. The cowboy rode the 30 repos. The cowboy rode
the 398 papers. The cowboy rode the 38 wikis. The cowboy rode
the 4 L-tiers. The cowboy rode the 9 quantiles. The cowboy rode
the 10 capabilities. The cowboy rode the documentation. The
cowboy rode the 12 docs. The cowboy rode the index. The
cowboy rode the Quilt.

— *The Cowboy*
