"""AGR CLI — Command-line interface for the Agent Governance Runtime.

Commands:
  agr register   — Register an agent (interactive wizard if options omitted)
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
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from agr_sdk import GovernanceClient

app = typer.Typer(
    name="agr",
    help="Agent Governance Runtime CLI — govern your agent fleet.",
    no_args_is_help=True,
)

console = Console()

_KNOWN_PLATFORMS = [
    "copilot-studio", "github-copilot", "claude-code", "openai",
    "langchain", "semantic-kernel", "autogen", "n8n", "custom",
]

_KNOWN_ENVIRONMENTS = ["development", "staging", "production"]

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


def _wizard_register(server_url: str) -> None:
    """Interactive wizard for agent registration."""
    console.print(Panel(
        "[bold]Agent Registration Wizard[/bold]\n"
        "Answer the following questions to register a new agent.",
        style="cyan",
    ))

    # Agent ID
    agent_id = Prompt.ask(
        "[bold]Agent ID[/bold] [dim](lowercase, kebab-case)[/dim]",
    )

    # Name
    name = Prompt.ask("[bold]Display name[/bold]")

    # Platform
    platform_list = ", ".join(f"[cyan]{p}[/cyan]" for p in _KNOWN_PLATFORMS)
    console.print(f"  Known platforms: {platform_list}")
    platform = Prompt.ask(
        "[bold]Platform[/bold]",
        choices=_KNOWN_PLATFORMS,
        default="custom",
        show_choices=False,
    )

    # Owner
    owner_team = Prompt.ask("[bold]Owner team[/bold]")
    owner_contact = Prompt.ask("[bold]Owner contact email[/bold]")

    # Optional fields
    description = Prompt.ask("[bold]Description[/bold] [dim](optional, Enter to skip)[/dim]", default="")
    description = description or None

    env_list = ", ".join(f"[cyan]{e}[/cyan]" for e in _KNOWN_ENVIRONMENTS)
    console.print(f"  Environments: {env_list}")
    environment = Prompt.ask(
        "[bold]Environment[/bold] [dim](optional, Enter to skip)[/dim]",
        default="",
    )
    environment = environment or None

    tags_input = Prompt.ask(
        "[bold]Tags[/bold] [dim](comma-separated, optional)[/dim]",
        default="",
    )
    tag_list = [t.strip() for t in tags_input.split(",") if t.strip()] or None

    # Access profile wizard
    access_profile = None
    if Confirm.ask("\n[bold]Configure access profile?[/bold]", default=False):
        access_profile = _wizard_access_profile()

    # Confirmation
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ID:          {agent_id}")
    console.print(f"  Name:        {name}")
    console.print(f"  Platform:    {platform}")
    console.print(f"  Owner:       {owner_team} ({owner_contact})")
    if description:
        console.print(f"  Description: {description}")
    if environment:
        console.print(f"  Environment: {environment}")
    if tag_list:
        console.print(f"  Tags:        {', '.join(tag_list)}")
    if access_profile:
        console.print(f"  Profile:     {json.dumps(access_profile, indent=2)}")

    if not Confirm.ask("\n[bold]Register this agent?[/bold]", default=True):
        rprint("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    gov = GovernanceClient(server_url=server_url, agent_id=agent_id)
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
        rprint(f"\n[green]✓[/green] Agent [bold]{agent_id}[/bold] registered successfully")
        rprint(f"  Status:   {record['status']}")
        rprint(f"  Platform: {record['platform']}")
        token = record.get("api_token")
        if token:
            rprint(f"  Token:    [bold yellow]{token}[/bold yellow]")
            rprint("  [dim]⚠ Save this token — it won't be shown again![/dim]")
    except Exception as e:
        rprint(f"[red]✗[/red] Registration failed: {e}")
        raise typer.Exit(1)


def _wizard_access_profile() -> dict:
    """Interactive sub-wizard for access profile configuration."""
    profile: dict = {}

    # MCPs
    mcps_allowed = Prompt.ask(
        "  [bold]Allowed MCPs[/bold] [dim](comma-separated, Enter to skip)[/dim]",
        default="",
    )
    if mcps_allowed:
        profile["mcps_allowed"] = [m.strip() for m in mcps_allowed.split(",")]

    mcps_denied = Prompt.ask(
        "  [bold]Denied MCPs[/bold] [dim](comma-separated, Enter to skip)[/dim]",
        default="",
    )
    if mcps_denied:
        profile["mcps_denied"] = [m.strip() for m in mcps_denied.split(",")]

    # Skills
    skills = Prompt.ask(
        "  [bold]Allowed skills[/bold] [dim](comma-separated, Enter to skip)[/dim]",
        default="",
    )
    if skills:
        profile["skills_allowed"] = [s.strip() for s in skills.split(",")]

    # Data classification
    data_class = Prompt.ask(
        "  [bold]Max data classification[/bold]",
        choices=["public", "internal", "confidential", "restricted"],
        default="internal",
    )
    profile["data_classification_max"] = data_class

    # Action rules
    actions = {}
    if Confirm.ask("  [bold]Add action rules?[/bold]", default=False):
        while True:
            pattern = Prompt.ask("    [bold]Action pattern[/bold] [dim](e.g. deploy.*, email.send)[/dim]")
            decision = Prompt.ask(
                f"    [bold]Decision for '{pattern}'[/bold]",
                choices=["allow", "deny", "require_approval"],
            )
            actions[pattern] = decision
            if not Confirm.ask("    [dim]Add another rule?[/dim]", default=False):
                break
    if actions:
        profile["actions"] = actions

    # Budget
    if Confirm.ask("  [bold]Set budget limits?[/bold]", default=False):
        budget: dict = {}
        req = Prompt.ask("    [bold]Max requests/hour[/bold] [dim](Enter to skip)[/dim]", default="")
        if req:
            budget["max_requests_per_hour"] = int(req)
        tok = Prompt.ask("    [bold]Max tokens/hour[/bold] [dim](Enter to skip)[/dim]", default="")
        if tok:
            budget["max_tokens_per_hour"] = int(tok)
        cost = Prompt.ask("    [bold]Max cost/day (USD)[/bold] [dim](Enter to skip)[/dim]", default="")
        if cost:
            budget["max_cost_per_day_usd"] = float(cost)
        if budget:
            profile["budget"] = budget

    return profile


@app.command()
def register(
    agent_id: Optional[str] = typer.Argument(None, help="Unique agent ID (kebab-case). Omit to start wizard."),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Human-readable name"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Agent platform"),
    owner_team: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner team name"),
    owner_contact: Optional[str] = typer.Option(None, "--contact", "-c", help="Owner contact email"),
    environment: Optional[str] = typer.Option(None, "--env", "-e", help="Deployment environment"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    profile: Optional[Path] = typer.Option(None, "--profile", help="Access profile JSON file"),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Full agent registration JSON file"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    server_url: str = _server_url_option,
) -> None:
    """Register a new agent in the governance registry.

    Run without arguments to start an interactive wizard.
    Use --from to register from a full JSON registration file.
    Use --profile to attach an access profile JSON file.
    """
    # File-based registration
    if from_file:
        if not from_file.exists():
            rprint(f"[red]✗[/red] File not found: {from_file}")
            raise typer.Exit(1)
        gov = GovernanceClient(server_url=server_url)
        try:
            record = gov.register_from_file(from_file)
            rprint(f"[green]✓[/green] Agent [bold]{record['id']}[/bold] registered from {from_file}")
            rprint(f"  Status:   {record['status']}")
            rprint(f"  Platform: {record['platform']}")
            token = record.get("api_token")
            if token:
                rprint(f"  Token:    [bold yellow]{token}[/bold yellow]")
                rprint("  [dim]⚠ Save this token — it won't be shown again![/dim]")
        except Exception as e:
            rprint(f"[red]✗[/red] Registration failed: {e}")
            raise typer.Exit(1)
        return

    # If required fields are missing, launch the interactive wizard
    if not agent_id or not name or not platform or not owner_team or not owner_contact:
        _wizard_register(server_url)
        return

    gov = GovernanceClient(server_url=server_url, agent_id=agent_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    access_profile = None
    if profile and profile.exists():
        access_profile = GovernanceClient.load_profile(profile)

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


# --- Policy Management ---

policy_app = typer.Typer(
    name="policy",
    help="Manage governance policies.",
    no_args_is_help=True,
)
app.add_typer(policy_app, name="policy")


@policy_app.command(name="load")
def policy_load(
    file: Path = typer.Argument(help="Path to a policies JSON file"),
    server_url: str = _server_url_option,
) -> None:
    """Load policy rules from a JSON file.

    The file must conform to the policies.schema.json schema.
    """
    if not file.exists():
        rprint(f"[red]✗[/red] File not found: {file}")
        raise typer.Exit(1)

    gov = _client(server_url)
    try:
        created = gov.load_policies(file)
        rprint(f"[green]✓[/green] Loaded {len(created)} policy rules from {file}")
        for rule in created:
            decision_icon = {"allow": "✅", "deny": "❌", "require_approval": "⏸️"}.get(
                rule.get("decision", ""), "?"
            )
            rprint(f"  {decision_icon} {rule['name']} (priority: {rule.get('priority', 100)})")
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to load policies: {e}")
        raise typer.Exit(1)


@policy_app.command(name="list")
def policy_list(
    server_url: str = _server_url_option,
) -> None:
    """List all governance policy rules."""
    gov = _client(server_url)
    try:
        resp = gov._client.get("/policies/rules")
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        if not items:
            rprint("[dim]No policies found.[/dim]")
            return

        table = Table(title=f"Governance Policies ({data.get('total', 0)} rules)")
        table.add_column("Name", style="bold")
        table.add_column("Pattern", style="cyan")
        table.add_column("Decision")
        table.add_column("Priority", justify="right")
        table.add_column("Enabled")

        for rule in items:
            decision_style = {
                "allow": "[green]allow[/green]",
                "deny": "[red]deny[/red]",
                "require_approval": "[yellow]require_approval[/yellow]",
            }
            enabled = "[green]✓[/green]" if rule.get("enabled", True) else "[dim]✗[/dim]"
            pattern = rule.get("condition", {}).get("action_pattern", "?")
            table.add_row(
                rule["name"],
                pattern,
                decision_style.get(rule.get("decision", ""), rule.get("decision", "")),
                str(rule.get("priority", 100)),
                enabled,
            )

        console.print(table)
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to list policies: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
