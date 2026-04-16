"""Agent registration and access profile models.

The access profile is the core governance primitive: it controls which MCP servers,
skills, data sources, and actions an agent can use. When AGR operates as an MCP
proxy, the access profile determines what tools the agent sees and what calls
are allowed, denied, or require approval.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """Lifecycle status of a registered agent."""

    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class DiscoveryMethod(StrEnum):
    """How this agent was discovered/registered."""

    MANUAL = "manual"
    SDK = "sdk"
    MCP = "mcp"
    SCAN = "scan"
    IMPORT = "import"


class AccessDecision(StrEnum):
    """Policy decision for a specific action or resource."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class BudgetLimit(BaseModel):
    """Resource consumption limits for an agent."""

    max_tokens_per_hour: int | None = None
    max_cost_per_day_usd: float | None = None
    max_requests_per_hour: int | None = None


class AccessProfile(BaseModel):
    """What an agent can access — MCPs, skills, data, actions.

    This is the enforcement surface. When AGR proxies tool calls, it evaluates
    the request against these rules. Server-side only — clients cannot override.

    Example::

        {
            "mcps_allowed": ["github-mcp", "jira-mcp", "knowledge-base"],
            "mcps_denied": ["production-db", "deploy-pipeline"],
            "skills_allowed": ["code-review", "triage", "docs-search"],
            "data_classification_max": "confidential",
            "actions": {
                "file.read": "allow",
                "file.write": "allow",
                "git.push": "require_approval",
                "deploy.*": "deny"
            },
            "budget": { "max_tokens_per_hour": 100000 }
        }
    """

    mcps_allowed: list[str] = Field(
        default_factory=list,
        description="MCP servers this agent may use (empty = none allowed)",
    )
    mcps_denied: list[str] = Field(
        default_factory=list,
        description="Explicitly denied MCP servers (takes precedence over allowed)",
    )
    skills_allowed: list[str] = Field(
        default_factory=list,
        description="Corporate skills this agent may invoke",
    )
    data_classification_max: str = Field(
        default="internal",
        description="Maximum data sensitivity level (public, internal, confidential, restricted)",
    )
    actions: dict[str, AccessDecision] = Field(
        default_factory=dict,
        description="Action patterns → decision. Supports wildcards (e.g. 'deploy.*': 'deny')",
    )
    budget: BudgetLimit | None = None

    def check_mcp(self, mcp_name: str) -> AccessDecision:
        """Check if an MCP server is allowed for this agent."""
        if mcp_name in self.mcps_denied:
            return AccessDecision.DENY
        if self.mcps_allowed and mcp_name not in self.mcps_allowed:
            return AccessDecision.DENY
        return AccessDecision.ALLOW

    def check_action(self, action: str) -> AccessDecision:
        """Check if an action is allowed. Supports glob matching on wildcards."""
        # Exact match first
        if action in self.actions:
            return self.actions[action]
        # Wildcard match (e.g. "deploy.*" matches "deploy.production")
        parts = action.split(".")
        for i in range(len(parts), 0, -1):
            pattern = ".".join(parts[:i]) + ".*"
            if pattern in self.actions:
                return self.actions[pattern]
        # Default: allow (governance applies to what's explicitly restricted)
        return AccessDecision.ALLOW


class AgentOwner(BaseModel):
    """Ownership information for an agent."""

    team: str
    contact: str
    business_unit: str | None = None


class AgentDeployment(BaseModel):
    """Deployment metadata."""

    environment: str = Field(description="Deployment environment (dev, staging, production)")
    region: str | None = None
    url: str | None = Field(default=None, description="Agent endpoint URL if applicable")


# --- Request / Response Models ---


class AgentCreate(BaseModel):
    """Request body for registering a new agent."""

    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
        description="Unique agent identifier (lowercase, kebab-case)",
    )
    name: str = Field(min_length=1, max_length=256, description="Human-readable name")
    description: str | None = None
    platform: str = Field(description="Agent platform (e.g. 'n8n', 'copilot-studio', 'claude-code')")
    owner: AgentOwner
    deployment: AgentDeployment | None = None
    access_profile: AccessProfile = Field(default_factory=AccessProfile)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Discovery / lineage
    source_system: str | None = Field(default=None, description="System that reported this agent")
    external_id: str | None = Field(default=None, description="ID in the source system")
    discovery_method: DiscoveryMethod = DiscoveryMethod.MANUAL


class AgentUpdate(BaseModel):
    """Request body for updating an agent registration."""

    name: str | None = None
    description: str | None = None
    platform: str | None = None
    owner: AgentOwner | None = None
    deployment: AgentDeployment | None = None
    access_profile: AccessProfile | None = None
    status: AgentStatus | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AgentRecord(BaseModel):
    """Full agent record as stored and returned by the API."""

    id: str
    name: str
    description: str | None = None
    platform: str
    owner: AgentOwner
    deployment: AgentDeployment | None = None
    access_profile: AccessProfile = Field(default_factory=AccessProfile)
    status: AgentStatus = AgentStatus.PENDING_APPROVAL
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Discovery / lineage
    source_system: str | None = None
    external_id: str | None = None
    discovery_method: DiscoveryMethod = DiscoveryMethod.MANUAL

    # Tenancy
    tenant_id: str = "default"

    # Auth — server-assigned token for this agent
    api_token: str | None = Field(default=None, description="Agent API token (shown once on creation)")

    # Timestamps
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRecordPublic(BaseModel):
    """Agent record for read endpoints — api_token is REDACTED.

    Token is only returned once on POST /registry/agents (creation).
    """

    id: str
    name: str
    description: str | None = None
    platform: str
    owner: AgentOwner
    deployment: AgentDeployment | None = None
    access_profile: AccessProfile = Field(default_factory=AccessProfile)
    status: AgentStatus = AgentStatus.PENDING_APPROVAL
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_system: str | None = None
    external_id: str | None = None
    discovery_method: DiscoveryMethod = DiscoveryMethod.MANUAL
    tenant_id: str = "default"
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_record(cls, record: AgentRecord) -> AgentRecordPublic:
        """Create a public record from a full record, stripping the token."""
        return cls.model_validate(record.model_dump(exclude={"api_token"}))


class AgentList(BaseModel):
    """Paginated list of agents (public — no tokens)."""

    items: list[AgentRecordPublic]
    total: int
    page: int
    page_size: int
    has_more: bool
