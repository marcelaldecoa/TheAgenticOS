---
name: triage-and-resolve
description: "Handle a support ticket end-to-end. Use when a customer reports an issue, needs help, has a question, or requires troubleshooting."
---

# Triage and Resolve

## When to Use
- A customer submits a support ticket
- A customer reports an issue via any channel

## Procedure

### 1. Triage
Delegate to `@triage`:
- Classify the ticket (category, urgency, sentiment)
- Check for known issue matches
- Load customer context

### 2. Route and Resolve
Based on triage result:

**Known issue (>80% confidence)**:
- Delegate to `@resolver` to apply the known fix
- Verify the fix worked

**Unknown issue**:
- Delegate to `@investigator` to diagnose
- If root cause found and fix is safe → apply it
- If engineering needed → prepare escalation package

### 3. Communicate
Draft a customer response that:
- Explains what happened (no jargon)
- States what was done to resolve it
- Offers follow-up options
- Adapts tone to customer sentiment (empathetic for frustrated, efficient for neutral)

### 4. Learn
- If this was a new issue: suggest adding to the knowledge base
- If an existing known issue: update resolution success rate
