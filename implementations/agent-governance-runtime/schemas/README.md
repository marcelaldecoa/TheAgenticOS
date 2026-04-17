# AGR JSON Schemas

JSON Schema definitions for all AGR configuration files. These schemas enable editor autocompletion, validation, and documentation.

## Schemas

| Schema | Purpose | Used By |
|---|---|---|
| [access-profile.schema.json](access-profile.schema.json) | Agent access profile (MCPs, skills, actions, budget) | `agr register --profile`, SDK `register()` |
| [policies.schema.json](policies.schema.json) | Tenant-wide governance policy rules | `agr policy load`, SDK |
| [agent-registration.schema.json](agent-registration.schema.json) | Full agent registration payload | `agr register --from`, SDK `register_from_file()` |

## Usage

### In JSON Files

Add a `$schema` property to get editor autocompletion and validation:

```json
{
  "$schema": "./schemas/access-profile.schema.json",
  "mcps_allowed": ["github-mcp"],
  "actions": {
    "deploy.*": "deny"
  }
}
```

### With the CLI

```bash
# Register using a full registration file
agr register --from agent.json

# Register with a separate profile file
agr register my-agent --profile profile.json ...

# Load policies from a file
agr policy load policies.json
```

### With the SDK

```python
from agr_sdk import GovernanceClient

gov = GovernanceClient(server_url="http://localhost:8600", agent_id="my-agent")

# Register from a JSON file
record = gov.register_from_file("agent.json")

# Or load the profile separately
import json
profile = json.load(open("profile.json"))
record = gov.register(
    name="My Agent",
    platform="custom",
    owner_team="eng",
    owner_contact="eng@acme.com",
    access_profile=profile,
)
```

## Schema Details

### Access Profile

Controls what an agent can access:

- **mcps_allowed** — MCP servers the agent may use (empty = none)
- **mcps_denied** — Explicitly blocked MCPs (takes precedence)
- **skills_allowed** — Copilot skills/extensions the agent may invoke
- **data_classification_max** — Maximum data sensitivity: `public` < `internal` < `confidential` < `restricted`
- **actions** — Action pattern → decision mapping with wildcard support (`deploy.*` → `deny`)
- **budget** — Request, token, and cost limits

### Policies

Tenant-wide governance rules that complement agent profiles:

- **condition.action_pattern** — Action pattern to match (supports `*` wildcards)
- **condition.platforms** — Restrict to specific platforms (e.g. `["github-copilot"]`)
- **condition.environments** — Restrict to specific environments (e.g. `["production"]`)
- **decision** — `allow`, `deny`, or `require_approval`
- **priority** — Higher number wins within same effect level (0–10000)

### Agent Registration

Full registration payload for file-based agent onboarding:

- **id** — Unique kebab-case identifier
- **name** — Human-readable name
- **platform** — Agent platform (github-copilot, claude-code, n8n, custom, etc.)
- **owner** — Team and contact info
- **access_profile** — Inline access profile (or use `--profile` separately)
- **deployment** — Environment, region, URL
- **tags** — Classification tags
