"""AGR MCP Server — Governance tools exposed as MCP.

This is the key integration mechanism. Agents (Claude Code, Copilot, etc.)
connect to this MCP server and get governance tools:

  - agr_check_access   — Check if an action is allowed by policy
  - agr_get_profile    — Get the agent's access profile
  - agr_audit          — Log an audit record for an action
  - agr_check_mcp      — Check if an MCP server is allowed

Authentication: The agent provides its API token via the AGR_AGENT_TOKEN
environment variable. The MCP server calls the AGR server's /governance/evaluate
endpoint for every decision — no stale cache, no local policy logic.

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

# Minimal cached identity (just id + name, not full profile)
_identity: dict | None = None


def _resolve_identity() -> dict:
    """Resolve agent identity from token via /auth/resolve. Cached per session."""
    global _identity
    if _identity is not None:
        return _identity

    if not AGR_AGENT_TOKEN:
        return {"error": "AGR_AGENT_TOKEN not set. Register your agent and set the token."}

    resp = _http.get(
        "/auth/resolve",
        headers={"Authorization": f"Bearer {AGR_AGENT_TOKEN}"},
    )
    if resp.status_code == 200:
        _identity = resp.json()
        return _identity

    return {"error": f"Token resolution failed: {resp.status_code} {resp.text}"}


def _auth_headers() -> dict[str, str]:
    """Return auth headers for AGR API calls."""
    if AGR_AGENT_TOKEN:
        return {"Authorization": f"Bearer {AGR_AGENT_TOKEN}"}
    return {}


def _evaluate_action(action: str, resource: str | None = None) -> dict:
    """Call /governance/evaluate — the single authoritative decision point."""
    identity = _resolve_identity()
    if "error" in identity:
        return {"decision": "deny", "reason": identity["error"]}

    body: dict = {
        "agent_id": identity["id"],
        "action": action,
    }
    if resource:
        body["resource"] = resource

    resp = _http.post(
        "/governance/evaluate",
        json=body,
        headers=_auth_headers(),
    )
    if resp.status_code == 200:
        return resp.json()
    return {"decision": "deny", "reason": f"Evaluation failed: {resp.status_code} {resp.text}"}


def _audit_log(action: str, result: str, **kwargs: str) -> dict:
    """Log an audit record via the AGR server. Agent_id derived from token."""
    identity = _resolve_identity()
    body = {
        "agent_id": identity.get("id", "unknown"),
        "action": action,
        "result": result,
        **{k: v for k, v in kwargs.items() if v},
    }
    resp = _http.post("/audit/records", json=body, headers=_auth_headers())
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
                "Returns: allow, deny, or require_approval with matched policies."
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
        result = _evaluate_action(
            arguments["action"],
            resource=arguments.get("resource"),
        )
        decision = result.get("decision", "deny")

        if decision == "deny":
            text = (
                f"❌ DENIED: {arguments['action']}\n"
                f"Reason: {result.get('reason', 'Policy violation')}\n\n"
                f"Do NOT proceed with this action. Inform the user it is blocked by policy."
            )
        elif decision == "require_approval":
            text = (
                f"⏸️ APPROVAL REQUIRED: {arguments['action']}\n"
                f"Reason: {result.get('reason', 'Requires approval')}\n\n"
                f"This action requires human approval before proceeding. "
                f"Ask the user to approve explicitly."
            )
        else:
            text = f"✅ ALLOWED: {arguments['action']}\nYou may proceed with this action."

        # Add matched rules info if available
        matched = result.get("matched_rules", [])
        if matched:
            text += f"\n\nMatched {len(matched)} policy rule(s):"
            for rule in matched:
                text += f"\n  - {rule['policy_name']} ({rule['matched_pattern']} → {rule['decision']})"

        # Add budget info if present
        if result.get("budget_status") and result["budget_status"] != "ok":
            text += f"\n\n⚠️ Budget: {result['budget_status']}"
            if result.get("budget_detail"):
                text += f" — {result['budget_detail']}"

        return [TextContent(type="text", text=text)]

    elif name == "agr_get_profile":
        identity = _resolve_identity()
        if "error" in identity:
            return [TextContent(type="text", text=f"Error: {identity['error']}")]

        # Fetch the full agent profile via the registry
        resp = _http.get(f"/registry/agents/{identity['id']}")
        if resp.status_code != 200:
            return [TextContent(type="text", text=f"Error: Could not fetch profile")]

        agent = resp.json()
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

        budget = profile.get("budget")
        if budget:
            lines.append("")
            lines.append("Budget limits:")
            for k, v in budget.items():
                if v is not None:
                    lines.append(f"  {k}: {v}")

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
        identity = _resolve_identity()
        if "error" in identity:
            return [TextContent(type="text", text=f"Error: {identity['error']}")]

        # Fetch profile for MCP check
        resp = _http.get(f"/registry/agents/{identity['id']}")
        if resp.status_code != 200:
            return [TextContent(type="text", text="Error: Could not fetch profile")]

        profile = resp.json().get("access_profile", {})
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
