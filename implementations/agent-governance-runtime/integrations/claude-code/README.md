# Claude Code Integration

**Add governance to any Claude Code / VS Code Copilot project in 3 steps.**

## Prerequisites

1. AGR server running: `agr-server` (port 8600)
2. Agent registered and activated:
   ```bash
   agr register my-agent --name "My Agent" --platform claude-code \
     --owner my-team --contact me@company.com
   # → Save the api_token from the response
   ```

## Setup

### Step 1: Copy these files to your project

```bash
cp -r integrations/claude-code/.vscode/mcp.json  your-project/.vscode/mcp.json
cp -r integrations/claude-code/.github/           your-project/.github/
```

### Step 2: Set your agent token

Edit `.vscode/mcp.json` and replace `YOUR_TOKEN_HERE` with your agent's API token.

Or set the environment variable:
```bash
export AGR_AGENT_TOKEN=agr_<your-token>
```

### Step 3: Open in VS Code

The governance MCP and instructions load automatically. The agent will:
- Check access before side-effecting actions
- Log audit records for significant actions
- Respect MCP/skill restrictions from the access profile

## What gets governed

| Action | Governed By |
|--------|------------|
| Using an MCP server | `agr_check_mcp` — checks access profile |
| Writing files, pushing code | `agr_check_access` — checks action policy |
| Calling external APIs | `agr_check_access` + audit logging |
| Deploying to production | Policy can require approval or deny |
| Every significant action | Auto-audited via `agr_audit` |

## Files

| File | Purpose |
|------|---------|
| `.vscode/mcp.json` | Configures AGR as an MCP server |
| `.github/instructions/governance.instructions.md` | Tells the agent to always check governance |
| `.github/skills/governance/SKILL.md` | Governance workflow skill |
