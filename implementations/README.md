# Agentic OS — Reference Implementations

Each folder is a self-contained workspace implementing one of the case studies from Part VI of the book. Copy the `.github/` folder into any project to activate agents, skills, and instructions with GitHub Copilot.

> **Start here**: See [`coding-os/TUTORIAL.md`](coding-os/TUTORIAL.md) for a hands-on walkthrough with a real To-Do API project.
>
> Each implementation has its own tutorial:
> [`coding-os`](coding-os/TUTORIAL.md) ·
> [`research-os`](research-os/TUTORIAL.md) ·
> [`support-os`](support-os/TUTORIAL.md) ·
> [`knowledge-os`](knowledge-os/TUTORIAL.md) ·
> [`multi-os`](multi-os/TUTORIAL.md)

## Quick Start

1. **Copy** any implementation's `.github/` folder into your project root
2. **Open** the project in VS Code with GitHub Copilot
3. **Chat** — `copilot-instructions.md` loads automatically
4. **Invoke agents** — `@coder`, `@scout`, `@triage`, etc.
5. **Use skills** — type `/` to see available skills: `/fix-bug`, `/competitive-analysis`, etc.

## Implementations

### [`coding-os/`](coding-os/)

A Coding OS for software development — agents for coding, testing, and reviewing.

| Component | Items |
|-----------|-------|
| **Agents** | `@coder` (implementation), `@tester` (tests), `@reviewer` (read-only quality review) |
| **Skills** | `/fix-bug` (reproduce → diagnose → fix → verify), `/new-feature` (plan → implement → test → review), `/code-review` (structured quality assessment) |
| **Instructions** | Python standards (`**/*.py`), Testing standards (`**/test_*.py`) |
| **MCP** | `filesystem` (scoped file access), `git` (version control) |
| **References** | Bug report template, feature spec template, review checklist |

### [`research-os/`](research-os/)

A Research OS for conducting rigorous research — agents for scouting, analysis, synthesis, and critique.

| Component | Items |
|-----------|-------|
| **Agents** | `@scout` (broad search), `@analyst` (deep source evaluation), `@synthesizer` (combine findings), `@critic` (adversarial review) |
| **Skills** | `/competitive-analysis` (market comparison), `/literature-review` (academic survey) |
| **Instructions** | Research output standards (citations, confidence calibration) |
| **MCP** | `web-research` (Tavily search + page extraction) |
| **References** | Competitive analysis report template |

### [`support-os/`](support-os/)

A Support OS for customer support — agents for triage, resolution, investigation, and communication.

| Component | Items |
|-----------|-------|
| **Agents** | `@triage` (classify & route), `@resolver` (apply known fixes), `@investigator` (diagnose unknowns), `@communicator` (customer responses) |
| **Skills** | `/triage-and-resolve` (end-to-end ticket handling), `/escalation` (human handoff) |
| **Instructions** | Data governance (PII rules) via copilot-instructions |
| **MCP** | `support-tools` (customer context, logs, cache ops), `knowledge-base` (known issues) |
| **References** | Escalation package template |

### [`knowledge-os/`](knowledge-os/)

A Knowledge OS for organizational knowledge management — agents for harvesting, curation, validation, and retrieval.

| Component | Items |
|-----------|-------|
| **Agents** | `@harvester` (extract from raw content), `@curator` (organize & link), `@validator` (check freshness), `@retriever` (answer questions) |
| **Skills** | `/harvest-knowledge` (capture workflow), `/validate-freshness` (maintenance sweep) |
| **Instructions** | Classification, provenance via copilot-instructions |
| **MCP** | `knowledge-store` (PostgreSQL + pgvector knowledge graph) |

### [`multi-os/`](multi-os/)

Multi-OS federation — a coordinator that routes work across independent OSs.

| Component | Items |
|-----------|-------|
| **Agents** | `@coordinator` (cross-OS orchestration), plus 4 delegates: `@coding-delegate`, `@research-delegate`, `@support-delegate`, `@knowledge-delegate` |
| **Instructions** | Federation governance (data classification, PII redaction, correlation IDs, audit trails) |
| **MCP** | `federation-bus` (cross-OS message routing) |

## Architecture Mapping

