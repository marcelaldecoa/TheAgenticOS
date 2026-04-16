"""AGR MCP Server — Governance tools exposed as MCP.

This is the key integration mechanism. Agents (Claude Code, Copilot, etc.)
connect to this MCP server and get governance tools:

  - agr_check_access   — Check if an action is allowed by policy
  - agr_get_profile    — Get the agent's access profile
  - agr_audit          — Log an audit record for an action
  - agr_list_agents    — List registered agents (admin)

Authentication: The agent provides its API token via the AGR_AGENT_TOKEN
environment variable. The MCP server validates the token against the AGR API
on every tool call — identity is transport-bound, not self-declared.

Usage in .vscode/mcp.json::

    {
      "servers": {
        "agr-governance": {
          "command": "agr-mcp",
          "env": {
            "AGR_SERVER_URL": "http://localhost:8600",
            "AGR_AGENT_TOKEN": "agr_<your-token>"
          }
        }
      }
    }
"""

from __future__ import annotations

import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

AGR_SERVER_URL = os.environ.get("AGR_SERVER_URL", "http://localhost:8600")
AGR_AGENT_TOKEN = os.environ.get("AGR_AGENT_TOKEN", "")

server = Server("agr-governance")
_http = httpx.Client(base_url=AGR_SERVER_URL, timeout=10.0)

# --- Cached agent profile (resolved from token) ---
_agent_cache: dict | None = None


def _resolve_agent() -> dict:
    """Resolve agent identity from token. Cached per session."""
    global _agent_cache
    if _agent_cache is not None:
        return _agent_cache

    if not AGR_AGENT_TOKEN:
        return {"error": "AGR_AGENT_TOKEN not set. Register your agent and set the token."}

    resp = _http.get(
        "/registry/agents",
        params={"search": ""},
        headers={"Authorization": f"Bearer {AGR_AGENT_TOKEN}"},
    )
    # For Phase 1, look up by iterating (token lookup endpoint would be better)
    # In production, this would be a dedicated /auth/resolve endpoint
    if resp.status_code == 200:
        for agent in resp.json().get("items", []):
            if agent.get("api_token") == AGR_AGENT_TOKEN:
                _agent_cache = agent
                return agent

    return {"error": "Invalid token or agent not found. Register with: agr register"}


def _check_access(action: str) -> dict:
    """Check action against the agent's access profile. Server-side enforcement."""
    agent = _resolve_agent()
    if "error" in agent:
        return {"decision": "deny", "reason": agent["error"]}

    if agent.get("status") != "active":
        return {
            "decision": "deny",
            "reason": f"Agent status is '{agent.get('status')}', not 'active'",
        }

    profile = agent.get("access_profile", {})
    actions = profile.get("actions", {})

    # Exact match
    if action in actions:
        decision = actions[action]
        return {"decision": decision, "reason": f"Policy: {action} → {decision}"}

    # Wildcard match (e.g. "deploy.*" matches "deploy.production")
    parts = action.split(".")
    for i in range(len(parts), 0, -1):
        pattern = ".".join(parts[:i]) + ".*"
        if pattern in actions:
            decision = actions[pattern]
            return {"decision": decision, "reason": f"Policy: {pattern} → {decision}"}

    return {"decision": "allow", "reason": "No policy restriction"}


def _audit_log(action: str, result: str, **kwargs: str) -> dict:
    """Log an audit record to the AGR server."""
    agent = _resolve_agent()
    agent_id = agent.get("id", "unknown")

    body = {
        "agent_id": agent_id,
        "action": action,
        "result": result,
        **{k: v for k, v in kwargs.items() if v},
    }
    resp = _http.post("/audit/records", json=body)
    if resp.status_code == 201:
        return resp.json()
    return {"error": f"Audit failed: {resp.status_code} {resp.text}"}


