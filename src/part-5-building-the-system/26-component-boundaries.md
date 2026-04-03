# Component Boundaries

The reference architecture identifies subsystems. This chapter examines where to draw the lines between them — and why those lines matter more in agentic systems than in traditional software.

## Why Boundaries Matter

In a traditional application, a poorly drawn boundary causes maintenance pain: tangled dependencies, hard-to-test modules, deployment bottlenecks. In an agentic system, a poorly drawn boundary causes *behavioral* failures: a worker that cannot do its job because it lacks access to a tool it needs, a governance policy bypassed because it was enforced in the wrong layer, a memory leak that degrades reasoning quality over time.

Boundaries in an agentic system are not just architectural niceties. They are the mechanism that enables isolation, security, composability, and independent evolution of components.

## The Kernel Boundary

The cognitive kernel sits at the center of the system, but it must not become the center of *everything*.

### What belongs in the kernel

- Intent interpretation and classification.
- Plan creation and adaptation.
- Task scheduling and prioritization.
- Result consolidation.
- Worker lifecycle decisions (spawn, terminate, restart).

### What does not belong in the kernel

- Domain logic. The kernel should not know how to write code, analyze data, or draft documents. That knowledge belongs in workers.
- Tool invocation. The kernel delegates to workers, which invoke tools. The kernel never directly calls a file system API or a database.
- Long-running state. The kernel coordinates but does not hold state. State belongs in the memory plane.

### The test

If the kernel needs to be modified when you add a new domain (e.g., supporting legal document review in addition to code generation), the boundary is wrong. The kernel should be domain-agnostic. New domains are added by registering new tools, skills, and workers — not by changing the kernel.

## The Process Boundary

Each worker process has a boundary defined by its sandbox.

### The Sandbox as Contract

The sandbox is not just a security mechanism — it is a contract between the kernel and the worker. The contract states:

- **What you can access**: These files, these tools, these APIs.
- **What you must produce**: An output conforming to this schema.
- **What you must not do**: Access anything outside the sandbox.
- **What resources you have**: This many tokens, this much time.

This contract enables the kernel to reason about workers without understanding their internals. A code worker and a research worker have different sandboxes but the same contractual interface: take input, produce output, respect constraints.

### Inter-Process Communication

Workers should communicate through the kernel, not directly with each other. Direct worker-to-worker communication creates hidden dependencies, bypasses governance, and makes the system's behavior opaque.

When worker A needs information from worker B, the flow is:

```text
Worker A → reports need to kernel → kernel retrieves from B's output → delivers to A
```

This is slightly less efficient than direct communication but dramatically more observable and controllable. The kernel can log the exchange, apply policies, and maintain a complete picture of information flow.

### Exceptions

Pipeline patterns, where the output of one worker feeds directly into the next, can use direct handoff for efficiency — but the kernel must be notified and the handoff must be logged.

## The Memory Boundary

Memory is shared infrastructure, but access must be scoped.

### Memory Scoping Rules

- **Working memory** is private to the worker that holds it. No other worker reads or writes to it directly.
- **Episodic memory** is scoped by project, team, or task. A worker on project A does not see episodic memories from project B unless explicitly granted.
- **Semantic memory** is broadly accessible but read-preferences vary. A code worker retrieves code-relevant knowledge. A documentation worker retrieves writing guidelines. The retrieval query, not access control, provides the natural scoping.
- **Procedural memory** is scoped by domain. Code strategies are available to code workers. Research strategies are available to research workers.

### The Memory API

All memory access goes through a unified API:

```text
store(content, tier, scope, metadata) → memory_id
retrieve(query, tier, scope, filters) → [results]
update(memory_id, content) → void
forget(memory_id) → void
```

Workers never access the underlying storage directly. This abstraction allows the memory system to change its implementation — switching from a local vector database to a distributed one, for example — without affecting any worker.

## The Governance Boundary

Governance sits above everything. Its boundary is defined by the principle: **governance cannot be bypassed**.

### Enforcement Points

The governance plane has hooks at every boundary crossing:

