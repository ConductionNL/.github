# Getting Started

_This is the **setup guide** — see [Workflow Overview](./workflow.md) for the architecture reference, and [End-to-End Walkthrough](./walkthrough.md) for a complete concrete example._

This guide walks you through setting up the spec-driven development workflow and completing your first change.

## Prerequisites

- **Node.js 20+** (required by OpenSpec CLI)
- **Global Claude settings installed** — mandatory for all Conduction work; see [global-claude-settings.md](global-claude-settings.md) for the install commands (sets up read-only Bash policy, write-approval hooks, and session-level version checking)
- **GitHub CLI** (`gh`) authenticated, or the GitHub MCP server active
- Access to the `ConductionNL` GitHub organization
- The `apps-extra` workspace cloned with at least one project

**Optional — Container authentication (needed for `/opsx-apply-loop` and `/opsx-pipeline`):**

These commands run Claude CLI inside an isolated Docker container, which cannot use the interactive OAuth login your host session uses. You need one of these environment variables set in your shell:

| Variable | Source | Cost |
|----------|--------|------|
| `CLAUDE_CODE_AUTH_TOKEN` (preferred) | Your existing Claude Max/Pro subscription | Free (included in subscription) |
| `ANTHROPIC_API_KEY` (fallback) | Anthropic API console | Prepaid credits (billed per token) |

**To set up `CLAUDE_CODE_AUTH_TOKEN` (recommended):**

```bash
# 1. Generate a long-lived token from your subscription
claude setup-token

# 2. Copy the token it outputs, then add to your shell profile:
echo 'export CLAUDE_CODE_AUTH_TOKEN="sk-ant-oat01-..."' >> ~/.bashrc

# 3. Reload your shell
source ~/.bashrc

# 4. Verify
echo $CLAUDE_CODE_AUTH_TOKEN | head -c 20
```

**To set up `ANTHROPIC_API_KEY` (alternative — costs money):**

```bash
# 1. Go to https://console.anthropic.com → API Keys → Create Key
# 2. Ensure your account has credits (Billing → Add credits)
# 3. Add to your shell profile:
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.bashrc

# 4. Reload your shell
source ~/.bashrc
```

> Neither variable is needed for interactive commands like `/opsx-apply` or `/opsx-verify` — only for the containerized automation commands.

**Optional — VS Code extensions:** See the [main README](../../README.md#4-install-vs-code-extensions) for the full list of required, recommended, and optional VS Code extensions.

**Optional — Usage monitoring:** Install the usage tracker to watch your Claude token consumption in real time inside VS Code. Especially useful before running multi-agent commands (see [parallel-agents.md](parallel-agents.md)).

```bash
bash .claude/usage-tracker/install.sh
```

See [`.claude/usage-tracker/README.md`](../../usage-tracker/README.md) for setup details.

## Step 1: Install OpenSpec

```bash
npm install -g @fission-ai/openspec@latest
```

Verify installation:

```bash
openspec --version
```

## Step 2: Understand the Workspace Structure

The workspace has two levels of spec management:

### Workspace level (shared)

```
apps-extra/
├── project.md              # Coding standards for ALL projects
├── openspec/
│   ├── config.yaml         # Shared context and rules
│   ├── schemas/conduction/ # Our custom workflow schema
│   ├── specs/              # Cross-project specs (NC conventions, APIs, etc.)
│   └── docs/               # You are here
```

These files define the patterns and conventions that apply to every project.

### Project level (specific)

```
openregister/
├── project.md              # What this project does, its architecture, dependencies
├── openspec/
│   ├── config.yaml         # Project config (points to shared schema)
│   ├── specs/              # Domain-specific specs for this project
│   └── changes/            # Active work in progress
```

Each project has its own specs describing its unique domain behavior.

## Step 3: Initialize a New Project (if needed)

If your project doesn't have OpenSpec set up yet, see [App Lifecycle](./app-lifecycle.md) for the bootstrapping commands and onboarding checklist.

If you're working on `openregister` or `opencatalogi`, they're already initialized.

## Step 4: Your First Change

Let's walk through creating your first spec-driven change.

### 4a. Start a new change

Navigate to your project and run:

```
/opsx-new my-first-feature
```

This creates `openspec/changes/my-first-feature/` with a `.openspec.yaml` metadata file.

### 4b. Build the specs

Generate all planning artifacts at once:

```
/opsx-ff
```

Claude will create:
1. **`proposal.md`** — Why this change exists and what it covers
2. **`specs/*.md`** — Detailed requirements with scenarios
3. **`design.md`** — Technical approach and architecture
4. **`tasks.md`** — Implementation checklist

### 4c. Review the artifacts

Read through each artifact. This is the most valuable step — catching issues in specs is much cheaper than catching them in code.

Things to check:
- Does the proposal cover the right scope?
- Are the spec requirements using the right RFC 2119 keywords (MUST vs SHOULD)?
- Do the scenarios cover edge cases?
- Is the task breakdown granular enough?

Edit the artifacts directly if needed — they're just markdown files.

### 4d. Create GitHub Issues

```
/opsx-plan-to-issues
```

This converts your tasks into GitHub Issues:
- A **tracking issue** with a full checklist (your "epic")
- **Individual issues** per task with acceptance criteria and spec references
- A **`plan.json`** file linking everything together

Open the tracking issue URL to see your kanban view.

### 4e. Start implementing

```
/opsx-apply
```

This starts the implementation loop. Each iteration:
1. Picks the next pending task from `plan.json`
2. Reads ONLY the spec section that task references
3. Implements the task
4. Closes the GitHub issue
5. Moves to the next task

The key benefit: each iteration works with minimal context, preventing AI "amnesia" on large changes.

> **Note:** `/opsx-ralph-start` is a planned dedicated implementation loop with deeper minimal-context loading and tighter GitHub integration — not yet implemented. Use `/opsx-apply` for now.

### 4f. Review your work

After all tasks are done:

```
/opsx-verify
```

This checks every spec requirement against your implementation and reports:
- **CRITICAL** findings that must be fixed
- **WARNING** findings that should be addressed
- **SUGGESTION** findings that are nice-to-have

> **Note:** `/opsx-ralph-review` is a planned dedicated review command — not yet implemented. Use `/opsx-verify` for now.

### 4g. Archive the change

Once review passes:

```
/opsx-archive
```

This merges your delta specs into the main specs and preserves the change for history.

## Quick Reference

| What you want to do | Command |
|---------------------|---------|
| Start a new feature | `/opsx-new <name>` |
| Generate all specs at once | `/opsx-ff` |
| Generate specs one at a time | `/opsx-continue` |
| Convert tasks to GitHub Issues | `/opsx-plan-to-issues` |
| Start implementing | `/opsx-apply` *(or `/opsx-ralph-start` once built)* |
| Review implementation | `/opsx-verify` *(or `/opsx-ralph-review` once built)* |
| Complete and archive | `/opsx-archive` |

## Next Steps

- Read the [Command Reference](./commands.md) for detailed options on each command
- Read [Writing Specs](./writing-specs.md) to write better specifications
- See the [Walkthrough](./walkthrough.md) for a full end-to-end example
- See [App Lifecycle](./app-lifecycle.md) to bootstrap or onboard a new app
