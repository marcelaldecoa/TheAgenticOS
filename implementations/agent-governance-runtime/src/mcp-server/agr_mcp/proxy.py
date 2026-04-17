"""AGR MCP Proxy — Hard enforcement via tool-call interception.

Unlike the advisory MCP server (agr-mcp), the proxy sits BETWEEN the agent
and downstream MCP servers. It intercepts every tool call, evaluates it
against governance, and only forwards allowed calls. Denied calls never
reach the downstream server.

Architecture::

    Agent ──► AGR MCP Proxy ──► /governance/evaluate ──► Decision
                   │                                         │
                   │  if ALLOW ──────────────────────────────►│
                   │        └──► Forward to downstream MCP ───┘
                   │
                   │  if DENY ──────────────────────────────►│
                   │        └──► Return error, never forward  │

Configuration (environment variables):

    AGR_SERVER_URL      — AGR server URL (default: http://localhost:8600)
    AGR_AGENT_TOKEN     — Agent API token for identity resolution
    AGR_PROXY_CONFIG    — Path to proxy config JSON (downstream MCP mappings)

Proxy config JSON::

    {
      "downstreams": {
        "github-mcp": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-github"],
          "env": {"GITHUB_TOKEN": "ghp_..."}
        },
        "filesystem-mcp": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
        }
      }
    }

Usage in .vscode/mcp.json::

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
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from mcp.client import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

AGR_SERVER_URL = os.environ.get("AGR_SERVER_URL", "http://localhost:8600")
AGR_AGENT_TOKEN = os.environ.get("AGR_AGENT_TOKEN", "")
AGR_PROXY_CONFIG = os.environ.get("AGR_PROXY_CONFIG", "")

proxy_server = Server("agr-mcp-proxy")
_http = httpx.Client(base_url=AGR_SERVER_URL, timeout=10.0)
_identity: dict | None = None

# Downstream MCP sessions: mcp_name → ClientSession
_downstream_sessions: dict[str, ClientSession] = {}
# Tool registry: tool_name → (mcp_name, original_tool)
_tool_registry: dict[str, tuple[str, Tool]] = {}
# Config
_proxy_config: dict = {}


def _resolve_identity() -> dict:
    """Resolve agent identity from token."""
    global _identity
    if _identity is not None:
        return _identity
    if not AGR_AGENT_TOKEN:
        return {"error": "AGR_AGENT_TOKEN not set"}
    resp = _http.get(
        "/auth/resolve",
        headers={"Authorization": f"Bearer {AGR_AGENT_TOKEN}"},
    )
    if resp.status_code == 200:
        _identity = resp.json()
        return _identity
    return {"error": f"Token resolution failed: {resp.status_code}"}


def _auth_headers() -> dict[str, str]:
    if AGR_AGENT_TOKEN:
        return {"Authorization": f"Bearer {AGR_AGENT_TOKEN}"}
    return {}


def _evaluate(action: str, resource: str | None = None) -> dict:
    """Evaluate an action against governance. Returns the full decision."""
    identity = _resolve_identity()
    if "error" in identity:
        return {"decision": "deny", "reason": identity["error"]}
    body: dict = {"agent_id": identity["id"], "action": action}
    if resource:
        body["resource"] = resource
    resp = _http.post("/governance/evaluate", json=body, headers=_auth_headers())
    if resp.status_code == 200:
        return resp.json()
    return {"decision": "deny", "reason": f"Evaluation failed: {resp.status_code}"}


def _audit(action: str, result: str, **kwargs: str) -> None:
    """Log an audit record."""
    identity = _resolve_identity()
    body = {
        "agent_id": identity.get("id", "unknown"),
        "action": action,
        "result": result,
        **{k: v for k, v in kwargs.items() if v},
    }
    _http.post("/audit/records", json=body, headers=_auth_headers())


def _check_mcp_access(mcp_name: str) -> dict:
    """Check MCP-level access from the agent's profile."""
    identity = _resolve_identity()
    if "error" in identity:
        return {"decision": "deny", "reason": identity["error"]}
    resp = _http.get(f"/registry/agents/{identity['id']}", headers=_auth_headers())
    if resp.status_code != 200:
        return {"decision": "deny", "reason": "Could not fetch profile"}
    profile = resp.json().get("access_profile", {})
    denied = profile.get("mcps_denied", [])
    allowed = profile.get("mcps_allowed", [])
    if mcp_name in denied:
        return {"decision": "deny", "reason": f"MCP '{mcp_name}' is in denied list"}
    if allowed and mcp_name not in allowed:
        return {"decision": "deny", "reason": f"MCP '{mcp_name}' is not in allowed list"}
    return {"decision": "allow", "reason": f"MCP '{mcp_name}' is allowed"}