| Agentic OS Layer | VS Code Copilot Primitive | Example |
|---|---|---|
| Cognitive Kernel | `copilot-instructions.md` | Workflow patterns, delegation rules |
| Workers / Subagents | `.agent.md` with scoped `tools:` | `@coder` has `[read, edit, search, execute]`, `@reviewer` has `[read, search]` |
| Skills / Strategies | `SKILL.md` with `## Procedure` | `/fix-bug`: Reproduce → Diagnose → Fix → Verify → Document |
| Tool Layer / Operators | MCP servers (`.vscode/mcp.json`) | `filesystem`, `git`, `web-research`, `support-tools` |
| Governance | Agent tool restrictions + instructions | Reviewer can't `edit`. Data classification in instructions. |
| Memory | MCP-backed storage | `knowledge-store` (pgvector), `knowledge-base` (vector search) |
| Skill Resources | `references/` folders in skills | Templates, checklists loaded on demand |

---

## Agent Governance Runtime (AGR)

### [`agent-governance-runtime/`](agent-governance-runtime/)

**A DAPR-like governance runtime for AI agents across heterogeneous platforms.**

> *"You don't need to standardize on one agent platform. You need to standardize on one governance plane."*

### The Problem

The case studies above show how to build effective agents. But enterprises face a harder question: **how do you govern dozens or hundreds of agents across different platforms?**

Today, organizations have "shadow agents" — AI agents built on N8N, GPT, Claude, Gemini, Copilot Studio, and custom code — with no central visibility, no audit trail, and no capability governance. CIOs and CISOs cannot answer basic questions:

- How many agents operate in our organization?
- Which agents have write access to production systems?
- What data flows through which agents?
- Who approved this agent's capabilities?
- What is the total cost of our agent fleet?

### The Insight: DAPR as Precedent

DAPR succeeded by providing infrastructure building blocks **alongside** microservices — without replacing them. AGR applies the same pattern to agents: govern the boundaries without owning the runtime.

| DAPR | AGR |
|------|-----|
| Sidecar alongside your microservice | MCP server / SDK alongside your agent |
| Building blocks (state, pub/sub) | Building blocks (registry, audit, policy, budget, approvals) |
| Pluggable components (Redis, Cosmos) | Pluggable backends (SQLite, PostgreSQL, Cosmos) |
| Control plane (Kubernetes) | Governance plane (fleet management) |

### Relationship to the Book

AGR is the **runtime implementation** of concepts defined in The Agentic OS:

| Book Chapter | AGR Component |
|-------------|---------------|
| [Ch. 12 — Governance Plane](../src/part-2-the-agentic-os-model/12-governance-plane.md) | The entire runtime — this IS the governance plane made real |
| [Ch. 17 — Governance Patterns](../src/part-3-design-patterns/17-governance-patterns.md) | Access profiles, policy engine, approval flows |
| Ch. 17 — Permission Gate pattern | `/governance/evaluate` — single authoritative decision point |
| Ch. 17 — Auditable Action pattern | Append-only audit trail with trace reconstruction |
| Ch. 17 — Risk-Tiered Execution | `allow` / `deny` / `require_approval` decisions |
| Ch. 17 — Human Escalation pattern | Approval flows with operator RBAC |
| [Ch. 25 — Reference Architecture](../src/part-5-building-the-system/25-reference-architecture.md) | Budget tracking + enforcement |
| [Appendix B — Governance Standards](../src/appendices/b-landscape-and-standards.md) | Compliance export with evidence completeness |

While the case studies (Coding OS, Research OS, etc.) demonstrate how agents work **within** a single system, AGR answers the enterprise question: how do you govern agents **across** all systems.

### What It Includes

| Building Block | Description |
|---------------|-------------|
| **Agent Registry** | Central catalog with access profiles (MCPs, skills, actions, data classification) |
| **Policy Engine** | Declarative tenant-wide rules with precedence (`deny > require_approval > allow`) |
| **Unified Evaluation** | `POST /governance/evaluate` — status + profile + policy + budget → one decision |
| **Audit Trail** | Append-only action logging with distributed trace reconstruction |
| **Budget Tracking** | Per-agent consumption limits (request hard-enforce, cost soft-enforce) |
| **Approval Flows** | Human-in-the-loop with operator RBAC, idempotent one-time-use approvals |
| **Fleet Dashboard** | Summary, top consumers, violations, approval stats |
| **Compliance Export** | JSON evidence report with schema versioning and gap detection |
| **MCP Server** | Governance as MCP — works natively with Claude Code, Copilot, any MCP agent |

