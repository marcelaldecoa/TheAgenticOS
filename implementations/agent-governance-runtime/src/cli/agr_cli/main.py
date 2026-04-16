"""AGR CLI — Command-line interface for the Agent Governance Runtime.

Commands:
  agr register   — Register an agent
  agr list       — List registered agents
  agr get        — Get agent details
  agr audit      — Query audit trail
  agr evaluate   — Evaluate an action against governance
  agr policy     — Manage policies
  agr health     — Check server health
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from agr_sdk import GovernanceClient

app = typer.Typer(
    name="agr",
    help="Agent Governance Runtime CLI — govern your agent fleet.",
    no_args_is_help=True,
)

console = Console()

_server_url_option = typer.Option(
    "http://localhost:8600",
    "--server", "-s",
    envvar="AGR_SERVER_URL",
    help="AGR server URL",
)

_token_option = typer.Option(
    None,
    "--token", "-t",
    envvar="AGR_AGENT_TOKEN",
    help="Agent API token (for authenticated operations)",
)


def _client(server_url: str, token: str | None = None) -> GovernanceClient:
    return GovernanceClient(server_url=server_url, token=token)


@app.command()
def register(
    agent_id: str = typer.Argument(help="Unique agent ID (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Human-readable name"),
    platform: str = typer.Option(..., "--platform", "-p", help="Agent platform"),
    owner_team: str = typer.Option(..., "--owner", "-o", help="Owner team name"),
    owner_contact: str = typer.Option(..., "--contact", "-c", help="Owner contact email"),
    environment: Optional[str] = typer.Option(None, "--env", "-e", help="Deployment environment"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    profile: Optional[Path] = typer.Option(None, "--profile", help="Access profile JSON file"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    server_url: str = _server_url_option,
) -> None:
    """Register a new agent in the governance registry."""
    gov = GovernanceClient(server_url=server_url, agent_id=agent_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    access_profile = None
    if profile and profile.exists():
        access_profile = json.loads(profile.read_text())

    try:
        record = gov.register(
            name=name,
            platform=platform,
            owner_team=owner_team,
            owner_contact=owner_contact,
            environment=environment,
            description=description,
            access_profile=access_profile,
            tags=tag_list,
        )
        rprint(f"[green]✓[/green] Agent [bold]{agent_id}[/bold] registered successfully")
        rprint(f"  Status:   {record['status']}")
        rprint(f"  Platform: {record['platform']}")
        token = record.get("api_token")
        if token:
            rprint(f"  Token:    [bold yellow]{token}[/bold yellow]")
            rprint("  [dim]⚠ Save this token — it won't be shown again![/dim]")
    except Exception as e:
        rprint(f"[red]✗[/red] Registration failed: {e}")
        raise typer.Exit(1)


@app.command(name="list")
def list_agents(
    platform: Optional[str] = typer.Option(None, "--platform", "-p"),
    status: Optional[str] = typer.Option(None, "--status"),
    search: Optional[str] = typer.Option(None, "--search", "-q"),
    server_url: str = _server_url_option,
) -> None:
    """List registered agents."""
    gov = _client(server_url)
    filters = {}
    if platform:
        filters["platform"] = platform
    if status:
        filters["status"] = status
    if search:
        filters["search"] = search

    try:
        result = gov.list_agents(**filters)
        items = result.get("items", [])

        if not items:
            rprint("[dim]No agents found.[/dim]")
            return

        table = Table(title=f"Agent Fleet ({result.get('total', 0)} agents)")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Platform", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Owner")

        for agent in items:
            status_style = {
                "active": "[green]active[/green]",
                "pending_approval": "[yellow]pending[/yellow]",
                "suspended": "[red]suspended[/red]",
                "deprecated": "[dim]deprecated[/dim]",
            }
            table.add_row(
                agent["id"],
                agent["name"],
                agent["platform"],
                status_style.get(agent["status"], agent["status"]),
                agent["owner"]["team"],
            )

        console.print(table)
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to list agents: {e}")
        raise typer.Exit(1)


@app.command()
def get(
    agent_id: str = typer.Argument(help="Agent ID"),
    server_url: str = _server_url_option,
) -> None:
    """Get details for a specific agent."""
    gov = _client(server_url)
    agent = gov.get_agent(agent_id)
    if agent is None:
        rprint(f"[red]✗[/red] Agent '{agent_id}' not found")
        raise typer.Exit(1)

    rprint(f"\n[bold]{agent['name']}[/bold] ({agent['id']})")
    rprint(f"  Platform:    {agent['platform']}")
    rprint(f"  Status:      {agent['status']}")
    rprint(f"  Owner:       {agent['owner']['team']} ({agent['owner']['contact']})")
    rprint(f"  Registered:  {agent['registered_at']}")
    if agent.get("tags"):
        rprint(f"  Tags:        {', '.join(agent['tags'])}")

    profile = agent.get("access_profile", {})
    if profile:
        rprint("\n  [bold]Access Profile:[/bold]")
        if profile.get("mcps_allowed"):
            rprint(f"    MCPs allowed: {', '.join(profile['mcps_allowed'])}")
        if profile.get("mcps_denied"):
            rprint(f"    MCPs denied:  {', '.join(profile['mcps_denied'])}")
        if profile.get("skills_allowed"):
            rprint(f"    Skills:       {', '.join(profile['skills_allowed'])}")
        rprint(f"    Data max:     {profile.get('data_classification_max', 'internal')}")
        actions = profile.get("actions", {})
        if actions:
            rprint("    Actions:")
            for act, decision in actions.items():
                icon = {"allow": "✅", "deny": "❌", "require_approval": "⏸️"}.get(decision, "?")
                rprint(f"      {icon} {act} → {decision}")
        budget = profile.get("budget")
        if budget:
            rprint("    Budget:")
            for k, v in budget.items():
                if v is not None:
                    rprint(f"      {k}: {v}")


@app.command()
def evaluate(
    action: str = typer.Argument(help="Action to evaluate (e.g. 'deploy.production')"),
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID"),
    server_url: str = _server_url_option,
    token: Optional[str] = _token_option,
) -> None:
    """Evaluate an action against governance policies."""
    gov = _client(server_url, token=token)
    if agent_id:
        gov.agent_id = agent_id

    try:
        result = gov.evaluate(action)
        decision = result["decision"]
        icons = {"allow": "✅", "deny": "❌", "require_approval": "⏸️"}
        rprint(f"\n{icons.get(decision, '?')} {action} → [bold]{decision}[/bold]")
        rprint(f"  Reason: {result['reason']}")
        if result.get("matched_rules"):
            rprint(f"  Matched policies: {len(result['matched_rules'])}")
            for rule in result["matched_rules"]:
                rprint(f"    - {rule['policy_name']} ({rule['matched_pattern']} → {rule['decision']})")
        if result.get("budget_status"):
            rprint(f"  Budget: {result['budget_status']}")
    except Exception as e:
        rprint(f"[red]✗[/red] Evaluation failed: {e}")
        raise typer.Exit(1)


@app.command()
def audit(
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent ID"),
    action: Optional[str] = typer.Option(None, "--action", help="Filter by action"),
    result: Optional[str] = typer.Option(None, "--result", "-r", help="Filter by result"),
    trace_id: Optional[str] = typer.Option(None, "--trace", help="Show full trace"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of records"),
    server_url: str = _server_url_option,
) -> None:
    """Query the audit trail."""
    gov = _client(server_url)
    try:
        if trace_id:
            resp = gov._client.get(f"/audit/traces/{trace_id}")
            resp.raise_for_status()
            records = resp.json()
            if not records:
                rprint(f"[dim]No records for trace '{trace_id}'[/dim]")
                return
            rprint(f"\n[bold]Trace:[/bold] {trace_id} ({len(records)} spans)\n")
            for r in records:
                icon = "✓" if r["result"] == "success" else "✗"
                color = "green" if r["result"] == "success" else "red"
                rprint(
                    f"  [{color}]{icon}[/{color}] "
                    f"[dim]{r['timestamp']}[/dim] "
                    f"[bold]{r['agent_id']}[/bold] → {r['action']} "
                    f"[{color}]{r['result']}[/{color}]"
                )
            return

        params: dict = {"page_size": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if action:
            params["action"] = action
        if result:
            params["result"] = result

        resp = gov._client.get("/audit/records", params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        if not items:
            rprint("[dim]No audit records found.[/dim]")
            return

        table = Table(title=f"Audit Trail ({data.get('total', 0)} records)")
        table.add_column("#", style="dim")
        table.add_column("Timestamp", style="dim")
        table.add_column("Agent", style="bold")
        table.add_column("Action", style="cyan")
        table.add_column("Result")
        table.add_column("Intent")

        for r in items:
            result_style = {
                "success": "[green]success[/green]",
                "failure": "[red]failure[/red]",
                "denied": "[yellow]denied[/yellow]",
                "error": "[red]error[/red]",
            }
            table.add_row(
                str(r["sequence"]),
                r["timestamp"][:19],
                r["agent_id"],
                r["action"],
                result_style.get(r["result"], r["result"]),
                r.get("intent") or "",
            )

        console.print(table)
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to query audit trail: {e}")
        raise typer.Exit(1)


@app.command()
def health(
    server_url: str = _server_url_option,
) -> None:
    """Check AGR server health."""
    gov = _client(server_url)
    try:
        h = gov.health()
        rprint(f"[green]✓[/green] AGR Server is [bold green]healthy[/bold green]")
        rprint(f"  Version:   {h['version']}")
        rprint(f"  Store:     {h['store']}")
        rprint(f"  Timestamp: {h['timestamp']}")
    except Exception as e:
        rprint(f"[red]✗[/red] Server unreachable: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