- **Kernel → Worker**: When the kernel spawns a worker, governance verifies the sandbox configuration, tool permissions, and budget allocation.
- **Worker → Tool**: When a worker invokes a tool, governance evaluates the action against policies before the tool executes.
- **Worker → Memory**: When a worker writes to memory, governance checks whether the data classification allows it.
- **Worker → External**: When a worker communicates with an external service, governance verifies the endpoint is allowed and the data leaving the system is permitted.

### Governance as Middleware

Governance is best implemented as middleware that wraps every boundary crossing, not as a monolithic checkpoint at the entrance. Monolithic governance catches policy violations at the front door but misses them inside the house. Middleware governance catches them everywhere.

```text
Without middleware:  Request → [Policy Check] → Kernel → Workers → Tools → Done
With middleware:     Request → [Policy] → Kernel → [Policy] → Worker → [Policy] → Tool → Done
```

## The Tool Boundary

Tools are the system's interface with the external world. Their boundaries must be crisp.

### Tool Interface Requirements

Every tool must:

- **Declare its inputs and outputs**: Types, formats, constraints. The system must know what to send and what to expect back.
- **Declare its side effects**: Does this tool read only, or does it modify state? Does it communicate externally? The governance plane needs this information.
- **Handle its own errors**: A tool failure should not crash the worker. The tool returns a structured error that the worker can interpret and handle.
- **Respect timeouts**: Tools that hang block workers. Every tool invocation must have a timeout, with clean failure on expiry.
- **Be idempotent when possible**: Running the same tool twice with the same input should produce the same result. This simplifies retry logic.

### Tool Composition

Complex capabilities are built by composing simple tools. "Deploy the service" is not a single tool — it is a sequence: build, test, push image, update config, roll out. Each step is a tool. The composition logic lives in the worker, not in the tools themselves.

This means tools should be small, focused, and composable. A tool that does too much is hard to compose, hard to scope, and hard to govern.

## The Operator Boundary

The boundary between the operator (human) and the system is the most important one to get right.

### What Crosses the Boundary

- **Inward**: Requests, approvals, corrections, feedback, configuration.
- **Outward**: Results, progress updates, approval requests, error reports, audit summaries.

### What Does Not Cross

- Implementation details. The operator does not need to see which model was used for step 3 of subtask 7 (unless they ask).
- Internal state. The operator sees the plan and the results, not the raw context windows.
- Transient failures. If a retry succeeds, the operator does not need to know about the initial failure (though it should be logged for audit).

### The Transparency Dial

Different operators want different levels of visibility. A developer debugging the system wants to see everything. An end user wants to see the result. The operator boundary should support a transparency dial — from minimal (just the answer) to maximal (every decision, every action, every policy evaluation).

## Anti-Patterns in Boundary Design

### The God Kernel

A kernel that does everything: parses requests, executes domain logic, calls tools, manages memory, enforces policies. This kernel is impossible to test, impossible to extend, and impossible to debug.

### The Leaky Sandbox

A worker sandbox with undeclared access. The worker "happens to" have access to the production database because the sandbox was configured too broadly. This is a security incident waiting to happen.

### The Bypass Channel

A direct connection between a worker and an external service that skips governance. "It was faster to call the API directly." Faster, yes — until the API returns sensitive data that the worker should not have seen.

### The Shared Memory Free-for-All

All workers read and write to the same memory space without scoping. Worker A writes a conclusion. Worker B reads it, misinterprets it, and acts on it. Worker A never intended the conclusion to be shared. The result is chaos.

## Drawing Good Boundaries

Good boundaries follow three principles:

1. **Each component has one reason to change.** The kernel changes when orchestration logic changes. The memory plane changes when storage requirements change. Tools change when external APIs change. They do not change for each other's reasons.

2. **Every boundary crossing is explicit and observable.** No hidden channels, no implicit dependencies. If component A uses component B, there is an interface, a contract, and a log entry.

3. **Boundaries enforce the minimum necessary coupling.** Components know about each other's interfaces, never about each other's internals. A tool does not know what worker is calling it. A worker does not know what model the kernel selected for planning.

These principles are not new. They are the same principles that make operating systems, microservices, and well-designed libraries work. The Agentic OS applies them to a new domain — but the engineering discipline is timeless.
