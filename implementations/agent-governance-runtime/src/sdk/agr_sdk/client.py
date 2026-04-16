"""Governance client for instrumenting AI agents.

Usage::

    from agr_sdk import GovernanceClient

    gov = GovernanceClient(server_url="http://localhost:8600", agent_id="my-agent")

    # Register on startup
    record = gov.register(
        name="My Agent", platform="custom",
        owner_team="eng", owner_contact="eng@co.com",
        access_profile={"actions": {"deploy.*": "deny"}},
    )
    token = record["api_token"]  # Save this — shown only once

    # Use token-based auth for all subsequent calls
    gov = GovernanceClient(server_url="http://localhost:8600", token=token)

    # Check access before actions
    decision = gov.evaluate("email.send")
    if decision["decision"] == "allow":
        send_email(...)

    # Or use the context manager for automatic audit logging
    with gov.action("email.send", intent="Notify customer") as act:
        send_email(...)
        act.set_result("success")
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

import httpx


@dataclass
class ActionContext:
    """Context manager state for an audited action."""

    action: str
    intent: str | None = None
    _result: str = "success"
    _detail: str | None = None
    _start: float = field(default_factory=time.monotonic, init=False)
    _metadata: dict[str, Any] = field(default_factory=dict, init=False)

    def set_result(self, result: str, detail: str | None = None) -> None:
        self._result = result
        self._detail = detail

    def set_metadata(self, **kwargs: Any) -> None:
        self._metadata.update(kwargs)

    @property
    def duration_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)


class GovernanceClient:
    """Client for the Agent Governance Runtime API.

    Provides a thin, ergonomic wrapper for agent developers to:
    - Register agents and receive API tokens
    - Evaluate actions against governance policies
    - Check MCP and action access
    - Log audit records after actions
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8600",
        agent_id: str | None = None,
        *,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.agent_id = agent_id
        self.token = token
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=self.server_url, timeout=timeout, headers=headers,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> GovernanceClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # --- Registry ---

    def register(
        self,
        *,
        name: str,
        platform: str,
        owner_team: str,
        owner_contact: str,
        description: str | None = None,
        environment: str | None = None,
        access_profile: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Register this agent in the governance registry.

        Returns the full agent record WITH api_token (shown only once).
        """
        assert self.agent_id, "agent_id is required for registration"
        body: dict[str, Any] = {
            "id": self.agent_id,
            "name": name,
            "platform": platform,
            "owner": {"team": owner_team, "contact": owner_contact},
        }
        if description:
            body["description"] = description
        if environment:
            body["deployment"] = {"environment": environment}
        if access_profile:
            body["access_profile"] = access_profile
        if tags:
            body["tags"] = tags
        body["discovery_method"] = "sdk"
        body.update(kwargs)

        resp = self._client.post("/registry/agents", json=body)
        resp.raise_for_status()
        return resp.json()

    def get_agent(self, agent_id: str | None = None) -> dict[str, Any] | None:
        """Get an agent record. Uses self.agent_id if not specified."""
        aid = agent_id or self.agent_id
        assert aid, "agent_id is required"
        resp = self._client.get(f"/registry/agents/{aid}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_agents(self, **filters: Any) -> dict[str, Any]:
        """List registered agents with optional filters."""
        resp = self._client.get("/registry/agents", params=filters)
        resp.raise_for_status()
        return resp.json()

    # --- Governance Evaluation ---

    def evaluate(
        self,
        action: str,
        *,
        resource: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate an action against all governance controls.

        Returns decision (allow/deny/require_approval), matched rules, budget status.
        """
        body: dict[str, Any] = {
            "agent_id": self.agent_id or "unknown",
            "action": action,
        }
        if resource:
            body["resource"] = resource
        if context:
            body["context"] = context

        resp = self._client.post("/governance/evaluate", json=body)
        resp.raise_for_status()
        return resp.json()

    def check_access(self, action: str) -> dict[str, Any]:
        """Shorthand for evaluate() — check if an action is allowed."""
        return self.evaluate(action)

    def check_mcp(self, mcp_name: str) -> dict[str, Any]:
        """Check if an MCP server is allowed. Resolves from agent profile."""
        resp = self._client.get("/auth/resolve")
        if resp.status_code != 200:
            return {"decision": "deny", "reason": "Token not set or invalid"}

        agent = self.get_agent(resp.json()["id"])
        if agent is None:
            return {"decision": "deny", "reason": "Agent not found"}

        profile = agent.get("access_profile", {})
        denied = profile.get("mcps_denied", [])
        allowed = profile.get("mcps_allowed", [])

        if mcp_name in denied:
            return {"decision": "deny", "reason": f"MCP '{mcp_name}' is in denied list"}
        if allowed and mcp_name not in allowed:
            return {"decision": "deny", "reason": f"MCP '{mcp_name}' is not in allowed list"}
        return {"decision": "allow", "reason": f"MCP '{mcp_name}' is allowed"}

    # --- Audit Trail ---

    def audit_log(
        self,
        *,
        action: str,
        result: str = "success",
        intent: str | None = None,
        detail: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
        cost: dict[str, Any] | None = None,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append an audit record for an action taken by this agent.

        When using token-based auth, agent_id is derived server-side from the token.
        """
        body: dict[str, Any] = {
            "agent_id": self.agent_id or "unknown",
            "action": action,
            "result": result,
            "severity": severity,
        }
        if intent:
            body["intent"] = intent
        if detail:
            body["detail"] = detail
        if trace_id:
            body["trace_id"] = trace_id
        if run_id:
            body["run_id"] = run_id
        if session_id:
            body["session_id"] = session_id
        if cost:
            body["cost"] = cost
        if metadata:
            body["metadata"] = metadata

        resp = self._client.post("/audit/records", json=body)
        resp.raise_for_status()
        return resp.json()

    @contextmanager
    def action(
        self, action_name: str, *, intent: str | None = None
    ) -> Generator[ActionContext, None, None]:
        """Context manager that automatically logs audit records.

        Usage::

            with gov.action("email.send", intent="Notify user") as act:
                result = send_email(to="user@example.com")
                act.set_result("success")
        """
        ctx = ActionContext(action=action_name, intent=intent)
        try:
            yield ctx
        except Exception as e:
            ctx.set_result("error", detail=str(e))
            raise
        finally:
            self.audit_log(
                action=ctx.action,
                result=ctx._result,
                intent=ctx.intent,
                detail=ctx._detail,
                cost={"duration_ms": ctx.duration_ms},
                metadata=ctx._metadata,
            )

    # --- Budget ---

    def report_consumption(
        self,
        *,
        requests: int = 1,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
        action: str | None = None,
    ) -> None:
        """Report resource consumption to the budget tracker."""
        body: dict[str, Any] = {
            "agent_id": self.agent_id or "unknown",
            "requests": requests,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
        }
        if action:
            body["action"] = action
        resp = self._client.post("/budget/consume", json=body)
        resp.raise_for_status()

    def get_budget(self) -> dict[str, Any]:
        """Get current budget status."""
        aid = self.agent_id or "unknown"
        resp = self._client.get(f"/budget/{aid}")
        resp.raise_for_status()
        return resp.json()

    # --- System ---

    def health(self) -> dict[str, Any]:
        """Check server health."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()
