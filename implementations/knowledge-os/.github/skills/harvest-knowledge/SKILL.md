---
name: harvest-knowledge
description: "Capture knowledge from raw content. Use when processing meeting notes, extracting decisions from documents, capturing architectural decisions, or ingesting new information into the knowledge base."
---

# Harvest Knowledge

## When to Use
- After a meeting — process notes into structured knowledge
- When a document is created or updated — extract key artifacts
- When a significant code change is made — capture architectural decisions
- When a new process is established — document it

## Procedure

### 1. Receive Raw Content
Accept input in any form: meeting notes, document text, commit messages, conversation excerpts.

### 2. Harvest
Delegate to `@harvester`:
- Extract all decisions, facts, action items, open questions
- Classify each artifact
- Tag with relevant keywords

### 3. Curate
For each harvested artifact:
- Check the knowledge base for duplicates or related artifacts
- Link to related existing knowledge
- Resolve conflicts (if new info contradicts existing, note the conflict)

### 4. Store
Write artifacts to the knowledge base with:
- Full provenance (source, date, author)
- Embedding for semantic search
- Links to related artifacts

### 5. Report
Output a summary of what was captured:
- Number of artifacts created
- Key decisions captured
- Links to related existing knowledge
- Any conflicts detected
