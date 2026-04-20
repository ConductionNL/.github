# OpenSpec Command Reference

These commands are installed per-project when you run `openspec init`. They're available inside each project directory.

---

### `/opsx-new <change-name>`

**Phase:** Spec Building

Start a new change. Creates the change directory with metadata.

**Usage:**
```
/opsx-new add-publication-search
```

**What it creates:**
```
openspec/changes/add-publication-search/
└── .openspec.yaml      # Change metadata (schema, created date)
```

**Tips:**
- Use descriptive kebab-case names: `add-dark-mode`, `fix-cors-headers`, `refactor-object-service`
- The name becomes a GitHub Issue label, so keep it readable

---

### `/opsx-ff`

**Phase:** Spec Building

Fast-forward: generates ALL artifacts in dependency order (proposal → specs → design → tasks) in one go.

**Usage:**
```
/opsx-ff
```

**What it creates:**
```
openspec/changes/add-publication-search/
├── .openspec.yaml
├── proposal.md         # Why & what
├── specs/              # Delta specs (ADDED/MODIFIED/REMOVED)
│   └── search/
│       └── spec.md
├── design.md           # How (technical approach)
└── tasks.md            # Implementation checklist
```

**When to use:** When you have a clear idea of what you want to build and want to generate everything quickly for review.

**When NOT to use:** When you want to iterate on each artifact step by step, getting feedback between each. Use `/opsx-continue` instead.

**Model:** Asked at run time — the command asks which model to use and spawns a subagent with that model for artifact generation. Artifact quality (specs, design, tasks) directly determines implementation quality downstream. **Sonnet** for most changes. **Opus** for complex or architectural changes where deeper reasoning improves the design.

---

### `/opsx-continue`

**Phase:** Spec Building

Creates the next artifact in the dependency chain. Run repeatedly to build specs incrementally.

**Usage:**
```
/opsx-continue    # Creates proposal.md (first time)
/opsx-continue    # Creates specs/ (second time)
/opsx-continue    # Creates design.md (third time)
/opsx-continue    # Creates tasks.md (fourth time)
```

**Dependency chain:**
```
proposal (root)
    ├── discovery  (optional — requires: proposal)
    ├── contract   (optional — requires: proposal)
    ├── specs      (requires: proposal)
    ├── design     (requires: proposal)
    ├── migration  (optional — requires: design)
    ├── test-plan  (optional — requires: specs)
    └── tasks      (requires: specs + design)
```

**When to use:** When you want to review and refine each artifact before proceeding to the next.

---

### `/opsx-explore`

**Phase:** Pre-spec

Think through ideas and investigate the codebase before starting a formal change. No artifacts are created.

**Usage:**
```
/opsx-explore
```

**When to use:** When you're not sure what approach to take yet and want to investigate first.

**Comparison with `/app-explore`:**

| | `/opsx-explore` | `/app-explore` |
|---|---|---|
| **Scope** | Any topic — a change, a bug, an idea | A specific Nextcloud app's configuration |
| **Output** | None — thinking only | Writes to `openspec/app-config.json` |
| **When to use** | Before starting a change (`/opsx-new`) when requirements are unclear | When designing or refining an app's goals, architecture, and features |
| **Phase** | Pre-spec | Design / Configuration |

Use `/opsx-explore` to think through *what to build*. Use `/app-explore` to document *how an app is designed and configured*.

**Model:** Checked at run time — stops on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most exploration sessions. **Opus** recommended — complex analysis, architecture decisions, and strategic thinking benefit from stronger reasoning.

---

### `/opsx-apply`

**Phase:** Implementation

OpenSpec's built-in implementation command. Reads `tasks.md` and works through tasks.

**Usage:**
```
/opsx-apply
```

**Model:** Checked at run time — stops if on Haiku. **Sonnet** for most implementation work. **Opus** for architecturally complex changes.

---

### `/opsx-verify`

**Phase:** Review

OpenSpec's built-in verification. Validates implementation against artifacts.

**Usage:**
```
/opsx-verify
```

**Checks:**
- **Completeness** — All tasks done, all requirements implemented
- **Correctness** — Implementation matches spec intent
- **Coherence** — Design decisions reflected in code
- **Test coverage** — Every new PHP service/controller has a corresponding test file; every new Vue component has a test if the project uses Jest/Vitest
- **Documentation** — New features and API endpoints are described in README.md or docs/

**Model:** Checked at run time — stops if on Haiku. **Sonnet** for most verification work. **Opus** for complex or large changes.

---

### `/opsx-sync`

**Phase:** Archive

Merges delta specs from the change into the main `openspec/specs/` directory.

**Usage:**
```
/opsx-sync
```

**What it does:**
- **ADDED** requirements → appended to main spec
- **MODIFIED** requirements → replace existing in main spec
- **REMOVED** requirements → deleted from main spec

Usually done automatically during archive.

---

### `/sync-docs`

