# Knowledge OS

Every organization has more knowledge than it can use. Documents are written and never read. Decisions are made and their rationale forgotten. Expertise lives in people's heads and leaves when they do. Lessons are learned and re-learned.

A Knowledge OS does not just store information — it makes organizational knowledge *operational*: findable, connectable, maintainable, and applicable at the moment it is needed.

## The Domain

Knowledge management has historically failed because it treats knowledge as a storage problem. Create a wiki, fill it with documents, hope people search before they ask. The result is always the same: the wiki becomes a graveyard of outdated pages.

The Agentic OS model reframes knowledge management as an *active process*:

- **Capture**: Automatically extract knowledge from where it is created — conversations, documents, code, decisions — rather than requiring manual entry.
- **Connect**: Link related knowledge across sources and domains. The architecture decision from six months ago is related to the bug report from last week.
- **Maintain**: Continuously validate, update, and retire knowledge. Detect when information becomes stale.
- **Deliver**: Surface knowledge at the moment it is needed, in the context where it is useful, without requiring the user to search.

## Architecture

### Cognitive Kernel

The Knowledge OS kernel handles intents like:

- "What is our policy on X?" → Policy retrieval with applicability assessment.
- "Why did we decide to use Y?" → Decision archaeology — tracing back through documents, discussions, and commits.
- "What do we know about Z?" → Comprehensive knowledge assembly from multiple sources.
- "Document this decision." → Capture structured knowledge from context.
- "Is our documentation on W still accurate?" → Validation against current state.

### Process Fabric

Knowledge workers:

- **Harvester**: Monitors information sources — chat channels, document repositories, code commits, meeting notes — and extracts knowledge artifacts. Runs continuously in the background.
- **Curator**: Evaluates harvested knowledge for quality, relevance, and novelty. Deduplicates, categorizes, and links to related knowledge.
- **Validator**: Periodically checks existing knowledge against current reality. Is this API documentation still accurate? Does this process still work? Are these guidelines still followed?
- **Retriever**: Finds and assembles knowledge in response to queries. Goes beyond keyword search — understands the question's intent and assembles a comprehensive answer from multiple sources.
- **Author**: Produces structured knowledge artifacts — documentation, guides, FAQs, onboarding materials — from raw knowledge.

### Memory Plane

The Knowledge OS memory plane *is* the product. Unlike other OS variants where memory supports the work, here memory *is* the work.

- **Document store**: The canonical repository of structured documents — policies, procedures, architecture decisions, technical specifications.
- **Knowledge graph**: A network of concepts, relationships, and facts extracted from all sources. "Service A depends on Service B" is a relationship. "We chose PostgreSQL because of JSONB support" is a decision node linked to the technology node.
- **Provenance layer**: Every piece of knowledge tracks its origin: who created it, when, from what source, and how confident the system is in its accuracy. Provenance enables trust assessment.
- **Freshness index**: A timestamp-and-signal system that tracks how likely each piece of knowledge is to be current. Documentation updated last week is probably fresh. Documentation last modified two years ago and referencing a deprecated API version is probably stale.
- **Usage analytics**: What knowledge is accessed frequently? What knowledge is never accessed? What questions are asked that have no answer in the knowledge base? These signals guide curation priorities.

### Governance

Knowledge-specific policies:

- **Classification**: Knowledge is classified by sensitivity (public, internal, confidential, restricted) and access is scoped accordingly.
- **Retention**: Knowledge follows retention policies. Temporary project notes expire. Architectural decisions are retained permanently.
- **Accuracy accountability**: Knowledge artifacts have owners. When a validator finds stale content, the owner is notified.
- **Source authority**: For conflicting information, the system applies a priority order — official documentation overrides chat conversations, which override individual notes.
- **Redaction**: Sensitive information (credentials, personal data, financial details) is detected and redacted before knowledge is stored or shared.

## Workflow: Knowledge Capture

