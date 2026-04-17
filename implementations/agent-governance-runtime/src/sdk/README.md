# AGR SDK

Python SDK for instrumenting AI agents with the **Agent Governance Runtime**. Provides a thin, ergonomic client for agent registration, governance evaluation, audit logging, budget tracking, and MCP access checks.

## Installation

```bash
pip install agr-sdk
```

Or install from source (editable mode):

```bash
cd implementations/agent-governance-runtime/src/sdk
pip install -e .
```

> **Requires:** Python 3.11+

## Quick Start

```python
from agr_sdk import GovernanceClient

# Register your agent on startup
gov = GovernanceClient(server_url="http://localhost:8600", agent_id="my-agent")
record = gov.register(
    name="My Agent",
    platform="custom",
    owner_team="engineering",
    owner_contact="eng@acme.com",
    access_profile={"actions": {"deploy.*": "deny"}},
)
token = record["api_token"]  # Save this — shown only once

# Create an authenticated client for subsequent calls
gov = GovernanceClient(server_url="http://localhost:8600", token=token)
```

## Core Concepts

### Evaluate Before Acting

Check governance policies **before** executing an action:

```python
decision = gov.evaluate("email.send")

if decision["decision"] == "allow":
    send_email(to="user@example.com")
elif decision["decision"] == "require_approval":
    request_approval(decision)
else:
    log.warning(f"Action denied: {decision['reason']}")
```

### Automatic Audit Logging

Use the `action()` context manager to wrap any operation. It automatically logs an audit record with timing, result, and optional metadata:

```python
with gov.action("email.send", intent="Notify customer") as act:
    result = send_email(to="customer@example.com")
    act.set_result("success")
```

If an exception occurs inside the block, the result is set to `"error"` with the exception message, and the exception re-raises.

```python
with gov.action("db.migrate", intent="Schema update") as act:
    act.set_metadata(migration_id="v2.3", tables=["users", "orders"])
    run_migration()
    act.set_result("success")
```

### Manual Audit Logging

For finer control, call `audit_log()` directly:

```python
gov.audit_log(
    action="document.generate",
    result="success",
    intent="Generate quarterly report",
    trace_id="abc-123",
    cost={"duration_ms": 450},
    metadata={"pages": 12},
)
```

## API Reference

### `GovernanceClient`

#### Constructor

```python
GovernanceClient(
    server_url: str = "http://localhost:8600",
    agent_id: str | None = None,
    *,
    token: str | None = None,
    timeout: float = 10.0,
)
```

| Parameter | Description |
|---|---|
| `server_url` | AGR server URL |
| `agent_id` | Agent ID (required for registration and non-token operations) |
| `token` | API token for authenticated requests (set `Authorization: Bearer` header) |
| `timeout` | HTTP request timeout in seconds |

Supports context manager protocol:

```python
with GovernanceClient(token="agr_xxx") as gov:
    gov.evaluate("deploy.staging")
```

---

#### Registry

**`register(**kwargs) → dict`**

Register this agent. Returns the full agent record **with `api_token`** (shown only once).

| Parameter | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable name |
| `platform` | Yes | Agent platform |
| `owner_team` | Yes | Owner team name |
| `owner_contact` | Yes | Owner contact email |
| `description` | No | Agent description |
| `environment` | No | Deployment environment |
| `access_profile` | No | Dict with actions, MCP lists, budget limits |
| `tags` | No | List of tags |

**`get_agent(agent_id=None) → dict | None`**

Get an agent record. Returns `None` if not found.

**`list_agents(**filters) → dict`**

List agents. Accepts filters as keyword arguments (`platform`, `status`, `search`). Returns `{"items": [...], "total": N}`.

---

#### Governance Evaluation

**`evaluate(action, *, resource=None, context=None) → dict`**

Evaluate an action against all governance controls. Returns:

```json
{
  "decision": "allow | deny | require_approval",
  "reason": "...",
  "matched_rules": [...],
  "budget_status": "..."
}
```

**`check_access(action) → dict`**

Shorthand for `evaluate()`.

**`check_mcp(mcp_name) → dict`**

Check if an MCP server is allowed based on the agent's access profile. Requires token-based auth.

```python
result = gov.check_mcp("filesystem")
if result["decision"] == "allow":
    use_mcp("filesystem")
```

---

#### Audit Trail

**`audit_log(**kwargs) → dict`**

Append an audit record.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `action` | Yes | — | Action name |
| `result` | No | `"success"` | Outcome (`success`, `failure`, `denied`, `error`) |
| `intent` | No | — | Human-readable intent description |
| `detail` | No | — | Additional detail text |
| `trace_id` | No | — | Correlation trace ID |
| `run_id` | No | — | Run identifier |
| `session_id` | No | — | Session identifier |
| `cost` | No | — | Cost dict (e.g. `{"duration_ms": 100}`) |
| `severity` | No | `"info"` | Log severity |
| `metadata` | No | — | Arbitrary metadata dict |

**`action(action_name, *, intent=None) → ActionContext`**

