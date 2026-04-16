"""Policy engine models — declarative governance rules.

Policies are tenant-wide rules that complement agent-level access profiles.
They provide organization-wide guardrails that individual agents cannot override.

Precedence (most restrictive wins):
  1. Effect order: deny > require_approval > allow
  2. Scope: exact match > wildcard match
  3. Priority: higher number wins within same effect + scope
  4. Source: tenant policy > agent access profile

Policies are soft-deletable (enabled/disabled), never hard-deleted.
All changes are audited.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agr_server.models.agent import AccessDecision


class PolicyCondition(BaseModel):
    """Conditions under which a policy rule applies."""

    action_pattern: str = Field(
        description="Action pattern to match (e.g. 'deploy.production', 'deploy.*', '*')"
    )
    platforms: list[str] = Field(
        default_factory=list,
        description="Only apply to agents on these platforms (empty = all)",
    )
    environments: list[str] = Field(
        default_factory=list,
        description="Only apply in these environments (empty = all)",
    )
    data_classification_min: str | None = Field(
        default=None,
        description="Only apply when data classification >= this level",
    )


class PolicyRuleCreate(BaseModel):
    """Request body for creating a policy rule."""

    name: str = Field(min_length=1, max_length=256, description="Human-readable rule name")
    description: str | None = None
    condition: PolicyCondition
    decision: AccessDecision = Field(description="What happens when conditions match")
    priority: int = Field(
        default=100, ge=0, le=10000,
        description="Higher priority wins within same effect level (0-10000)",
    )
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRuleUpdate(BaseModel):
    """Request body for updating a policy rule (enable/disable, metadata)."""

    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class PolicyRule(BaseModel):
    """Full policy rule as stored and returned by the API."""

    id: str = Field(description="Server-assigned unique ID")
    tenant_id: str = "default"
    name: str
    description: str | None = None
    condition: PolicyCondition
    decision: AccessDecision
    priority: int = 100
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(description="When the rule was created")
    updated_at: datetime = Field(description="When the rule was last modified")
    created_by: str | None = Field(default=None, description="Who created the rule")


class PolicyRuleList(BaseModel):
    """Paginated list of policy rules."""

    items: list[PolicyRule]
    total: int
    page: int
    page_size: int
    has_more: bool


class PolicyEvalRequest(BaseModel):
    """Request to evaluate an action against policies."""

    agent_id: str = Field(description="Agent requesting the action")
    action: str = Field(description="Action to evaluate (e.g. 'deploy.production')")
    resource: str | None = Field(default=None, description="Target resource")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (environment, data_classification, etc.)",
    )


class PolicyMatch(BaseModel):
    """A policy rule that matched during evaluation."""

    policy_id: str
    policy_name: str
    decision: AccessDecision
    priority: int
    matched_pattern: str


class PolicyEvalResponse(BaseModel):
    """Result of policy evaluation."""

    decision: AccessDecision
    reason: str
    matched_rules: list[PolicyMatch] = Field(default_factory=list)
    agent_status: str | None = None
    budget_status: str | None = Field(
        default=None,
        description="ok | warning | exceeded",
    )
    budget_detail: str | None = None
