"""Abstract store interface.

Deliberately thin — only the operations needed for each phase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agr_server.models.agent import AgentCreate, AgentList, AgentRecord, AgentUpdate
from agr_server.models.audit import AuditQuery, AuditRecord, AuditRecordCreate, AuditRecordList
from agr_server.models.policy import PolicyRule, PolicyRuleCreate, PolicyRuleList, PolicyRuleUpdate
from agr_server.models.budget import BudgetConsumeRequest, BudgetStatus


class Store(ABC):
    """Abstract storage backend for the Agent Governance Runtime."""

    # --- Lifecycle ---

    @abstractmethod
    async def initialize(self) -> None:
        """Create tables/indexes. Called once at server startup."""

    @abstractmethod
    async def close(self) -> None:
        """Release connections."""

    # --- Agent Registry ---

    @abstractmethod
    async def register_agent(self, agent: AgentCreate, tenant_id: str) -> AgentRecord:
        """Register a new agent. Raises ``ValueError`` if ID already exists."""

    @abstractmethod
    async def get_agent(self, agent_id: str, tenant_id: str) -> AgentRecord | None:
        """Get agent by ID, or ``None`` if not found."""

    @abstractmethod
    async def get_agent_by_token(self, token: str) -> AgentRecord | None:
        """Look up an agent by its API token. Used for auth resolve."""

    @abstractmethod
    async def update_agent(
        self, agent_id: str, update: AgentUpdate, tenant_id: str
    ) -> AgentRecord | None:
        """Update an existing agent. Returns updated record or ``None``."""

    @abstractmethod
    async def deprecate_agent(self, agent_id: str, tenant_id: str) -> bool:
        """Mark agent as deprecated. Returns ``True`` if found."""

    @abstractmethod
    async def list_agents(
        self,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        platform: str | None = None,
        status: str | None = None,
        owner_team: str | None = None,
        search: str | None = None,
    ) -> AgentList:
        """List agents with pagination and filtering."""

    # --- Audit Trail (append-only) ---

    @abstractmethod
    async def append_audit_record(
        self, record: AuditRecordCreate, tenant_id: str
    ) -> AuditRecord:
        """Append an audit record. Server assigns sequence and timestamp."""

    @abstractmethod
    async def query_audit_records(
        self, query: AuditQuery, tenant_id: str
    ) -> AuditRecordList:
        """Query audit records with filtering and pagination."""

    @abstractmethod
    async def get_agent_audit_trail(
        self,
        agent_id: str,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditRecordList:
        """Get audit trail for a specific agent."""

    @abstractmethod
    async def get_trace(self, trace_id: str, tenant_id: str) -> list[AuditRecord]:
        """Reconstruct a full trace by trace_id."""

    # --- Policy Engine ---

    @abstractmethod
    async def create_policy(self, rule: PolicyRuleCreate, tenant_id: str) -> PolicyRule:
        """Create a new policy rule."""

    @abstractmethod
    async def get_policy(self, policy_id: str, tenant_id: str) -> PolicyRule | None:
        """Get a policy rule by ID."""

    @abstractmethod
    async def update_policy(
        self, policy_id: str, update: PolicyRuleUpdate, tenant_id: str
    ) -> PolicyRule | None:
        """Update a policy rule (enable/disable, metadata)."""

    @abstractmethod
    async def list_policies(
        self,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        enabled_only: bool = False,
    ) -> PolicyRuleList:
        """List policy rules."""

    @abstractmethod
    async def get_enabled_policies(self, tenant_id: str) -> list[PolicyRule]:
        """Get all enabled policies for evaluation."""

    # --- Budget Tracking ---

    @abstractmethod
    async def record_consumption(
        self, request: BudgetConsumeRequest, tenant_id: str
    ) -> None:
        """Record resource consumption for an agent."""

    @abstractmethod
    async def get_budget_status(
        self, agent_id: str, tenant_id: str
    ) -> BudgetStatus:
        """Get current budget status for an agent."""
