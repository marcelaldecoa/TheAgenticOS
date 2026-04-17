# GitHub Copilot Integration with AGR

Complete examples for governing **GitHub Copilot agents**, **extensions (skills)**, and **MCP servers** using the Agent Governance Runtime.

## Overview

AGR provides governance building blocks that work with GitHub Copilot the same way they work with any other agent platform. The integration pattern is:

1. **Register** your Copilot agent in AGR with an access profile (JSON file)
2. **Evaluate** actions before executing them
3. **Audit** every significant action automatically
4. **Track** token/cost consumption against budget limits

## Prerequisites

- AGR server running (`agr-server`, default port 8600)
- AGR CLI installed (`pip install -e src/cli`)
- AGR SDK installed (`pip install -e src/sdk`)

## Directory Structure

```
github-copilot/
├── README.md                      ← This file
├── profiles/
│   ├── code-reviewer.profile.json     ← Access profile for a code review agent
│   ├── devops-agent.profile.json      ← Access profile for a DevOps agent
│   └── fullstack-dev.profile.json     ← Access profile for a full-stack dev agent
├── policies/
│   ├── copilot-fleet.policies.json    ← Tenant-wide policies for all Copilot agents
│   └── production-guardrails.policies.json  ← Production-specific guardrails
└── examples/
    ├── governed_copilot_agent.py      ← Copilot extension with governance
    ├── governed_mcp_gateway.py        ← MCP gateway with access control
    ├── governed_skill_runner.py       ← Skill invocation with governance
    └── fleet_monitor.py               ← Fleet monitoring script
```

## Quick Start

### Step 1 — Register a Copilot agent

```bash
# Using the interactive wizard
agr register

# Or using a profile JSON file
agr register copilot-code-reviewer \
  --name "Copilot Code Reviewer" \
  --platform github-copilot \
  --owner platform-engineering \
  --contact platform@acme.com \
  --env production \
  --profile profiles/code-reviewer.profile.json \
  --tags copilot,code-review,production
```

Save the returned `api_token` — it is only shown once.

### Step 2 — Apply tenant policies

```bash
# Load policies from a JSON file
agr policy load policies/copilot-fleet.policies.json
```

### Step 3 — Run the example

```bash
export AGR_SERVER_URL=http://localhost:8600
export AGR_AGENT_TOKEN=agr_<your-token>

python examples/governed_copilot_agent.py
```

## Examples

### 1. Governed Copilot Agent

[examples/governed_copilot_agent.py](examples/governed_copilot_agent.py) — A GitHub Copilot chat participant that checks governance before every action.

### 2. Governed MCP Gateway

[examples/governed_mcp_gateway.py](examples/governed_mcp_gateway.py) — A gateway that intercepts MCP tool calls and enforces access control.

### 3. Governed Skill Runner

[examples/governed_skill_runner.py](examples/governed_skill_runner.py) — Skill invocation with governance checks, audit trail, and budget tracking.

### 4. Fleet Monitor

[examples/fleet_monitor.py](examples/fleet_monitor.py) — Monitor all Copilot agents in the fleet: status, budget, violations.

## Access Profiles

Access profiles define what an agent can and cannot do. They are JSON files that follow the AGR access profile schema.

See [profiles/](profiles/) for ready-to-use templates. See [schemas/](../../schemas/) for the full JSON Schema definitions.

## Policies

Policies are tenant-wide governance rules that override agent-level profiles. They apply to all agents matching the conditions (platform, environment, etc.).

See [policies/](policies/) for ready-to-use templates. See [schemas/](../../schemas/) for the full JSON Schema definitions.
