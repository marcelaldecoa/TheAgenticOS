"""Auth API routes — token-based agent identity resolution.

Endpoints:
  GET /auth/resolve    — Resolve Bearer token to agent principal
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from agr_server.store.base import Store

router = APIRouter(prefix="/auth", tags=["auth"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


class AgentPrincipal(BaseModel):
    """Minimal agent identity returned from token resolution."""

    id: str
    name: str
    status: str
    tenant_id: str
    platform: str


def _extract_token(authorization: str) -> str:
    """Extract token from 'Bearer <token>' header."""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


@router.get("/resolve", response_model=AgentPrincipal)
async def resolve_token(
    authorization: str = Header(..., description="Bearer <agent-token>"),
) -> AgentPrincipal:
    """Resolve an agent API token to a minimal principal.

    Used by MCP servers and SDKs to identify the calling agent.
    """
    token = _extract_token(authorization)
    agent = await _get_store().get_agent_by_token(token)
    if agent is None:
        raise HTTPException(status_code=401, detail="Invalid or expired agent token")
    return AgentPrincipal(
        id=agent.id,
        name=agent.name,
        status=agent.status.value,
        tenant_id=agent.tenant_id,
        platform=agent.platform,
    )
