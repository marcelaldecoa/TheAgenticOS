# Process Patterns

These patterns govern how workers are created, isolated, managed, and coordinated.

---

## Subagent as Process

### Intent
Model every unit of delegated work as an isolated process with its own context, capabilities, and lifecycle.

### Context
When the kernel delegates work, the worker must operate independently without polluting the kernel's context or other workers. This is the foundational pattern of the process fabric.

### Forces
- Workers need enough context to do their job
- Workers must not see more than they need
- The kernel must be able to inspect, manage, and terminate workers
- Worker failures must not cascade

### Structure
Each worker is spawned as an isolated process with:
- A context sandbox (only relevant information)
- A capability set (only authorized tools)
- A task contract (inputs, constraints, outputs)
- A lifecycle (creation, execution, completion/failure, termination)

### Benefits
Clean isolation. Predictable resource usage. Observable execution. Governed capabilities.

### Tradeoffs
Isolation adds overhead (context copying, capability scoping). Very simple tasks may not justify the overhead.

### Related Patterns
Context Sandbox, Scoped Worker Contract, Ephemeral Worker

---

## Context Sandbox

### Intent
Provide each worker with exactly the context it needs — no more, no less.

### Context
Context windows are a finite resource. Giving a worker the entire conversation history wastes tokens and introduces noise. Giving it too little context leads to poor results.

### Forces
- More context → better understanding but more cost and potential confusion
- Less context → faster and cheaper but higher risk of misunderstanding
- The right amount depends on the task

### Structure
The kernel curates a context package for each worker: task definition, relevant retrieved information, relevant prior results, and any required constraints. Irrelevant history, other workers' contexts, and system internals are excluded.

### Benefits
Focused workers produce better results. Token budgets are respected. Information leakage between tasks is prevented.

### Tradeoffs
Context curation requires effort and judgment. Mistakes in curation (missing critical information) lead to poor worker performance.

### Related Patterns
Subagent as Process, Memory on Demand

---

## Ephemeral Worker

### Intent
For one-shot tasks, spawn a worker that is fully discarded after completion.

### Context
Many subtasks are atomic: summarize this document, extract these fields, classify this ticket. They do not need persistent state or long-running context.

### Structure
The worker is created, given its task and context, produces its output, and is immediately terminated. No state is preserved from the worker itself — though the kernel may store the result in memory.

### Benefits
Minimal resource usage. No stale state. Clean lifecycle.

### Tradeoffs
If the same type of work recurs, the lack of persistent state means the worker cannot learn from previous invocations. The kernel's memory must compensate.

### Related Patterns
Context Sandbox, Subagent as Process

---

## Scoped Worker Contract

### Intent
Define a formal contract between the kernel and each worker specifying inputs, constraints, capabilities, outputs, and failure handling.

### Context
Without a clear contract, workers operate on implicit assumptions. They may exceed their scope, use unauthorized tools, or produce output in unexpected formats.

### Structure
```text
Contract:
  Task:         "Summarize the changes in this pull request"
  Inputs:       { diff: string, files_changed: string[] }
  Capabilities: [ file.read, git.diff ]
  Constraints:  "Do not modify any files. Output ≤ 500 words."
  Output:       { summary: string, risk_assessment: string }
  On Failure:   "Return partial results with explanation"
  Timeout:      30 seconds
```

### Benefits
Explicit expectations. Verifiable compliance. Clear failure semantics.

### Related Patterns
Subagent as Process, Permission Gate

---

## Parallel Specialist Swarm

### Intent
Execute independent subtasks concurrently using specialized workers.

### Context
When a complex request decomposes into independent subtasks (e.g., analyze code quality, check security vulnerabilities, review documentation), running them sequentially wastes time.

### Structure
The kernel identifies independent subtasks, spawns a specialist worker for each, and runs them in parallel. Results are collected and consolidated when all workers complete (or when a timeout is reached).

### Benefits
Dramatic latency reduction for decomposable tasks. Each specialist is optimized for its domain.

### Tradeoffs
Parallel execution increases peak resource usage. Consolidation of parallel results adds complexity. Not all tasks are truly independent.

### Related Patterns
Result Consolidator, Planner-Executor Split

---

## Reviewer Process

### Intent
Validate the output of a primary worker before returning it to the kernel.

### Context
Worker output may be incorrect, incomplete, or inconsistent. A separate reviewer with different perspective or criteria can catch errors.

### Structure
After a primary worker produces output, a reviewer process is spawned with: the original task, the output, and review criteria. The reviewer validates, critiques, and either approves or sends back for revision.

### Benefits
Higher quality output. Catches errors that the primary worker is blind to.

### Tradeoffs
Adds latency and cost. The reviewer itself can be wrong. Reviewing every task is overkill — use selectively for high-risk or high-value outputs.

### Related Patterns
Result Consolidator, Recovery Process

---

## Recovery Process

### Intent
Handle failed tasks with a specialized recovery strategy rather than simple retries.

### Context
When a worker fails, the failure may require diagnosis, alternative approaches, or human escalation — not just repeating the same work.

### Structure
A recovery process is spawned with: the original task, the failure details, and previous attempts. It analyzes the failure, determines a recovery strategy (retry with modifications, use alternative approach, request more context, escalate), and executes it.

### Benefits
Intelligent failure recovery. Avoids wasting resources on repeated failures.

### Tradeoffs
Recovery logic is itself fallible. Multiple recovery attempts can consume significant resources.

### Related Patterns
Reflective Retry, Failure Containment, Human Escalation
