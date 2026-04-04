# Operator Patterns

These patterns govern how the Agentic OS interacts with external tools, APIs, and services.

---

## Tool as Operator

### Intent
Wrap every external tool as a typed, permissioned, observable operator.

### Context
Raw tool access — "give the model a function and let it call it" — lacks governance, typing, and observability. Wrapping tools as operators provides the control surface needed for production systems.

### Structure
An operator wraps a tool with:
- **Type signature** — Inputs and outputs are explicitly typed
- **Permission requirements** — What capabilities are needed to invoke it
- **Risk classification** — Low, medium, high
- **Observability** — Invocations are logged with inputs, outputs, latency, and errors
- **Error handling** — Failures are captured and returned as structured results

### Benefits
Governed, observable, reliable tool access. Consistent interface regardless of underlying tool implementation.

### Related Patterns
Operator Registry, Operator Isolation, Skill over Operators

---

## Operator Registry

### Intent
Maintain a central catalog of all available operators with their metadata, permissions, and status.

### Context
As the number of available tools grows, the system needs a way to discover, select, and manage them. Without a registry, tool selection is ad-hoc and ungoverned.

### Structure
A registry that stores for each operator:
- Name and description
- Type signature
- Permission requirements
- Risk classification
- Status (active, deprecated, disabled)
- Usage metrics

The kernel consults the registry when deciding which operators to make available to a worker.

### Benefits
Central governance point. Dynamic capability management. Clear documentation.

### Related Patterns
Tool as Operator, Capability-Based Access

---

## Skill over Operators

### Intent
Compose multiple operators into a higher-level reusable recipe called a skill.

### Context
Many real-world tasks require a specific sequence of tool invocations with logic connecting them. Rather than having the model improvise this sequence every time, encode it as a skill.

### Structure
A skill is a named, tested recipe that:
- Combines specific operators in a defined sequence or graph
- Includes logic for handling intermediate results
- Has its own input/output contract
- Is registered and versioned

Example:
```text
Skill: "Code Review"
  Steps:
    1. git.diff → Get changes
    2. file.read → Read changed files for context
    3. analyze → Assess code quality and risks
    4. comment.create → Post review feedback
```

### Benefits
Consistency and reliability. Tested workflows. Reusable across contexts.

### Tradeoffs
Skills are less flexible than improvised workflows. They must be maintained as tools and APIs evolve.

### Related Patterns
Composable Operator Chain, Patternized Skills

---

## Composable Operator Chain

### Intent
Allow operators to be chained into pipelines where the output of one becomes the input of the next.

### Context
Many tasks are naturally pipelines: fetch → transform → validate → store. Expressing these as chains makes them composable and reusable.

### Structure
Operators expose typed inputs and outputs. The system matches output types to input types, forming a pipeline. Each step in the chain is independently observable and governable.

### Benefits
Clean data flow. Each operator is testable in isolation. Chains are composable — new pipelines from existing operators.

### Related Patterns
Skill over Operators, Tool as Operator

---

## Operator Isolation

### Intent
Ensure that a failure in one operator does not crash the system or corrupt other operators.

### Context
External tools fail. APIs time out. Services return errors. These failures must be contained.

### Structure
Each operator invocation runs in its own error boundary. Failures are captured as structured results (not exceptions) and returned to the caller. The caller (worker or kernel) decides how to handle the failure.

### Benefits
System stability. Graceful degradation. Clear error handling paths.

### Related Patterns
Operator Fallback, Failure Containment

---

## Operator Fallback

### Intent
When a primary operator fails, automatically attempt an alternative operator that can fulfill the same need.

### Context
External services are unreliable. Having a fallback operator reduces the impact of failures.

### Structure
The operator registry associates fallback operators with primary operators:
```text
Primary: search_web (API A)
Fallback: search_web_alt (API B)
Condition: On timeout or 5xx error
```

### Benefits
Higher reliability. Transparent to the caller.

### Tradeoffs
Fallback operators may have different characteristics (latency, result quality). Managing fallback chains adds complexity.

### Related Patterns
Operator Isolation, Tool as Operator

---

## Resource-Aware Invocation

### Intent
Consider resource costs (latency, tokens, API limits) when deciding which operator to invoke and how.

### Context
Operators have costs: API rate limits, token consumption, latency, monetary cost. Ignoring these leads to budget exhaustion, throttling, or excessive latency.

### Structure
The kernel tracks resource budgets and operator costs. Before invoking an operator, it checks:
- Is the budget sufficient?
- Is the operator within rate limits?
- Is a cheaper alternative available?
- Should this invocation be batched or deferred?

### Benefits
Sustainable execution. Cost control. Graceful behavior under resource pressure.

### Related Patterns
Resource Envelope, Context Budget Enforcement

---

## Applicability Guide

Operator patterns structure how the system interacts with the external world. Start with the minimum tooling surface and expand deliberately.

### Decision Matrix

| Pattern | Apply When | Do Not Apply When |
|---|---|---|
| **Tool as Operator** | The system needs to interact with external services, files, or APIs through a uniform interface | The system is purely reasoning-based with no external side effects |
| **Operator Registry** | You have 5+ tools; workers need to discover tools dynamically; governance must scope tool access | You have 1-2 hardcoded tools that every worker always uses |
| **Skill over Operators** | Recurring multi-step workflows benefit from packaged instructions, strategies, and tool selections | Every task is novel; no workflow repeats enough to justify packaging |
| **Composable Operator Chain** | Multi-stage operations where one tool's output feeds the next (e.g., search → fetch → extract) | Each tool invocation is independent; composition adds indirection without value |
| **Operator Isolation** | Tool failures should not crash the worker; untrusted tools need sandboxing | All tools are trusted, well-tested, and fast; isolation overhead is not justified |
| **Operator Fallback** | Primary tools have reliability issues; alternative providers exist | Each tool is unique with no equivalent alternative; or reliability is already sufficient |
| **Resource-Aware Invocation** | Tools have rate limits, costs, or latency constraints that require budgeting | Tools are free, unlimited, and fast; cost tracking adds overhead without benefit |

### Start Here

Every system needs **Tool as Operator** (a structured interface to external capabilities). Add the **Operator Registry** once you have more than a handful of tools. Add **Skill over Operators** when you notice teams repeatedly assembling the same tool combinations for similar tasks. The other patterns respond to operational pressures — add them when you observe the specific problem they solve.
