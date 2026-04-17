# Agent Governance Runtime (AGR)

**A DAPR-like governance runtime for AI agents across heterogeneous platforms.**

> *"You don't need to standardize on one agent platform. You need to standardize on one governance plane."*

Part of the [Agentic OS](https://marcelaldecoa.github.io/TheAgenticOS) project — implementing the Governance Plane (Ch. 12), Governance Patterns (Ch. 17), and Reference Architecture (Ch. 25).

---

## The Problem

Enterprises face an explosion of "shadow agents" — AI agents on N8N, GPT, Claude, Gemini, Copilot Studio, and custom code — with no central visibility, no audit trail, and no capability governance.

## The Solution

AGR provides **governance building blocks** that work with any agent platform — the same way DAPR provides infrastructure building blocks for any microservice.

## Architecture

![AGR Architecture](docs/diagrams/architecture.drawio.svg)

## Quick Start

### 1. Run the Server

```bash
git clone https://github.com/marcelaldecoa/TheAgenticOS.git
cd TheAgenticOS/implementations/agent-governance-runtime
cd src/server && pip install -e ".[dev]" && agr-server
# → API at http://localhost:8600, Swagger at /docs
```

### 2. Register an Agent

```bash
pip install -e src/sdk && pip install -e src/cli

curl -X POST http://localhost:8600/registry/agents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-agent",
    "name": "My Agent",
    "platform": "custom",
    "owner": {"team": "eng", "contact": "eng@company.com"},
    "access_profile": {
      "mcps_allowed": ["github-mcp", "docs-mcp"],
      "mcps_denied": ["production-db"],
      "actions": {
        "file.read": "allow",
        "file.write": "allow",
        "git.push": "require_approval",
        "deploy.*": "deny"
      },
      "budget": {"max_requests_per_hour": 100, "max_cost_per_day_usd": 5.00}
    }
  }'
# → Returns api_token: "agr_abc123..." — save it, shown only once!
```

### 3. Create Tenant Policies

```bash
curl -X POST http://localhost:8600/policies/rules \
  -H "Content-Type: application/json" \
  -d '{"name": "No prod deploys", "condition": {"action_pattern": "deploy.production"}, "decision": "deny", "priority": 200}'
```

### 4. Evaluate Actions

```bash
curl -X POST http://localhost:8600/governance/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer agr_abc123..." \
  -d '{"agent_id": "my-agent", "action": "deploy.production"}'
# → {"decision": "deny", "reason": "Policy 'No prod deploys': deploy.production → deny", ...}
```

## Unified Governance Evaluation

Every decision flows through one endpoint — `/governance/evaluate`:

![Evaluation Flow](docs/diagrams/evaluation-flow.drawio.svg)

**Precedence**: deny > require_approval > allow. Tenant policies override agent profiles.

## Platform Integrations

| Platform | Method | Details |
|----------|--------|---------|
| **GitHub Copilot** | SDK + profiles + policies | [integrations/github-copilot/](integrations/github-copilot/) |
| **Claude Code** | MCP server + instructions | [integrations/claude-code/](integrations/claude-code/) |
| **N8N** | HTTP Request nodes | [integrations/n8n/](integrations/n8n/) |
| **Custom Python** | SDK (`GovernanceClient`) | [src/sdk/](src/sdk/) |
| **Any HTTP client** | REST API | `/docs` for OpenAPI |

### GitHub Copilot

```bash
# Register with a profile JSON file
agr register copilot-reviewer \
  --name "Code Reviewer" --platform github-copilot \
  --owner engineering --contact eng@acme.com \
  --profile integrations/github-copilot/profiles/code-reviewer.profile.json

# Or register from a full registration file
agr register --from agent.registration.json

# Load fleet-wide policies
agr policy load integrations/github-copilot/policies/copilot-fleet.policies.json
```

See [integrations/github-copilot/](integrations/github-copilot/) for complete examples with agents, MCPs, and skills.

### Claude Code

```json
// .vscode/mcp.json
{"servers": {"agr-governance": {"command": "agr-mcp", "env": {"AGR_SERVER_URL": "http://localhost:8600", "AGR_AGENT_TOKEN": "agr_<token>"}}}}
```

### Python SDK

```python
from agr_sdk import GovernanceClient

gov = GovernanceClient(server_url="http://localhost:8600", agent_id="my-agent")
record = gov.register(name="My Agent", platform="custom", owner_team="eng", owner_contact="eng@co.com")
token = record["api_token"]

gov = GovernanceClient(server_url="http://localhost:8600", token=token)
decision = gov.evaluate("email.send")
if decision["decision"] == "allow":
    with gov.action("email.send", intent="Notify customer") as act:
        send_email(...)
        act.set_result("success")
```

## JSON Schemas

All configuration files have JSON Schema definitions for editor autocompletion and validation:

| Schema | Purpose |
|---|---|
| [access-profile.schema.json](schemas/access-profile.schema.json) | Agent access profile (MCPs, skills, actions, budget) |
| [policies.schema.json](schemas/policies.schema.json) | Tenant-wide governance policy rules |
| [agent-registration.schema.json](schemas/agent-registration.schema.json) | Full agent registration payload |

```bash
# Register from a file with schema validation
agr register --from agent.registration.json

# Or use a separate profile
agr register my-agent --profile profile.json ...

# Load policies from a file
agr policy load policies.json
```

See [schemas/](schemas/) for documentation and examples.

## Security

- **Tokens**: Generated server-side, prefixed `agr_`, shown once on creation, redacted from all GET/LIST
- **Auth resolution**: `GET /auth/resolve` maps token → agent principal (no iteration, no self-declared identity)
- **Audit integrity**: Bearer token present → `agent_id` derived from token, not request body
- **Server-side enforcement**: All decisions via `/governance/evaluate` — clients are thin
- **Append-only audit**: No update/delete on audit records

## Enforcement Architecture

![Enforcement Tiers](docs/diagrams/agr-enforcement-tiers.drawio.svg)

AGR provides **three enforcement tiers** — from cooperative to hard-blocking:

### Tier 1: Advisory Mode (Default)

The agent calls `/governance/evaluate` before acting. If denied, the agent is instructed not to proceed. Enforcement relies on the agent's instruction-following.

```
Agent → agr_check_access("deploy.production") → ❌ DENIED → Agent stops
```

Used by: `agr-mcp` server, SDK `evaluate()`, CLI `agr evaluate`.

### Tier 2: MCP Proxy Mode (Hard Block)

AGR sits **between the agent and all MCP servers**. Every tool call is intercepted, evaluated against governance, and only forwarded if allowed. Denied calls **never reach** the downstream server.

```
Agent → AGR MCP Proxy → evaluate() → ✅ ALLOW → Forward to github-mcp → Result
                                    → ❌ DENY  → Return error (never forwarded)
```

```bash
# Install
pip install -e src/mcp-server

# Configure downstream MCPs in proxy-config.json
# Start proxy instead of individual MCP servers
agr-mcp-proxy
```

`.vscode/mcp.json`:
```json
{
  "servers": {
    "governed-tools": {
      "command": "agr-mcp-proxy",
      "env": {
        "AGR_SERVER_URL": "http://localhost:8600",
        "AGR_AGENT_TOKEN": "agr_<token>",
        "AGR_PROXY_CONFIG": "./proxy-config.json"
      }
    }
  }
}
```

See [examples/proxy-config.json](examples/proxy-config.json) for the downstream MCP configuration format.

### Tier 3: Infrastructure-Level Gating

Server-side middleware that enforces controls at the HTTP/network layer — **cannot be bypassed** by a misbehaving agent or SDK.

| Control | Env Var | Effect |
|---------|---------|--------|
| **Rate Limiting** | `AGR_ENFORCE_RATE_LIMIT=true` | HTTP 429 when per-token limit exceeded |
| **Network Gating** | `AGR_ALLOWED_NETWORKS=10.0.0.0/8` | HTTP 403 for IPs outside allowed CIDRs |
| **API Gateway Auth** | `AGR_REQUIRE_GATEWAY=true` + `AGR_GATEWAY_SECRET=<secret>` | HTTP 403 for requests not routed through the gateway |
| **Mutual TLS** | `AGR_REQUIRE_MTLS=true` | HTTP 403 without client certificate |

```bash
# Example: production deployment with all gating enabled
export AGR_ENFORCE_RATE_LIMIT=true
export AGR_RATE_LIMIT_DEFAULT=100
export AGR_ALLOWED_NETWORKS=10.0.0.0/8,172.16.0.0/12
export AGR_REQUIRE_GATEWAY=true
export AGR_GATEWAY_SECRET=my-gateway-shared-secret
agr-server
```

## Azure Services Mapping

How each AGR capability maps to Azure services. Use this to decide whether to use AGR standalone, Azure-native services, or a hybrid approach.

| AGR Capability | Azure Service | Status | Recommendation |
|---|---|---|---|
| **Agent Registry** | No direct equivalent | ⚠️ Not Supported | Use AGR. Azure has no registry for AI agents across platforms. Azure AI Foundry tracks its own agents but not cross-platform (N8N, Claude, etc.). |
| **Access Profiles** (MCPs, skills, actions) | No direct equivalent | ⚠️ Not Supported | Use AGR. Azure RBAC/Entra ID manages identity but has no concept of MCP allow-lists, skill restrictions, or action-pattern governance for AI agents. |
| **Policy Engine** (action patterns, platform/env filters) | **Azure Policy** + **Azure API Management policies** | 🟡 Partial | Azure Policy governs Azure resources, not AI agent actions. **Hybrid approach**: Use Azure Policy for infrastructure-level rules and AGR for agent-level action governance. |
| **Governance Evaluation** (`/governance/evaluate`) | No direct equivalent | ⚠️ Not Supported | Use AGR. Azure has no single decision endpoint for "should this AI agent do X?" Azure AD Conditional Access is identity-focused, not action-focused. |
| **Audit Trail** (append-only, immutable) | **Azure Monitor** + **Log Analytics** + **Azure Event Hubs** | ✅ Supported | **Best approach**: Forward AGR audit records to Azure Monitor via Log Analytics workspace. Use Event Hubs for real-time streaming. AGR's append-only design maps well to Log Analytics immutable tables. |
| **Budget / Quota Tracking** | **Azure API Management** (rate limiting) + **Azure Cost Management** | 🟡 Partial | APIM provides hard rate limiting at the API gateway level. Azure Cost Management tracks spend. **Hybrid**: Use APIM rate policies for hard enforcement (`AGR_REQUIRE_GATEWAY=true`) and AGR for agent-level token/cost budget tracking. |
| **Rate Limiting** | **Azure API Management** (rate-limit, rate-limit-by-key) | ✅ Supported | **Best approach**: Deploy AGR behind APIM. Use APIM `rate-limit-by-key` policy keyed on `Authorization` header. This gives infrastructure-level rate limiting that agents cannot bypass. |
| **Network Gating / IP Filtering** | **Azure VNET** + **NSG** + **Private Endpoints** | ✅ Supported | **Best approach**: Deploy AGR in an Azure VNET with Private Endpoints. Use NSGs to restrict inbound traffic to known agent networks. Stronger than AGR's `AGR_ALLOWED_NETWORKS` middleware. |
| **API Gateway Auth** | **Azure API Management** (subscription keys, OAuth, mTLS) | ✅ Supported | **Best approach**: Deploy AGR behind APIM with subscription key validation. Map APIM subscriptions to AGR agent tokens. Enables throttling, analytics, and certificate validation at the edge. |
| **Mutual TLS** | **Azure App Gateway** + **Azure Front Door** | ✅ Supported | **Best approach**: Use Azure App Gateway with mTLS enabled. Forward client cert headers (`X-Client-Cert-CN`) to AGR. AGR's `MutualTLSMiddleware` extracts the identity. |
| **Approval Flows** (human-in-the-loop) | **Azure Logic Apps** + **Power Automate** | 🟡 Partial | Logic Apps provides approval workflows with Teams/Outlook integration. **Hybrid**: Use AGR for approval creation + webhook (`AGR_APPROVAL_WEBHOOK_URL`) → trigger Logic App → human approves → Logic App calls AGR `/approvals/{id}/decide`. |
| **Webhook Notifications** | **Azure Event Grid** + **Azure Logic Apps** | ✅ Supported | **Best approach**: Set `AGR_APPROVAL_WEBHOOK_URL` to an Event Grid topic or Logic App HTTP trigger. Event Grid provides fan-out to multiple subscribers (Teams, Slack, email). |
| **Operator RBAC** | **Microsoft Entra ID** (Azure AD) | 🟡 Partial | Entra ID provides enterprise identity and RBAC. **Hybrid**: Use Entra ID for operator authentication (SSO) and AGR for fine-grained agent governance roles (admin/approver/auditor). Map Entra ID groups to AGR operator roles. |
| **Compliance Export** | **Microsoft Purview** + **Azure Policy compliance** | 🟡 Partial | Purview handles data governance, not AI agent governance. **Hybrid**: Export AGR compliance reports to a storage account and import into Purview for unified compliance dashboards. |
| **Fleet Dashboard** | **Azure Monitor Workbooks** + **Power BI** | ✅ Supported | **Best approach**: Forward AGR dashboard data to Log Analytics and build Azure Monitor Workbooks or Power BI dashboards. Richer visualization than AGR's built-in JSON endpoints. |
| **MCP Proxy** (hard tool-call blocking) | No direct equivalent | ⚠️ Not Supported | Use AGR `agr-mcp-proxy`. Azure has no concept of MCP tool-call interception. The proxy pattern is specific to the Model Context Protocol. |

### Recommended Azure Architecture

![AGR on Azure](docs/diagrams/agr-azure-architecture.drawio.svg)

### Key Decisions

1. **AGR-only capabilities** (use AGR, no Azure equivalent):
   - Agent registry with cross-platform support
   - Access profiles (MCP, skills, action patterns)
   - Governance evaluation endpoint
   - MCP Proxy Mode

2. **Azure-native replacements** (can replace AGR):
   - Rate limiting → APIM
   - Network gating → VNET + NSG
   - API gateway auth → APIM + Entra ID
   - mTLS → App Gateway

3. **Hybrid** (use both for defense-in-depth):
   - Audit → AGR + Azure Monitor
   - Approvals → AGR + Logic Apps
   - Compliance → AGR + Purview
   - RBAC → AGR operators + Entra ID

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/registry/agents` | POST | Register (returns token) |
| `/registry/agents` | GET | List (tokens redacted) |
| `/registry/agents/{id}` | GET/PUT/DELETE | CRUD |
| `/auth/resolve` | GET | Token → principal |
| `/governance/evaluate` | POST | **Decision endpoint** |
| `/policies/rules` | POST/GET | Policy CRUD |
| `/policies/rules/{id}` | GET/PATCH | Get/disable policy |
| `/audit/records` | POST/GET | Audit trail |
| `/audit/traces/{id}` | GET | Trace reconstruction |
| `/budget/consume` | POST | Record consumption |
| `/budget/{agent_id}` | GET | Budget status |
| `/operators` | POST/GET | Operator RBAC management |
| `/approvals/request` | POST | Create approval (idempotent) |
| `/approvals/pending` | GET | List pending approvals |
| `/approvals/{id}/decide` | POST | Approve/deny (operator) |
| `/dashboard/summary` | GET | Fleet stats |
| `/dashboard/violations` | GET | Recent denied actions |
| `/dashboard/top-consumers` | GET | Top agents by usage |
| `/dashboard/approvals` | GET | Approval flow stats |
| `/compliance/export` | GET | Evidence report (JSON) |

Full OpenAPI: `http://localhost:8600/docs`

## What's New in Phase 3 (This Release)

- ✅ **Operator RBAC** — admin/approver/auditor roles, API key auth, bootstrap flow
- ✅ **Approval flows** — idempotent creation, one-time-use, auto-expiry, operator decisions
- ✅ **Approval ↔ evaluate integration** — approved requests waive require_approval (but NOT deny/budget)
- ✅ **Fleet dashboard** — summary, top consumers, violations, approval stats
- ✅ **Compliance export** — structured JSON evidence report with schema versioning and gap detection
- ✅ **Structured governance audit** — decision, source, matched_policy_ids, approval_id in metadata
- ✅ **Webhook notifications** — configurable webhook on approval creation (Teams/Slack ready)
- ✅ **79 tests** across all 9 test files

### Previous Releases

**Phase 2**: Auth hardening, policy engine, unified evaluate, budget tracking, MCP v2, N8N integration
**Phase 1**: Agent registry, audit trail, access profiles, MCP server, SDK, CLI, Claude Code integration

## Azure AI Ecosystem Integration

How AGR complements the latest Azure AI services. AGR fills the **cross-platform governance gap** — none of these services provide unified governance for agents across heterogeneous platforms.

### Microsoft Foundry

[Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry) is Azure's AI app and agent factory. AGR complements each Foundry component:

| Foundry Component | What It Does | AGR Complement |
|---|---|---|
| **Foundry Models** (model catalog) | Hosts OpenAI, DeepSeek, Llama, Mistral, and partner models with deployment types (global, data-zone, provisioned) | AGR adds **model access governance** — control which agents can use which models. An agent's access profile can restrict model access by name or tier. See [Roadmap](#roadmap). |
| **Foundry Agent Service** | Orchestrates and hosts AI agents with tools, knowledge, and actions | AGR provides the **governance layer** that Foundry Agent Service lacks: action-level policies, MCP restrictions, budget limits, and cross-platform audit trails. Register Foundry agents in AGR and evaluate every action. |
| **Foundry Control Plane** | Content Safety, red teaming, tracing, evaluation | AGR complements with **action-level governance** (allow/deny/require_approval). Content Safety handles prompt safety; AGR handles capability governance ("can this agent deploy to production?"). Use both. |
| **Foundry IQ** | Knowledge base integration for agents | AGR governs **which knowledge bases** an agent can access via MCP allow-lists and data classification levels (`data_classification_max`). |
| **Foundry Local** | Run LLMs on local devices | AGR can govern local agents the same way — the SDK works anywhere. Register local agents, enforce policies, audit locally. |

**Integration pattern**: Register Foundry agents in AGR → set access profiles with model restrictions → evaluate actions via SDK → audit to Azure Monitor.

### Microsoft Agent 365

[Microsoft Agent 365](https://learn.microsoft.com/en-us/microsoft-agent-365/overview) brings autonomous agents into Microsoft 365 (Teams, Outlook, SharePoint). These agents act on behalf of users across the M365 ecosystem.

| Capability | What Agent 365 Provides | AGR Complement |
|---|---|---|
| **Agent autonomy** | Agents perform tasks (scheduling, email, file management) autonomously | AGR adds **action governance** — define which autonomous actions are allowed, which need approval, and which are denied. Prevents agents from taking unintended actions. |
| **M365 data access** | Agents access SharePoint, OneDrive, Exchange, Teams data | AGR enforces **data classification limits** (`data_classification_max`) — restrict agents from accessing confidential/restricted content. |
| **Cross-app agents** | Agents operate across Teams, Outlook, Word, Excel | AGR provides a **unified audit trail** across all M365 surfaces — see every action an agent takes, regardless of which M365 app it runs in. |
| **Enterprise deployment** | Managed via M365 admin center | AGR adds **fleet-wide governance policies** — apply organization-wide rules (e.g., "no agent can send external emails without approval") that complement M365 admin controls. |

**Integration pattern**: Register Agent 365 instances in AGR → apply tenant policies → forward audit records to Azure Monitor → approval workflows via Logic Apps + Teams.

### Microsoft 365 Copilot & Copilot Studio

| Platform | AGR Value |
|---|---|
| **Microsoft 365 Copilot** | Govern Copilot extensions (declarative agents, plugins, connectors). AGR controls which MCPs and skills each extension can use. |
| **Copilot Studio** | Register Copilot Studio agents in AGR. Use access profiles to restrict which connectors and actions each bot can invoke. Budget tracking for token consumption per bot. |
| **Microsoft 365 Agents Toolkit / SDK** | AGR SDK integrates directly — wrap agent actions with `gov.evaluate()` and `gov.action()` for governance + audit. |

### Microsoft Purview for AI

[Microsoft Purview](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview) provides data security and compliance for AI apps. AGR and Purview are complementary:

| Purview Capability | What It Covers | AGR Complement |
|---|---|---|
| **DSPM for AI** | Data Security Posture Management — discover AI usage, assess risk, apply controls | AGR provides the **agent-level posture** that DSPM doesn't cover: which agents exist, what they can do, what they've done. Export AGR compliance data into Purview dashboards. |
| **DLP for AI** | Prevent sensitive data leaks in AI prompts/responses | AGR prevents **capability leaks** — agents can't invoke tools or MCPs they're not authorized for. DLP handles content; AGR handles actions. |
| **Sensitivity labels** | Classify and protect AI-accessed data | AGR enforces `data_classification_max` per agent — an agent with `internal` clearance can't access `confidential`-labeled content. |
| **Audit logs** | Audit AI prompts/responses in unified audit log | AGR's audit trail captures **agent actions** (not just prompts). Forward AGR audit records to Purview for a complete picture: what data was accessed (Purview) + what the agent did with it (AGR). |
| **Communication compliance** | Monitor AI interactions for policy violations | AGR monitors **agent actions** for governance violations (denied actions, budget exceeded, unauthorized MCP access). |
| **Insider Risk Management** | Detect risky AI usage including prompt injection | AGR detects risky **agent behavior** — agents exceeding budgets, repeatedly hitting deny policies, or accessing suspended MCPs. |

### Microsoft Entra ID + Conditional Access

| Scenario | Integration |
|---|---|
| **Operator SSO** | Entra ID authenticates AGR operators → map Entra groups to AGR roles (admin/approver/auditor) |
| **Agent identity** | Future: map AGR agent tokens to Entra Managed Identities for zero-trust agent authentication |
| **Conditional Access** | Entra Conditional Access gates user/device access; AGR gates agent action access. Defense-in-depth. |

## Roadmap

Planned capabilities for future AGR releases:

### Phase 4 — Model Governance & Catalog

| Feature | Description |
|---|---|
| **Model access profiles** | New `models_allowed` / `models_denied` fields in access profiles. Control which LLMs each agent can use (e.g., agent X can only use `gpt-4o`, not `deepseek-r1`). |
| **Model catalog integration** | Connect to Microsoft Foundry Models catalog. Auto-discover available models and apply governance policies per model tier (standard, provisioned, global). |
| **Model-level budget** | Budget limits per model — max tokens/cost per model per agent. Prevent runaway costs on expensive models while allowing unrestricted access to cheaper ones. |
| **Model evaluation policies** | Policies that match on model name in addition to action pattern. E.g., `{"model_pattern": "deepseek-*", "decision": "deny", "platforms": ["production"]}`. |
| **Foundry Agent Service connector** | Native integration with Foundry Agent Service — auto-register Foundry agents, sync access profiles, forward audit records. |

### Phase 5 — Multi-Platform Agent Discovery

| Feature | Description |
|---|---|
| **Agent 365 connector** | Auto-discover and register Microsoft Agent 365 instances. Sync agent metadata, apply governance policies, track actions. |
| **Copilot Studio connector** | Discover and register Copilot Studio bots. Import connector configurations as MCP restrictions. |
| **N8N workflow scanner** | Auto-discover N8N workflows with AI nodes. Register as agents with action profiles derived from workflow structure. |
| **Shadow agent detection** | Detect unregistered agents hitting the governance endpoint. Alert operators about unmanaged agents in the fleet. |
| **Agent health scoring** | Compute a governance health score per agent based on: registration completeness, policy compliance rate, audit coverage, budget adherence. |

### Phase 6 — Purview & Compliance Integration

| Feature | Description |
|---|---|
| **Purview data export** | Native export of AGR compliance reports to Microsoft Purview. Map AGR audit records to Purview activity explorer. |
| **Sensitivity label enforcement** | Read Microsoft Purview sensitivity labels and enforce `data_classification_max` against actual content labels — not just declared classification. |
| **DLP integration** | Forward agent actions to Purview DLP for content-level inspection. AGR gates the action; Purview gates the data. |
| **Compliance Manager assessments** | Provide AGR-specific assessment templates for Purview Compliance Manager — assess AI agent governance maturity. |
| **Regulatory templates** | Pre-built policy sets for common regulations (EU AI Act, NIST AI RMF, ISO 42001) mapped to AGR policy rules. |

### Phase 7 — Enterprise Scale

| Feature | Description |
|---|---|
| **Multi-tenant federation** | Federated governance across multiple AGR instances. Central policy management with local enforcement. |
| **Azure Cosmos DB store** | Production-grade persistent store replacing SQLite. Geo-distributed, multi-region, automatic failover. |
| **Event-driven architecture** | Replace webhook polling with Azure Event Grid / Service Bus for real-time approval notifications and audit streaming. |
| **Helm chart + AKS deployment** | Production-ready Helm chart for AKS deployment with auto-scaling, health probes, and ingress configuration. |
| **Operator portal** | Web-based dashboard for operators to manage agents, policies, approvals, and view fleet analytics. React + Azure Static Web Apps. |
| **API versioning** | Versioned API endpoints (v1, v2) with backward compatibility guarantees for production consumers. |

## Theoretical Foundation

| Concept | Source | AGR Component |
|---------|--------|---------------|
| Governance Plane | Agentic OS, Ch. 12 | The entire runtime |
| Capability-Based Access | Agentic OS, Ch. 17 | Access profiles |
| Permission Gate | Agentic OS, Ch. 17 | `/governance/evaluate` |
| Auditable Action | Agentic OS, Ch. 17 | Append-only audit trail |
| Risk-Tiered Execution | Agentic OS, Ch. 17 | allow / deny / require_approval |
| Budget Controller | Agentic OS, Ch. 25 | Budget tracking + enforcement |
| Human Escalation | Agentic OS, Ch. 17 | Approval flows |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
