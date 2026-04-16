# Agent Governance Runtime (AGR)

**A DAPR-like runtime for governing AI agents across heterogeneous platforms.**

> *"You don't need to standardize on one agent platform. You need to standardize on one governance plane."*

Part of the [Agentic OS](https://marcelaldecoa.github.io/TheAgenticOS) project — implementing the Governance Plane (Chapter 12), Governance Patterns (Chapter 17), and Reference Architecture (Chapter 25).

---

## The Problem

Enterprises face an explosion of "shadow agents" — AI agents built on N8N, GPT, Claude, Gemini, Copilot Studio, and custom code — with no central visibility, no audit trail, and no capability governance. CIOs and CISOs cannot answer:

- How many agents operate in our organization?
- Which agents have write access to production systems?
- What data flows through which agents?
- Who approved this agent's capabilities?
- What is the total cost of our agent fleet?

## The Solution

AGR provides **governance building blocks** that work with any agent platform — the same way DAPR provides infrastructure building blocks that work with any microservice.

| DAPR | AGR |
|------|-----|
| Sidecar alongside your microservice | SDK/proxy alongside your agent |
| Building blocks (state, pub/sub, service invocation) | Building blocks (registry, audit, policy, identity) |
| Pluggable components (Redis, Cosmos, Kafka) | Pluggable backends (SQLite, PostgreSQL, Cosmos) |
| Control plane (Kubernetes operator) | Governance plane (fleet management) |

## Quick Start

### Run the Server

```bash
# Clone
git clone https://github.com/marcelaldecoa/TheAgenticOS.git
cd TheAgenticOS/implementations/agent-governance-runtime

# Install and start
cd src/server
pip install -e ".[dev]"
agr-server
# → API at http://localhost:8600
# → Swagger docs at http://localhost:8600/docs
```

### Register an Agent and Get a Token

```bash
# Install SDK + CLI
pip install -e src/sdk
pip install -e src/cli

# Register with an access profile
curl -X POST http://localhost:8600/registry/agents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-support-agent",
    "name": "Customer Support Agent",
    "platform": "claude-code",
    "owner": {"team": "support", "contact": "support@company.com"},
    "access_profile": {
      "mcps_allowed": ["github-mcp", "jira-mcp", "knowledge-base"],
      "mcps_denied": ["production-db", "deploy-pipeline"],
      "actions": {
        "file.read": "allow",
        "file.write": "allow",
        "git.push": "require_approval",
        "deploy.*": "deny"
      }
    }
  }'
# → Returns api_token: "agr_abc123..." (save this!)

# Check fleet
agr list
```

### Use with Claude Code (Real Integration)

**1. Install the AGR MCP server:**
```bash
pip install -e src/mcp-server
```

**2. Add to your project's `.vscode/mcp.json`:**
```json
{
  "servers": {
    "agr-governance": {
      "command": "agr-mcp",
      "env": {
        "AGR_SERVER_URL": "http://localhost:8600",
        "AGR_AGENT_TOKEN": "agr_abc123..."
      }
    }
  }
}
```

**3. Copy governance instructions to your project:**
```bash
cp -r integrations/claude-code/.github/ your-project/.github/
```

**Now Claude Code will:**
- Call `agr_check_access` before any side-effecting action
- Call `agr_check_mcp` before using external MCP servers
- Call `agr_audit` after every significant action
- Respect `deny` and `require_approval` policies

### Use with Python Agents (SDK)

```python
from agr_sdk import GovernanceClient

gov = GovernanceClient(
    server_url="http://localhost:8600",
    agent_id="my-support-agent",
)

# Context manager — automatically audits actions
with gov.action("email.send", intent="Notify customer") as act:
    send_email(...)
    act.set_result("success")
else:
    gov.audit_log(action="email.send", result="denied", detail=decision.reason)
```

## Phase 1 Scope

| Building Block | Status | Description |
|---------------|--------|-------------|
| **Agent Registry** | ✅ | Register agents with access profiles (MCPs, skills, actions, data) |
| **Audit Trail** | ✅ | Append-only action logging, distributed traces |
| **Access Profiles** | ✅ | Control which MCPs, skills, actions each agent can use |
| **MCP Server** | ✅ | AGR as MCP — governance tools for Claude Code, Copilot, etc. |
| **Python SDK** | ✅ | `GovernanceClient` for custom agents |
| **CLI** | ✅ | `agr` commands for fleet management |
| **Claude Code integration** | ✅ | Skill + instructions + MCP config (copy to any project) |
| Policy Engine (OPA) | 🔜 Phase 2 | External policy evaluation |
| Budget Control | 🔜 Phase 2 | Token/cost quotas |
| MCP Proxy | 🔜 Phase 2 | Transparent governance proxy for backend MCPs |
| Dashboard | 🔜 Phase 3 | Fleet visualization for CISOs |
| Approval Flows | 🔜 Phase 3 | Human-in-the-loop via Teams/Slack |

## How It Works

### The Key Insight: AGR IS an MCP Server

Instead of asking agents to call an API, AGR **speaks the same protocol agents already use**.
Claude Code, GitHub Copilot, and other MCP-compatible agents connect to AGR like any MCP server.
Every tool call is checked against the agent's **access profile** — server-side, not client-side.

```
┌─────────────────────────────────────────────────────────┐
│                  AGR CONTROL PLANE                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Agent    │  │ Audit    │  │ Access Profiles      │  │
│  │ Registry │  │ Store    │  │ (MCPs, skills, data) │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│                                                          │
│                   REST API (:8600)                        │
└──────────────────────┬───────────────────────────────────┘
                       │
          ┌────────────┼─────────────┐
          │            │             │
   ┌──────┴─────┐ ┌───┴────┐ ┌─────┴──────┐
   │ AGR MCP    │ │ Python │ │    CLI     │
   │ Server     │ │ SDK    │ │            │
   │ (stdio)    │ │        │ │            │
   └──────┬─────┘ └────────┘ └────────────┘
          │
   ┌──────┴──────────────────────────────────┐
   │  Claude Code / Copilot / Any MCP Agent  │
   │                                          │
   │  Calls agr_check_access before actions   │
   │  Calls agr_check_mcp before using MCPs   │
   │  Calls agr_audit after every action      │
   └──────────────────────────────────────────┘
```

### What Gets Governed

| Agent wants to... | AGR checks... | Possible outcomes |
|-------------------|--------------|-------------------|
| Write a file | `agr_check_access("file.write")` | ✅ allow, ❌ deny |
| Push to git | `agr_check_access("git.push")` | ⏸️ require_approval |
| Deploy to prod | `agr_check_access("deploy.production")` | ❌ deny |
| Use GitHub MCP | `agr_check_mcp("github-mcp")` | ✅ allow |
| Use prod database MCP | `agr_check_mcp("production-db")` | ❌ deny |
| Send email | `agr_check_access("email.send")` | ✅ allow → 📝 audit |

## Project Structure

```
agent-governance-runtime/
├── src/
│   ├── server/          # FastAPI governance API server
│   │   └── agr_server/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── models/  # Pydantic models (Agent, AccessProfile, AuditRecord)
│   │       ├── api/     # FastAPI route handlers
│   │       └── store/   # Pluggable storage (SQLite, PostgreSQL, Cosmos)
│   ├── mcp-server/      # AGR as MCP server (the key integration)
│   │   └── agr_mcp/
│   │       └── server.py  # MCP tools: check_access, check_mcp, audit, get_profile
│   ├── sdk/             # Python SDK (GovernanceClient)
│   │   └── agr_sdk/
│   └── cli/             # CLI tool (agr register, list, audit)
│       └── agr_cli/
├── integrations/        # Platform-specific integration files
│   ├── claude-code/     # Copy to any project for instant governance
│   │   ├── .vscode/mcp.json
│   │   └── .github/
│   │       ├── instructions/governance.instructions.md
│   │       └── skills/governance/SKILL.md
│   └── n8n/             # N8N workflow templates
├── deploy/
│   └── Dockerfile
├── examples/
│   └── instrument_agent.py
└── docs/
```

### Platform Integrations

| Platform | Integration Method | Files |
|----------|-------------------|-------|
| **Claude Code** | MCP server + skill + instructions | `integrations/claude-code/` |
| **VS Code Copilot** | Same MCP server + instructions | `integrations/claude-code/` |
| **Custom Python** | SDK (`GovernanceClient`) | `src/sdk/` |
| **N8N** | HTTP Request nodes → AGR API | `integrations/n8n/` |
| **Copilot Studio** | Custom connector → AGR API | Planned |
| **Any MCP-compatible** | AGR MCP server | `src/mcp-server/` |

## Theoretical Foundation

This implementation is grounded in the following concepts from [The Agentic OS](https://marcelaldecoa.github.io/TheAgenticOS) and [The Architecture of Intent](https://marcelaldecoa.github.io/TheArchitectureOfIntent):

| Concept | Source | AGR Component |
|---------|--------|---------------|
| Governance Plane | Agentic OS, Ch. 12 | The entire runtime |
| Capability-Based Access | Agentic OS, Ch. 17 | Access profiles |
| Permission Gate | Agentic OS, Ch. 17 | `agr_check_access` MCP tool |
| Auditable Action | Agentic OS, Ch. 17 | Audit trail (append-only) |
| Risk-Tiered Execution | Agentic OS, Ch. 17 | allow / deny / require_approval |
| Agent Registry | Architecture of Intent | Registry API + fleet view |
| Distributed Trace | Architecture of Intent | Trace propagation via audit |
| Proportional Governance | Architecture of Intent | Access profiles per agent |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
