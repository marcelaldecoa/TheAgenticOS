# Problem Decomposition

A single well-stated goal can hide enormous complexity. "Build me a REST API for user management" sounds like one task. It is dozens: design the data model, define endpoints, implement authentication, write validation logic, handle error cases, set up database migrations, add tests, document the API. Each of those contains subtasks of its own.

Decomposition — breaking a problem into smaller, manageable pieces — is perhaps the most important cognitive operation in an agentic system. It is the moment where a vague mountain of work becomes a structured plan.

## Why Decomposition Matters

Language models have finite context windows and finite reasoning depth. A model asked to "build the entire API" in one pass will produce something superficial — correct in shape but wrong in details. The same model asked to "implement the email validation function for user registration" will produce something precise, tested, and robust.

This is not a limitation to work around. It is a fundamental principle: **focused context produces better results**.

Decomposition is how the Agentic OS turns broad intent into focused work. Each subtask gets a worker with a scoped context, a clear objective, and explicit success criteria. The worker does not need to know about the entire API. It needs to know about email validation.

## The Decomposition Spectrum

Not all decomposition is equal. Tasks fall along a spectrum of decomposability:

### Trivially Decomposable

Tasks that split naturally into independent parts. "Rename all occurrences of `userId` to `user_id` in these five files." Five independent find-and-replace operations. No dependencies, no coordination needed.

### Sequentially Decomposable

Tasks with a natural order. "Parse the CSV, validate each row, transform to JSON, upload to the API." Each step depends on the previous one's output. The decomposition is a pipeline.

### Graph-Decomposable

Tasks with partial ordering. Some subtasks depend on others; many can run in parallel. "Build a dashboard: fetch user data (API), fetch analytics data (API), design layout (UI), render charts (UI, depends on data), compose page (depends on layout and charts)." This is a dependency graph.

### Iteratively Decomposable

Tasks where the decomposition itself evolves. "Research the best caching strategy for our application." You cannot decompose this upfront because you do not know what you will find. Each step — analyzing the workload, reviewing options, prototyping a solution — may change the plan.

### Non-Decomposable

Tasks that require holistic reasoning. "Review this code for architectural coherence." This cannot be split because the insight comes from seeing the whole. These tasks must be given to a single worker with sufficient context.

## Decomposition Strategies

The cognitive kernel employs different strategies depending on the task:

### Functional Decomposition

Split by *what* needs to be done. Each subtask is a distinct function: "design the schema," "implement the endpoint," "write the tests." This is the most common strategy and works well when the functions are relatively independent.

### Data Decomposition

Split by *what data* is being processed. "Analyze logs from the last 30 days" becomes 30 parallel tasks, one per day. This is powerful when the operation is uniform and the data partitions cleanly.

### Temporal Decomposition

Split by *when* things happen. "Set up the deployment pipeline" decomposes into: build stage, test stage, staging deploy, production deploy. Each phase is a natural boundary.

### Risk-Based Decomposition

Split by *risk level*. Separate the safe changes from the risky ones. Apply the safe changes first, validate, then proceed to the risky changes with human approval. This strategy interleaves with the governance plane.

## The Decomposition Contract

Each subtask produced by decomposition should carry a contract:

- **Objective**: What this subtask must achieve, stated precisely.
- **Inputs**: What information or artifacts the subtask receives.
- **Outputs**: What the subtask must produce.
- **Constraints**: What the subtask must not do.
- **Success criteria**: How to verify the subtask was completed correctly.
- **Dependencies**: What other subtasks must complete before this one can start.

This contract is not bureaucracy — it is the mechanism that allows independent workers to produce results that fit together. Without it, you get a puzzle where the pieces were cut by different people using different templates.

## Depth of Decomposition

How far should you decompose? Too shallow, and subtasks are still too complex for focused execution. Too deep, and the coordination overhead drowns out the work.

The right depth depends on two factors:

1. **Worker capability**: How complex a task can a single worker handle reliably? This varies with the model, the domain, and the available tools: larger models, well-tooled domains, and routine tasks allow shallower decomposition.
2. **Coordination cost**: Each additional level of decomposition adds overhead — more context assembly, more result consolidation, more potential for miscommunication.

The sweet spot is where each subtask is small enough to be executed with high reliability but large enough to carry meaningful context. In practice, this is often 2-3 levels of decomposition for complex tasks.

## Decomposition Failures

Decomposition can go wrong in characteristic ways:

- **Over-decomposition**: Splitting a task so finely that each piece lacks the context needed to make good decisions. A function split into "write line 1," "write line 2" is absurd. But less obvious versions of this happen when semantic units are broken across workers.

- **Under-decomposition**: Leaving a task too large for reliable execution. The worker produces something that looks complete but collapses under scrutiny.

- **Wrong boundaries**: Splitting at the wrong seam. Two subtasks that should share context are separated; two unrelated subtasks are grouped. This leads to duplicate work or contradictory outputs.

- **Missing dependencies**: Failing to identify that subtask B needs the output of subtask A. The result is a worker blocked on information it does not have, forced to guess or fail.

- **Circular dependencies**: A decomposition where A depends on B and B depends on A. This happens when the decomposition does not respect the natural information flow.

## Decomposition as a First-Class Operation

In the Agentic OS, decomposition is not an informal step buried inside a prompt. It is a first-class operation with explicit inputs (the structured intent) and explicit outputs (a task graph). The kernel can inspect it, modify it, visualize it. When a plan fails, the kernel can ask: Was the decomposition wrong? Should we re-decompose?

This explicitness is what separates an Agentic OS from a chatbot chain. The chatbot chain decomposes implicitly — each link in the chain vaguely hands off to the next. The Agentic OS decomposes explicitly — the task graph is a data structure that can be reasoned about, optimized, and adapted.

The next chapter explores what happens after decomposition: how the system executes, monitors, and adapts the plan.
