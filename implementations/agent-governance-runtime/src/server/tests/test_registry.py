"""Tests for the Agent Registry API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_AGENT = {
    "id": "test-agent-001",
    "name": "Test Agent",
    "platform": "custom",
    "owner": {"team": "test-team", "contact": "test@example.com"},
    "deployment": {"environment": "test"},
    "access_profile": {
        "mcps_allowed": ["github-mcp", "docs-mcp"],
        "mcps_denied": ["production-db"],
        "actions": {
            "file.read": "allow",
            "file.write": "allow",
            "deploy.*": "deny",
            "git.push": "require_approval",
        },
    },
    "tags": ["test"],
}


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_agent(client: AsyncClient):
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "test-agent-001"
    assert data["status"] == "pending_approval"
    assert data["tenant_id"] == "default"
    assert data["discovery_method"] == "manual"
    assert data["api_token"] is not None
    assert data["api_token"].startswith("agr_")


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.get("/registry/agents/test-agent-001")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Agent"
    # Token must be redacted from GET responses
    assert "api_token" not in resp.json()


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    resp = await client.get("/registry/agents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.get("/registry/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    # Tokens must be redacted from list responses
    for agent in data["items"]:
        assert "api_token" not in agent


@pytest.mark.asyncio
async def test_list_agents_filter_platform(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.get("/registry/agents", params={"platform": "custom"})
    assert resp.status_code == 200
    assert all(a["platform"] == "custom" for a in resp.json()["items"])


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.put(
        "/registry/agents/test-agent-001",
        json={"name": "Updated Agent", "status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Agent"
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_access_profile_persists(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.get("/registry/agents/test-agent-001")
    profile = resp.json()["access_profile"]
    assert "github-mcp" in profile["mcps_allowed"]
    assert "production-db" in profile["mcps_denied"]
    assert profile["actions"]["deploy.*"] == "deny"
    assert profile["actions"]["git.push"] == "require_approval"


@pytest.mark.asyncio
async def test_agent_gets_api_token(client: AsyncClient):
    resp = await client.post("/registry/agents", json=SAMPLE_AGENT)
    token = resp.json()["api_token"]
    assert token is not None
    assert token.startswith("agr_")
    assert len(token) > 20


@pytest.mark.asyncio
async def test_deprecate_agent(client: AsyncClient):
    await client.post("/registry/agents", json=SAMPLE_AGENT)
    resp = await client.delete("/registry/agents/test-agent-001")
    assert resp.status_code == 204

    resp = await client.get("/registry/agents/test-agent-001")
    assert resp.json()["status"] == "deprecated"
