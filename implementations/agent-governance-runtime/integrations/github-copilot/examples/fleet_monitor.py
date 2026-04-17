"""Example: Fleet monitoring dashboard for GitHub Copilot agents.

This script queries the AGR server to display:
  - All registered agents with status
  - Budget status per agent
  - Recent violations (denied actions)
  - Fleet-wide statistics

Prerequisites:
  - AGR server running: agr-server
  - Agents registered
"""

from __future__ import annotations

import os

from agr_sdk import GovernanceClient


def main() -> None:
    gov = GovernanceClient(
        server_url=os.environ.get("AGR_SERVER_URL", "http://localhost:8600"),
    )

    # 1. Health check
    health = gov.health()
    print(f"🏥 AGR Server: {health['status']} (v{health['version']})")
    print(f"   Store: {health['store']}")
    print()

    # 2. Fleet overview
    fleet = gov.list_agents()
    print(f"📋 Fleet: {fleet['total']} agents registered\n")

    status_icons = {
        "active": "🟢",
        "pending_approval": "🟡",
        "suspended": "🔴",
        "deprecated": "⚪",
    }

    copilot_agents = []
    for agent in fleet["items"]:
        icon = status_icons.get(agent["status"], "❓")
        print(f"  {icon} {agent['id']:<35} {agent['platform']:<20} {agent['status']}")
        if agent["platform"] == "github-copilot":
            copilot_agents.append(agent)

    # 3. Copilot-specific summary
    if copilot_agents:
        print(f"\n🤖 GitHub Copilot Agents: {len(copilot_agents)}")
        for agent in copilot_agents:
            profile = agent.get("access_profile", {})
            mcps = len(profile.get("mcps_allowed", []))
            skills = len(profile.get("skills_allowed", []))
            actions = len(profile.get("actions", {}))
            print(f"  {agent['id']}")
            print(f"    MCPs: {mcps} allowed | Skills: {skills} | Action rules: {actions}")

    # 4. Budget status
    print("\n💰 Budget Status")
    for agent in fleet["items"]:
        if agent["status"] != "active":
            continue
        try:
            agent_gov = GovernanceClient(
                server_url=os.environ.get("AGR_SERVER_URL", "http://localhost:8600"),
                agent_id=agent["id"],
            )
            budget = agent_gov.get_budget()
            status_icon = {"ok": "✅", "warning": "⚠️", "exceeded": "🚨"}.get(
                budget["status"], "❓"
            )
            print(f"  {status_icon} {agent['id']}: {budget['status']}")
            for warning in budget.get("warnings", []):
                print(f"     ⚠ {warning}")
        except Exception:
            print(f"  ❓ {agent['id']}: unable to fetch budget")

    # 5. Recent violations
    print("\n🚫 Recent Violations (last 10)")
    try:
        resp = gov._client.get("/audit/records", params={
            "result": "denied",
            "page_size": 10,
        })
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            print("  No violations found ✅")
        else:
            for record in items:
                print(
                    f"  {record['timestamp'][:19]}  "
                    f"{record['agent_id']:<25} "
                    f"{record['action']:<30} "
                    f"denied"
                )
    except Exception as e:
        print(f"  Error fetching violations: {e}")

    # 6. Dashboard stats
    print("\n📊 Dashboard")
    try:
        resp = gov._client.get("/dashboard/summary")
        resp.raise_for_status()
        summary = resp.json()
        print(f"  Total agents:    {summary.get('total_agents', 'N/A')}")
        print(f"  Active agents:   {summary.get('active_agents', 'N/A')}")
        print(f"  Pending agents:  {summary.get('pending_agents', 'N/A')}")
        print(f"  Total policies:  {summary.get('total_policies', 'N/A')}")
        print(f"  Audit records:   {summary.get('total_audit_records', 'N/A')}")
    except Exception:
        print("  Dashboard endpoint not available")


if __name__ == "__main__":
    main()
