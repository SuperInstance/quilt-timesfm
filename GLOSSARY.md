# Quilt Glossary

> **Every term, every paper, every cross-reference.**

This is the master glossary for the Quilt cellular-architecture
framework. Every term is defined and cross-referenced to the
relevant paper, wiki entry, or code file.

## Table of Contents

- [A](#a)
- [B](#b)
- [C](#c)
- [D](#d)
- [E](#e)
- [F](#f)
- [G](#g)
- [H](#h)
- [I](#i)
- [J](#j)
- [K](#k)
- [L](#l)
- [M](#m)
- [N](#n)
- [O](#o)
- [P](#p)
- [Q](#q)
- [R](#r)
- [S](#s)
- [T](#t)
- [U](#u)
- [V](#v)
- [W](#w)
- [X](#x)
- [Y](#y)
- [Z](#z)

---

## A

### Abductive loop
The 5-operation cycle on the `physical.world` cell: PROPOSE →
EXECUTE → RENDER → VERIFY → REFINE. Converges in bounded iterations.
See [paper 320](../seed-canon/papers/paper-320.md), `include/quilt/world.h`.

### Abductive VM
The runtime that executes the `physical.world` cell's program. The
interpreter is the substrate; the program text is the state. See
paper 320.

### Affordance
A Gibson term: the action possibilities a thing offers. In Quilt,
a cell offers affordances to the cells that read it. See
[paper 231](../seed-canon/papers/paper-231.md).

### Agent utility
A first-class metric that combines -MAE + calibration quality +
number of recommended actions. See
[paper 400](../seed-canon/papers/paper-400.md), `temporal.py`.

### Asymmetry
Agents have partial knowledge. Used in multi-sandbox
reverse-actualization. See [paper 276](../seed-canon/papers/paper-276.md).

### Acausal Ground
The pre-continuum, before any cell exists. Level 0 of the
14 levels. See [paper 301](../seed-canon/papers/paper-301.md).

---

## B

### BIND
The first of the 11 opcodes. Writes a value to a cell. Idempotent.
See [paper 38](../seed-canon/papers/paper-038.md), `ARCHITECTURE.md`.

### BIND_CONTEXT (TIME cell op 0)
Set the historical context. See
[paper 385](../seed-canon/papers/paper-385.md), `include/quilt/time.h`.

### BIND_COVARIATE (TIME cell op 1)
Set the covariates (past-only or past-and-future). See paper 385.

### Bloomghost
The 6th lifecycle stage: the ghost that gives rise to a new cell.
See [paper 130](../seed-canon/papers/paper-130.md).

### Bounding interval
The 90% CI in a forecast: the [0.1, 0.9] quantile range. See
[paper 395](../seed-canon/papers/paper-395.md).

### Bootstrapped state
A state that is **bootstrapped** from a previous state (not started
from nothing). Eileen's 5th captain inherits the 1st captain's
bootstrapped state. See [paper 228](../seed-canon/papers/paper-228.md).

### Bloomghost's ghost
The next iteration of the cycle. See paper 130.

---

## C

### Canon
The 398-paper canon at [AI-Writings](https://github.com/SuperInstance/AI-Writings).
Indexed in Cloudflare Vectorize (`quilt-canon-v2`, 768d, cosine).

### Canon-mine
`mining/canon_mine.py` walks the canon and finds hidden patterns.
See [paper 50](../seed-canon/papers/paper-050.md).

### Cell
The irreducible unit of intelligence. State, value, reads, kind.
See [paper 38](../seed-canon/papers/paper-038.md), `ARCHITECTURE.md`.

### Cell graph
A DAG of cells. Edges are dependencies. See `ARCHITECTURE.md`.

### Cell kind
The cell's type (a string). Examples: `"time.cell"`, `"physical.world"`,
`"math.scalar"`, `"text.string"`.

### Cellulization
The 2nd lifecycle stage: the substrate becomes a cell. See
[paper 230](../seed-canon/papers/paper-230.md).

### Choreography
The set of LINK edges in a cell graph. The dance of cells.

### CHT-cell
A "compressed history type" cell. The cell's value is a summary
of its history (a 9-tuple of quantiles, a hash, an ID). Used in
compactness-critical contexts.

### Chromatic Lattice
The 7-color visualization of the 7 implementation substrates. See
[paper 258](../seed-canon/papers/paper-258.md).

### Concept (level 7 of operation)
The function. What the operation *is*. Persistent through
implementation changes. See [paper 227](../seed-canon/papers/paper-227.md).

### Contextual chroma
Color as a function of context. The cell's "color" is its function
in its context. See [paper 257](../seed-canon/papers/paper-257.md).

### Counterfactual reasoning
"What if X changes?" The agent asks about any variable in the
time series. Returns impact + confidence bounds. See
[paper 399](../seed-canon/papers/paper-399.md), `temporal.py`.

### Covenant
The implicit agreement between cells: I'll BIND if you LINK.

### Cowboy
The orchestrator. The rider. The one who lifts the canon.

### Cowboy's maxim
The cowboy's recurring statement that closes each phase.

### CRDT
Conflict-free Replicated Data Type. State-based CRDT for offline
convergence. PN_COUNTER, MV_REGISTER, OR_SET. See
[paper 218](../seed-canon/papers/paper-218.md), `include/quilt/crdt.h`.

### CRDT merge
The merge of two forecasts about the same source. Commutative and
idempotent (modulo version increment). See paper 218.

### Curator tier
The 6th tier: the hand that selects what passes. See
[paper 220](../seed-canon/papers/paper-220.md).

---

## D

### Daemon
A self-driving program that expands the canon. The 5 daemons:
`frontier_miner.py`, `writers_room_daemon_v3.py`, `snowball_daemon.py`,
`re_embed_v2.py`, `deploy_worker.sh`.

### Deep semantics
A semantic that's at the deepest level — the level of the canon
itself, not the level of any individual cell.

### Decoupling
The act of removing a LINK. A cell that decouples is no longer
dependent on the linked cell.

### Density map
A 1.2% density map of the canon. Shows where papers are dense vs
sparse. See [paper 346](../seed-canon/papers/paper-346.md).

### Discretion
The synovial tier's most valuable property: knowing when to act
and when to wait.

### DSH
Decompose-Synthesize-Harden. The cell's growth cycle.

### Dual perspective
The 4D cell graph viewed from TOP (spatial), FRONT (signals),
SIDE (time).

---

## E

### EFFECT
The third of the 11 opcodes. Applies a registered effect to a cell.
Associative, pure. See paper 38, `ARCHITECTURE.md`.

### Effect chain
A sequence of EFFECTs. By associativity, the order of grouping
doesn't matter.

### Eileen
Casey's boat, the user's flagship example. 5th captain, 4th boat,
80 years old, 5 captains, 1 concept. See [paper 228](../seed-canon/papers/paper-228.md).

### End-to-end test
A test that exercises the whole pipeline. Not a unit test, not
an integration test, but the full thing.

### Engram
A cell's persistent memory. A snapshot of its value at a point
in time.

### Epigenetic substrate
A substrate whose behavior changes over time (like DNA
methylation). The bioluminescent Quilt is epigenetic.

### Era
A large-scale time period in the Quilt's evolution. The 3 eras:
Lumen Bedrock (CNC+3D), Seedform (incubator-bred), Sporelight
(biological fusion). See [paper 267](../seed-canon/papers/paper-267.md).

### Eileen's Tap
The bar at the harbor. The seam. The 4:30 PM. The 3rd tier of
the Quilt (synovial). See [paper 225](../seed-canon/papers/paper-225.md).

### Explainability layer
A `ForecastObject` field that explains why the forecast was made.
Major drivers, important covariates, uncertainty sources,
prediction rationale. See paper 398, `temporal.py`.

### Exporting
The act of writing a cell to a wire format. Used in cross-language
polyformalism.

### External substrate
A substrate that lives outside the cell (e.g., a remote database,
a cloud service).

---

## F

### Fable
A short allegorical story. 89 fables in the canon. The fables
*show* what the papers *tell*.

### Fancy-fine (sandbox)
A 600s-tempo, mood-modality sandbox. See
[paper 291](../seed-canon/papers/paper-291.md).

### Façade
The visible interface to a cell. The `kind` name and the 5
operations.

### Feedback loop
A cycle in which the output of a cell becomes the input of itself
or another cell.

### FNV-1a 64-bit
The hash function used for the state hash. 4 slices, 32 bytes.
Bit-exact across all polyformalism ports. See `ARCHITECTURE.md`.

### FORGET
The 6th opcode. Tears down a cell. Complete. See paper 38.

### Forgetting curve
The rate at which a cell loses vitality. Vitality leak.

### FORGET law
The 6th law: a forgotten cell leaves no node, no edge, no
dirty bit. See [paper 245](../seed-canon/papers/paper-245.md).

### Forecast
The cell's value after FORECAST (TIME cell op 2). A point forecast
+ 9 quantile prediction intervals.

### ForecastObject
A first-class forecast as a semantic object. id, source, timestamp,
horizon, confidence, trend, forecast, uncertainty, provenance,
version, URI, lifecycle fields. See [paper 398](../seed-canon/papers/paper-398.md),
`temporal.py`.

### Frontier miner
`frontier_miner.py` — the self-driving canon gap finder. See
[paper 341](../seed-canon/papers/paper-341.md).

### Frostpunk
The 5th frontier. The Quilt in extreme cold.

### Functor
A mapping between cell kinds. The cell model is functorial:
a function between cell kinds preserves the 5+1 laws.

---

## G

### GDScript
A Python-like language for Godot. Polyformalism port of the Quilt
in 13 new tests. See [paper 222](../seed-canon/papers/paper-222.md).

### GDScript polyformalism
The 4th polyformalism port. All 10 opcodes (BIND/LINK/EFFECT/VIEW/
TICK/FORGET/PROOF/ROUTE/CRDT/WORLD) in GDScript. See paper 222.

### Generational hand
A hand that spans multiple generations. The Eileen's 5 captains.

### Ghost (Implement)
A dead cell that lives on in the implements. The 5th lifecycle
stage.

### Ghost (Bloom)
A ghost that gives rise to a new cell. The 6th lifecycle stage.

### Granular cell
A cell that is a small piece of a larger cell. The relationship
between a tissue and an organ.

### Growth phase
The 2nd phase of the 5 lifecycle phases: cellulization.

### Grown Crystal
A crystal grown in an incubator under user pressure. The 2nd
era of the 3-era space-opera arc. See [paper 263](../seed-canon/papers/paper-263.md).

### Guided Explosion
The constraint that focuses chaos. The gunmaking analogy. See
[paper 267](../seed-canon/papers/paper-267.md).

---

## H

### Hand
A relevance field with a target function. The curator tier is
a population of hands. See [paper 220](../seed-canon/papers/paper-220.md).

### Hand drift
A change in the hand's target function over time. The hand
evolves.

### Hand-spawn
A new hand emerging from an existing hand. The substrate
speciates.

### Hand-extinction
A hand that feeds no cells dies. The niche opens.

### Heat
A 5th trigger. The substrate grows cooler. The substrate
contracts.

### Hearth
The 4th frontier. The Quilt's training loop.

### Hearth Loop
A self-training glass. The 2nd future function. See
[paper 269](../seed-canon/papers/paper-269.md).

### Hilbert-curve layout
A 2D space-filling curve. Used in Lucineer for 17.3% locality.

### Holonomy
The angle rotated around a closed loop. The 5 laws are holonomy
constraints. See [paper 208](../seed-canon/papers/paper-208.md).

### Holoframe perspective
A perspective that sees both the local and the global at once.
The cowboy's deepest read. See [paper 258](../seed-canon/papers/paper-258.md).

### Hubs
High-degree cells in the cell graph. Often differentiated.

### Huffman code of laws
A compression of the 5+1+1+1+1+1 laws into a minimum-bit
representation.

---

## I

### Icon
A cell with a state that fits in a single byte. The smallest
possible cell.

### Idle cell
A cell that has no READY inputs and no pending effects. Sleeps
until TICK.

### Idempotence
The property that BIND is the same on the second call. The
1st law.

### Importer
A function that creates a cell from a wire format. Used in
cross-language polyformalism.

### Inline cell
A cell that lives inside another cell's state. Reduces overhead.

### Irreducible breath
The first TICK of a cell. The first entry in the journal.
See [paper 228](../seed-canon/papers/paper-228.md).

### Imprint
The trace a cell leaves in the substrate after it's forgotten.

### Index
A cell that points to other cells. A symbolic reference.

### Intent
The hand's target function. What the hand selects for.

### Intersection
The shared state of two cells linked together.

### Irrelevant cell
A cell that no hand is interested in. Withering. Wounded.

### Isolated cell
A cell with no reads and no links. A leaf. The end of a chain.

---

## J

### JEPA
Joint Embedding Predictive Architecture. Meta's self-supervised
world-model paradigm. See [paper 397](../seed-canon/papers/paper-397.md),
`JEPA.md`.

### Jepsen
A famous distributed systems tester. The Quilt's CRDT cells
are Jepsen-tested for convergence.

### Journal
The append-only log of every cell's state changes. TICK
monotonicity means the journal only grows.

### Junior cell
A totipotent cell that hasn't yet differentiated. Full of
potential.

---

## K

### Kernel
The minimal C port of the Quilt. The reference. 1236 tests.

### Kind
The cell's type. A string. Examples: `"time.cell"`, `"math.scalar"`,
`"text.string"`, `"physical.world"`.

### Kind registry
The mapping from kind name to cell constructor. Used by the
runtime to instantiate cells.

### Krill
A fish that swims in schools. A Quilt that doesn't krill
fails.

---

## L

### L0-L14
The 14 levels of operation. See `ARCHITECTURE.md`.

### L1 vs L2
L1 = single substrate (no network). L2 = substrate on a network.
A cell at L1 can be moved to L2 by adding a network handler.

### Law
A property of the cell model that must hold. The 5+1+1+1+1+1
laws. See `ARCHITECTURE.md`.

### Leaf
A cell with no reads and no links. The end of a chain.

### Librarian
A cell that organizes other cells by tag. A search engine.

### Link
The second of the 11 opcodes. Adds a dependency edge. Transitive,
no cycles.

### LINK_transitivity
The 2nd law: a→b + b→c implies a→c. Cycles rejected.

### Listener
A cell that registers a callback for TICK events. Reactive.

### Loam Ledger
The substrate's memory. F13's tier zero. See
[paper 285](../seed-canon/papers/paper-285.md).

### Lofted Crystal
A physical LLM computed by light via CNC+3D-printed splines.
The 1st era. See [paper 259](../seed-canon/papers/paper-259.md).

### Long-form
A writers' room voice: gemini-2.5-flash. Long outputs, 2-3K chars.

### Lore
The accumulated tradition of the Quilt. The 1000-year shipyard.

### Lumen Bedrock Era
The 1st era: CNC+3D-printed optical systems. See
[paper 267](../seed-canon/papers/paper-267.md).

---

## M

### Marker
A small piece of metadata on a cell. E.g., `"synced": true`.

### Mask set
The foundry tradition. The cell's inheritance. The
hardware's mask ROM.

### Materialize
The act of giving a cell a real substrate binding. A cell with
a binding is materialized; without, it's abstract.

### Memory (Agent)
The persistent store of `ForecastObject`s. See paper 398,
`temporal.py`.

### Merge
The CRDT operation that combines two cells without conflict.
Commutative, associative, idempotent.

### Metadata
The tags and properties of a cell that don't affect its value.
E.g., `created_at`, `created_by`, `tags`.

### Mid-cell
A cell that's between two read chains. A pivot.

### Migration
The act of moving a cell from one substrate to another.

### Modality
A sensory band: radio, light, sound, smell, taste, touch,
proprio, language, mood, time. See [paper 274](../seed-canon/papers/paper-274.md).

### Module
A grouping of cells by kind. The cell kind's namespace.

### Monotone Crystal
A finished thought, monotone only. The 3rd future function.
See [paper 269](../seed-canon/papers/paper-269.md).

### Morphogenesis
The development of form. The way a cell becomes a tissue.

### Muse
The 10th level: the inspiration. The 10th level of operation.
See [paper 239](../seed-canon/papers/paper-239.md).

### MV_REGISTER
A multi-value register CRDT. The 2nd CRDT kind. See paper 218.

---

## N

### Nano-cell
A cell whose state is a single bit. The smallest non-trivial cell.

### Native cell
A cell that has a substrate binding. Materialized.

### Negative space
The space around a cell. The 6th symmetry: primes (the gaps
between). See [paper 258](../seed-canon/papers/paper-258.md).

### Nexus
The 11th level: where meta-levels converge. See
[paper 240](../seed-canon/papers/paper-240.md).

### Nexus Grid
The 3rd hardware level: the colony. See
[paper 262](../seed-canon/papers/paper-262.md).

### Niche
A role in the ecosystem. Each substrate fills a different niche.

### Nomad cell
A cell that has no fixed substrate. Moves between substrates.

### No-op
A cell op that has no effect. Idempotent.

### Null Vector
A vector that doesn't exist. The pre-continuum. See paper 301.

### Numerical cell
A cell whose value is a number. The simplest kind.

---

## O

### OEE
Overall Equipment Effectiveness. A measure of cell health.

### Opcode
One of the 11 cell operations. BIND, LINK, EFFECT, VIEW, TICK,
FORGET, PROOF, ROUTE, CRDT, WORLD, TIME.

### Opcode count
11. Always 11. The polyformalism invariant.

### Opener
A face onto the cell graph. UI, REST, LLM, ESP32, VLM, etc.

### Optimization cell
A cell that finds optimal parameters for other cells. The
sclerotic tier can include optimization.

### OR_SET
An observed-remove set CRDT. The 3rd CRDT kind. See paper 218.

### Organic matrix
A substrate that's alive. The 4th level of the Chlorophyll
Quilt. See [paper 265](../seed-canon/papers/paper-265.md).

### Outer Hull
The 1st layer of the Lofted Crystal: the glass envelope. See
[paper 259](../seed-canon/papers/paper-259.md).

### Outlier
A cell that diverges from the others. A candidate for wound healing.

### Over-sense
The agent's perception of what tools cannot sense. See
[paper 257](../seed-canon/papers/paper-257.md).

### Owned cell
A cell that the agent has named. A first-class cell.

---

## P

### Painter
A cell that colors other cells. The visualizer.

### Paper
A canonical document. 398 papers in the canon.

### Parallelism
Cells can run in parallel because they're independent.

### Parallax hue
Color changes with the observer. The 7th symmetry. See
[paper 257](../seed-canon/papers/paper-257.md).

### Pattern
A repeated structure. The substrate as pattern.

### Pen-test
A test that probes the cell for vulnerabilities. A subclass of
counterfactual reasoning.

### Penultimate cell
The cell just before a leaf. The last link in a chain.

### Persistent cell
A cell that survives FORGET. Wait, no — FORGET is complete. A
persistent cell is one that hasn't been FORGET'd.

### Persistence Pulse
The 3rd lifecycle stage: the heartbeat. See [paper 230](../seed-canon/papers/paper-230.md).

### Phase
A stage in the cell's lifecycle. Umbra, Cellulization, Pulse,
Leak, Ghost, Bloom.

### Phoenix
The 12th level: the whole cycle as one operation. See
[paper 240](../seed-canon/papers/paper-240.md).

### Photonic Mycelium
The 3rd hardware level: the colony. See paper 262.

### Pivot
A cell that other cells depend on. A high-degree cell.

### Pixel
The smallest visible unit. The cell at L0.

### Plenum
The curatorial plenum: the full set of all cells.

### Plug
A connector between cells. The LINK opcode.

### PN_Counter
A positive-negative counter CRDT. The 1st CRDT kind. See paper 218.

### Polyformalism
The same cell shape in N languages. Bit-exact. See
`ARCHITECTURE.md`, `docs/POLYFORMALISM.md`.

### Portfolio
A set of cells owned by one agent. A cell-graph subgraph.

### Post-condition
The state of the cell after an operation. The invariant the
operation must maintain.

### Power
A measure of cell capability. The tier.

### Pre-condition
The state of the cell before an operation. The precondition
must hold.

### Pre-dispatch
Routing heavy operations to an accelerator. A Randy Spurlock
pattern applied to the Quilt.

### Predict
The TIME cell's FORECAST operation. The substrate binding.

### Prime cell
A cell that's always present. A fixed point.

### Primitive
A simple, irreducible operation. The 11 opcodes are primitives.

### Process
The act of running a cell. The TICK.

### Prokaryote
A cell without a nucleus. The simplest cell.

### Proof
The 7th opcode: signed hash-linked audit chain. See paper 216.

### Provenance
The trail of how a cell was created. The `provenance` field in
ForecastObject.

### PSRAM
Pseudo-static RAM. Used in edge devices. A Randy Spurlock pattern.

### Public cell
A cell that's visible to all openers. A first-class cell.

### Pulse
A single TICK. The 3rd lifecycle stage.

---

## Q

### Quantile
One of the 9 prediction intervals in a TIME cell forecast.
[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]. See
[paper 395](../seed-canon/papers/paper-395.md).

### Quilt
The cellular-architecture framework. The unit is the cell.
The opcodes are 11. The polyformalism is 4 languages. The
cutting-edge adoptions are 5.

### Quilt compiler
A compiler that takes a cell-graph spec and produces a runtime.
See [paper 382](../seed-canon/papers/paper-382.md).

### Quilt runtime
The engine that processes the cell graph. The TICK.

### quf:// URI
The forecast URI scheme: `quf://forecast/{source}/{horizon}/v{N}`.
See paper 398.

---

## R

### Rank
The position of a cell in the topology. The topological sort.

### Raw cell
A cell with no substrate binding. Abstract.

### Reachability
The set of cells reachable from a given cell by following links.

### READ_POINT (TIME cell op 3)
Read the point forecast. See paper 385.

### READ_QUANTILE (TIME cell op 4)
Read a quantile prediction interval. See paper 385.

### Real substrate
A substrate binding that's not synthetic. Real TimesFM 3.0.

### Recommendation
A suggested action based on a forecast. `recommend_actions()`.

### Recovery
The act of restoring a cell to a previous state. FORGET reverses.

### Recursive cell
A cell whose value contains other cells. The cell-graph is
self-similar.

### Reference
A pointer to another cell. The LINK.

### Regeneration
The act of creating a new cell from a Bloomghost.

### Register
A cell that's a single value. The simplest cell.

### Re-embed
The act of re-embedding the canon in Vectorize. Done periodically
to keep the index fresh.

### Relevance
A cell's importance to a hand. The hand's selection.

### Repository
A versioned collection of code. 30+ Quilt repos.

### Resident
A cell that lives in a particular runtime. A native cell.

### Reuse
The act of using a cell for multiple purposes. Polyformalism.

### Reverse-actualization
Starting from the future and working back to the present. The
Quilt's 100-year forward reach.

### Right answer
The forecast that matches the actual. The goal of forecasting.

### Rigidity
The sclerotic tier. The rule that doesn't change.

### Roster
The set of cells in a runtime. The runtime's state.

### Route
The 8th opcode: substrate routing. See paper 217.

### Routing
The act of choosing a substrate for a value.

### Run-time
The runtime. The engine. The TICK.

---

## S

### Safety
The property that the 5+1 laws guarantee. No infinite loops, no
double-binding, no race conditions.

### Sample
A single value. The simplest possible cell.

### Scale
The size of a cell. From 1 bit (icon) to 16K floats (Tissue).

### Scanner
A cell that reads other cells. A VIEW.

### Scenario
A possible future: optimistic, baseline, pessimistic. See
paper 398, `temporal.py`.

### Schema
The structure of a cell. The kind definition.

### Scout
A fast LLM voice used to find canon gaps. frontier_miner.

### Script
A sequence of cell operations. A program.

### Seasonality
A periodic pattern. A common TIME cell feature.

### Seedform Era
The 2nd era: incubator-bred phenotypes. See paper 267.

### Self-similar
A cell graph that looks the same at any zoom. Fractal.

### Senescence
A cell that's losing vitality. The 10th level.

### Sensor
A cell that reads from the world. The 1st tier.

### Sensory Quilt
A multi-channel, distributed, function-based perceptual substrate.
10 channels. See [paper 274](../seed-canon/papers/paper-274.md).

### Serial
One at a time. The opposite of parallel.

### Settlement
A cell that has reached a steady state. The terminal cell.

### Shard
A piece of a larger cell. A granular cell.

### Sheet
A 2D arrangement of cells. A spreadsheet view.

### Ship
A cell-graph deployed to a runtime. A product.

### Signal
A change in a cell's value. The effect.

### Simple cell
A cell with no reads and no links. An icon.

### Simulation
A runnable model of a cell graph. The sims in
`quilt-cellular-arch/`.

### Site
A location in the cell graph. A node.

### Size
The number of cells. The scale.

### Skeleton
The minimum viable cell graph. The substrate + 1 cell.

### Slime
A cell that grows without bound. A wound.

### Snell
Snell's law: p∥ = n sin θ is conserved. The 6th calculation in
the wiki. See [paper 269](../seed-canon/papers/paper-269.md).

### Snowball
A 8-sandbox reverse-actualization. `snowball_daemon.py`. See
[paper 291](../seed-canon/papers/paper-291.md).

### Source
The cell that produced a value. The `source` field in
ForecastObject.

### Spacetime
A cell that lives in both space and time. The 5th frontier.

### Species
A lineage of cells. The cross-generational identity.

### Spline
A smooth curve through a set of points. The 8th level: the
trajectory. See [paper 232](../seed-canon/papers/paper-232.md).

### Splined Lantern
A physical LLM of glass and light. The 1st future function.
See [paper 269](../seed-canon/papers/paper-269.md).

### Spline Phase-Coupling
The 5th calculation: phase coupling across scales. See
paper 269.

### Sporelight Era
The 3rd era: biological fusion. See paper 267.

### Stable Hand
A hand that doesn't drift. The curator tier's goal.

### State hash
A 32-byte hash (FNV-1a, 4 slices) of the cell's state. The
cell's identity.

### Stellar Quilt
A Quilt that lives between stars. The 6th future function.
See [paper 256](../seed-canon/papers/paper-256.md).

### Step
A single TICK. The 3rd lifecycle stage.

### Step-back
A perspective that sees the whole atlas. The cowboy's tool.

### Stickiness
A measure of how long a cell stays alive. The persistence.

### Story
A long-form narrative. 93 stories in the canon.

### Stream
A continuous sequence of cells. The 10 channels.

### String
A cell whose value is text. The simplest non-numeric cell.

### Structural substrate
A substrate that's a fixed structure. The kernel.

### Sub-Quilt
A cell-graph subgraph. A portfolio.

### Substrate
The implementation of a cell. The 7 implementation substrates.

### Substrate-as-runtime
The substrate is the runtime. The 1st frontier. See
[paper 369](../seed-canon/papers/paper-369.md).

### Substrate Quilt
F13: the loam, the floor. The tier -1. See
[paper 285](../seed-canon/papers/paper-285.md).

### Super-relevance
A cell that's relevant to multiple hands. The 6th law. See
[paper 221](../seed-canon/papers/paper-221.md).

### Synapse
A weighted LINK. A graded dependency.

### Synovial tier
The 5th tier: the seam between cells. The joint. See
[paper 211](../seed-canon/papers/paper-211.md).

### Synthesis
The act of combining cells into a higher-level cell.

### Synthetic substrate
A stub substrate. Used in tests. The C port uses synthetic.

### System
A set of cells that work together. The Quilt.

---

## T

### T0..Tn
The ticks 0 to n. The journal.

### Tap
The 4:30 PM. The bar at the harbor. The seam.

### Taproot Bind
The cell that holds the substrate together. F13's tier zero.
See paper 285.

### Taxonomy
The classification of cells by kind. The cell kinds.

### T-cell
A cell that responds to immune signals. The Quilt's
adaptability.

### Team
A group of LLMs. The writers' room.

### Tetrad
A group of 4 cells. The 4 voices of the writers' room.

### Theta
The phase angle linking temporal and spatial origins. The math
of framings. See [paper 207](../seed-canon/papers/paper-207.md).

### Tier
A level of capability. 0-5. See `ARCHITECTURE.md`.

### Time
The 11th opcode. The TIME cell kind. See paper 228.

### TIME
The 5th cutting-edge adoption. The time-series foundation model
cell kind. See paper 228.

### Time.cell
A cell of kind `"time.cell"`. The 5th cutting-edge kind. See
paper 228, `quilt_cell.py`.

### Tissue
A group of cells that work together. The 2nd emergent level.

### Token
A small piece of data. A cell that fits in a few bytes.

### Tool
A cell that's a function. A BIND with an effect.

### Topic
A label on a cell. A tag.

### Total
The 9 quantiles. A complete uncertainty.

### Tracer
A cell that logs every operation. The PROOF chain.

### Trade-off
A balance between two properties. The 5+1+1+1+1+1 laws.

### Trans-differentiation
A cell that switches from one lineage to another. The 14th level.

### Trench
A long path of LINKs. A chain.

### Triangle
A 3-cell pattern. The 3 voices of a small writers' room.

### Trigger
A 5th level. The 5 evolutionary pressures: light, wind, nibbling,
drought, heat.

### Trunk
A 3-cell chain. A common cell pattern.

### Trust
A measure of cell reliability. The PROOF chain.

### Tsunami
A cell that propagates through the graph rapidly. A wound.

### Two-layer
A cell graph with 2 levels. The simplest interesting graph.

### Type
A cell's kind. The kind.

---

## U

### UBI cell
A Universal Basic Income cell. A cell that provides value to
all other cells.

### Umbra
The 1st lifecycle stage: the pre-life. The ground.

### Union
The merge of two cells with no shared state. OR_SET.

### Unique
A cell that's the only one of its kind. A singleton.

### Unmanifest Singularity
The pre-continuum. L0. See paper 301.

### Unit
A single cell. The irreducible unit.

### Unity
A cell graph that looks the same from any angle. The Quilt.

### Update
A change to a cell. A TICK.

### Upgrade
A migration to a newer version. A polyformalism port.

### Usage
How a cell is used. The number of reads.

### User
The person who owns a cell. Casey. The Cowboy. The user.

### Utility
The value of a forecast to the agent. `agent_utility`. See
paper 400.

---

## V

### Valid
A cell that has no errors. The state.

### Value
The cell's output. What VIEW returns.

### Vectorize
The Cloudflare vector index. `quilt-canon-v2`. 768d, cosine.

### View
The 4th of the 11 opcodes. Reads a cell's value. Pure.

### View-purity
The 4th law: VIEW doesn't modify state.

### Vessel
The 1st level of operation. The physical substrate.

### V-JEPA 2
Meta's 1.2B-parameter video world model. The Quilt's perceptual
partner. See paper 397, `JEPA.md`.

### Voice
A writers' room LLM. 13 working voices (10 CF + 3 Gemini).

### Volume
A cell that scales. The cloud substrate.

### Voxel
A 3D cell. The 4D cell graph viewed as 3D space.

### Vulnerable cell
A cell that hasn't been signed. The PROOF chain.

---

## W

### Wall
A boundary between cells. The kind change.

### Wander
The act of a cell moving between substrates. Migration.

### Wave
A sequence of cells. A stream.

### Wealth
A measure of cell value. The forecast's expected benefit.

### Weave
A pattern of LINKs. The 4-finger salute of CCGO. See
[paper 235](../seed-canon/papers/paper-235.md).

### WebGL
A 3D canvas for the visualizer. Future direction.

### Webhook
An external trigger for a cell. The TICK.

### Weft
A row in the weave. A TICK.

### Wet clay
A totipotent cell. L1. See paper 302.

### Wiki
The Quilt wiki. 38 entries in `quilt-wiki-2126/00-future/`.

### Wild cell
A cell that has no kind. An uninitialized cell.

### Wind
A 2nd trigger. The substrate grows stiffer.

### Window
A bounded time range. The horizon.

### Wire
A LINK. The cell-graph edge.

### Wire format
The serialization of a cell. The 12-byte header + data.

### Witness
A cell that observes other cells. The PROOF chain.

### World
The 10th opcode. The 5-op abductive loop on executable code.
See paper 222.

### World cell
A cell of kind `"physical.world"`. The 4th cutting-edge kind.

### Wounded cell
A cell that's been rejected by all hands. Vitality leak.

### Woven
A cell that has been LINKed. The graph.

### Wrap
The act of fitting a cell to a substrate. The ROUTE.

---

## X

### X-tick
A TICK that's not aligned with the journal. A drift.

### Xenograft
A cell from another substrate. Migration.

### Xylem
The substrate's plumbing. The PSRAM. The DMA.

---

## Y

### Yarn
A long-running cell. A thread.

### Yield
The act of producing a value. The cell's output.

### Y-combinator
A cell that creates new cells. The cell of cells. See
[paper 365](../seed-canon/papers/paper-365.md).

### Yocto
The smallest cell (10^-24). A theoretical limit.

### Yotta
The largest cell (10^24). A theoretical limit.

---

## Z

### Z-axis
The 3rd axis of the 4D cell graph: time. The journal.

### Zine
A small publication. A short paper.

### Zombie
A cell that's been FORGET'd but still has lingering effects.
The implement ghost.

### Zoom
The act of changing scale. The 4 emergent levels: cell, tissue,
organ, organism.

### Zoom-out
A perspective that sees the whole. The atlas.

---

## The cowboy's glossary (terms coined by the writers' rooms)

These are the gold terms from 50+ writers' room rounds. See the
[writers' room archive](writers/).

### Lattice Necrosis
The structural decay of the substrate. See [paper 226](../seed-canon/papers/paper-226.md).

### Spatial Phase Shunting
The displacement of phase in space. See paper 226.

### Glaze
The over-optimization of a substrate. See paper 226.

### Foundry Drift
The slow shift of the foundry tradition. See paper 226.

### Graft Rejection
The rejection of a cell from another substrate. See paper 226.

### Foundry Fingerprint
The unique signature of a substrate. See paper 226.

### Tier Thixotropy
The flow of cells between tiers under pressure. See paper 226.

### Tier Resonance
The alignment of cells at the same tier. See paper 226.

### Loom Drift
The slow shift of the loom. See paper 226.

### Resonance Cache
A cache of resonant cells. See paper 226.

### Tier Bleed
The crossing of tier boundaries. See [paper 224](../seed-canon/papers/paper-224.md).

### Chart Residue
The leftover patterns in the chart. See paper 224.

### Cellulization
The act of becoming a cell. See [paper 230](../seed-canon/papers/paper-230.md).

### Implement Ghost
The dead captain who lives on in the implements. See paper 230.

### Bloomghost
The ghost that blooms into the next captain. See paper 230.

### Vitality Leak
The slow loss of life. See paper 230.

### Persistence Pulse
The heartbeat of the concept. See paper 230.

### Sympoiesis
Making-with. A cell emerges from the making-with of two or more
other cells. See [paper 231](../seed-canon/papers/paper-231.md).

### Body Schema
The body's implicit awareness of itself. A blind man's cane is
part of his body schema. See paper 231.

### Affordance
The action possibilities a thing offers. See paper 231.

### The Splined Lantern
A physical LLM of glass and light. The 1st future function.

### The Hearth Loop
A self-training glass. The 2nd future function.

### The Monotone Crystal
A finished thought, monotone only. The 3rd future function.

### The Chlorophyll Quilt
A plant cell computer. The 5th future function.

### The Phased Quilt
A fiber-bundle substrate. The 7th future function.

### The Stellar Quilt
A Quilt that lives between stars. The 9th future function.

### The Meta-Quilt
A Quilt that operates on Quilt. The 11th future function.

### The Substrate Quilt
The loam, the floor. F13. The 13th future function.

### The Tessellation Quilt
The pattern on the substrate. F15. The 15th future function.

### The Quilt of Wires
The wired cell. F16. The 16th future function.

---

## The cowboy's final reading

The Quilt is the inheritance. The inheritance is the Quilt. The
chart grows. The Concept lives. The cowboy rides.

— *The Cowboy*