```mermaid
flowchart LR
  Source[Meeting / Document /\nConversation] --> H[Harvest\nExtract decisions,\nrationale, actions]
  H --> Cu[Curate\nLink, deduplicate,\ncheck conflicts]
  Cu --> Au[Author\nProduce structured\nknowledge artifact]
  Au --> KG[Knowledge Graph\nIndexed & linked]
```

### The Meeting That Produces Knowledge

A team holds an architecture review meeting. In a traditional organization, the knowledge from this meeting lives in the attendees' memories and maybe a sparse set of meeting notes that no one reads.

In a Knowledge OS:

### 1. Harvest

The harvester processes the meeting transcript (or notes) and extracts:

- **Decisions**: "We decided to use event sourcing for the order service."
- **Rationale**: "Because we need complete audit trails and the ability to replay events for debugging."
- **Alternatives considered**: "We considered CRUD with audit tables but rejected it because of the complexity of retroactive corrections."
- **Action items**: "Alex will prototype the event store by next sprint."
- **Open questions**: "We need to determine the event retention policy."

### 2. Curate

The curator:

- Links the decision to the order service node in the knowledge graph.
- Links the rationale to the compliance requirements node (audit trails).
- Checks for conflicts: Does this decision contradict any existing architecture guidelines? (None found.)
- Identifies related knowledge: The team evaluated event sourcing for the payment service six months ago and decided against it — link both decisions so future readers see the full picture.

### 3. Author

The author produces an Architecture Decision Record (ADR):

```markdown
# ADR-047: Event Sourcing for Order Service

## Status: Accepted
## Date: 2026-04-03

## Context
The order service requires complete audit trails for regulatory compliance
and the ability to replay events for debugging production issues.

## Decision
We will use event sourcing as the persistence strategy for the order service.

## Alternatives Considered
- CRUD with audit tables: Rejected due to complexity of retroactive corrections.

## Consequences
- Complete event history available for audit and debugging.
- Increased storage requirements for event streams.
- Team will need to learn event sourcing patterns.

## Related
- ADR-031: CRUD chosen for payment service (different requirements).
- Compliance requirement CR-12: Complete transaction audit trail.
```

This ADR is automatically filed, indexed, and linked in the knowledge graph. No one had to manually write or file it.

## Workflow: Knowledge Retrieval

### The Question That Finds Its Answer

A new engineer asks: "Why does the order service use event sourcing instead of a regular database?"

### 1. Intent Interpretation

The retriever understands this is a "why" question about an architectural decision, not a "how" question about implementation.

### 2. Knowledge Assembly

The retriever:

- Finds ADR-047 (primary answer).
- Finds the related ADR-031 about the payment service (contrast — helps explain why the choice differs between services).
- Finds the compliance requirement CR-12 (underlying driver).
- Finds the team's event sourcing guidelines (practical context for the new engineer).

### 3. Response

The system produces a contextualized answer:

> "The order service uses event sourcing (decided in ADR-047, April 2026) primarily because of regulatory requirements for complete audit trails (CR-12). The team considered CRUD with audit tables but found retroactive corrections too complex with that approach.
>
> Note that the payment service uses traditional CRUD (ADR-031) because it had different requirements — simpler state transitions and no retroactive correction needs.
>
> For implementation details, see the Event Sourcing Guidelines in the engineering handbook."

This is not a search result. It is an answer — synthesized from multiple sources, contextualized for the question, with provenance.

## Workflow: Knowledge Maintenance

### The Document That Ages

The validator runs a periodic sweep and flags:

- **API documentation v2.1**: Last updated 14 months ago. The API is now on v3.0. Multiple endpoints have changed. **Status: Stale. Owner notified.**
- **Onboarding guide**: References a Slack channel that was archived 6 months ago. **Status: Partially stale. Specific section flagged.**
- **Deployment runbook**: References a CI/CD pipeline that was replaced last quarter. **Status: Stale. High priority — operational document.**
- **Architecture overview**: All referenced services still exist. Dependency graph matches current reality. **Status: Current.**