def _load_config() -> dict:
    """Load proxy configuration from file."""
    global _proxy_config
    if AGR_PROXY_CONFIG and Path(AGR_PROXY_CONFIG).exists():
        _proxy_config = json.loads(Path(AGR_PROXY_CONFIG).read_text(encoding="utf-8"))
    return _proxy_config


@proxy_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all tools from downstream MCPs, prefixed with their MCP name."""
    all_tools: list[Tool] = []

    # Add governance tools (always available)
    all_tools.append(Tool(
        name="agr_check_access",
        description="Check if an action is allowed by governance policy.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action in dotted notation"},
                "resource": {"type": "string", "description": "Target resource"},
            },
            "required": ["action"],
        },
    ))
    all_tools.append(Tool(
        name="agr_get_profile",
        description="Get your governance access profile.",
        inputSchema={"type": "object", "properties": {}},
    ))

    # Add downstream tools (prefixed with MCP name)
    for tool_name, (mcp_name, tool) in _tool_registry.items():
        # Prefix the description with governance context
        desc = (
            f"[via {mcp_name}] {tool.description or ''}\n"
            f"⚡ This tool is governed — calls are evaluated against policy before execution."
        )
        all_tools.append(Tool(
            name=tool_name,
            description=desc,
            inputSchema=tool.inputSchema,
        ))

    return all_tools


@proxy_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Handle governance tools directly
    if name == "agr_check_access":
        result = _evaluate(arguments["action"], arguments.get("resource"))
        decision = result.get("decision", "deny")
        icons = {"allow": "✅", "deny": "❌", "require_approval": "⏸️"}
        return [TextContent(type="text", text=(
            f"{icons.get(decision, '?')} {arguments['action']} → {decision}\n"
            f"Reason: {result.get('reason', 'N/A')}"
        ))]

    if name == "agr_get_profile":
        identity = _resolve_identity()
        if "error" in identity:
            return [TextContent(type="text", text=f"Error: {identity['error']}")]
        resp = _http.get(f"/registry/agents/{identity['id']}", headers=_auth_headers())
        if resp.status_code != 200:
            return [TextContent(type="text", text="Error: Could not fetch profile")]
        agent = resp.json()
        profile = agent.get("access_profile", {})
        return [TextContent(type="text", text=json.dumps(profile, indent=2))]

    # Handle downstream MCP tool calls with governance enforcement
    if name not in _tool_registry:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    mcp_name, original_tool = _tool_registry[name]

    # Step 1: Check MCP-level access
    mcp_check = _check_mcp_access(mcp_name)
    if mcp_check["decision"] != "allow":
        _audit(
            action=f"{mcp_name}.{original_tool.name}",
            result="denied",
            detail=f"MCP blocked: {mcp_check['reason']}",
            severity="warning",
        )
        return [TextContent(type="text", text=(
            f"❌ BLOCKED: MCP '{mcp_name}' is not allowed for this agent.\n"
            f"Reason: {mcp_check['reason']}\n\n"
            f"This call was intercepted by the AGR proxy and never reached the server."
        ))]

    # Step 2: Evaluate action-level governance
    action = f"{mcp_name}.{original_tool.name}"
    decision = _evaluate(action, resource=arguments.get("resource"))

    if decision.get("decision") == "deny":
        _audit(
            action=action,
            result="denied",
            detail=f"Policy denied: {decision.get('reason', '')}",
            severity="warning",
        )
        return [TextContent(type="text", text=(
            f"❌ BLOCKED: Action '{action}' is denied by governance policy.\n"
            f"Reason: {decision.get('reason', 'Policy violation')}\n\n"
            f"This call was intercepted by the AGR proxy and never reached "
            f"the downstream MCP server '{mcp_name}'."
        ))]

    if decision.get("decision") == "require_approval":
        _audit(
            action=action,
            result="denied",
            detail=f"Requires approval: {decision.get('reason', '')}",
        )
        return [TextContent(type="text", text=(
            f"⏸️ BLOCKED: Action '{action}' requires human approval.\n"
            f"Reason: {decision.get('reason', 'Requires approval')}\n\n"
            f"This call was intercepted by the AGR proxy. Request approval "
            f"before retrying."
        ))]

    # Step 3: ALLOWED — forward to downstream MCP
    session = _downstream_sessions.get(mcp_name)
    if session is None:
        return [TextContent(type="text", text=(
            f"Error: Downstream MCP '{mcp_name}' session not available."
        ))]

    try:
        result = await session.call_tool(original_tool.name, arguments)
        # Audit successful call
        _audit(action=action, result="success")
        return result.content
    except Exception as e:
        _audit(action=action, result="error", detail=str(e))
        return [TextContent(type="text", text=f"Error calling {mcp_name}: {e}")]


async def _connect_downstream(
    mcp_name: str,
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
) -> None:
    """Connect to a downstream MCP server and register its tools."""
    merged_env = {**os.environ, **(env or {})}
    params = StdioServerParameters(
        command=command,
        args=args,
        env=merged_env,
    )
    try:
        read, write = await asyncio.wait_for(
            stdio_client(params).__aenter__(),
            timeout=30.0,
        )
        session = ClientSession(read, write)
        await session.initialize()
        _downstream_sessions[mcp_name] = session

        # Discover tools and register with prefix
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            prefixed_name = f"{mcp_name}__{tool.name}"
            _tool_registry[prefixed_name] = (mcp_name, tool)

        print(
            f"  ✓ {mcp_name}: {len(tools_result.tools)} tools",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"  ✗ {mcp_name}: failed to connect — {e}", file=sys.stderr)


def main() -> None:
    """Entry point for the AGR MCP Proxy."""

    if not AGR_AGENT_TOKEN:
        print(
            "WARNING: AGR_AGENT_TOKEN not set. All calls will be denied.\n"
            "  export AGR_AGENT_TOKEN=agr_<your-token>",
            file=sys.stderr,
        )

    if not AGR_PROXY_CONFIG:
        print(
            "WARNING: AGR_PROXY_CONFIG not set. No downstream MCPs configured.\n"
            "  export AGR_PROXY_CONFIG=./proxy-config.json",
            file=sys.stderr,
        )

    config = _load_config()

    async def run():
        # Connect to all downstream MCPs
        downstreams = config.get("downstreams", {})
        if downstreams:
            print(f"AGR MCP Proxy: connecting to {len(downstreams)} downstream(s)...", file=sys.stderr)
            for mcp_name, mcp_config in downstreams.items():
                await _connect_downstream(
                    mcp_name=mcp_name,
                    command=mcp_config["command"],
                    args=mcp_config.get("args", []),
                    env=mcp_config.get("env"),
                )
            print(
                f"AGR MCP Proxy: {len(_tool_registry)} tools registered, "
                f"governance enforced.",
                file=sys.stderr,
            )
        else:
            print("AGR MCP Proxy: no downstreams configured.", file=sys.stderr)

        # Start proxy server
        async with stdio_server() as (read_stream, write_stream):
            await proxy_server.run(
                read_stream, write_stream,
                proxy_server.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
