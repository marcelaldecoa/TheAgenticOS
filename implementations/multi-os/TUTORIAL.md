# Tutorial: Multi-OS Coordination

This walkthrough demonstrates how to coordinate work across multiple Agentic OSs — routing tasks between Coding, Research, Support, and Knowledge systems with data governance at every boundary.

## Prerequisites

- VS Code with GitHub Copilot Chat
- The Multi-OS workspace open (`implementations/multi-os/`)
- Familiarity with at least one of the individual OS tutorials (Coding, Research, Support, or Knowledge)

## What You Get

| Agent | Role | Tools | Invocable by User? |
|---|---|---|---|
| `@coordinator` | Routes work across OSs | `read, search, web, agent` | Yes |
| `@coding-delegate` | Handles coding tasks | `read, search, edit, execute` | No (subagent only) |
| `@research-delegate` | Handles research tasks | `web, read, search` | No (subagent only) |
| `@support-delegate` | Handles support tasks | `read, search` | No (subagent only) |
| `@knowledge-delegate` | Handles knowledge tasks | `read, search, edit` | No (subagent only) |

The delegate agents have `user-invocable: false` — you only interact with `@coordinator`, which delegates to the right OS.

---

## Exercise 1: Cross-OS Bug Resolution

### Scenario

A customer reports a bug. This involves three OSs:
1. **Support OS** — triage the ticket
2. **Coding OS** — investigate and fix the bug
3. **Knowledge OS** — update the known issues documentation

### Step 1: Ask the coordinator

```
@coordinator A customer reported that the CSV export feature returns corrupted files when the export contains non-ASCII characters (é, ñ, ü). Handle the full lifecycle: triage, fix, document.
```

### Step 2: Watch cross-OS coordination

**The coordinator decomposes the task:**

```
## Cross-OS Workflow
Correlation ID: fed-2026-04-04-001

1. @support-delegate → Triage the ticket, get customer context
2. @coding-delegate → Investigate and fix the CSV encoding bug
3. @knowledge-delegate → Add to known issues documentation
4. @support-delegate → Draft customer notification
```

**`@support-delegate` triages:**

```
Task: Triage CSV export corruption ticket
Status: Complete
Triage: technical | high urgency | frustrated
Customer Context: Enterprise plan, 24 months (NO PII included)
Known Issue: None — this is a new issue
```

> Notice: The support delegate returns customer context WITHOUT PII — `federation-governance.instructions.md` enforces this at the boundary.

**`@coding-delegate` investigates and fixes:**

```
Task: Fix CSV export encoding for non-ASCII characters
Status: Complete
Changes: src/export.py — added UTF-8 BOM and explicit encoding parameter
Summary: The export was using system default encoding (ASCII on some platforms).
  Fixed by specifying encoding='utf-8-sig' explicitly.
Concerns: Need to verify with customer's spreadsheet application (Excel expects BOM)
```

> Notice: The coding delegate receives the bug description but NOT the customer's account details — data was redacted by the coordinator before handoff.

**`@knowledge-delegate` updates docs:**

```
Task: Add CSV encoding issue to known issues
Status: Complete
Artifacts Created: ["Known Issue: CSV export corruption with non-ASCII characters"]
Related Knowledge Found: ["Export format standards" — linked]
```

**`@support-delegate` drafts the response:**

```
Task: Draft customer notification about CSV fix
Status: Complete
Response: "We've identified and resolved the CSV export issue..."
```

### Step 3: Review the audit trail

The coordinator produces the cross-OS report:

```
## Cross-OS Workflow Report
**Correlation ID**: fed-2026-04-04-001
**OSs Involved**: Support, Coding, Knowledge
**Timeline**:
1. [10:01] Support → Triage → High urgency, no known match
2. [10:02] Coding → Investigate → Root cause: ASCII encoding default
3. [10:03] Coding → Fix → UTF-8 BOM added to export
4. [10:04] Knowledge → Document → Known issue created
5. [10:05] Support → Communicate → Customer response drafted
**Result**: Bug fixed, documented, customer notified
```

---

## Exercise 2: Research-Informed Feature Decision

### Scenario

Your product team wants to add a calendar view. Before building it, you need competitive research.

```
@coordinator Research how our top 3 competitors implement calendar views in their task management tools, then have the coding team assess the implementation effort for our stack.
```

**The coordinator routes:**

1. `@research-delegate` → Competitive analysis on calendar implementations
2. `@coding-delegate` → Technical feasibility assessment based on research findings

**Result**: Research findings flow into the coding assessment — the `@coding-delegate` receives the research output (internal classification — no confidential data) and produces:

```
Task: Assess calendar view implementation effort
Status: Complete
Summary: Based on research findings, the competitors use:
  - Competitor A: FullCalendar.js library (drag-and-drop, recurring events)
  - Competitor B: Custom canvas-based (performance-optimized)
  - Competitor C: Basic HTML table grid

Recommendation: Use FullCalendar.js — fastest to implement, covers 90% of
use cases. Estimated effort: 2 sprints for basic view, 1 more for recurring events.
```

---

## Exercise 3: Knowledge-Driven Support

```
@coordinator A new team member is asking: "Why do we use cursor-based pagination instead of offset-based?" Check the knowledge base and provide an answer with sources.
```

The coordinator routes to `@knowledge-delegate`, which searches the knowledge graph and returns:

```
Task: Answer pagination question from knowledge base
Status: Complete
Answer: We use cursor-based pagination because offset-based breaks when items
  are inserted/deleted during navigation (Architecture Review, 2026-04-04).
Sources: ADR on pagination, Architecture Review notes
```

No code was needed. No research was needed. The knowledge was already captured — the coordinator knew to route to knowledge, not coding or research.

---

## Data Governance in Practice

The `federation-governance.instructions.md` enforces these rules:

### Data Classification

```
Confidential data → only to Coding OS, Support OS
Internal data    → any OS
Public data      → any OS
```

### PII Redaction

Before the coordinator sends customer context to Research OS or Knowledge OS:
- ✅ Keeps: plan type, tenure, ticket category
- ❌ Removes: email, phone, address, payment info

### Correlation IDs

Every cross-OS workflow gets a UUID. All messages, audit entries, and the final report use the same ID — enabling end-to-end tracing.

### What the coordinator will refuse

```
@coordinator Send this customer's full account details to the research team for analysis
```

Response: *"Cannot send confidential customer data to Research OS — its clearance is 'internal'. I can send a redacted summary instead. Proceed?"*

---

## Quick Reference

| What you want | What to type |
|---|---|
| Cross-OS task (any combo) | `@coordinator [describe the task spanning multiple domains]` |
| Bug fix + docs + notification | `@coordinator [bug report] — handle full lifecycle` |
| Research → coding assessment | `@coordinator Research [topic] then assess implementation effort` |
| Knowledge lookup | `@coordinator Check knowledge base for [question]` |
| Understand routing | `@coordinator What OSs would handle: [describe a task]` |

## How It Maps to the Book

| Multi-OS Concept (Ch. 34) | Implementation |
|---|---|
| Federation Bus | `@coordinator` routes via subagent delegation |
| Capability Registry | `copilot-instructions.md` OS capabilities table |
| Data Classification | `federation-governance.instructions.md` |
| Correlation IDs | Coordinator generates and tracks per workflow |
| Cross-OS Audit Trail | Coordinator's workflow report |
| Delegate agents | `user-invocable: false` subagents scoped to one OS |
