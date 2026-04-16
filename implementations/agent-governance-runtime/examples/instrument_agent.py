"""Example: Instrumenting a custom agent with AGR SDK.

This example shows how to:
1. Register your agent with an access profile
2. Evaluate actions before executing them
3. Use the context manager for automatic audit logging
4. Report resource consumption
5. Check budget status

Prerequisites:
  - AGR server running: cd src/server && pip install -e ".[dev]" && agr-server
  - SDK installed: cd src/sdk && pip install -e .
"""

from agr_sdk import GovernanceClient


def main() -> None:
    # 1. Register the agent with an access profile
    gov = GovernanceClient(
        server_url="http://localhost:8600",
        agent_id="demo-support-agent",
    )

    try:
        record = gov.register(
            name="Demo Support Agent",
            platform="custom",
            owner_team="support-engineering",
            owner_contact="support-eng@company.com",
            environment="development",
            description="Customer support agent that answers questions and files tickets",
            access_profile={
                "mcps_allowed": ["knowledge-base-mcp", "ticketing-mcp"],
                "mcps_denied": ["production-db"],
                "skills_allowed": ["search-docs", "create-ticket"],
                "data_classification_max": "confidential",
                "actions": {
                    "knowledge.search": "allow",
                    "ticket.create": "allow",
                    "ticket.update": "allow",
                    "email.send": "require_approval",
                    "deploy.*": "deny",
                },
                "budget": {
                    "max_requests_per_hour": 100,
                    "max_tokens_per_hour": 50000,
                    "max_cost_per_day_usd": 5.00,
                },
            },
            tags=["support", "customer-facing", "demo"],
        )
        token = record["api_token"]
        print(f"✓ Agent registered (token: {token[:20]}...)")
    except Exception as e:
        if "409" in str(e):
            print("· Agent already registered")
            token = None
        else:
            raise

    # 2. Switch to token-based auth for all subsequent calls
    if token:
        gov = GovernanceClient(
            server_url="http://localhost:8600",
            agent_id="demo-support-agent",
            token=token,
        )

    # 3. Evaluate action before executing
    decision = gov.evaluate("knowledge.search")
    print(f"· knowledge.search → {decision['decision']}")

    decision = gov.evaluate("deploy.production")
    print(f"· deploy.production → {decision['decision']} ({decision['reason']})")

    decision = gov.evaluate("email.send")
    print(f"· email.send → {decision['decision']}")

    # 4. Context manager — automatically logs success/failure
    with gov.action("ticket.create", intent="Create ticket for unresolved question") as act:
        ticket_id = "TICKET-42"
        act.set_metadata(ticket_id=ticket_id)
        act.set_result("success", detail=f"Created {ticket_id}")
    print("✓ Audit record logged (context manager)")

    # 5. Report resource consumption
    gov.report_consumption(
        requests=1,
        tokens_input=500,
        tokens_output=200,
        cost_usd=0.003,
        action="knowledge.search",
    )
    print("✓ Consumption reported")

    # 6. Check budget status
    budget = gov.get_budget()
    print(f"· Budget status: {budget['status']}")
    if budget.get("warnings"):
        for w in budget["warnings"]:
            print(f"  ⚠ {w}")

    # 7. List all agents in the fleet
    fleet = gov.list_agents()
    print(f"\n📋 Agent Fleet: {fleet['total']} agents registered")
    for agent in fleet["items"]:
        print(f"   {agent['id']} ({agent['platform']}) — {agent['status']}")

    # 8. Health check
    health = gov.health()
    print(f"\n💚 Server: {health['status']} (v{health['version']})")


if __name__ == "__main__":
    main()
