---
name: validate-freshness
description: "Check knowledge base freshness. Use when auditing stale content, verifying documentation accuracy, checking for broken references, or performing periodic knowledge maintenance."
---

# Validate Knowledge Freshness

## When to Use
- Periodic maintenance sweep (weekly/monthly)
- Before relying on knowledge for a critical decision
- When a system changes (deployment, migration, API update)

## Procedure

### 1. Identify Stale Candidates
Query the knowledge base for artifacts older than the threshold (default: 90 days).

### 2. Validate
Delegate to `@validator`:
- Check each artifact against current reality
- Verify referenced entities, URLs, APIs
- Cross-reference with recent system changes

### 3. Report
Produce a freshness report:
```
## Freshness Report — [date]

### Stale (requires update)
- [artifact]: [issue] → [suggested fix] — Owner: [who]

### Partially Stale
- [artifact]: [specific section] outdated

### Current
- [count] artifacts verified as current

### Action Items
- [ ] Update [artifact] — assigned to [owner]
```

### 4. Notify
Flag stale artifacts to their owners for review.