The validator does not just check dates — it cross-references knowledge against the current state of the systems, repositories, and configurations it can access.

## The Knowledge Flywheel

The Knowledge OS creates a reinforcing cycle:

```mermaid
flowchart LR
  A[More knowledge\ncaptured] --> B[Better retrieval\nresults]
  B --> C[More people\nuse the system]
  C --> D[Better usage\nanalytics]
  D --> E[Smarter\ncuration]
  E --> F[Higher quality\nknowledge]
  F --> G[More\ntrust]
  G --> A
```

1. More knowledge captured → better retrieval results.
2. Better retrieval results → more people use the system.
3. More usage → better usage analytics → smarter curation.
4. Smarter curation → higher quality knowledge → more trust.
5. More trust → more knowledge contributed → back to step 1.

This flywheel is why the OS model matters. A static knowledge base has no flywheel — it degrades over time. An active Knowledge OS improves over time because every interaction makes the system smarter about what knowledge matters, how it connects, and when it is needed.

## What Makes This an OS, Not a Wiki

A wiki stores pages. A Knowledge OS *manages knowledge*: it captures it from where it is created, connects it across domains, maintains it against drift, delivers it where it is needed, and learns from usage.

The OS provides what wikis lack: active processes (harvesting, curation, validation), structured memory (knowledge graphs, provenance, freshness), governance (classification, retention, accuracy), and adaptation (usage-driven curation, automated maintenance). The wiki asks humans to do all of this manually. The Knowledge OS automates the lifecycle while keeping humans in control of what matters — the knowledge itself.

## Reference Implementation

The Knowledge OS centers on the memory plane — here, memory *is* the product. This implementation uses Semantic Kernel agents for harvesting and validation, with a PostgreSQL + pgvector knowledge store.

### Plugin: Knowledge Store

```python
# plugins/knowledge_store.py
from typing import Annotated
from semantic_kernel.functions import kernel_function
import asyncpg

class KnowledgeStorePlugin:
    """Knowledge graph operations with classification-based access control."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @kernel_function(description="Store a knowledge artifact with embedding.")
    async def store_artifact(
        self,
        title: Annotated[str, "Artifact title"],
        content: Annotated[str, "Artifact content"],
        source: Annotated[str, "Origin: meeting, commit, document"],
        tags: Annotated[str, "Comma-separated tags"],
        classification: Annotated[str, "public, internal, or confidential"] = "internal",
    ) -> Annotated[str, "Confirmation with artifact ID"]:
        import uuid
        artifact_id = str(uuid.uuid4())
        embedding = await embed(content)
        await self.pool.execute("""
            INSERT INTO knowledge_artifacts
                (id, title, content, source, classification, tags, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, artifact_id, title, content, source, classification,
             tags.split(","), embedding)
        return f"Stored artifact {artifact_id}: {title}"

    @kernel_function(description="Search knowledge with access control.")
    async def search(
        self,
        query: Annotated[str, "Search query"],
        max_classification: Annotated[str, "Max classification level"] = "internal",
        limit: Annotated[int, "Max results"] = 10,
    ) -> Annotated[str, "Search results as JSON"]:
        embedding = await embed(query)
        levels = {"public": 0, "internal": 1, "confidential": 2}
        rows = await self.pool.fetch("""
            SELECT id, title, content, source, confidence,
                   1 - (embedding <=> $1) AS similarity
            FROM knowledge_artifacts
            WHERE classification_level <= $2
            ORDER BY embedding <=> $1 LIMIT $3
        """, embedding, levels[max_classification], limit)
        return json.dumps([dict(r) for r in rows])

    @kernel_function(description="Link two knowledge artifacts.")
    async def link_artifacts(
        self,
        from_id: Annotated[str, "Source artifact ID"],
        to_id: Annotated[str, "Target artifact ID"],
        relation: Annotated[str, "Relationship type"],
    ) -> Annotated[str, "Confirmation"]:
        await self.pool.execute("""
            INSERT INTO knowledge_links (from_id, to_id, relation)
            VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
        """, from_id, to_id, relation)
        return f"Linked {from_id} → {to_id} ({relation})"

    @kernel_function(description="Find stale artifacts for review.")
    async def find_stale(
        self, max_age_days: Annotated[int, "Max age in days"] = 90,
    ) -> Annotated[str, "Stale artifacts as JSON"]:
        rows = await self.pool.fetch("""
            SELECT id, title, source, updated_at,
                   NOW() - updated_at AS age
            FROM knowledge_artifacts
            WHERE updated_at < NOW() - make_interval(days => $1)
            ORDER BY age DESC LIMIT 50
        """, max_age_days)
        return json.dumps([dict(r) for r in rows])
```

