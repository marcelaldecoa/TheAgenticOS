"""Example: MCP Gateway with AGR governance.

This example shows how to wrap MCP tool calls with governance checks.
Every MCP invocation goes through:
  1. MCP-level access check (is this MCP server allowed?)
  2. Action-level policy evaluation (is this specific tool call allowed?)
  3. Audit logging with timing and metadata
  4. Budget tracking

This pattern works for any agent that uses MCP servers — not just Copilot.

Prerequisites:
  - AGR server running: agr-server
  - Agent registered with MCP restrictions in the access profile
  - Token saved in AGR_AGENT_TOKEN env var
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agr_sdk import GovernanceClient


@dataclass
class MCPCallResult:
    """Result of a governed MCP tool call."""

    allowed: bool
    decision: str
    reason: str
    result: Any = None


class GovernedMCPGateway:
    """Gateway that enforces AGR governance on MCP tool calls.

    Usage::

        gateway = GovernedMCPGateway(gov_client)

        # This checks MCP access + action policy + logs audit + tracks budget
        result = gateway.call("github-mcp", "create_pull_request", {
            "repo": "acme/backend",
            "title": "Fix user API",
            "base": "main",
        })

        if result.allowed:
            print(f"PR created: {result.result}")
        else:
            print(f"Blocked: {result.reason}")
    """

    def __init__(self, gov: GovernanceClient) -> None:
        self._gov = gov

    def call(
        self,
        mcp_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        intent: str | None = None,
    ) -> MCPCallResult:
        """Execute a governed MCP tool call.

        1. Check MCP-level access
        2. Evaluate action-level policy
        3. Execute with audit logging
        4. Report consumption
        """
        arguments = arguments or {}

        # Step 1: MCP-level access check
        mcp_result = self._gov.check_mcp(mcp_name)
        if mcp_result["decision"] != "allow":
            self._gov.audit_log(
                action=f"{mcp_name}.{tool_name}",
                result="denied",
                intent=intent,
                detail=f"MCP blocked: {mcp_result['reason']}",
                severity="warning",
            )
            return MCPCallResult(
                allowed=False,
                decision="deny",
                reason=f"MCP '{mcp_name}' blocked: {mcp_result['reason']}",
            )

        # Step 2: Action-level policy evaluation
        action = f"{mcp_name}.{tool_name}"
        decision = self._gov.evaluate(action, context=arguments)
        if decision["decision"] == "deny":
            self._gov.audit_log(
                action=action,
                result="denied",
                intent=intent,
                detail=f"Policy denied: {decision['reason']}",
                severity="warning",
            )
            return MCPCallResult(
                allowed=False,
                decision="deny",
                reason=decision["reason"],
            )
        if decision["decision"] == "require_approval":
            self._gov.audit_log(
                action=action,
                result="denied",
                intent=intent,
                detail=f"Requires approval: {decision['reason']}",
                severity="info",
            )
            return MCPCallResult(
                allowed=False,
                decision="require_approval",
                reason=decision["reason"],
            )

        # Step 3: Execute with audit logging
        with self._gov.action(action, intent=intent) as act:
            # --- Replace with actual MCP call ---
            tool_result = self._simulate_mcp_call(mcp_name, tool_name, arguments)
            # ------------------------------------
            act.set_metadata(mcp=mcp_name, tool=tool_name, args=arguments)
            act.set_result("success")

        # Step 4: Report consumption
        self._gov.report_consumption(requests=1, action=action)

        return MCPCallResult(
            allowed=True,
            decision="allow",
            reason="Allowed by policy",
            result=tool_result,
        )

    @staticmethod
    def _simulate_mcp_call(mcp_name: str, tool_name: str, arguments: dict) -> dict:
        """Simulate an MCP tool call (replace with real MCP client)."""
        return {
            "mcp": mcp_name,
            "tool": tool_name,
            "status": "ok",
            "simulated": True,
        }


def main() -> None:
    gov = GovernanceClient(
        server_url=os.environ.get("AGR_SERVER_URL", "http://localhost:8600"),
        agent_id="copilot-devops-agent",
        token=os.environ.get("AGR_AGENT_TOKEN"),
    )

    gateway = GovernedMCPGateway(gov)

    # Allowed MCP call
    print("--- github-mcp.list_pulls (allowed) ---")
    result = gateway.call(
        "github-mcp", "list_pulls",
        {"repo": "acme/backend", "state": "open"},
        intent="List open PRs for review",
    )
    print(f"  Decision: {result.decision}")
    if result.allowed:
        print(f"  Result: {result.result}")

    # Blocked MCP
    print("\n--- production-db-mcp.query (blocked MCP) ---")
    result = gateway.call(
        "production-db-mcp", "query",
        {"sql": "SELECT * FROM users"},
        intent="Query production database",
    )
    print(f"  Decision: {result.decision}")
    print(f"  Reason: {result.reason}")

    # Action requires approval
    print("\n--- kubernetes-mcp.deploy (requires approval) ---")
    result = gateway.call(
        "kubernetes-mcp", "deploy",
        {"namespace": "production", "image": "acme/api:v2"},
        intent="Deploy to production Kubernetes",
    )
    print(f"  Decision: {result.decision}")
    print(f"  Reason: {result.reason}")


if __name__ == "__main__":
    main()
