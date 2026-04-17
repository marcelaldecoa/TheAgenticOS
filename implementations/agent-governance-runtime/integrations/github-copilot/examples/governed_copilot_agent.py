"""Example: GitHub Copilot agent extension governed by AGR.

This example shows how a Copilot chat participant (agent) integrates with
AGR governance. Every action the agent takes is:
  1. Evaluated against governance policies
  2. Checked for MCP access
  3. Audited with timing and metadata
  4. Tracked for budget consumption

Prerequisites:
  - AGR server running: agr-server
  - Agent registered: agr register copilot-code-reviewer --profile profiles/code-reviewer.profile.json ...
  - Token saved in AGR_AGENT_TOKEN env var
"""

from __future__ import annotations

import os

from agr_sdk import GovernanceClient


def create_governed_client() -> GovernanceClient:
    """Create an AGR client from environment variables."""
    return GovernanceClient(
        server_url=os.environ.get("AGR_SERVER_URL", "http://localhost:8600"),
        agent_id="copilot-code-reviewer",
        token=os.environ.get("AGR_AGENT_TOKEN"),
    )


def handle_code_review(gov: GovernanceClient, repo: str, file_path: str) -> str:
    """Handle a code review request with full governance."""

    # 1. Evaluate the action
    decision = gov.evaluate("code.review", context={"repo": repo, "file": file_path})
    if decision["decision"] == "deny":
        return f"⛔ Code review denied: {decision['reason']}"
    if decision["decision"] == "require_approval":
        return f"⏸️ Code review requires approval: {decision['reason']}"

    # 2. Check MCP access (we need github-mcp to read the file)
    mcp_check = gov.check_mcp("github-mcp")
    if mcp_check["decision"] != "allow":
        return f"⛔ Cannot access GitHub MCP: {mcp_check['reason']}"

    # 3. Perform the action with automatic audit logging
    with gov.action("code.review", intent=f"Review {repo}/{file_path}") as act:
        # --- Your actual code review logic here ---
        issues = [
            {"line": 42, "severity": "warning", "message": "Unused import"},
            {"line": 87, "severity": "error", "message": "SQL injection risk"},
        ]
        # -------------------------------------------
        act.set_metadata(
            repo=repo,
            file=file_path,
            issues_found=len(issues),
            severities={"error": 1, "warning": 1},
        )
        act.set_result("success", detail=f"Found {len(issues)} issues")

    # 4. Report token consumption
    gov.report_consumption(
        requests=1,
        tokens_input=2000,
        tokens_output=800,
        cost_usd=0.01,
        action="code.review",
    )

    return f"✅ Review complete: {len(issues)} issues found"


def handle_code_commit(gov: GovernanceClient, repo: str, branch: str, message: str) -> str:
    """Handle a code commit request — requires approval per profile."""

    decision = gov.evaluate(
        "code.commit",
        context={"repo": repo, "branch": branch, "message": message},
    )

    if decision["decision"] == "deny":
        return f"⛔ Commit denied: {decision['reason']}"
    if decision["decision"] == "require_approval":
        return (
            f"⏸️ Commit requires approval.\n"
            f"  Reason: {decision['reason']}\n"
            f"  Request approval via: agr approve request --action code.commit"
        )

    with gov.action("code.commit", intent=f"Commit to {repo}/{branch}") as act:
        # --- Your actual commit logic here ---
        commit_sha = "abc1234"
        # -------------------------------------
        act.set_metadata(repo=repo, branch=branch, commit=commit_sha)
        act.set_result("success")

    return f"✅ Committed: {commit_sha}"


def main() -> None:
    gov = create_governed_client()

    # Verify connectivity
    health = gov.health()
    print(f"AGR Server: {health['status']} (v{health['version']})")

    # Simulate Copilot interactions
    print("\n--- Code Review (allowed) ---")
    result = handle_code_review(gov, "acme/backend", "src/api/users.py")
    print(result)

    print("\n--- Code Commit (requires approval) ---")
    result = handle_code_commit(gov, "acme/backend", "main", "Fix user API")
    print(result)

    print("\n--- Deploy (denied) ---")
    decision = gov.evaluate("deploy.production")
    print(f"deploy.production → {decision['decision']} ({decision['reason']})")

    print("\n--- Budget ---")
    budget = gov.get_budget()
    print(f"Status: {budget['status']}")
    for w in budget.get("warnings", []):
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
