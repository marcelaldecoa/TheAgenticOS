# AGR CLI

Command-line interface for the **Agent Governance Runtime**. Lets operators and developers register agents, evaluate actions against governance policies, query the audit trail, and check server health — all from the terminal.

## Installation

```bash
pip install agr-cli
```

Or install from source (editable mode):

```bash
cd implementations/agent-governance-runtime/src/cli
pip install -e .
```

> **Requires:** Python 3.11+, a running AGR server (default `http://localhost:8600`).

## Quick Start

```bash
# Check that the server is reachable
agr health

# Register an agent with the interactive wizard (just omit the flags)
agr register

# Or register inline with all options
agr register my-agent \
  --name "My Agent" \
  --platform openai \
  --owner engineering \
  --contact eng@acme.com

# Evaluate an action against governance policies
agr evaluate deploy.production --agent my-agent

# List all registered agents
agr list

# Query the audit trail
agr audit --agent my-agent --limit 10
```

## Interactive Wizard

When you run `agr register` without providing all required options, the CLI launches an interactive wizard that walks you through every field:

```
╭─────────────────────────────────────────╮
│   Agent Registration Wizard             │
│   Answer the following questions to     │
│   register a new agent.                 │
╰─────────────────────────────────────────╯
Agent ID (lowercase, kebab-case): my-support-agent
Display name: My Support Agent
  Known platforms: copilot-studio, github-copilot, claude-code, ...
Platform [custom]: github-copilot
Owner team: platform-engineering
Owner contact email: platform@acme.com
Description (optional, Enter to skip):
Environment (optional, Enter to skip): production
Tags (comma-separated, optional): support, production

Configure access profile? [y/N]: y
  Allowed MCPs (comma-separated, Enter to skip): knowledge-base, ticketing
  Denied MCPs (comma-separated, Enter to skip): production-db
  Allowed skills (comma-separated, Enter to skip): search-docs
  Max data classification [internal]: confidential
  Add action rules? [y/N]: y
    Action pattern (e.g. deploy.*, email.send): deploy.*
    Decision for 'deploy.*': deny
    Add another rule? [y/N]: n
  Set budget limits? [y/N]: y
    Max requests/hour (Enter to skip): 100
    Max tokens/hour (Enter to skip): 50000
    Max cost/day (USD) (Enter to skip): 5.0

Summary:
  ID:          my-support-agent
  Name:        My Support Agent
  Platform:    github-copilot
  ...

Register this agent? [Y/n]: y
✓ Agent my-support-agent registered successfully
  Token:    agr_xxxxx...
  ⚠ Save this token — it won't be shown again!
```

The wizard includes:
- Known platform suggestions (copilot-studio, github-copilot, claude-code, openai, etc.)
- Access profile sub-wizard for MCPs, skills, actions, data classification, and budgets
- Confirmation summary before submitting

## Global Options

Every command accepts these options:

| Option | Env Var | Default | Description |
|---|---|---|---|
| `--server`, `-s` | `AGR_SERVER_URL` | `http://localhost:8600` | AGR server URL |
| `--token`, `-t` | `AGR_AGENT_TOKEN` | — | Agent API token (for authenticated operations) |

## Commands

### `agr register`

Register a new agent in the governance registry. **Run without arguments to start an interactive wizard.**

```bash
# Interactive wizard
agr register

# From a full JSON registration file
agr register --from agent.registration.json

# Inline with a separate profile file
agr register <agent-id> \
  --name <name> \
  --platform <platform> \
  --owner <team> \
  --contact <email> \
  [--env <environment>] \
  [--description <text>] \
  [--profile <path-to-json>] \
  [--tags <comma-separated>]
```

| Argument / Option | Required | Description |
|---|---|---|
| `agent-id` | Yes | Unique agent ID (kebab-case) |
| `--name`, `-n` | Yes | Human-readable name |
| `--platform`, `-p` | Yes | Agent platform (e.g. `openai`, `langchain`, `custom`) |
| `--owner`, `-o` | Yes | Owner team name |
| `--contact`, `-c` | Yes | Owner contact email |
| `--env`, `-e` | No | Deployment environment |
| `--description`, `-d` | No | Agent description |
| `--profile` | No | Path to an access profile JSON file (see [schemas/](../../schemas/)) |
| `--from` | No | Path to a full agent registration JSON file (see [schemas/](../../schemas/)) |
| `--tags` | No | Comma-separated list of tags |

When `--from` is provided, the agent is registered from the JSON file and all other options are ignored (except `--server`).

On success the command prints the agent's API token. **Save it — it is only shown once.**

### `agr list`

List registered agents with optional filters.

```bash
agr list [--platform <platform>] [--status <status>] [--search <query>]
```

| Option | Description |
|---|---|
| `--platform`, `-p` | Filter by platform |
| `--status` | Filter by status (`active`, `pending_approval`, `suspended`, `deprecated`) |
| `--search`, `-q` | Free-text search |

### `agr get`

Get details for a specific agent including access profile and budget.

```bash
agr get <agent-id>
```

### `agr evaluate`

Evaluate an action against governance policies. Returns the decision (`allow`, `deny`, or `require_approval`) with matched rules.

```bash
agr evaluate <action> [--agent <agent-id>] [--token <token>]
```

| Argument / Option | Description |
|---|---|
| `action` | Action to evaluate (e.g. `deploy.production`, `email.send`) |
| `--agent`, `-a` | Agent ID to evaluate for |

### `agr audit`

Query the audit trail.

```bash
agr audit \
  [--agent <agent-id>] \
  [--action <action>] \
  [--result <result>] \
  [--trace <trace-id>] \
  [--limit <n>]
```

| Option | Description |
|---|---|
| `--agent`, `-a` | Filter by agent ID |
| `--action` | Filter by action |
| `--result`, `-r` | Filter by result (`success`, `failure`, `denied`, `error`) |
| `--trace` | Show all spans for a specific trace ID |
| `--limit`, `-l` | Number of records to return (default: 20) |

When `--trace` is provided, the command displays all spans for that trace instead of the paginated list.

### `agr health`

Check AGR server health and print version, store backend, and timestamp.

```bash
agr health
```

### `agr policy load`

Load governance policy rules from a JSON file.

```bash
agr policy load <file>
```

The file must conform to the [policies.schema.json](../../schemas/policies.schema.json) schema:

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

### `agr policy list`

List all governance policy rules in a table.

```bash
agr policy list
```

## JSON Schemas

All JSON configuration files have schema definitions with editor autocompletion. Add a `$schema` property to get validation and IntelliSense:

| Schema | Purpose | CLI Flag |
|---|---|---|
| [access-profile.schema.json](../../schemas/access-profile.schema.json) | MCPs, skills, actions, budget | `--profile` |
| [policies.schema.json](../../schemas/policies.schema.json) | Tenant-wide governance rules | `agr policy load` |
| [agent-registration.schema.json](../../schemas/agent-registration.schema.json) | Full agent registration | `--from` |

See [schemas/](../../schemas/) for full documentation.

## Configuration

The CLI reads configuration from environment variables so you can avoid passing flags on every invocation:

```bash
export AGR_SERVER_URL=http://localhost:8600
export AGR_AGENT_TOKEN=agr_xxxxx
```

## Dependencies

| Package | Purpose |
|---|---|
| `agr-sdk` | Python SDK for AGR API communication |
| `typer` | CLI framework |
| `rich` | Terminal formatting and tables |

## License

Apache-2.0
