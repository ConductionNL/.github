
# Writing Skills

How to create, structure, and improve Claude Code skills in this repository.

Skills live in `.claude/skills/<skill-name>/` and are invoked with `/<skill-name>`. Each skill is a folder containing a `SKILL.md` entry point and optional subfolders for supporting files.

**Related docs:**
- [Skill Patterns & Subfolder Guide](skill-patterns.md) — common patterns, subfolder conventions, description writing
- [Skill Evaluation Guide](skill-evals.md) — evals.json schema, Skill Creator setup, baseline_score
- [Skill Checklist](skill-checklist.md) — quick validation checklist per maturity level

---

## Skill Maturity Levels

Skills evolve through 7 maturity levels. Each level builds on the previous — a skill is at the highest level where **all** criteria are met. Use these levels to assess existing skills, plan improvements, and set quality targets.

> **Source:** This framework is based on Simon Scrapes' "Every Level of Claude Code Skills" (March 2026), validated against Anthropic's official skill authoring best practices ([platform.claude.com](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)), the Barry Zhang & Mahesh Murag talk "Don't Build Agents, Build Skills Instead" (AI Engineer Summit, November 2025), and the Agent Skills Open Standard ([agentskills.io](https://agentskills.io/specification)).

### Levels Are Cumulative but Not Always Sequential

Levels 1-7 build on each other in terms of criteria. However, in practice **skills can exhibit higher-level patterns while skipping intermediate levels**. For example, a skill that orchestrates 8 parallel agents (L7 structure) but has never been formally evaluated (L5) or given a learnings pipeline (L6) is **"structurally L7 but maturity L4."**

When assessing skills, note both the **structural level** (highest level pattern present) and the **maturity level** (highest level where ALL criteria through that level are met). The goal is to close gaps — add measurement and self-improvement to skills that already have orchestration.

Not every skill needs to reach Level 7. A simple utility skill (`clean-env`) may peak at L3-L4. The target level depends on how critical and frequently-used the skill is.

---

### Level 1: Anatomy — What Good Skills Are Made Of

The skill exists as a properly structured folder with a valid SKILL.md.

**Criteria:**
- Has `SKILL.md` with valid frontmatter (`name`, `description`, `metadata`)
- Has numbered, self-contained steps
- Has guardrails (what the skill must NOT do)
- Folder name matches `name` field and slash command

**Anti-patterns:**
- No frontmatter or missing `description`
- Steps are vague paragraphs instead of numbered instructions
- No guardrails — skill can do anything without constraints

> **Reference:** Anthropic's [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) defines this baseline structure. The [Agent Skills Open Standard](https://agentskills.io/specification) (adopted by 20+ tools including OpenAI Codex, Gemini CLI, GitHub Copilot, Cursor) uses the same SKILL.md format.

---

### Level 2: The Golden Rule — Context Management & Triggering

The skill uses progressive disclosure and has a description optimized for reliable auto-triggering.

**The Golden Rule:** Only the skill's `description` field is loaded into context initially. Claude decides whether to load the full skill based on that description alone. If the description is vague, the skill never fires automatically.

> **Source:** Confirmed by Barry Zhang & Mahesh Murag (Anthropic) in "Don't Build Agents, Build Skills Instead" — only metadata is loaded initially, the LLM decides whether to load the full skill. Also confirmed by Anthropic's official docs: descriptions are capped at 250 characters in skill listings.

**Criteria (in addition to L1):**
- Description is written in **third person** (it gets injected into the system prompt)
- Description **front-loads the key use case** in the first 250 characters (longer gets truncated in listings)
- Description includes **specific trigger terms**, not vague phrases like "helps with code"
- `SKILL.md` body is **under 500 lines** — heavy content extracted to subfolders
- **Progressive disclosure** is actively used (see [Size Limits & Progressive Disclosure](#size-limits--progressive-disclosure) below)

**Example — bad vs good description:**
```
# Bad: vague, passive, no trigger terms
description: A skill that helps with various document-related tasks

# Good: specific, third-person, front-loaded action + trigger terms
description: Create a Pull Request from the current branch — runs local checks, picks target branch, and opens the PR on GitHub
```

**Known limitation:** Multiple independent sources report ~50% auto-activation rates for skills. The `SLASH_COMMAND_TOOL_CHAR_BUDGET` defaults to 1% of context window, limiting how many descriptions fit. With large skill libraries, explicit `/skill-name` invocation is more reliable than auto-triggering.

> **Sources:** Jesse Vincent ([blog.fsck.com](https://blog.fsck.com/2025/12/17/claude-code-skills-not-triggering/)), Scott Spence ([scottspence.com](https://scottspence.com/posts/claude-code-skills-dont-auto-activate)), GitHub community discussions.

---

### Level 3: Import & Improve — Build on Proven Foundations

The skill is built on recognized patterns, community best practices, or existing validated templates — then customized and improved.

**Why this matters:** Research shows ~80% of community-created skills make output worse. The 20% that work are built by domain experts using iterative evaluation (Corporate Waters, 2026). Starting from proven foundations avoids reinventing broken wheels.

**Criteria (in addition to L2):**
- Built on a **recognized pattern**: Anthropic official patterns, validated community skill, or your own proven pattern library
- Has **at least one supporting subfolder**: `examples/` (output format demos), `references/` (standards docs), or `templates/` (fillable scaffolds)
- Uses **at least one common pattern** consistently (model guard, AskUserQuestion, destructive action confirmation, quality gates — see [skill-patterns.md](skill-patterns.md#common-patterns))
- References **standards documents** where applicable (in `references/`)

> **What the script auto-detects for L3:** at least one common pattern keyword present in SKILL.md from any of these categories: (1) model guard (`model:`, `On Haiku`, `active model`, ...), (2) `AskUserQuestion`, (3) quality gates (`composer check`, `phpcs`, `phpstan`, `make check`, `ruff`, `psalm`), (4) subfolder references (`examples/`, `refs/`, `references/`, or `templates/` as text in SKILL.md), or (5) destructive/browser patterns (`confirm.*before`, `browser_snapshot`, `browser_navigate`, `## Hard Rule`, `## Verification`, `acceptance_criteria`) — AND existence of at least one of `examples/`, `references/`, or `templates/` on disk. These are structural proxies for the full criteria above.

**Sources for proven patterns:**
- Anthropic's official `/skill-creator` bundled plugin ([GitHub](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md))
- Agent Skills Open Standard: [agentskills.io/specification](https://agentskills.io/specification)
- Community repos: [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code), [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills)
- Your own skill library — reuse patterns that work across skills

---

### Level 4: Personalization — Your Business Context

The skill contains domain-specific knowledge that makes it uniquely effective for your project. It couldn't be dropped into another company and work as-is.

**Criteria (in addition to L3):**
- Has **business-specific reference files** (e.g., `references/dutch-gov-backend-standards.md`, persona cards, ADR documents)
- Uses **project-specific templates** (PR format, spec format matching your workflow)
- References **your architecture, ADRs, coding standards** — not just generic best practices
- Skill output is **recognizably tailored** to your domain

**Example — generic vs personalized:**
```
# Generic (L3): "Run linting checks after code changes"
# Personalized (L4): "Run `composer check:strict` from the app directory.
#   This runs PHPCS, PHPMD, Psalm, and PHPStan.
#   Fix all issues before continuing — do not skip.
#   Follow PSR-4 structure with Conduction naming conventions."
```

**In this repository**, L4 personalization includes:
- Dutch government standards (GEMMA, ZGW, BIO2, Common Ground)
- NL Design System CSS variables and WCAG AA compliance
- Conduction app patterns (openregister, opencatalogi, etc.)
- 8 Dutch citizen/professional personas for testing
- OpenSpec workflow integration (specs, ADRs, changes)

---

### Level 5: Measurement — Evaluated and Optimized with Data

The skill has been systematically tested with evaluation scenarios. Its performance has been measured and improved based on data, not just intuition.

**Why most skills plateau at L4:** A skill that "feels right" but has never been measured may have blind spots, false confidence, or suboptimal triggering. Measurement turns intuition into evidence.

**Criteria (in addition to L4):**
- Has **3+ evals** with input prompts, expected output characteristics, and assertion criteria
- **Description trigger testing**: 10+ `should_trigger` + 10+ `should_not_trigger` prompts
- **Evals have been run**: `last_validated` is set in `evals.json`
- **Baseline measurement** exists: what does Claude produce without the skill?
- Skill has been through at least **one improve cycle** based on eval results
- `evals/` folder with `evals.json`; `timing.json` and `grading.json` produced after running evals

> **What the script auto-detects for L5:** 3+ evals (checks `evals` key, falls back to `scenarios`), 10+/10+ trigger tests, and `last_validated` non-null in evals.json. Baseline measurement and improve cycles are required for true L5 but not auto-checked by the script.

For the full evals.json schema, Skill Creator setup guide, and baseline_score usage, see [skill-evals.md](skill-evals.md).

---

### Level 6: Self-Improvement — Skills That Learn from Experience

The skill captures learnings during execution and periodically consolidates them into improved standing rules.

**The Learnings-to-Rules Pipeline:**
```
Execution -> Capture observations -> learnings.md -> Consolidation -> Updated SKILL.md rules
                                       ^                              |
                                       └──────────────────────────────┘
```

**Criteria (in addition to L5):**
- Has a **`learnings.md`** file in the skill folder
- SKILL.md includes a **"capture learnings" step** near the end of execution
- Each learning entry is **dated and atomic** (one insight per bullet)
- Learnings have **5 sections**: Patterns That Work, Mistakes to Avoid, Domain Knowledge, Open Questions, Consolidated Principles
- **Consolidation triggers** at ~80-100 entries: remove outdated, merge duplicates, extract cross-entry patterns, promote validated principles to SKILL.md guardrails/rules

**Improvement: Learning Candidates Ledger**

Rather than writing every observation directly to `learnings.md`, use a two-stage buffer to prevent garbage learnings from polluting context:

```
learning-candidates.md  ->  (promotion criteria met?)  ->  learnings.md  ->  SKILL.md rules
       ↓ (no)
    discarded after 30 days
```

Promotion criteria: observation confirmed across 3+ executions, or resolves a measured eval failure.

> **Source:** The learnings-to-rules pattern is documented by MindStudio ([mindstudio.ai/blog](https://www.mindstudio.ai/blog/how-to-build-learnings-loop-claude-code-skills)) and implemented in community tools: [claude-reflect-system](https://github.com/haddock-development/claude-reflect-system), [claude-meta](https://github.com/aviadr1/claude-meta), [turbo](https://github.com/tobihagemann/turbo). The two-stage buffer improvement was suggested by @jacksonporter1949 in community discussion.

**Example `learnings.md`:**
```markdown
# Learnings — create-pr

## Patterns That Work
- 2026-03-15: Branch protection on `main` requires status checks — always verify checks exist first
- 2026-03-20: Including GitHub issue number in PR title improves traceability

## Mistakes to Avoid
- 2026-03-18: Do NOT create PR with uncommitted changes — causes confusion about what's included
- 2026-03-22: Lock file conflicts (composer.lock) -> run `composer update` locally, don't accept either side

## Domain Knowledge
- 2026-03-19: Conduction repos use `development` as primary integration branch, not `main`

## Open Questions
- Should PRs auto-assign reviewers based on CODEOWNERS?

## Consolidated Principles
- (promoted after 3+ confirmations)
- Always run `composer check:strict` before creating PR — catches 90% of review feedback
```

---

### Level 7: AI Workforce — Multi-Agent Orchestration

The skill orchestrates multiple agents or is part of a coordinated workflow where specialized skills work together autonomously.

**Criteria (in addition to L6):**
- **Orchestrates sub-agents** (spawns parallel workers) or is **orchestrated by a parent skill**
- Part of a **defined workflow chain** with explicit handoff points:
  ```
  opsx-new -> opsx-ff -> opsx-plan-to-issues -> opsx-apply -> opsx-verify -> opsx-archive
  ```
- **Hands off context** to the next skill (shows "Next steps: run `/opsx-verify`")
- Uses **isolated execution contexts** when needed (git worktrees, Docker containers)
- Has **autonomous operation capability** for defined scope
- Participates in **parallel execution** (e.g., 8 agents simultaneously)

**Orchestration patterns in this repository:**

| Pattern | Example | Description |
|---------|---------|-------------|
| **Pipeline** | `opsx-pipeline` | Full lifecycle for 1+ changes in parallel via subagents |
| **Fan-out/Fan-in** | `test-counsel`, `feature-counsel` | Spawn N agents in parallel, synthesize results |
| **Sequential Chain** | `opsx-new` -> ... -> `opsx-archive` | Each skill hands off to the next |
| **Autonomous Loop** | `opsx-apply-loop` | Runs apply->verify cycle with retry logic, auto-archives |
| **Multi-perspective** | `test-app` | Spawns 6 specialized test agents simultaneously |

> **Reference:** Claude Code Agent Teams (experimental) and the Agent SDK support these patterns natively. See [Claude Code Agent Teams docs](https://code.claude.com/docs/en/agent-teams).

**Important — structural vs mature L7:** A skill can exhibit L7 orchestration patterns (spawning subagents, workflow chains) while lacking L5 measurement and L6 self-improvement. Such a skill is **"structurally L7, maturity L4"** — it has the architecture of a workforce but the self-awareness of a static tool. The goal is to close the L5-L6 gap so the orchestration is not just complex but also measurably effective and continuously improving.

---

### Maturity Assessment Quick Reference

| Check | Yes -> at least | No -> stuck at |
|-------|:---:|:---:|
| Has SKILL.md with frontmatter, steps, guardrails? | L1 | Below L1 |
| Description optimized for triggering, progressive disclosure used, <500 lines? | L2 | L1 |
| Built on proven patterns, has examples/references? | L3 | L2 |
| Contains business-specific domain context? | L4 | L3 |
| Has eval scenarios, measured and optimized with data? | L5 | L4 |
| Has learnings.md with consolidation process? | L6 | L5 |
| Orchestrates agents or part of workflow chain? | L7 | L6 |

---

### Maintaining Skill Maturity

Skills degrade over time. Schedule periodic reviews:

**Monthly:**
- Run eval scenarios for L5+ skills — have pass rates changed?
- Review `learnings.md` for L6+ skills — consolidate if >80 entries
- Check description trigger rates for frequently-used skills

**Quarterly:**
- Re-evaluate L4 skills: has the business context changed? (new ADRs, standards, deprecated patterns)
- Check if L7 workflow chains still work end-to-end
- Prune skills that are never invoked

**When something breaks:**
- Add the failure to `learnings.md` (L6 skills) or create an eval scenario (L5 skills)
- Don't just fix the symptom — update the skill's standing rules to prevent recurrence
- If a skill consistently fails, consider splitting it (simpler skills trigger more reliably)

---

### Common Upgrade Paths

**L4 -> L5 (most common need):** Create 3 eval scenarios from real usage. Run the skill, grade output, identify one weakness, improve, re-eval.

**L5 -> L6:** Add `learnings.md` and a "capture learnings" step to SKILL.md. After 5-10 executions, review learnings and promote validated patterns to standing rules.

**L4 -> L7 (standalone -> workflow):** Identify which workflow chain the skill belongs to. Add "Next steps" guidance. Add context handoff. Test the full chain end-to-end.

**Fixing "structurally L7 but maturity L4":** Add L5 evals and L6 learnings to the orchestrator skill first — its improvements cascade to all sub-agents.

---

## Folder Structure

```
.claude/skills/
  <skill-name>/
    SKILL.md              <- required: the skill logic (L1+)
    templates/            <- files Claude fills in and writes to disk (L2+)
    references/           <- standards and guides Claude reads for context (L3+)
    examples/             <- worked output demonstrations and few-shot patterns (L3+)
    assets/               <- non-markdown static files (SVG, JS, YAML, JSON)
    evals/                <- evaluation scenarios and results (L5+)
    learnings.md          <- accumulated execution insights (L6+)
    learning-candidates.md <- unverified observations awaiting promotion (L6+)
```

Not every skill needs all subfolders. Create them only when content qualifies. A skill with no supporting files is just a `SKILL.md` — no subfolders needed.

**Extraction threshold**: Extract content from `SKILL.md` into a subfolder when the block is:
- 10%+ of the total file size, AND
- A standalone unit (not tightly coupled to surrounding procedural steps)

Do not extract short inline code snippets, conditional logic, or step-by-step instructions — those belong in `SKILL.md`.

---

## Size Limits & Progressive Disclosure

Claude loads skill content in three layers. Respecting these limits keeps skills fast and context-efficient.

| Layer | What | Budget | When loaded |
|-------|------|--------|-------------|
| **Metadata** | `name` + `description` in frontmatter | ~100 words / **250 characters** visible in listings | **Always** — part of system prompt |
| **SKILL.md body** | Steps, guardrails, inline instructions | **< 500 lines** | When skill triggers (auto or `/slash`) |
| **Reference files** | `references/`, `templates/`, `examples/`, `assets/` | Unlimited (but each file adds to context on read) | On demand during execution |

> **Source:** Anthropic's [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — "Concise is key: the context window is a shared resource. Only add what Claude does not already know."

**When SKILL.md exceeds 500 lines:**
1. Move large reference blocks to `references/` and link them
2. Move output format examples to `examples/`
3. Move templates with placeholders to `templates/`
4. Keep in SKILL.md: procedural steps, conditional logic, guardrails, short inline snippets (<20 lines)

**Context budget with many skills:** The `SLASH_COMMAND_TOOL_CHAR_BUDGET` defaults to 1% of context window (with 8,000 character fallback). With 50+ skills, descriptions compete for space — keep them concise and front-loaded.

---

## SKILL.md Format

```markdown
---
name: <skill-name>
description: <one-line action description — shown in skill picker, max 250 chars visible>
metadata:
  category: <Workflow | Testing | Development | Delivery>
  tags: [tag1, tag2]
---

# Skill Title

Brief explanation of what the skill does.

**Input**: How to invoke the skill and what arguments it accepts.

**Steps**

1. **Step name**

   Instructions...

2. **Step name**

   Instructions...

**Guardrails**
- What the skill must never do
- What to check before destructive actions
```

### Frontmatter Rules

- `name` must match the folder name exactly (e.g. folder `test-counsel` -> `name: test-counsel`)
- `description` is what users see in the skill picker AND what Claude uses to decide whether to load the skill — make it action-oriented, specific, and written in **third person**
- Front-load the key use case in the first 250 characters
- Include specific trigger terms (verbs and nouns a user would naturally say)
- `tags` are free-form; use them for filtering and grouping

### Advanced Frontmatter Fields

Beyond `name`, `description`, and `metadata`, several optional frontmatter fields control skill behavior:

```yaml
---
name: my-skill
description: "..."
allowed-tools: [Read, Glob, Grep, Bash]  # restrict which tools the skill can use
context: fork                              # run in isolated subagent context
paths: ["openspec/**", "docs/**"]          # only auto-trigger when working in these paths
disable-model-invocation: true             # prevent auto-triggering; slash-only invocation
---
```

| Field | Purpose | When to use |
|-------|---------|-------------|
| `allowed-tools` | Restricts which tools the skill can call | Safety-critical skills — e.g., a read-only audit skill should not have Write access |
| `context: fork` | Runs the skill in an isolated subagent context | Skills that should not pollute the parent conversation's context window |
| `paths` | Limits auto-activation to specific file patterns | Skills that only apply to certain parts of the repo (e.g., `openspec/**`) |
| `disable-model-invocation` | Blocks auto-triggering entirely | Skills that should only run when explicitly invoked via `/skill-name` |

> **Source:** Anthropic's [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) and the [Agent Skills Open Standard](https://agentskills.io/specification).

### Dynamic Content in Skills

Skills can inject dynamic content at invocation time:

| Syntax | Purpose | Example |
|--------|---------|---------|
| `$ARGUMENTS` | Full argument string passed after `/skill-name` | `/app-create my-app` -> `$ARGUMENTS` = `"my-app"` |
| `$ARGUMENTS[0]` | Individual positional argument | First argument after the skill name |
| `${CLAUDE_SKILL_DIR}` | Absolute path to the skill's own folder | Useful for referencing bundled scripts or assets |
| `` !`command` `` | Shell command output injected before skill loads | `` !`git branch --show-current` `` injects the current branch name |

The `` !`command` `` syntax is particularly powerful for injecting runtime context into skills — the command runs before the skill content is loaded into context.

### Degrees of Freedom

Match the skill's specificity to its task fragility:

| Task type | Freedom level | Skill style |
|-----------|:---:|-------------|
| Exploration, code review, brainstorming | **High** | Provide goals and constraints, let Claude decide approach |
| Feature implementation, refactoring | **Medium** | Provide steps with decision points, let Claude adapt |
| Database migrations, production deploys, CI config | **Low** | Prescribe exact commands, explicit confirmation gates |

A skill for `/app-explore` (thinking mode) should have high degrees of freedom — it's about creativity and investigation. A skill for `/app-apply` (config -> code sync) should have low freedom — it must apply changes predictably and safely.

> **Source:** Anthropic's [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — "Set appropriate degrees of freedom: match specificity to task fragility."

---

## Naming Conventions

Skills use the `namespace-action` format with lowercase letters, numbers, and hyphens only.

| Namespace | Covers |
|-----------|--------|
| `opsx-` | OpenSpec workflow steps (`opsx-new`, `opsx-apply`, `opsx-archive`) |
| `app-` | Nextcloud app lifecycle (`app-design`, `app-create`, `app-explore`, `app-apply`) |
| `test-` | Testing — counsel, persona agents, regression (`test-counsel`, `test-persona-henk`) |
| `team-` | Scrum team agents (`team-backend`, `team-qa`, `team-reviewer`) |
| `swc-` | Softwarecatalogus-specific (`swc-test`, `swc-update`) |
| `ecosystem-` | Ecosystem research (`ecosystem-investigate`, `ecosystem-propose-app`) |
| `tender-` | Tender intelligence (`tender-scan`, `tender-status`) |

The folder name, `name` frontmatter field, and the slash command all must match exactly.

---

## What NOT to Put in SKILL.md

Extract to subfolders when a block qualifies (10%+, standalone). Leave in `SKILL.md`:

- Short inline code snippets (< 20 lines, embedded in a step)
- Conditional logic that references the step context
- Procedural steps that only make sense in sequence
- Guardrails and constraints (they're part of the skill's contract)
