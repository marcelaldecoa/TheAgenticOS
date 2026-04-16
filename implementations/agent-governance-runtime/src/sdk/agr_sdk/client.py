"""Governance client for instrumenting AI agents.

Usage::

    from agr_sdk import GovernanceClient

    gov = GovernanceClient(server_url="http://localhost:8600", agent_id="my-agent")

    # Register on startup
    gov.register(name="My Agent", platform="custom", archetype="executor",
                 owner_team="eng", owner_contact="eng@co.com")

    # Before tool calls
    decision = gov.check_capability("email.send")
    if decision.granted:
        send_email(...)
        gov.audit_log(action="email.send", result="success")

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
class CapabilityDecision:
    """Result of a capability check."""

    granted: bool
    reason: str | None = None


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
    - Register agents
    - Check capabilities before tool calls
    - Log audit records after actions
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8600",
        agent_id: str | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.agent_id = agent_id
        self._client = httpx.Client(base_url=self.server_url, timeout=timeout)

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
        archetype: str = "executor",
        owner_team: str,
        owner_contact: str,
        description: str | None = None,
        environment: str | None = None,
        capabilities: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Register this agent in the governance registry.

        Returns the full agent record.
        """
        assert self.agent_id, "agent_id is required for registration"
        body: dict[str, Any] = {
            "id": self.agent_id,
            "name": name,
            "platform": platform,
            "archetype": archetype,
            "owner": {"team": owner_team, "contact": owner_contact},
        }
        if description:
            body["description"] = description
        if environment:
            body["deployment"] = {"environment": environment}
        if capabilities:
            body["capabilities_requested"] = capabilities
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

    # --- Capability Checks ---

    def check_capability(self, resource: str, action: str = "invoke") -> CapabilityDecision:
        """Check if this agent has a specific capability.

        Phase 1: Checks against the agent's ``capabilities_granted`` field.
        Phase 2: Will evaluate against the policy engine.
        """
        agent = self.get_agent()
        if agent is None:
            return CapabilityDecision(granted=False, reason="Agent not registered")

        for cap in agent.get("capabilities_granted", []):
            if cap.get("resource") == resource and action in cap.get("actions", []):
                return CapabilityDecision(granted=True)

        return CapabilityDecision(
            granted=False,
            reason=f"Capability '{resource}:{action}' not granted",
        )

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
        capabilities_exercised: list[str] | None = None,
        cost: dict[str, Any] | None = None,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append an audit record for an action taken by this agent."""
        assert self.agent_id, "agent_id is required for audit logging"
        body: dict[str, Any] = {
            "agent_id": self.agent_id,
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
        if capabilities_exercised:
            body["capabilities_exercised"] = capabilities_exercised
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

    # --- System ---

    def health(self) -> dict[str, Any]:
        """Check server health."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()
