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
```