**Phase:** Maintenance

Check and sync documentation to reflect the current project state. Two targets: **app docs** (`{app}/docs/`) for a specific Nextcloud app's users and admins, and **dev docs** (`.github/docs/claude/`) for Claude and developers.

**Usage:**
```
/sync-docs                       # prompts for target
/sync-docs app                   # prompts for which app, then syncs its docs/
/sync-docs app openregister      # sync docs for a specific app
/sync-docs dev                   # sync developer/Claude docs (.github/docs/claude/)
```

Before syncing, runs 4 preliminary checks in parallel — config.yaml rules vs writing-docs.md/writing-specs.md, Sources of Truth accuracy, writing-specs.md vs schema template alignment (`openspec/schemas/conduction/`), and forked schema drift from the upstream `spec-driven` schema. Reports gaps and asks whether to fix before proceeding.

**App docs mode** (`{app}/docs/`) — checks the app's `README.md` (root), `docs/features/`, `docs/ARCHITECTURE.md`, `docs/FEATURES.md`, `docs/GOVERNMENT-FEATURES.md`, and any other user-facing `.md` files against the app's current specs. Also loads all company-wide ADRs from `hydra/openspec/architecture/` and any app-level ADRs as auditing context (never as link targets in app docs). Flags outdated descriptions, missing features, stale `[Future]` markers (with full removal checklist), broken links, duplicated content, writing anti-patterns, ADR compliance gaps (screenshots, i18n, API conventions), and missing GEMMA/ZGW/Forum Standaardisatie standards references. Never inserts links into `.claude/` paths. Always shows a diff and asks for confirmation before writing.

**Dev docs mode** (`.github/docs/`) — checks `commands.md`, `workflow.md`, `writing-specs.md`, `writing-docs.md`, `testing.md`, `getting-started.md`, `README.md`, plus the conduction schema (`hydra/openspec/schemas/conduction/schema.yaml`) and its `templates/spec.md` for alignment with `writing-specs.md`. Never changes intent without user confirmation. After syncing, runs a Phase 6 review of all commands and skills for stale references, outdated instructions, and redundant inline content — and asks whether to update them.

Both modes enforce the [Documentation Principles](writing-docs.md) — duplication and wrong-audience content are flagged as issues, with direct links to the relevant writing-docs.md sections.

**When to use:** After a significant batch of changes — new commands, archived features, updated specs, or structural changes to the project.

---

### `/opsx-archive`

**Phase:** Archive

Complete a change and preserve it for the historical record.

**Usage:**
```
/opsx-archive
```

