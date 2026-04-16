"""Agent Registry API routes.

Endpoints:
  POST   /registry/agents          — Register a new agent
  GET    /registry/agents          — List/search agents (paginated)
  GET    /registry/agents/{id}     — Get agent by ID
  PUT    /registry/agents/{id}     — Update agent registration
  DELETE /registry/agents/{id}     — Deprecate an agent
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from agr_server.config import settings
from agr_server.models.agent import (
    AgentCreate,
    AgentList,
    AgentRecord,
    AgentRecordPublic,
    AgentUpdate,
)
from agr_server.store.base import Store

router = APIRouter(prefix="/registry", tags=["registry"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


@router.post("/agents", response_model=AgentRecord, status_code=201)
async def register_agent(agent: AgentCreate) -> AgentRecord:
    """Register a new agent. Returns full record WITH api_token (shown once)."""
    try:
        return await _get_store().register_agent(agent, settings.default_tenant)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/agents", response_model=AgentList)
async def list_agents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    platform: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner_team: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Search by name or ID"),
) -> AgentList:
    """List registered agents (tokens redacted)."""
    return await _get_store().list_agents(
        settings.default_tenant,
        page=page,
        page_size=page_size,
        platform=platform,
        status=status,
        owner_team=owner_team,
        search=search,
    )


@router.get("/agents/{agent_id}", response_model=AgentRecordPublic)
async def get_agent(agent_id: str) -> AgentRecordPublic:
    """Get a registered agent by ID (token redacted)."""
    record = await _get_store().get_agent(agent_id, settings.default_tenant)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return AgentRecordPublic.from_record(record)


@router.put("/agents/{agent_id}", response_model=AgentRecordPublic)
async def update_agent(agent_id: str, update: AgentUpdate) -> AgentRecordPublic:
    """Update an existing agent registration (token redacted in response)."""
    record = await _get_store().update_agent(agent_id, update, settings.default_tenant)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return AgentRecordPublic.from_record(record)


@router.delete("/agents/{agent_id}", status_code=204, response_model=None)
async def deprecate_agent(agent_id: str) -> None:
    """Deprecate an agent (soft delete — marks as deprecated)."""
    found = await _get_store().deprecate_agent(agent_id, settings.default_tenant)
    if not found:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
