# Planning, Acting, Checking, Adapting

A plan is a hypothesis about how to achieve a goal. Like all hypotheses, it is wrong — or at least incomplete. The question is not whether the plan will survive contact with reality, but how quickly the system can detect the mismatch and adapt.

This chapter describes the execution loop at the heart of the Agentic OS: the cycle of planning, acting, checking, and adapting that turns a decomposed task graph into a delivered result.

## The Execution Loop

```text
Plan → Act → Check → Adapt → (repeat)
```

This is not a waterfall. It is a tight loop that runs at every level of the system: at the macro level (the overall task), at the subtask level (each decomposed unit), and at the micro level (each individual action within a worker).

### Plan

The planner — a function of the cognitive kernel — takes the current state, the goal, and the available resources, and produces a plan: an ordered set of steps with dependencies, resource requirements, and success criteria.

Planning is not a one-time event. The initial plan is the best guess given what is known at the start. It *will* be revised.

The plan is a data structure, not prose. It has nodes (tasks), edges (dependencies), annotations (risk levels, estimated cost), and metadata (which governance policies apply). This structure makes it inspectable, diffable, and shareable.

### Act

Execution happens through the process fabric. Each step in the plan is assigned to a worker — a scoped process with defined inputs, tools, and boundaries. The worker executes its step and produces output.

Acting is where the system interacts with the real world: reading files, calling APIs, querying databases, generating code, writing documents. Each action has consequences, some of which are irreversible. The governance plane applies here — risky actions may be gated by approval.

### Check

After each act, the system verifies the result. Did the action succeed? Does the output meet the success criteria? Are there side effects?

Checking takes multiple forms:

- **Output validation**: Does the output match the expected format and content? Does generated code compile? Do tests pass?
- **State validation**: Is the system in the expected state after the action? Did the database update correctly? Is the file where it should be?
- **Goal alignment**: Does this result move us closer to the overall goal, or have we drifted?
- **Constraint compliance**: Did the action stay within policy boundaries? Were any governance rules triggered?

Checking is *not* optional. Systems that skip checking rely on hope. Hope is not an engineering strategy.

### Adapt

When checking reveals a mismatch — the output is wrong, a dependency failed, new information changes the picture — the system adapts.

Adaptation ranges from minor to radical:

- **Retry**: The simplest adaptation. The action failed due to a transient issue. Try again, possibly with minor adjustments. But retrying the same thing the same way is not adaptation — it is denial.
- **Revise**: The step's approach was wrong. Try a different technique. If the regex-based parser failed, try an AST-based parser. This is local adaptation within a single step.
- **Replan**: The plan itself is flawed. A dependency produced unexpected output. A new constraint was discovered. The kernel re-decomposes from the current state and produces a new plan.
- **Escalate**: The system cannot resolve the issue autonomously. It escalates to a human operator with a clear explanation of what happened, what was tried, and what options remain.
- **Abort**: The goal is unachievable, or the cost of continuing exceeds the value of the result. The system stops, reports why, and reclaims resources.

## Depth of the Loop

The loop runs at multiple depths simultaneously:

### Micro Loop: Within a Worker

A single worker performing a single step runs its own plan-act-check-adapt cycle. It generates a function, checks if it compiles, adapts the implementation if it does not. This loop is fast and tight — measured in seconds.

### Meso Loop: Across Steps

The kernel monitors progress across the task graph. As each step completes, the kernel checks whether the plan is still valid, whether dependencies are satisfied, and whether the next step should proceed as planned or be revised. This loop runs on the scale of minutes.

### Macro Loop: The Overall Task

At the highest level, the kernel evaluates whether the overall goal is being achieved. After all the code was written, does the feature actually work? After all the sections were drafted, does the document make sense? This requires stepping back from the individual steps and assessing the whole. This loop may trigger complete re-decomposition.

## The Feedback Problem

The quality of adaptation depends on the quality of feedback. If the system cannot tell whether an action succeeded, it cannot adapt.

This creates a design imperative: **build checkability into every step**.

- Code tasks should include tests that validate the output.
- Data tasks should include assertions on the data.
- Writing tasks should include criteria that can be checked (word count, coverage of topics, absence of contradictions).
- Integration tasks should include smoke tests.

When feedback is unavailable or unreliable, the system must proceed with lower confidence and narrower autonomy — checking with humans more frequently.

## Planning Strategies

Not all tasks need the same planning approach:

### Scripted Plans

For well-understood tasks with known steps. "Deploy this service: build, test, push image, update config, roll out." The plan is essentially a script. The adaptation space is small — if a step fails, retry or abort.

### Exploratory Plans

For tasks where the path is unknown. "Find out why latency increased last week." The plan is a series of investigations. Each step's result determines the next step. The plan evolves as knowledge accumulates.

### Constraint-Satisfaction Plans

For tasks defined by constraints rather than steps. "Generate a test suite that covers all public methods and achieves 80% branch coverage." The plan is iterative: generate tests, check coverage, generate more for uncovered paths, repeat until constraints are met.

### Adversarial Plans

For tasks where the system must consider failure modes. "Migrate the database schema without downtime." The plan includes rollback steps, canary checks, and fallback paths. Each step has a "what if this fails" contingency.

## When Plans Fail

Plan failure is not system failure — it is information. A failed plan tells the system something it did not know before. The question is whether the system can learn from the failure and produce a better plan.

Common failure patterns:

- **Cascading failure**: One step fails and the failure propagates through the dependency graph. The system must identify the root failure and re-plan from there, not retry each downstream step.
- **Silent failure**: A step appears to succeed but produces subtly wrong output that causes failures later. This is the hardest to detect and requires robust checking at every stage.
- **Plan obsolescence**: The world changed while the plan was executing. The file was modified by someone else. The API endpoint was deprecated. The requirements shifted. The system must detect this and replan.

## The Cost of Iteration

Every loop iteration costs resources: model calls, tool invocations, time. A system that iterates too freely burns through budgets. A system that iterates too conservatively delivers poor results.

The kernel must manage this tradeoff explicitly:

- Set iteration budgets per task and per step.
- Track the trajectory: are iterations improving the result, or oscillating?
- Recognize diminishing returns and accept "good enough."
- Report cost alongside results so operators can calibrate.

## Execution as Learning

The most important insight about the execution loop is that each cycle produces *knowledge*, not just output. The system learns what works in this context, what constraints truly apply, and what shortcuts are viable. In a mature Agentic OS, this knowledge is captured in the memory plane and improves future performance.

The plan-act-check-adapt loop is the system's method of thinking. It is trial and error made rigorous, feedback made structural, and learning made explicit. It is the difference between an agent that follows a script and an agent that *solves problems*.
