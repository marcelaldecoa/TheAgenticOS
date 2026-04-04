# Tutorial: Knowledge OS

This walkthrough demonstrates how to capture, organize, validate, and retrieve organizational knowledge using specialized agents.

## Prerequisites

- VS Code with GitHub Copilot Chat
- The Knowledge OS workspace open (`implementations/knowledge-os/`)

## What You Get

| Agent | Role | Tools |
|---|---|---|
| `@harvester` | Extract knowledge from raw content | `read, search, edit` |
| `@curator` | Organize, deduplicate, link artifacts | `read, search, edit` |
| `@validator` | Check freshness and accuracy | `read, search, web` |
| `@retriever` | Answer questions from the knowledge base | `read, search` |

| Skill | Workflow |
|---|---|
| `/harvest-knowledge` | Receive → Harvest → Curate → Store → Report |
| `/validate-freshness` | Find stale → Validate → Report → Notify |

---

## Exercise 1: Capture Knowledge from a Meeting

### Scenario

Your team just had an architecture review meeting. Here are the notes:

```
Architecture Review — April 4, 2026
Attendees: Alice, Bob, Carol

Decision: We'll use cursor-based pagination for all new API endpoints.
Rationale: Offset-based pagination breaks when items are inserted/deleted
during navigation. Cursor-based is stable.
Alternative considered: Offset-based with page tokens — rejected because
it still requires sequential page access.

Decision: The search service will use Elasticsearch instead of PostgreSQL
full-text search.
Rationale: We need fuzzy matching, faceted search, and relevance scoring.
Full-text search in PG doesn't support facets well.

Action item: Bob will set up the Elasticsearch cluster by next sprint.
Open question: What's our retention policy for search indices?
```

### Step 1: Harvest the knowledge

```
/harvest-knowledge Process these meeting notes:

Architecture Review — April 4, 2026
Attendees: Alice, Bob, Carol

Decision: We'll use cursor-based pagination for all new API endpoints.
Rationale: Offset-based pagination breaks when items are inserted/deleted
during navigation. Cursor-based is stable.
Alternative considered: Offset-based with page tokens — rejected because
it still requires sequential page access.

Decision: The search service will use Elasticsearch instead of PostgreSQL
full-text search.
Rationale: We need fuzzy matching, faceted search, and relevance scoring.
Action item: Bob will set up the Elasticsearch cluster by next sprint.
Open question: What's our retention policy for search indices?
```

### Step 2: Watch the agents work

**`@harvester` extracts structured artifacts:**

```yaml
- title: "Cursor-based pagination for all new API endpoints"
  content: "Use cursor-based pagination instead of offset-based for new endpoints.
    Offset breaks when items change during navigation."
  type: decision
  source: "Architecture Review — 2026-04-04"
  tags: [api, pagination, architecture]
  classification: internal
  confidence: 0.95

- title: "Elasticsearch for search service"
  content: "Use Elasticsearch instead of PostgreSQL full-text search.
    Needed for fuzzy matching, faceted search, relevance scoring."
  type: decision
  source: "Architecture Review — 2026-04-04"
  tags: [search, elasticsearch, architecture]
  classification: internal
  confidence: 0.95

- title: "Set up Elasticsearch cluster"
  content: "Bob will set up the Elasticsearch cluster by next sprint."
  type: action_item
  source: "Architecture Review — 2026-04-04"
  tags: [search, elasticsearch, infrastructure]
  classification: internal
  confidence: 0.9

- title: "Search index retention policy — TBD"
  content: "Open question: What retention policy for search indices?"
  type: question
  source: "Architecture Review — 2026-04-04"
  tags: [search, elasticsearch, policy]
  classification: internal
  confidence: 0.8
```

**`@curator` organizes and links:**

```
## Curation Report
Artifacts processed: 4
Duplicates merged: 0
Links created: 2
  - "Elasticsearch for search service" → "Set up Elasticsearch cluster" (implements)
  - "Elasticsearch for search service" → "Search index retention policy" (related_question)
Tags standardized: [elasticsearch → search/elasticsearch]
Conflicts detected: 0
```

### Result

Four knowledge artifacts stored, linked, and ready for retrieval. No manual wiki editing required.

---

## Exercise 2: Ask a Question

### Scenario

A new team member asks: *"Why do we use cursor-based pagination?"*

### Step 1: Ask the retriever

```
@retriever Why does our project use cursor-based pagination instead of offset-based?
```

### Step 2: Get a grounded answer

```
**Answer**: We use cursor-based pagination for all new API endpoints because offset-based
pagination breaks when items are inserted or deleted during navigation. Cursor-based
pagination provides stable results regardless of data changes. Offset-based with page
tokens was considered but rejected because it still requires sequential page access.

**Sources**:
- "Cursor-based pagination for all new API endpoints" (captured: 2026-04-04) — Architecture Review decision
- Related alternative: "Offset-based with page tokens — rejected"

**Confidence**: High (primary decision record from architecture review)
```

The answer cites its source, includes the rationale and alternatives considered, and states confidence level. Compare this to searching a wiki: the `@retriever` synthesizes the answer from the knowledge graph, not just returns a page.

---

## Exercise 3: Validate Freshness

### Scenario

It's been 90 days. Is the knowledge base still accurate?

### Step 1: Run the validation skill

```
/validate-freshness Check all knowledge artifacts older than 90 days for accuracy
```

### Step 2: Review the report

**`@validator` checks each stale artifact:**

```
### "Elasticsearch for search service" (captured: 2026-04-04)
**Status**: Current
Elasticsearch cluster is active. Search service uses ES 8.x.

### "Set up Elasticsearch cluster" (captured: 2026-04-04)
**Status**: Partially stale
Action item was completed 2 months ago. Should be marked as done.
**Suggested Update**: Change type from action_item to completed_action

### "Search index retention policy — TBD" (captured: 2026-04-04)
**Status**: Stale
Still marked as open question but a policy was defined in May.
**Suggested Update**: Replace with actual retention policy (30 day rolling window)
```

---

## Exercise 4: Direct Agent Use

### Extract from a commit message

```
@harvester Extract any architectural decisions from this commit:

"refactor: migrate user service to async handlers

Switched from sync to async request handlers in the user service.
This was necessary because the sync handlers were blocking the event loop
during database queries, causing 2-second latency spikes under load.
All endpoints now use async/await with aiopg."
```

### Check a specific artifact

```
@validator Is our API documentation for the /users endpoint still accurate? Check against the current codebase.
```

### Link related knowledge

```
@curator Link the "async migration" decision to the "latency optimization" initiative. Also check if there are any related architecture decisions about database connection pooling.
```

---

## Quick Reference

| What you want | What to type |
|---|---|
| Capture from any content | `/harvest-knowledge [content]` |
| Check freshness | `/validate-freshness` |
| Answer a question | `@retriever [question]` |
| Extract from raw text | `@harvester [raw content]` |
| Organize & link | `@curator [task]` |
| Verify accuracy | `@validator [artifact or scope]` |
