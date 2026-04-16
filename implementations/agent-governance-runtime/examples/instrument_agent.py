"""Example: Instrumenting a custom agent with AGR SDK.

This example shows how to:
1. Register your agent at startup
2. Log audit records for every action
3. Use the context manager for automatic audit logging
4. Check capabilities before taking actions

Prerequisites:
  - AGR server running: cd src/server && pip install -e . && agr-server
  - SDK installed: cd src/sdk && pip install -e .
"""

from agr_sdk import GovernanceClient


def main() -> None:
    # Connect to AGR
    gov = GovernanceClient(
        server_url="http://localhost:8600",
        agent_id="demo-support-agent",
    )

    # 1. Register the agent (idempotent — safe to call on every startup)
    try:
        gov.register(
            name="Demo Support Agent",
            platform="custom",
            archetype="advisor",
            owner_team="support-engineering",
            owner_contact="support-eng@company.com",
            environment="development",
            description="Customer support agent that answers questions and files tickets",
            capabilities=[
                {"resource": "knowledge-base", "actions": ["read", "search"]},
                {"resource": "ticket", "actions": ["create", "update"]},
                {"resource": "email", "actions": ["send"]},
            ],
            tags=["support", "customer-facing", "demo"],
        )
        print("✓ Agent registered")
    except Exception as e:
        if "409" in str(e):
            print("· Agent already registered")
        else:
            raise

    # 2. Simple audit logging
    gov.audit_log(
        action="knowledge-base.search",
        result="success",
        intent="Find answer to customer question about billing",
        cost={"tokens_input": 500, "tokens_output": 200, "duration_ms": 1200},
    )
    print("✓ Audit record logged (manual)")

    # 3. Context manager — automatically logs success/failure
    with gov.action("ticket.create", intent="Create ticket for unresolved question") as act:
        # Simulate creating a ticket
        ticket_id = "TICKET-42"
        act.set_metadata(ticket_id=ticket_id)
        act.set_result("success", detail=f"Created {ticket_id}")
    print("✓ Audit record logged (context manager)")

    # 4. Capability check (Phase 1: checks granted capabilities)
    decision = gov.check_capability("email", "send")
    if decision.granted:
        print("✓ Capability 'email.send' granted")
    else:
        print(f"· Capability 'email.send' not yet granted: {decision.reason}")
        gov.audit_log(
            action="email.send",
            result="denied",
            intent="Send resolution email to customer",
            detail=decision.reason,
            severity="warning",
        )

    # 5. List all agents in the fleet
    fleet = gov.list_agents()
    print(f"\n📋 Agent Fleet: {fleet['total']} agents registered")
    for agent in fleet["items"]:
        print(f"   {agent['id']} ({agent['platform']}) — {agent['status']}")

    # 6. Health check
    health = gov.health()
    print(f"\n💚 Server: {health['status']} (v{health['version']})")


if __name__ == "__main__":
    main()
