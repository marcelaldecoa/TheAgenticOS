# Kernel Patterns

These patterns govern how the cognitive kernel interprets intent, plans work, and coordinates execution.

---

## Intent Router

### Intent
Route incoming requests to the appropriate execution strategy based on their nature, complexity, and requirements.

### Context
When the kernel receives a new request, it must decide: Is this a simple task or a complex one? Does it need decomposition? Which specialists are required? What governance applies?

### Forces
- Requests vary enormously in complexity and type
- Misrouting wastes resources or produces poor results
- Over-analysis of simple requests adds unnecessary latency

### Structure
The intent router classifies requests along dimensions: complexity (simple → compound → complex), domain (code, research, operations), risk level, and required capabilities. Each classification maps to an execution strategy.

### Dynamics
Simple requests are executed directly. Compound requests are decomposed into independent subtasks. Complex requests trigger full planning with iterative refinement.

### Benefits
Efficient resource usage. Simple things stay simple. Complex things get the structure they need.

### Tradeoffs
Routing logic itself becomes a point of failure. Misclassification leads to under- or over-engineering a response.

### Failure Modes
A complex request classified as simple produces shallow results. A simple request classified as complex wastes resources and adds latency.

### Related Patterns
Planner-Executor Split, Policy-Aware Scheduler

---

## Planner-Executor Split

### Intent
Separate the decision of *what to do* from the execution of *how to do it*.

### Context
When a task requires multiple steps, reasoning about the plan and executing the steps are different cognitive activities. Mixing them leads to plans that drift and executions that lack coherence.

### Forces
- Planning requires broad context and strategic thinking
- Execution requires focused context and precision
- Tight coupling between planning and execution makes adaptation difficult

### Structure
The planner creates a structured plan: a sequence (or graph) of steps with dependencies, required capabilities, and success criteria. The executor takes each step and carries it out within a focused worker. The planner reviews results and adapts the plan.

### Dynamics
Plan → Execute step 1 → Review → Adapt plan → Execute step 2 → ... → Consolidate

### Benefits
Plans are inspectable and adjustable. Execution is focused. Adaptation is explicit.

### Tradeoffs
The overhead of maintaining a plan is not justified for trivial tasks. The planner must be invoked again after each step, adding latency.

### Related Patterns
Intent Router, Execution Loop Supervisor, Reflective Retry

---

## Policy-Aware Scheduler

### Intent
Prioritize and sequence work based on both task requirements and governance policies.

### Context
When the kernel has multiple tasks to execute, it must decide what runs first, what runs in parallel, and what is blocked by policy (e.g., requires human approval).

### Forces
- Some tasks are urgent but risky
- Some tasks are safe but low priority
- Policy constraints can block otherwise-ready work

### Structure
The scheduler maintains a priority queue of tasks, each annotated with risk level, dependencies, resource requirements, and policy status. It selects the next task to execute based on a scoring function that balances urgency, readiness, and governance compliance.

### Benefits
High-priority safe work proceeds immediately. Risky work waits for appropriate approval without blocking the rest.

### Tradeoffs
Scheduling logic adds complexity. Poor priority functions lead to starvation of important work.

### Related Patterns
Permission Gate, Staged Autonomy

---

## Result Consolidator

### Intent
Synthesize outputs from multiple workers into a coherent, unified result.

### Context
When a task is decomposed and delegated to multiple workers, their individual outputs must be combined. Different workers may produce overlapping, complementary, or conflicting results.

### Forces
- Workers operate independently with partial views
- Results may conflict
- Simple concatenation is rarely sufficient

### Structure
The consolidator collects worker outputs, identifies overlaps and conflicts, resolves contradictions (or flags them for escalation), and synthesizes a unified result that addresses the original intent.

### Benefits
Coherent output despite distributed execution. Contradictions are surfaced, not hidden.

### Tradeoffs
Consolidation itself requires model invocations and context. Complex consolidation can be as expensive as the original work.

### Related Patterns
Subagent as Process, Reviewer Process

---

## Reflective Retry

### Intent
When an action fails, analyze the failure before retrying — do not simply retry blindly.

### Context
Failures in agentic systems are common: tools return errors, models produce invalid output, context is insufficient. Blind retries waste resources and often repeat the same failure.

### Forces
- Some failures are transient (network errors) — simple retry works
- Some failures are structural (wrong approach) — retrying the same way is futile
- Distinguishing between them requires reasoning

### Structure
On failure, the kernel (or worker) analyzes the error: What went wrong? Is it transient or structural? If transient, retry with backoff. If structural, modify the approach (different tool, different decomposition, more context) and try again.

### Benefits
Higher success rate with fewer wasted invocations. Structural problems are addressed, not repeated.

### Tradeoffs
Reflection adds latency. The analysis itself can be wrong.

### Related Patterns
Recovery Process, Failure Containment

---

## Execution Loop Supervisor

### Intent
Monitor the kernel's execution loop to prevent infinite cycles, resource exhaustion, and unproductive repetition.

### Context
The kernel operates in a loop: plan, delegate, consolidate, adapt. Without supervision, this loop can run indefinitely — especially when the system retries failed tasks or refines plans endlessly.

### Forces
- Some tasks genuinely require many iterations
- Some loops are pathological (no progress despite effort)
- Arbitrary iteration limits are crude but necessary

### Structure
The supervisor tracks loop metrics: iteration count, progress indicators, resource consumption, time elapsed. It triggers alerts or termination when:
- Iteration count exceeds a threshold
- No measurable progress is made across N iterations
- Resource budget is exhausted

### Benefits
Prevents runaway execution. Provides diagnostic data for post-mortem analysis.

### Tradeoffs
A strict supervisor may kill useful work that is simply slow. A lenient supervisor may waste resources.

### Related Patterns
Resource Envelope, Context Budget Enforcement
