# Tutorial: Support OS

This walkthrough demonstrates how to handle customer support tickets using specialized agents for triage, resolution, investigation, and communication.

## Prerequisites

- VS Code with GitHub Copilot Chat
- The Support OS workspace open (`implementations/support-os/`)

## What You Get

| Agent | Role | Tools |
|---|---|---|
| `@triage` | Classify tickets, check known issues, route | `read, search` |
| `@resolver` | Apply known fixes (safe, reversible ops) | `read, search, execute` |
| `@investigator` | Diagnose unknown issues via logs/metrics | `read, search, execute` |
| `@communicator` | Draft customer responses (no tools — text only) | none |

| Skill | Workflow |
|---|---|
| `/triage-and-resolve` | Triage → Route → Resolve/Investigate → Communicate → Learn |
| `/escalation` | Build escalation package for human handoff |

---

## Exercise 1: Handle a Known Issue

### Scenario

A customer submits: *"My dashboard has been showing 'loading' for the past hour. I've tried refreshing and clearing my cache."*

### Step 1: Run the full workflow

```
/triage-and-resolve Customer ticket: "My dashboard has been showing 'loading' for the past hour. I've tried refreshing and clearing my cache."
```

### Step 2: Watch the agents work

**`@triage` classifies and routes:**

```
Classification: technical | high urgency | neutral sentiment
Customer: Pro plan, 14 months
Known Issue Match: #847 — Dashboard timeout for large datasets (>10K rows)
System Status: No active incidents. Data migration ran 3 hours ago.
Route To: @resolver (known issue with high confidence)
```

**`@resolver` applies the fix:**

```
Issue: Known issue #847
Action Taken: Cache invalidation for customer account
Verification: Dashboard loaded in 2.1 seconds
Status: Resolved
```

**`@communicator` drafts the response:**

> Hi there,
>
> I've identified and resolved the issue with your dashboard. A recent data update temporarily affected the cache for accounts with larger datasets like yours. I've cleared the affected cache, and your dashboard should now load normally.
>
> If you notice this again, please let us know — we're keeping an eye on it.
>
> Is there anything else I can help with?

Notice: no jargon ("cache invalidation"), no blame, empathetic tone for neutral sentiment.

---

## Exercise 2: Investigate an Unknown Issue

### Scenario

A customer reports: *"I keep getting error 500 when trying to export my data to CSV. Started about 2 hours ago."*

### Step 1: Triage

```
@triage Customer says: "Error 500 on CSV export, started 2 hours ago."
```

**Result**: No known issue match. Routes to `@investigator`.

### Step 2: Investigate

```
@investigator Diagnose: CSV export returning 500 errors for the past 2 hours. No known issue match. Check logs, recent deployments, and system metrics.
```

**Investigation log:**

```
1. Checked error logs → Found: TimeoutError in export service at 14:23
2. Checked recent deployments → Found: export service v2.4 deployed 3 hours ago
3. Checked v2.4 changelog → Found: new CSV encoding parameter added
4. Checked export service metrics → Found: memory spike at 14:20, OOM kills

Root Cause: v2.4 introduced a memory-intensive encoding step that crashes
for exports > 5MB. Customer's export is ~12MB.

Proposed Fix: Requires engineering rollback or hotfix — exceeds autonomy level.
```

### Step 3: Escalate

```
/escalation Prepare escalation for the CSV export OOM issue diagnosed by the investigator.
```

The skill produces a complete escalation package following the [escalation template](./github/skills/escalation/references/escalation-template.md):

```
## Escalation Package

**Ticket ID**: T-4521
**Priority**: High
**Customer**: Pro plan, 14 months tenure

### Summary
CSV export fails with 500 error for exports > 5MB since v2.4 deployment.
Root cause: memory-intensive encoding step causes OOM kill.

### Investigation Log
1. Error logs → TimeoutError at 14:23
2. Deployment check → v2.4 deployed 3 hours ago
3. Changelog → new encoding parameter
4. Metrics → memory spike, OOM at 14:20

### Evidence
[relevant log entries]

### Proposed Fix
Rollback to v2.3 or apply memory limit to encoding step.

### Customer Communication Draft
> We've identified the issue and our engineering team is working on a fix...
```

**Key point**: The human agent receiving this escalation has everything they need. They don't re-investigate — they verify and authorize the fix.

---

## Exercise 3: Direct Agent Use

### Quick triage

```
@triage Customer says they can't reset their password. Classify and check for known issues.
```

### Draft a response

```
@communicator The customer's issue is resolved — their account was locked due to too many failed login attempts. We've unlocked it. Customer seems frustrated (3 contacts about this). Draft a response.
```

### Investigate with specific tools

```
@investigator Search the logs for customer account A-1234 in the last 6 hours for any errors related to authentication.
```

---

## Data Governance in Practice

The Support OS enforces data governance automatically:

- **`@triage`** loads customer context WITHOUT PII (plan type, tenure, ticket count — no email, phone, or address)
- **`@communicator`** has NO tools — it can't access databases or logs, only text it's given
- **`@resolver`** can only execute Level 0 operations (safe, reversible — cache clear, session reset)
- **`@investigator`** has time-scoped log access (bounded to a time window per query)

These constraints are defined in the agent `.md` files and the `copilot-instructions.md`. They're structural, not aspirational.

---

## Quick Reference

| What you want | What to type |
|---|---|
| Full ticket workflow | `/triage-and-resolve [customer message]` |
| Prepare escalation | `/escalation [issue summary]` |
| Classify a ticket | `@triage [customer message]` |
| Apply known fix | `@resolver [issue details]` |
| Diagnose unknown issue | `@investigator [symptoms]` |
| Draft customer response | `@communicator [resolution + context]` |
