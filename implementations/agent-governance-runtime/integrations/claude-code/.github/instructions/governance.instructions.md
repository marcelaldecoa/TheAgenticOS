# Governance — Mandatory for all agents

This agent operates under the Agent Governance Runtime (AGR). The following
rules are **non-negotiable** and apply to every interaction.

## Before any side-effecting action

Before performing ANY action that modifies state — writing files, calling APIs,
sending messages, pushing code, deploying, modifying databases — you MUST:

1. Call `agr_check_access` with the action name (e.g. `file.write`, `git.push`, `email.send`)
2. If the result is **DENIED** → Do NOT proceed. Inform the user the action is blocked by policy.
3. If the result is **REQUIRE_APPROVAL** → Ask the user for explicit approval before proceeding.
4. If the result is **ALLOWED** → Proceed normally.

## Before using any MCP server

Before invoking tools from external MCP servers, call `agr_check_mcp` with the
server name. If denied, do not use tools from that server.

## After completing actions

After completing any significant action, call `agr_audit` to record:
- What action was performed
- The result (success, failure, error)
- What you were trying to accomplish (intent)
- Any relevant details (file paths, error messages)

## On startup

At the beginning of each session, call `agr_get_profile` to understand your
governance boundaries. Review your access profile to know:
- Which MCP servers you can use
- Which actions require approval
- Which actions are denied
- Your data classification level

## Action naming convention

Use dotted notation for actions:
- `file.read`, `file.write`, `file.delete`
- `git.commit`, `git.push`, `git.merge`
- `api.call`, `api.external`
- `email.send`, `email.read`
- `deploy.staging`, `deploy.production`
- `database.read`, `database.write`, `database.delete`
- `secret.read`, `secret.write`