### Platform Integrations

| Platform | Method |
|----------|--------|
| **Claude Code** | MCP server + governance skill + instructions |
| **N8N** | HTTP Request nodes → AGR REST API |
| **Custom Python** | SDK (`GovernanceClient` with token auth) |
| **Any HTTP client** | REST API (OpenAPI at `/docs`) |

### Getting Started

```bash
cd implementations/agent-governance-runtime
cd src/server && pip install -e ".[dev]" && agr-server
# → API at http://localhost:8600, Swagger at /docs
```

See the full [AGR README](agent-governance-runtime/README.md) for quick start, API reference, and integration guides.

---

## File Inventory

```
implementations/
├── README.md                          # This file
├── coding-os/
│   ├── TUTORIAL.md                    # Step-by-step walkthrough
│   ├── .github/
│   │   ├── copilot-instructions.md
│   │   ├── agents/
│   │   │   ├── coder.agent.md
│   │   │   ├── tester.agent.md
│   │   │   └── reviewer.agent.md
│   │   ├── instructions/
│   │   │   ├── python-standards.instructions.md
│   │   │   └── testing-standards.instructions.md
│   │   └── skills/
│   │       ├── fix-bug/
│   │       │   ├── SKILL.md
│   │       │   └── references/bug-report-template.md
│   │       ├── new-feature/
│   │       │   ├── SKILL.md
│   │       │   └── references/feature-spec-template.md
│   │       └── code-review/
│   │           ├── SKILL.md
│   │           └── references/review-checklist.md
│   └── .vscode/mcp.json
├── research-os/
│   ├── .github/
│   │   ├── copilot-instructions.md
│   │   ├── agents/
│   │   │   ├── scout.agent.md
│   │   │   ├── analyst.agent.md
│   │   │   ├── synthesizer.agent.md
│   │   │   └── critic.agent.md
│   │   ├── instructions/
│   │   │   └── research-standards.instructions.md
│   │   └── skills/
│   │       ├── competitive-analysis/
│   │       │   ├── SKILL.md
│   │       │   └── references/report-template.md
│   │       └── literature-review/
│   │           └── SKILL.md
│   └── .vscode/mcp.json
├── support-os/
│   ├── .github/
│   │   ├── copilot-instructions.md
│   │   ├── agents/
│   │   │   ├── triage.agent.md
│   │   │   ├── resolver.agent.md
│   │   │   ├── investigator.agent.md
│   │   │   └── communicator.agent.md
│   │   └── skills/
│   │       ├── triage-and-resolve/
│   │       │   └── SKILL.md
│   │       └── escalation/
│   │           ├── SKILL.md
│   │           └── references/escalation-template.md
│   └── .vscode/mcp.json
├── knowledge-os/
│   ├── .github/
│   │   ├── copilot-instructions.md
│   │   ├── agents/
│   │   │   ├── harvester.agent.md
│   │   │   ├── curator.agent.md
│   │   │   ├── validator.agent.md
│   │   │   └── retriever.agent.md
│   │   └── skills/
│   │       ├── harvest-knowledge/
│   │       │   └── SKILL.md
│   │       └── validate-freshness/
│   │           └── SKILL.md
│   └── .vscode/mcp.json
└── multi-os/
    ├── .github/
    │   ├── copilot-instructions.md
    │   ├── agents/
    │   │   ├── coordinator.agent.md
    │   │   ├── coding-delegate.agent.md
    │   │   ├── research-delegate.agent.md
    │   │   ├── support-delegate.agent.md
    │   │   └── knowledge-delegate.agent.md
    │   └── instructions/
    │       └── federation-governance.instructions.md
    └── .vscode/mcp.json
├── agent-governance-runtime/      # AGR — Governance runtime for agent fleets
│   ├── README.md
│   ├── src/
│   │   ├── server/                # FastAPI governance API
│   │   ├── mcp-server/            # AGR as MCP server
│   │   ├── sdk/                   # Python SDK
│   │   └── cli/                   # CLI tool
│   ├── integrations/
│   │   ├── claude-code/           # Skill + instructions + MCP config
│   │   └── n8n/                   # Workflow templates
│   ├── deploy/Dockerfile
│   └── examples/
```
