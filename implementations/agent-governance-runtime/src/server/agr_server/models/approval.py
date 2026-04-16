"""Approval flow models — human-in-the-loop governance.

When /governance/evaluate returns require_approval, agents create an
ApprovalRequest. Human operators (approvers) decide via the API.

Key design:
- Idempotent creation via context_hash (agent_id + action + resource)
- One-time-use: approved request can only be consumed once
- Auto-expiry: pending requests expire after configured duration (default 1h)
- Re-validation: consuming an approval still checks deny/budget gates
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ApprovalRequestCreate(BaseModel):
    """Request body for creating an approval request."""

    agent_id: str
    action: str
    resource: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, description="Why this action needs approval")

    # Provenance — what triggered the approval requirement
    triggering_policies: list[str] = Field(
        default_factory=list,
        description="Policy IDs that triggered require_approval",
    )
    triggering_source: str = Field(
        default="access_profile",
        description="What required approval: 'access_profile' or 'policy'",
    )

    def compute_context_hash(self) -> str:
        """Idempotency key: same agent+action+resource = same request."""
        data = json.dumps({
            "agent_id": self.agent_id,
            "action": self.action,
            "resource": self.resource or "",
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ApprovalDecision(BaseModel):
    """Request body for approving/denying a request."""

    decision: ApprovalStatus = Field(description="approved or denied")
    reason: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.decision not in (ApprovalStatus.APPROVED, ApprovalStatus.DENIED):
            raise ValueError("Decision must be 'approved' or 'denied'")


class ApprovalRecord(BaseModel):
    """Full approval request record."""

    id: str
    tenant_id: str = "default"
    agent_id: str
    action: str
    resource: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    context_hash: str

    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str | None = None
    decision_reason: str | None = None
    decided_by: str | None = Field(default=None, description="Operator ID who decided")
    decided_at: datetime | None = None

    triggering_policies: list[str] = Field(default_factory=list)
    triggering_source: str = "access_profile"

    expires_at: datetime
    created_at: datetime
    consumed_at: datetime | None = None


class ApprovalList(BaseModel):
    """Paginated list of approval requests."""

    items: list[ApprovalRecord]
    total: int
    page: int
    page_size: int
    has_more: bool
