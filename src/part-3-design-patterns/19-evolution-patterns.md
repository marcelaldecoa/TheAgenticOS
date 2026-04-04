# Evolution Patterns

These patterns address how an Agentic OS grows, adapts, and extends over time without collapsing into chaos. A system that cannot evolve is dead. A system that evolves without discipline is dangerous.

---

## Patternized Skills

### Intent
Capture proven sequences of reasoning, operator usage, and decision-making as reusable, versioned skills that agents can invoke.

### Context
Agents repeatedly solve similar classes of problems — refactoring code, summarizing research, triaging tickets. Each time, the agent reasons from scratch, sometimes well, sometimes poorly. This is wasteful and inconsistent.

### Forces
- Ad hoc reasoning is flexible but inconsistent
- Rigid templates are consistent but brittle
- Skills must evolve as domains and tools change

### Structure
A skill is a structured artifact containing: the problem class it addresses, the recommended decomposition strategy, the operators typically needed, the memory patterns to apply, the governance constraints, and example execution traces. Skills are versioned and stored in a skill registry.

### Dynamics
Agent encounters a problem → Skill registry matches problem class → Agent loads relevant skill → Skill guides decomposition and operator selection → Agent adapts skill to specific context → Execution results feed back into skill refinement.

### Benefits
Consistency. Faster execution. Knowledge preservation. Onboarding acceleration.

### Tradeoffs
Skill maintenance burden. Risk of applying stale skills to changed domains.

### Failure Modes
Skills that become gospel instead of guidance. Skill registries that grow without curation.

### Related Patterns
Reusable Worker Archetypes, Operator Adapters, Governed Extensibility

---

## Reusable Worker Archetypes

### Intent
Define standard worker templates — archetypes — that can be instantiated for common roles: researcher, reviewer, coder, analyst, summarizer.

### Context
Many agentic workflows use workers with similar configurations: a code reviewer always needs source access, linting tools, and a quality rubric. Configuring these from scratch each time is error-prone and slow.

### Forces
- Custom workers are flexible but expensive to configure
- Standard archetypes are efficient but may not fit every situation
- Archetypes must be customizable without losing their core character

### Structure
A worker archetype defines: the worker's role, default capability set, standard operators, memory access patterns, quality criteria, and typical interaction patterns. Archetypes are parameterized — the "code reviewer" archetype can be instantiated with different language contexts, style guides, and risk tolerance.

### Dynamics
Kernel needs a worker for a specific role → Selects matching archetype → Instantiates with task-specific parameters → Worker operates with archetype defaults plus customizations → Post-task review identifies archetype improvements.

### Benefits
Rapid worker provisioning. Consistent quality per role. Captured organizational knowledge about effective configurations.

### Tradeoffs
Archetype maintenance. Risk of forcing problems into existing archetypes when a novel approach would be better.

### Failure Modes
"One archetype fits all" thinking. Archetypes that diverge from actual effective practice.

### Related Patterns
Patternized Skills, Subagent as Process, Scoped Worker Contract

---

## Operator Adapters

### Intent
Create a uniform interface layer over heterogeneous external tools and services so that operators can be swapped, upgraded, or replaced without changing the agents that use them.

### Context
External tools change their APIs. New tools emerge that are better than current ones. Multiple tools provide similar functionality with different interfaces. Agents should not be coupled to specific tool implementations.

### Forces
- Direct tool coupling is simple but creates fragile dependencies
- Abstraction layers add indirection but enable evolution
- Adapter quality determines whether abstraction helps or hurts

### Structure
An operator adapter implements a standard interface (the operator contract) and translates between that interface and the specific external tool. The adapter handles authentication, error mapping, rate limiting, and response normalization. Agents interact only with the standard interface.

### Dynamics
Agent invokes operator through standard interface → Adapter translates to tool-specific API → Tool executes → Adapter normalizes response → Agent receives standard response format. Tool upgrades or replacements only require adapter changes.

