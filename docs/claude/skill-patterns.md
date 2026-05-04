# Skill Patterns & Subfolder Guide

Proven, reusable building blocks for Claude Code skills. These are **L3 patterns** — apply them consistently across skills. For the full maturity framework, see [writing-skills.md](writing-skills.md).

---

## Description Writing Guide

The description is the single most important line in your skill. It determines auto-triggering reliability (L2).

```
# Structure: [Action verb] [what] — [key detail or when to use]

# Good examples:
description: Create a Pull Request from the current branch — runs local checks, picks target branch, and opens the PR on GitHub
description: Run automated browser tests for a Nextcloud app — single agent or multi-perspective parallel testing
description: Archive a completed change in the experimental workflow

# Bad examples:
description: Helps with PRs                          # too vague, no trigger terms
description: This skill creates pull requests for you  # first person, wastes chars
description: A useful tool for managing code reviews   # passive, no specificity
```

---

## Subfolder Guide

### `templates/`

Files with `{PLACEHOLDER}` variables that Claude fills in at runtime. Claude reads the file, substitutes values, and either writes the result to the user's project or injects it into a sub-agent.

**Use for:**
- JSON/YAML/Markdown documents Claude writes to disk (e.g. `app-config.json`, `CHANGELOG.md`)
- Sub-agent prompts with variable substitution
- PR/issue body formats Claude fills in before creating
- Spec or design document scaffolds

**Do not use for:** documents Claude reads without modifying, or fixed reference material.

In `SKILL.md`, reference with:
```
Write the file using the template in `templates/architecture-template.md`.
```

### `references/`

Static content Claude reads to inform decisions — no placeholder variables, never written to the user's project. This is a key subfolder for **L4 personalization** — business-specific standards, architecture docs, and domain knowledge live here.

**Use for:**
- Standards documents (Dutch government guidelines, GEMMA/ZGW compliance, coding standards)
- Architecture guidelines and conventions
- Spec excerpts or capability descriptions
- Multi-page guides Claude consults during a step

**Do not use for:** templates, examples, or binary files.

In `SKILL.md`, reference with:
```
Follow the standards in `references/dutch-gov-backend-standards.md`.
```

### `examples/`

Worked demonstrations showing what expected output looks like. Used for few-shot guidance — Claude sees a concrete example and produces output in the same pattern. Critical for **L3** (proven patterns).

**Use for:**
- Output format blocks (e.g. "Archive Complete", "Implementation Paused")
- Worked conflict resolution or decision examples
- Sample report sections showing expected structure

**Do not use for:** templates with placeholders (those go in `templates/`), or static reference docs.

In `SKILL.md`, reference with:
```
For the expected output format, see `examples/output-templates.md`.
```

### `assets/`

Non-markdown static files that get copied as-is to the user's project or used by the skill tooling.

**Use for:**
- SVG illustrations or placeholder images
- JavaScript/TypeScript config stubs (`webpack.config.js`, `docusaurus.config.js`)
- YAML/JSON configuration stubs copied verbatim

**Do not use for:** markdown files (even if they're config-like — those go in `templates/`).

### `evals/` (L5+)

Evaluation scenarios and benchmark results for measured skills.

**Use for:**
- `evals.json` — test scenarios, `trigger_tests` (should/should-not-trigger examples), and `last_validated` (date of last eval run; required for L5 green circle)
- `timing.json` — token usage and duration per eval run
- `grading.json` — assertion pass/fail results with evidence

See [skill-evals.md](skill-evals.md) for format details.

---

## Common Patterns

### Model guard (for heavy reasoning skills)

Place at the top of `SKILL.md` when the skill needs Sonnet or Opus:

```markdown
**Check the active model** from your system context.

- **On Haiku**: stop immediately — this skill requires Sonnet or Opus.
  Switch with `/model sonnet` and re-run.
- **On Sonnet or Opus**: proceed normally.
```

### User input

Always use the **AskUserQuestion** tool — never assume or auto-select:

```markdown
Use **AskUserQuestion** to ask:

> "Which change should I archive?"

Options:
- **change-a** — description
- **change-b** — description
```

For multi-select prompts:
```markdown
Use **AskUserQuestion** with `multiSelect: true` to let the user choose.
```

### Destructive action confirmation

Before any irreversible action, show what will happen and ask for explicit confirmation:

```markdown
Show a preview of the changes, then use **AskUserQuestion**:

> "Create these issues in `owner/repo`?"

Options:
- **Yes, proceed** — continue
- **Cancel** — end without changes
```

### Referencing subfolders

Use relative markdown links — Claude resolves them relative to the skill folder:

```markdown
Use the template in `templates/architecture-template.md`.
Follow the standards in `references/dutch-gov-backend-standards.md`.
For output examples, see `examples/output-templates.md`.
```

### PHP quality checks (for skills that trigger implementation)

After code changes, run the quality suite and block on failures:

```markdown
Run `composer check:strict` from the app directory.
If it fails, fix all issues before continuing — do not skip.
```

### Capture learnings step (L6+)

Add as the final step in skills that should self-improve:

```markdown
**Capture learnings**

After execution, review what happened and append new observations to
`learnings.md` under the appropriate section:

- **Patterns That Work** — approaches that produced good results
- **Mistakes to Avoid** — errors encountered and how they were resolved
- **Domain Knowledge** — facts discovered during this run
- **Open Questions** — unresolved items for future investigation

Each entry must include today's date. One insight per bullet. Skip if nothing new was learned.
```

### Next steps handoff (L7)

For skills that are part of a workflow chain:

```markdown
**Next steps**

Suggest the logical next action:
- If tasks remain → "Run `/opsx-apply` to implement"
- If implementation done → "Run `/opsx-verify` to validate"
- If verified → "Run `/opsx-archive` to complete"
```
