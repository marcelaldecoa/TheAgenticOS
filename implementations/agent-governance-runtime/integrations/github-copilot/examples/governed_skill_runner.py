"""Example: Governed skill invocation for GitHub Copilot extensions.

Skills are specialized capabilities (e.g. code-generation, test-generation).
This example shows how to gate skill invocations through AGR governance:
  1. Check if the skill is in the agent's allowed list
  2. Evaluate action-level policy for the skill
  3. Execute with audit trail
  4. Track consumption

Prerequisites:
  - AGR server running: agr-server
  - Agent registered with skills_allowed in the access profile
  - Token saved in AGR_AGENT_TOKEN env var
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agr_sdk import GovernanceClient


@dataclass
class SkillResult:
    """Result of a governed skill invocation."""

    allowed: bool
    decision: str
    reason: str
    output: Any = None


class GovernedSkillRunner:
    """Runs Copilot skills with AGR governance checks.

    Usage::

        runner = GovernedSkillRunner(gov_client)

        result = runner.invoke("code-generation", {
            "language": "python",
            "description": "REST API for user profiles",
        })

        if result.allowed:
            print(result.output)
    """

    def __init__(self, gov: GovernanceClient) -> None:
        self._gov = gov
        self._agent: dict | None = None

    def _get_allowed_skills(self) -> list[str]:
        """Fetch the agent's allowed skills from the access profile."""
        if self._agent is None:
            self._agent = self._gov.get_agent() or {}
        return self._agent.get("access_profile", {}).get("skills_allowed", [])

    def invoke(
        self,
        skill_name: str,
        context: dict[str, Any] | None = None,
        *,
        intent: str | None = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> SkillResult:
        """Invoke a skill with full governance checks."""
        context = context or {}
        intent = intent or f"Run skill: {skill_name}"

        # Step 1: Check skill allow-list
        allowed_skills = self._get_allowed_skills()
        if allowed_skills and skill_name not in allowed_skills:
            self._gov.audit_log(
                action=f"skill.{skill_name}",
                result="denied",
                intent=intent,
                detail=f"Skill '{skill_name}' not in allowed list",
                severity="warning",
            )
            return SkillResult(
                allowed=False,
                decision="deny",
                reason=f"Skill '{skill_name}' is not in the agent's allowed skills: {allowed_skills}",
            )

        # Step 2: Evaluate action-level policy
        action = f"skill.{skill_name}"
        decision = self._gov.evaluate(action, context=context)
        if decision["decision"] == "deny":
            return SkillResult(
                allowed=False,
                decision="deny",
                reason=decision["reason"],
            )
        if decision["decision"] == "require_approval":
            return SkillResult(
                allowed=False,
                decision="require_approval",
                reason=decision["reason"],
            )

        # Step 3: Execute with audit trail
        with self._gov.action(action, intent=intent) as act:
            # --- Replace with actual skill execution ---
            output = self._simulate_skill(skill_name, context)
            # -------------------------------------------
            act.set_metadata(skill=skill_name, **context)
            act.set_result("success")

        # Step 4: Track consumption
        self._gov.report_consumption(
            requests=1,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            action=action,
        )

        return SkillResult(
            allowed=True,
            decision="allow",
            reason="Allowed by policy",
            output=output,
        )

    @staticmethod
    def _simulate_skill(skill_name: str, context: dict) -> dict:
        """Simulate skill execution (replace with real implementation)."""
        return {
            "skill": skill_name,
            "status": "completed",
            "simulated": True,
        }


def main() -> None:
    gov = GovernanceClient(
        server_url=os.environ.get("AGR_SERVER_URL", "http://localhost:8600"),
        agent_id="copilot-full-stack",
        token=os.environ.get("AGR_AGENT_TOKEN"),
    )

    runner = GovernedSkillRunner(gov)

    # Allowed skill
    print("--- code-generation (allowed) ---")
    result = runner.invoke(
        "code-generation",
        {"language": "python", "description": "REST API endpoint"},
        tokens_input=500,
        tokens_output=1200,
    )
    print(f"  Decision: {result.decision}")
    if result.allowed:
        print(f"  Output: {result.output}")

    # Allowed skill
    print("\n--- test-generation (allowed) ---")
    result = runner.invoke(
        "test-generation",
        {"language": "python", "target": "src/api/users.py"},
        tokens_input=800,
        tokens_output=2000,
    )
    print(f"  Decision: {result.decision}")

    # Requires approval
    print("\n--- database-migration (requires approval) ---")
    result = runner.invoke(
        "database-migration",
        {"migration": "add_user_roles_table"},
    )
    print(f"  Decision: {result.decision}")
    print(f"  Reason: {result.reason}")

    # Not in allowed list
    print("\n--- infrastructure-change (not allowed) ---")
    result = runner.invoke(
        "infrastructure-change",
        {"action": "resize-cluster"},
    )
    print(f"  Decision: {result.decision}")
    print(f"  Reason: {result.reason}")


if __name__ == "__main__":
    main()