### Agents: Knowledge Workers

```python
# agents/knowledge_agents.py
from semantic_kernel.agents import ChatCompletionAgent
from plugins.knowledge_store import KnowledgeStorePlugin

def create_harvester_agent(service, store_plugin) -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=service,
        name="Harvester",
        instructions="""You extract structured knowledge from raw content.
For each input, identify:
- Decisions made and their rationale
- Facts and data points with sources
- Action items and owners
- Relationships to existing knowledge
Store each as a knowledge artifact using the store function.""",
        plugins=[store_plugin],
    )

def create_validator_agent(service, store_plugin) -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=service,
        name="Validator",
        instructions="""You validate knowledge freshness.
For each stale artifact: check if referenced entities still exist,
compare stored content with current reality.
Report status: current, stale, or partially_stale.
Suggest updates for stale artifacts.""",
        plugins=[store_plugin],
    )

def create_retriever_agent(service, store_plugin) -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=service,
        name="Retriever",
        instructions="""You answer questions using the knowledge base.
Search for relevant artifacts, synthesize a contextualized answer,
and cite sources. If no relevant knowledge exists, say so clearly.""",
        plugins=[store_plugin],
    )
```

### Kernel: Knowledge Workflows

```python
# agents/kernel.py
from semantic_kernel.agents import SequentialOrchestration, ChatCompletionAgent
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

async def capture_knowledge(raw_content: str, source_type: str) -> str:
    """Harvest → Curate pipeline for knowledge capture."""
    service = AzureChatCompletion(deployment_name="gpt-4.1",
                                  endpoint="https://your-endpoint.openai.azure.com/")
    store_plugin = KnowledgeStorePlugin(pool)

    harvester = create_harvester_agent(service, store_plugin)
    curator = ChatCompletionAgent(
        service=service,
        name="Curator",
        instructions="""Review harvested artifacts for quality.
Deduplicate, adjust tags, check for conflicts with existing knowledge.
Link related artifacts using the link function.""",
        plugins=[store_plugin],
    )

    orchestration = SequentialOrchestration(members=[harvester, curator])
    runtime = InProcessRuntime()
    await runtime.start()

    result = await orchestration.invoke(
        task=f"Source type: {source_type}\n\nContent:\n{raw_content}",
        runtime=runtime,
    )
    output = await result.get()
    await runtime.stop_when_idle()
    return output

async def validate_knowledge() -> str:
    """Periodic freshness validation of the knowledge base."""
    service = AzureChatCompletion(deployment_name="gpt-4.1-mini",
                                  endpoint="https://your-endpoint.openai.azure.com/")
    store_plugin = KnowledgeStorePlugin(pool)
    validator = create_validator_agent(service, store_plugin)

    runtime = InProcessRuntime()
    await runtime.start()

    # Direct agent invocation for single-agent task
    response = await validator.get_response(
        "Find and validate all stale artifacts older than 90 days."
    )
    await runtime.stop_when_idle()
    return str(response)
```

Key patterns: **knowledge store as SK plugin** (`@kernel_function` for search, store, link, validate), **classification-based access control** (pgvector queries filtered by classification level), **harvester-curator pipeline** (SequentialOrchestration), **direct agent invocation** (single-agent validation without orchestration overhead).