**What it does:**
1. Checks artifact and task completion
2. Syncs delta specs into main specs (if not already done)
3. Moves the change to `openspec/changes/archive/YYYY-MM-DD-<name>/`
4. All artifacts are preserved for audit trail
5. Updates or creates `docs/features/<change-name>.md` — creates it if no matching feature doc exists
6. Updates the feature overview table in `docs/features/README.md` (creates the file if it doesn't exist)
7. Creates or updates `CHANGELOG.md` — completed tasks become versioned entries (version from `app-config.json`); uses [Keep a Changelog](https://keepachangelog.com/) format

---

### `/opsx-bulk-archive`

**Phase:** Archive

Archive multiple completed changes at once.

**Usage:**
```
/opsx-bulk-archive
```

**When to use:** When you have several changes that are all complete and want to clean up.

---

### `/opsx-apply-loop`

**Phase:** Full Lifecycle (experimental)

Automated apply→verify loop for a single change in a specific app. Runs the implementation loop inside an isolated Docker container, optionally runs targeted tests on the host, then archives and syncs to GitHub.

**Usage:**
```
/opsx-apply-loop                          # asks which app + change to run
/opsx-apply-loop procest add-sla-tracking # run a specific app/change
/opsx-apply-loop openregister seed-data   # run in a different app
```

**What it does:**
1. Selects app and change (scans across all apps, or uses provided arguments)
2. Checks for a GitHub tracking issue (runs `/opsx-plan-to-issues` first if missing)
3. Creates a `feature/<issue-number>/<change-name>` branch in the app's git repo
4. Checks the Nextcloud environment is running
5. Reads `test-plan.md` (if present) and classifies which test commands to include in the loop
6. Asks whether to include a test cycle (tests run **outside the container** against the live Nextcloud app)
7. Builds and starts an isolated Docker container — mounts the app directory + shared `.claude/` skills (read-only); no git, no GitHub
8. Inside the container: runs `/opsx-apply` → `/opsx-verify` in a loop (max 5 iterations)
   - CRITICAL issues retrigger the loop; WARNING issues also retrigger but never block archive
   - At max iterations with only warnings remaining, archive still proceeds
   - Seed data (ADR-016) is created/updated during apply as required
9. Captures container logs to `.claude/logs/`, then removes container
10. **If test cycle enabled:** runs targeted single-agent test commands on the host (max 3 test iterations); failures loop back into apply→verify
11. **If test cycle enabled and deferred tests exist:** asks about multi-agent/broad tests from the test-plan that were excluded from the loop; runs them once if confirmed, with one final apply→verify if they fail
12. Runs `/opsx-archive` on the host (after tests pass or tests skipped)
13. Commits all changes in the app repo with a generated commit message
14. Syncs GitHub: updates issue checkboxes, posts a completion comment, prompts to close
15. Asks about test scenario conversion (deferred from archive)
16. Shows a final report with iterations used, tasks completed, and what's next

**When to use:** When you want hands-off implementation of a single change in one app. Prefer `/opsx-pipeline` for running multiple changes across apps in parallel.

**Container design:** The container mounts the app directory at `/workspace` and the shared `.claude/` at `/workspace/.claude` (read-only). This gives the container's Claude session access to all shared skills without requiring git or GitHub. Each app is isolated — the container only touches one app directory.

**Container limitations:** GitHub operations, `docker compose exec`, browser tests, and git commands are not available inside the container — all handled on the host after the container exits. Tests always run on the host against the live Nextcloud environment.

**Cap impact:** High — runs apply + verify sequentially (up to 5 iterations), optionally followed by targeted tests (up to 3 test iterations). Each iteration is a full implementation + verification pass.

**Model:** Sonnet recommended for most changes; Opus for complex architectural work. Asked at run time.

**Requires:**
- Docker running
- `gh` CLI authenticated on the host
- Nextcloud containers up (auto-started if not running — uses `docker compose -f` pointed at the docker-dev root's `.github/docker-compose.yml`)
- **Container authentication** — the Docker container cannot use interactive OAuth, so it needs an explicit token. One of these environment variables must be set in your shell (see [Getting Started — Container authentication](getting-started.md#prerequisites) for full setup instructions):
  1. `CLAUDE_CODE_AUTH_TOKEN` (preferred) — uses your existing Claude Max/Pro subscription at no extra cost. Generate with `claude setup-token`, then `export CLAUDE_CODE_AUTH_TOKEN="..."` in `~/.bashrc`.
  2. `ANTHROPIC_API_KEY` (fallback) — uses prepaid API credits from console.anthropic.com (costs money). `export ANTHROPIC_API_KEY="sk-ant-api03-..."` in `~/.bashrc`.

---

### `/opsx-pipeline`

**Phase:** Full Lifecycle (experimental)

Process one or more OpenSpec changes through the full lifecycle in parallel — each change gets its own subagent, git worktree, feature branch, and PR.

**Usage:**
```
/opsx-pipeline all                      # process all open proposals across all repos
/opsx-pipeline procest                  # all open proposals in one app
/opsx-pipeline sla-tracking routing     # specific changes by name
```

**What it does:**
1. Discovers open proposals (changes with `proposal.md` but not yet archived)
2. Presents an execution plan and asks for confirmation
3. Creates a git worktree and feature branch per change
4. Launches up to 5 parallel subagents — each runs ff → apply → verify → archive
5. Monitors progress and queues remaining changes as slots free up
6. Creates a PR per completed change to `development`
7. Reports full results including tasks completed, quality checks, and PR links

**Subagent lifecycle per change:**
```
ff (artifacts) → plan-to-issues → apply (implement + tests + docs) → verify → archive → push + PR
```

**When to use:** When you have multiple open proposals ready to implement and want to run them hands-off.

**Cap impact:** High — up to 5 agents running full implementations in parallel. Each agent may run for 10-30 minutes depending on change complexity.

**Model:** Asked at run time with three options: one model for all sub-agents, choose per change, or auto-select by reading each proposal. **Haiku** for simple changes (config, text, minor fixes). **Sonnet** for standard feature work. **Opus** for complex architectural changes. The model applies per implementation sub-agent — choose based on change complexity and available quota.

**Requires:** `gh` CLI authenticated; quality checks must pass per app (`composer check:strict` / `npm run lint`)

---

### `/opsx-onboard`

**Phase:** Setup

Get an overview of the current project's OpenSpec setup and active changes.

**Usage:**
```
/opsx-onboard
```

---

## OpenSpec CLI Commands

These are terminal commands (not Claude slash commands) for managing specs directly.

| Command | Description |
|---------|-------------|
| `openspec init --tools claude` | Initialize OpenSpec in a project |
| `openspec list --changes` | List all active changes |
| `openspec list --specs` | List all specs |
| `openspec show <name>` | View details of a change or spec |
| `openspec status --change <name>` | Show artifact completion status |
| `openspec validate --all` | Validate all specs and changes |
| `openspec validate --strict` | Strict validation (errors on warnings) |
| `openspec update` | Regenerate AI tool config after CLI upgrade |
| `openspec schema which` | Show which schema is being used |
| `openspec config list` | Show all configuration |

Add `--json` to any command for machine-readable output.
