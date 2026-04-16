"""Tests for auth resolution, token redaction, and authenticated audit."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AGENT = {
    "id": "auth-test-agent",
    "name": "Auth Test Agent",
    "platform": "custom",
    "owner": {"team": "security-team", "contact": "sec@example.com"},
    "access_profile": {
        "mcps_allowed": ["github-mcp"],
        "actions": {"file.read": "allow", "deploy.*": "deny"},
    },
}


async def _register_and_get_token(client: AsyncClient) -> str:
    """Register an agent and return its API token."""
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    assert resp.status_code == 201
    token = resp.json()["api_token"]
    assert token.startswith("agr_")
    return token


@pytest.mark.asyncio
async def test_token_only_on_create(client: AsyncClient):
    """Token should only be in POST response, not GET."""
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    assert resp.status_code == 201
    assert resp.json()["api_token"] is not None

    resp = await client.get("/registry/agents/auth-test-agent")
    assert resp.status_code == 200
    assert "api_token" not in resp.json()


@pytest.mark.asyncio
async def test_token_redacted_in_list(client: AsyncClient):
    """Token should not appear in list responses."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.get("/registry/agents")
    for agent in resp.json()["items"]:
        assert "api_token" not in agent


@pytest.mark.asyncio
async def test_token_redacted_in_update(client: AsyncClient):
    """Token should not appear in PUT response."""
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.put(
        "/registry/agents/auth-test-agent",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert "api_token" not in resp.json()


@pytest.mark.asyncio
async def test_auth_resolve_valid_token(client: AsyncClient):
    """Valid token should resolve to agent principal."""
    token = await _register_and_get_token(client)
    resp = await client.get(
        "/auth/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "auth-test-agent"
    assert data["name"] == "Auth Test Agent"
    assert data["platform"] == "custom"
    assert data["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_auth_resolve_invalid_token(client: AsyncClient):
    """Invalid token should return 401."""
    resp = await client.get(
        "/auth/resolve",
        headers={"Authorization": "Bearer agr_invalid_token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_resolve_no_header(client: AsyncClient):
    """Missing auth header should return 422."""
    resp = await client.get("/auth/resolve")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_derives_agent_from_token(client: AsyncClient):
    """When Bearer token is present, audit should use the token's agent_id."""
    token = await _register_and_get_token(client)

    # Post audit with a DIFFERENT agent_id in the body
    resp = await client.post(
        "/audit/records",
        json={
            "agent_id": "fake-agent-id",
            "action": "file.read",
            "result": "success",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    # Should be overridden to the token's agent
    assert resp.json()["agent_id"] == "auth-test-agent"


@pytest.mark.asyncio
async def test_audit_without_token_uses_body(client: AsyncClient):
    """Without Bearer token, audit uses the body's agent_id."""
    resp = await client.post(
        "/audit/records",
        json={
            "agent_id": "manual-agent",
            "action": "file.read",
            "result": "success",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["agent_id"] == "manual-agent"
