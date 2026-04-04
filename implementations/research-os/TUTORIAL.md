# Tutorial: Research OS

This walkthrough demonstrates how to conduct structured research using specialized agents that scout, analyze, synthesize, and critique.

## Prerequisites

- VS Code with GitHub Copilot Chat
- The Research OS workspace open (`implementations/research-os/`)

## What You Get

| Agent | Role | Tools |
|---|---|---|
| `@scout` | Broad search across sources | `web, search, read` |
| `@analyst` | Deep source evaluation | `web, read` |
| `@synthesizer` | Combine findings into insights | `read` |
| `@critic` | Adversarial quality review | `read` |

| Skill | Workflow |
|---|---|
| `/competitive-analysis` | Scope → Scout → Analyze → Synthesize → Critique → Report |
| `/literature-review` | Frame Question → Search → Analyze → Synthesize → Quality Check |

---

## Exercise 1: Competitive Analysis

### Scenario

Your team is evaluating task management tools. You need a comparison of Todoist, TickTick, and Microsoft To Do.

### Step 1: Invoke the skill

```
/competitive-analysis Compare Todoist, TickTick, and Microsoft To Do for our team's task management needs. Focus on pricing, collaboration features, and API availability.
```

### Step 2: Watch the pipeline

**`@scout` searches broadly:**
- Pricing pages for each product
- Review sites (G2, Capterra)
- API documentation
- Recent feature announcements

Returns ~10-15 sources per competitor with URLs, titles, and relevance notes.

**`@analyst` deep-reads each source:**

For each competitor, extracts:
```
### Source: Todoist Pricing Page
**Credibility**: High (primary source)
**Key Claims**:
1. Free tier: up to 5 projects — Evidence: pricing page as of [date]
2. Pro: $4/month — Evidence: pricing page
**Limitations**: Does not show enterprise or volume discounts
```

**`@synthesizer` combines findings:**

Produces a comparative table with confidence scoring:
```
### Pricing Comparison
| Feature | Todoist | TickTick | MS To Do |
|---------|---------|----------|----------|
| Free tier | 5 projects | Unlimited lists | Unlimited |
| Pro price | $4/mo | $2.79/mo | Included in M365 |

**Confidence**: Strong — all from primary sources
```

**`@critic` challenges the synthesis:**
```
### Major Issues
- Source bias: all pricing data from vendor websites — no independent verification
- Missing perspective: no user reviews on reliability or support quality

### Minor Issues
- MS To Do "free" is misleading — requires Microsoft account
```

### Step 3: Get the final report

The output follows the [competitive analysis report template](./github/skills/competitive-analysis/references/report-template.md): executive summary, detailed comparison, confidence-rated findings, gaps, recommendations, and full source list.

---

## Exercise 2: Quick Research (Direct Agent Use)

For simpler questions, skip the skill and talk to agents directly.

### Find sources

```
@scout Find the top 5 most-cited papers on retrieval-augmented generation (RAG)
```

### Analyze a source

```
@analyst Read this paper and extract: key methodology, main findings, and limitations. [paste URL or content]
```

### Check your work

```
@critic Review my draft analysis for unsupported claims and source bias. [paste draft]
```

---

## Exercise 3: Literature Review

```
/literature-review What are the current best practices for AI agent evaluation? Cover academic papers, industry benchmarks, and practitioner guides from the last 2 years.
```

This produces:
1. A scoped research question
2. Sources organized by type (academic, industry, practitioner)
3. Thematic findings with citations
4. Gaps analysis
5. Annotated bibliography

---

## Key Governance Rules

The `research-standards.instructions.md` enforces these automatically whenever you're working in research output files:

- Every claim must cite a source with URL
- Unsourced inferences marked as "Based on the evidence, we infer..."
- Confidence language: "strongly suggests" (3+ sources), "indicates" (1-2), "no evidence found"
- Single-source claims flagged with ⚠️

---

## Quick Reference

| What you want | What to type |
|---|---|
| Full competitive analysis | `/competitive-analysis [competitors + dimensions]` |
| Academic literature review | `/literature-review [research question]` |
| Broad source search | `@scout [query]` |
| Deep source evaluation | `@analyst [source or topic]` |
| Combine findings | `@synthesizer [findings to combine]` |
| Challenge conclusions | `@critic [draft to review]` |