### Benefits
Tool independence. Smooth migrations. Consistent error handling across diverse tools.

### Tradeoffs
Adapter development and maintenance. Potential loss of tool-specific features behind a generic interface.

### Failure Modes
Leaky abstractions where tool-specific errors propagate through. Adapters that eliminate capabilities unique to specific tools.

### Related Patterns
Tool as Operator, Operator Registry, Operator Isolation

---

## Domain-Specific Agentic OS

### Intent
Create specialized operational systems optimized for a particular domain — code engineering, research, customer support, compliance — rather than a single general-purpose system.

### Context
A general-purpose Agentic OS can handle any domain but excels at none. Different domains have fundamentally different requirements: code engineering needs tight tool integration and test feedback loops; research needs broad source access and uncertainty tracking; customer support needs knowledge bases and escalation policies.

### Forces
- Generality provides flexibility but diffuses capability
- Specialization provides depth but limits scope
- Organizations handle multiple domains

### Structure
A domain-specific Agentic OS inherits the core architecture (kernel, process fabric, memory plane, operator fabric, governance plane) but customizes: the skill library, the operator registry, the memory schemas, the governance policies, and the worker archetypes for its specific domain.

### Dynamics
Organization identifies a domain with sufficient volume and pattern regularity → Forks the base OS configuration → Adds domain skills, operators, and policies → Operators develop domain expertise through accumulated memory → Domain OS becomes increasingly effective.

### Benefits
Deep domain performance. Appropriate governance per domain. Cleaner evolution paths.

### Tradeoffs
Duplication across domain OSs. Integration complexity for cross-domain workflows.

### Failure Modes
Over-specialization that prevents cross-domain learning. Under-specialization that's just the general system with a label.

### Related Patterns
Meta-Orchestrator, Capability Marketplace, Patternized Skills

---

## Meta-Orchestrator

### Intent
Coordinate work across multiple specialized Agentic OS instances when a task spans several domains.

### Context
A complex business process might require code changes (handled by the Coding OS), documentation updates (handled by the Writing OS), compliance checks (handled by the Compliance OS), and customer notification (handled by the Support OS). No single OS handles all of this.

### Forces
- Single-OS execution is simpler but limited to one domain
- Multi-OS coordination enables cross-domain workflows but adds orchestration complexity
- Each OS has its own governance which the meta-orchestrator must respect

### Structure
The meta-orchestrator is itself an Agentic OS that understands domain boundaries, maintains a cross-domain plan, and delegates sub-intents to the appropriate domain OS. It receives results from each domain OS, reconciles them, and tracks cross-domain dependencies.

### Dynamics
Meta-orchestrator receives cross-domain intent → Decomposes by domain → Delegates to domain OSs → Tracks progress across domains → Reconciles results → Handles cross-domain dependencies → Reports consolidated outcome.

### Benefits
Cross-domain workflow support. Preserved domain specialization. Coordinated execution.

### Tradeoffs
Orchestration overhead. Cross-domain governance complexity. Error correlation across domains.

### Failure Modes
Meta-orchestrator that micromanages domain OSs. Domain OSs that cannot operate independently.

### Related Patterns
Domain-Specific Agentic OS, Multi-OS Coordination, Active Plan Board

---

## Capability Marketplace

### Intent
Enable discovery and composition of capabilities (skills, operators, worker archetypes) across organizational boundaries through a shared registry.

### Context
As an organization develops multiple domain OSs and accumulates skills and operators, valuable capabilities become siloed. A skill developed for the customer support domain might be useful in the research domain. An operator adapter for a data service might be needed across all domains.

### Forces
- Siloed capabilities lead to duplication and inconsistency
- Shared capabilities require quality standards and compatibility guarantees
- Openness enables innovation but introduces quality risk

### Structure
The capability marketplace is a curated registry where teams can publish and discover skills, operators, worker archetypes, and policy packs. Each published capability includes: description, interface contract, quality metrics, governance requirements, version history, and usage examples.