# --- MCP Tool Definitions ---


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="agr_check_access",
            description=(
                "Check if an action is allowed by the governance policy. "
                "Call this BEFORE performing any action with side effects "
                "(file writes, API calls, deployments, data modifications). "
                "Returns: allow, deny, or require_approval."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "The action to check, in dotted notation. "
                            "Examples: 'file.write', 'git.push', 'email.send', "
                            "'deploy.production', 'database.write'"
                        ),
                    },
                    "resource": {
                        "type": "string",
                        "description": "Optional target resource (e.g. repo name, file path, DB name)",
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="agr_get_profile",
            description=(
                "Get your access profile — what MCPs, skills, data sources, "
                "and actions you are allowed to use. Call this to understand "
                "your governance boundaries."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="agr_audit",
            description=(
                "Log an audit record for an action you have performed. "
                "Call this AFTER completing any significant action — especially "
                "side-effecting actions (writes, sends, deployments). "
                "Audit records are append-only and immutable."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action performed (e.g. 'file.write', 'email.send')",
                    },
                    "result": {
                        "type": "string",
                        "enum": ["success", "failure", "denied", "error"],
                        "description": "Outcome of the action",
                    },
                    "intent": {
                        "type": "string",
                        "description": "What you were trying to accomplish",
                    },
                    "detail": {
                        "type": "string",
                        "description": "Additional context (file path, error message, etc.)",
                    },
                },
                "required": ["action", "result"],
            },
        ),
        Tool(
            name="agr_check_mcp",
            description=(
                "Check if you are allowed to use a specific MCP server. "
                "Call this before invoking tools from external MCP servers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mcp_name": {
                        "type": "string",
                        "description": "Name of the MCP server (e.g. 'github-mcp', 'jira-mcp')",
                    },
                },
                "required": ["mcp_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "agr_check_access":
        result = _check_access(arguments["action"])

        # Auto-audit the access check itself
        _audit_log(
            action=f"governance.check_access:{arguments['action']}",
            result=result["decision"],
            detail=result.get("reason", ""),
        )

        if result["decision"] == "deny":
            return [TextContent(
                type="text",
                text=f"❌ DENIED: {arguments['action']}\nReason: {result['reason']}\n\n"
                     f"Do NOT proceed with this action. Inform the user it is blocked by policy.",
            )]
        elif result["decision"] == "require_approval":
            return [TextContent(
                type="text",
                text=f"⏸️ APPROVAL REQUIRED: {arguments['action']}\nReason: {result['reason']}\n\n"
                     f"This action requires human approval before proceeding. "
                     f"Ask the user to approve explicitly.",
            )]
        else:
            return [TextContent(
                type="text",
                text=f"✅ ALLOWED: {arguments['action']}\nYou may proceed with this action.",
            )]

    elif name == "agr_get_profile":
        agent = _resolve_agent()
        if "error" in agent:
            return [TextContent(type="text", text=f"Error: {agent['error']}")]

        profile = agent.get("access_profile", {})
        lines = [
            f"Agent: {agent['id']} ({agent['name']})",
            f"Platform: {agent['platform']}",
            f"Status: {agent['status']}",
            f"Owner: {agent['owner']['team']}",
            "",
            "=== Access Profile ===",
            f"MCPs allowed: {', '.join(profile.get('mcps_allowed', [])) or 'none specified'}",
            f"MCPs denied: {', '.join(profile.get('mcps_denied', [])) or 'none'}",
            f"Skills allowed: {', '.join(profile.get('skills_allowed', [])) or 'none specified'}",
            f"Data classification max: {profile.get('data_classification_max', 'internal')}",
            "",
            "Action policies:",
        ]
        for act, decision in profile.get("actions", {}).items():
            icon = {"allow": "✅", "deny": "❌", "require_approval": "⏸️"}.get(decision, "?")
            lines.append(f"  {icon} {act} → {decision}")

        if not profile.get("actions"):
            lines.append("  (no explicit restrictions)")

        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "agr_audit":
        result = _audit_log(
            action=arguments["action"],
            result=arguments["result"],
            intent=arguments.get("intent", ""),
            detail=arguments.get("detail", ""),
        )
        if "error" in result:
            return [TextContent(type="text", text=f"Audit failed: {result['error']}")]
        return [TextContent(
            type="text",
            text=f"📝 Audit recorded (seq: {result.get('sequence', '?')}): "
                 f"{arguments['action']} → {arguments['result']}",
        )]

    elif name == "agr_check_mcp":
        agent = _resolve_agent()
        if "error" in agent:
            return [TextContent(type="text", text=f"Error: {agent['error']}")]

        profile = agent.get("access_profile", {})
        mcp = arguments["mcp_name"]
        denied = profile.get("mcps_denied", [])
        allowed = profile.get("mcps_allowed", [])

        if mcp in denied:
            _audit_log(action=f"governance.check_mcp:{mcp}", result="denied")
            return [TextContent(
                type="text",
                text=f"❌ MCP '{mcp}' is DENIED by policy. Do not use tools from this server.",
            )]
        if allowed and mcp not in allowed:
            _audit_log(action=f"governance.check_mcp:{mcp}", result="denied")
            return [TextContent(
                type="text",
                text=f"❌ MCP '{mcp}' is not in your allowed list. "
                     f"Allowed: {', '.join(allowed)}",
            )]

        _audit_log(action=f"governance.check_mcp:{mcp}", result="success")
        return [TextContent(
            type="text",
            text=f"✅ MCP '{mcp}' is allowed. You may use tools from this server.",
        )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def main() -> None:
    """Entry point for the AGR MCP server (stdio transport)."""
    import asyncio

    if not AGR_AGENT_TOKEN:
        print(
            "WARNING: AGR_AGENT_TOKEN not set. Governance checks will fail.\n"
            "Register your agent and set the token:\n"
            "  export AGR_AGENT_TOKEN=agr_<your-token>",
            file=sys.stderr,
        )

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