Context manager for automatic audit logging. See [Automatic Audit Logging](#automatic-audit-logging).

---

#### Budget

**`report_consumption(**kwargs) → None`**

Report resource consumption to the budget tracker.

| Parameter | Default | Description |
|---|---|---|
| `requests` | `1` | Number of requests |
| `tokens_input` | `0` | Input tokens consumed |
| `tokens_output` | `0` | Output tokens consumed |
| `cost_usd` | `0.0` | Cost in USD |
| `action` | — | Associated action name |

**`get_budget() → dict`**

Get current budget status for this agent.

---

#### System

**`health() → dict`**

Check server health. Returns version, store backend, and timestamp.

### `ActionContext`

Returned by `GovernanceClient.action()`. Tracks action state within the context manager.

| Method | Description |
|---|---|
| `set_result(result, detail=None)` | Set the action result (`success`, `failure`, `error`) |
| `set_metadata(**kwargs)` | Attach arbitrary key-value metadata |
| `duration_ms` | Property — elapsed time in milliseconds |

## Dependencies

| Package | Purpose |
|---|---|
| `httpx` | HTTP client for API communication |
| `pydantic` | Data validation (transitive, used by server models) |

## File-Based Configuration

### Register from a JSON File

Instead of passing every parameter inline, register an agent from a full JSON file:

```python
gov = GovernanceClient(server_url="http://localhost:8600")
record = gov.register_from_file("agent.registration.json")
token = record["api_token"]
```

The file conforms to the [agent-registration.schema.json](../../schemas/agent-registration.schema.json) schema:

```json
{
  "$schema": "../../schemas/agent-registration.schema.json",
  "id": "my-support-agent",
  "name": "Support Agent",
  "platform": "github-copilot",
  "owner": { "team": "support", "contact": "support@acme.com" },
  "access_profile": {
    "mcps_allowed": ["knowledge-base", "ticketing"],
    "actions": { "deploy.*": "deny" },
    "budget": { "max_requests_per_hour": 100 }
  }
}
```

### Load an Access Profile

Load a profile from a separate file and pass it to `register()`:

```python
profile = GovernanceClient.load_profile("agent.profile.json")
record = gov.register(
    name="My Agent",
    platform="custom",
    owner_team="eng",
    owner_contact="eng@acme.com",
    access_profile=profile,
)
```

Profile files conform to the [access-profile.schema.json](../../schemas/access-profile.schema.json) schema.

### Load Policies

Load tenant-wide governance policies from a JSON file:

```python
gov = GovernanceClient(server_url="http://localhost:8600")
created = gov.load_policies("policies.json")
print(f"Loaded {len(created)} policies")
```

Policy files conform to the [policies.schema.json](../../schemas/policies.schema.json) schema:

```json
{
  "$schema": "../../schemas/policies.schema.json",
  "policies": [
    {
      "name": "Block production deploys",
      "condition": { "action_pattern": "deploy.production" },
      "decision": "deny",
      "priority": 1000
    }
  ]
}
```

## JSON Schemas

All configuration files have JSON Schema definitions with editor autocompletion support. Add a `$schema` property to any JSON file:

| Schema | Purpose |
|---|---|
| [access-profile.schema.json](../../schemas/access-profile.schema.json) | MCPs, skills, actions, budget limits |
| [policies.schema.json](../../schemas/policies.schema.json) | Tenant-wide governance rules |
| [agent-registration.schema.json](../../schemas/agent-registration.schema.json) | Full agent registration payload |

See [schemas/](../../schemas/) for details.

## Practical Examples

### End-to-End: Customer Support Agent

A complete example covering registration, governance checks, audit logging, and budget tracking:

```python
from agr_sdk import GovernanceClient

gov = GovernanceClient(server_url="http://localhost:8600", agent_id="cs-support-agent")

# Register with an access profile file
profile = GovernanceClient.load_profile("support.profile.json")
record = gov.register(
    name="Customer Support Agent",
    platform="langchain",
    owner_team="support-engineering",
    owner_contact="support-eng@acme.com",
    environment="production",
    access_profile=profile,
    tags=["support", "tier-1"],
)
token = record["api_token"]

# Switch to token auth
gov = GovernanceClient(server_url="http://localhost:8600", token=token)

# Evaluate → execute → audit → track — all in one
decision = gov.evaluate("knowledge.search")
if decision["decision"] == "allow":
    with gov.action("knowledge.search", intent="Answer ticket #1234") as act:
        results = search_knowledge_base("password reset")
        act.set_metadata(query="password reset", results=len(results))
        act.set_result("success")

    gov.report_consumption(
        requests=1, tokens_input=350, tokens_output=150, cost_usd=0.002,
        action="knowledge.search",
    )
```

See [examples/](../../examples/) for complete runnable scripts.

### Multi-Agent Pipeline

Correlate audit records across agents using `trace_id`:

```python
import uuid
from agr_sdk import GovernanceClient

trace_id = str(uuid.uuid4())

orchestrator = GovernanceClient(server_url="http://localhost:8600", token="agr_orch_token")
with orchestrator.action("pipeline.start", intent="Process invoice batch") as act:
    act.set_metadata(batch_size=50, trace_id=trace_id)
    act.set_result("success")

worker = GovernanceClient(server_url="http://localhost:8600", token="agr_worker_token")
for i in range(50):
    with worker.action("invoice.process", intent=f"Invoice {i}") as act:
        act.set_metadata(invoice_id=f"INV-{i:04d}", trace_id=trace_id)
        act.set_result("success")
    worker.report_consumption(requests=1, tokens_input=800, tokens_output=200, cost_usd=0.004)
```

Query the full trace: `agr audit --trace <trace-id>`

## Platform Integrations

For platform-specific examples with complete implementations, profiles, and policies:

| Platform | Location |
|---|---|
| **GitHub Copilot** | [integrations/github-copilot/](../../integrations/github-copilot/) — agents, skills, MCPs |
| **Claude Code** | [integrations/claude-code/](../../integrations/claude-code/) — MCP server + instructions |
| **N8N** | [integrations/n8n/](../../integrations/n8n/) — HTTP Request nodes |

## License

Apache-2.0