### Dynamics
Team develops a useful capability → Publishes to marketplace with metadata → Other teams discover via search → Consumers evaluate compatibility → Adoption with optional customization → Usage metrics and feedback improve the capability.

### Benefits
Knowledge sharing. Reduced duplication. Cross-pollination. Community-driven quality.

### Tradeoffs
Marketplace governance overhead. Version management across consumers. Quality consistency.

### Failure Modes
Marketplace pollution with low-quality capabilities. Version conflicts across consumers. Abandoned capabilities.

### Related Patterns
Operator Registry, Patternized Skills, Governed Extensibility

---

## Governed Extensibility

### Intent
Allow the system to be extended with new capabilities, operators, and skills while maintaining governance invariants.

### Context
A system that cannot be extended becomes obsolete. A system that can be extended without controls becomes unstable. The tension between extensibility and governance is fundamental.

### Forces
- Openness enables adaptation and innovation
- Openness without governance enables chaos
- Extension points must be designed, not accidental

### Structure
The system defines explicit extension points: operator adapters, skill packages, policy modules, worker archetypes. Each extension point has a contract that extensions must satisfy. Extensions are validated against the contract before activation. Governance policies define who can publish extensions, what testing is required, and what approval flow applies.

### Dynamics
Developer creates extension → Validates against contract → Submits for review → Governance pipeline evaluates (automated tests, policy compliance, security scan) → Approved extensions are published → Activated extensions operate within the system's governance framework.

### Benefits
Safe evolution. Innovation within guardrails. Quality assurance for extensions.

### Tradeoffs
Extension development overhead. Governance pipeline latency. Contract design complexity.

### Failure Modes
Contracts that are too restrictive, preventing useful extensions. Contracts that are too permissive, admitting low-quality extensions.

### Related Patterns
Capability Marketplace, Operator Adapters, Patternized Skills

---

## Applicability Guide

Evolution patterns govern how the system grows and adapts over time. They are relevant for systems that will live beyond a prototype — but premature investment in evolution infrastructure is a common trap.

### Decision Matrix

| Pattern | Apply When | Do Not Apply When |
|---|---|---|
| **Patternized Skills** | You have recurring task types that benefit from codified instructions, tools, and strategies | Every task is unique; or you are still discovering what skills the system needs |
| **Reusable Worker Archetypes** | Multiple projects need the same types of workers (coder, reviewer, researcher); standardization reduces duplication | You have a single project with bespoke worker types that will not be reused |
| **Operator Adapters** | External tool APIs change frequently; you need an abstraction layer to isolate the system from API drift | You integrate with a single stable API that has not changed in years |
| **Domain-Specific Agentic OS** | A vertical domain (legal, medical, financial) has unique requirements that justify a specialized system | A general-purpose system with skill packages is sufficient for your domain needs |
| **Meta-Orchestrator** | You need to coordinate multiple independent Agentic OSs; cross-OS workflows are a real requirement | A single OS with internal modularity handles all your domains |
| **Capability Marketplace** | Multiple teams develop and share skills, tools, and policies; a distribution mechanism is needed | A single team builds everything; sharing infrastructure adds overhead without benefit |
| **Governed Extensibility** | Third parties or untrusted teams contribute extensions; you need safety guarantees for extensions | All extensions are built by a trusted core team; governance overhead is not justified |

### Evolution Timing

**Before launch**: Invest in **Operator Adapters** (insulate from external API changes) and **Patternized Skills** (codify what you already know works).

**After 3 months of operation**: Introduce **Reusable Worker Archetypes** (standardize what you have learned) and evaluate whether **Governed Extensibility** is needed.

**After 6+ months, multiple teams**: Consider **Capability Marketplace** and **Meta-Orchestrator** only if you have genuine multi-team or multi-OS coordination needs.

**Domain-Specific Agentic OS** is a strategic decision, not an incremental one. Build it when you have enough domain expertise and operational evidence to justify the investment.
