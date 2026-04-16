"""Budget & Quota API routes.

Endpoints:
  POST /budget/consume          — Record resource consumption
  GET  /budget/{agent_id}       — Get current budget status
"""

from __future__ import annotations

from fastapi import APIRouter

from agr_server.config import settings
from agr_server.models.budget import BudgetConsumeRequest, BudgetStatus
from agr_server.store.base import Store

router = APIRouter(prefix="/budget", tags=["budget"])

_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    assert _store is not None, "Store not set. Call set_store() first."
    return _store


@router.post("/consume", status_code=204, response_model=None)
async def record_consumption(request: BudgetConsumeRequest) -> None:
    """Record resource consumption for an agent."""
    await _get_store().record_consumption(request, settings.default_tenant)


@router.get("/{agent_id}", response_model=BudgetStatus)
async def get_budget_status(agent_id: str) -> BudgetStatus:
    """Get current budget status for an agent."""
    return await _get_store().get_budget_status(agent_id, settings.default_tenant)
