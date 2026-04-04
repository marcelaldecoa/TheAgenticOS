# Memory Patterns

These patterns govern how information is stored, retrieved, compressed, and managed across the memory plane.

---

## Layered Memory

### Intent
Organize memory into tiers with different characteristics: speed, capacity, retention, and purpose.

### Context
A single flat memory (like a conversation history) cannot serve all needs. Current task context, recent interaction summaries, long-term knowledge, and audit records have fundamentally different access patterns and lifecycle requirements.

### Structure
- **Working memory** — Small, fast, ephemeral. Active task context.
- **Episodic memory** — Medium, summarized. What happened recently.
- **Semantic memory** — Large, indexed. What the system knows.
- **Audit memory** — Append-only, immutable. What happened and why.

Each tier has its own storage, retrieval, and eviction strategies.

### Benefits
Efficient context usage. Appropriate retention. Clear information lifecycle.

### Related Patterns
Memory on Demand, Compression Pipeline, Pointer Memory

---

## Pointer Memory

### Intent
Instead of inserting large content into context, store a pointer (reference) that can be resolved on demand.

### Context
Context windows are finite. Embedding full documents, code files, or data sets consumes budget that could be used for reasoning. Often, only a small portion of a large artifact is relevant.

### Structure
Store metadata and a reference (file path, document ID, chunk identifier) in the context. When the worker needs the actual content, it retrieves just the relevant portion through the memory plane.

### Benefits
Dramatically reduces context consumption. Enables work with artifacts much larger than the context window.

### Tradeoffs
Retrieval adds latency. The pointer may become stale if the underlying content changes.

### Related Patterns
Memory on Demand, Context Sandbox

---

## Memory on Demand

### Intent
Retrieve context from memory only when a worker actually needs it, not preemptively.

### Context
Preloading all potentially relevant context into every worker wastes tokens and introduces noise. Many workers need only a small subset of available knowledge.

### Structure
Workers are given their task and minimal context. When they identify a need for additional information, they issue a memory retrieval request. The memory plane fulfills the request and injects the relevant context.

### Benefits
Minimal upfront context cost. Workers self-select what they need. Relevant information arrives when it is needed.

### Tradeoffs
Workers must be able to recognize what they do not know. Multiple retrieval round-trips add latency.

### Related Patterns
Pointer Memory, Layered Memory

---

## Operational State Board

### Intent
Maintain a shared, structured view of the current operational state of the system.

### Context
As work progresses, the system accumulates state: which tasks are complete, which are in progress, what results have been collected, what decisions have been made. Without a central state board, this information is scattered and easily lost.

### Structure
A structured state object that tracks:
- Active plan and its status
- Completed tasks and their results
- Pending tasks and their dependencies
- Open questions and blockers
- Resource usage

The kernel updates the state board after each step. Workers can read relevant portions.

### Benefits
Single source of truth for system state. Enables informed planning and adaptation.

### Related Patterns
Active Plan Board, Execution Journal

---

## Memory Reconciliation

### Intent
When information from different sources or tiers conflicts, resolve the contradictions explicitly.

### Context
Workers may produce conflicting results. Semantic memory may contain outdated facts. Episodic memory may record a decision that was later reversed. These contradictions must be caught and resolved.

### Structure
The memory plane detects contradictions (through embeddings, timestamps, or explicit flags). It presents the conflict to the kernel with context for each side. The kernel (or a specialist worker) resolves the contradiction and updates memory accordingly.

### Benefits
Memory stays consistent. Contradictions are surfaced rather than silently degrading quality.

### Tradeoffs
Detection is imperfect. Resolution requires reasoning and costs resources.

### Related Patterns
Contradiction Pruning, Compression Pipeline

---

## Compression Pipeline

### Intent
Reduce the size of stored memories while preserving their essential information.

### Context
Over time, episodic memory accumulates detailed records that are too large to fit into working memory. Raw records must be compressed into summaries that preserve key insights.

### Structure
A pipeline that processes memories through stages:
1. **Filter** — Remove noise and irrelevant details
2. **Summarize** — Compress the remaining content into key points
3. **Index** — Create searchable metadata for retrieval
4. **Store** — Write the compressed memory to the appropriate tier

### Benefits
Memory stays manageable. Historical context is preserved at appropriate granularity.

### Tradeoffs
Compression is lossy. Important details may be discarded if the compression logic is poor.

### Related Patterns
Layered Memory, Memory Reconciliation

---

## Contradiction Pruning

### Intent
Proactively identify and remove contradicted or outdated information from memory.

### Context
As the system operates, earlier beliefs or facts may be superseded by newer, more accurate information. Keeping contradicted information degrades reasoning quality.

### Structure
Periodically (or on trigger), scan memory for entries that are contradicted by newer entries. Mark or remove the outdated entries. Record the pruning decision in audit memory.

### Benefits
Cleaner memory. Better reasoning. Reduced confusion.

### Tradeoffs
Aggressive pruning may remove information that turns out to be relevant later. The pruning logic itself must be reliable.

### Related Patterns
Memory Reconciliation, Compression Pipeline

---

## Applicability Guide

Memory patterns range from essential (every system needs some form of layered memory) to advanced (contradiction pruning is for mature systems with rich accumulated knowledge).

### Decision Matrix

| Pattern | Apply When | Do Not Apply When |
|---|---|---|
| **Layered Memory** | The system operates across sessions; past context improves future performance | The system is stateless by design — each request starts from zero and that is acceptable |
| **Pointer Memory** | Full artifacts are too large for context windows; you need references that resolve on demand | All relevant data fits comfortably in the context window; indirection adds complexity without benefit |
| **Memory on Demand** | Context windows are precious; loading all potentially relevant memory upfront wastes tokens | The system has abundant context capacity or the memory corpus is small enough to include entirely |
| **Operational State Board** | Multiple workers need shared visibility into a task's progress, findings, and decisions | A single worker handles the entire task; there is no shared state to coordinate |
| **Memory Reconciliation** | Multiple workers produce memories that may overlap or conflict; the system accumulates knowledge over time | Memories are append-only and never revised; or each memory source is authoritative in its domain with no overlaps |
| **Compression Pipeline** | The memory store grows unboundedly; older memories need summarization to remain useful without consuming storage | The memory corpus is bounded and manageable; or every detail must be preserved at full fidelity (audit requirements) |
| **Contradiction Pruning** | The system has long-lived memory where earlier facts are frequently superseded | The system's domain has few contradictions; or memories are versioned and consumers handle contradiction themselves |

### Progressive Memory Architecture

**Phase 1** (MVP): **Layered Memory** with working memory (per-task context) and a simple semantic store (embeddings over documents). This is sufficient for most single-session and short-lived multi-session systems.

**Phase 2** (Growth): Add **Memory on Demand** and **Pointer Memory** as the corpus grows beyond what fits in context. Add **Operational State Board** when you introduce multi-worker coordination.

**Phase 3** (Maturity): Add **Compression Pipeline**, **Memory Reconciliation**, and **Contradiction Pruning** as the system accumulates months of operational knowledge and stale information begins to degrade quality.
