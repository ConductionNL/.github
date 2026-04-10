# Command Reference

Complete reference for all commands available in the spec-driven development workflow.

## OpenSpec Built-in Commands

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

**Model:** Checked at run time — stops on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most exploration sessions. ✅ **Opus** recommended — complex analysis, architecture decisions, and strategic thinking benefit from stronger reasoning.

---

### `/opsx-apply`

**Phase:** Implementation

OpenSpec's built-in implementation command. Reads `tasks.md` and works through tasks.

**Usage:**
```
/opsx-apply
```

**Note:** `/opsx-ralph-start` (not yet built) is planned as a dedicated implementation loop with minimal context loading and deeper GitHub Issues integration. For now, use this command — it already supports `plan.json` and GitHub Issues when a `plan.json` exists.

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

**Note:** `/opsx-ralph-review` (not yet built) is planned as a dedicated review command that cross-references shared specs and creates GitHub Issues for findings. For now, use this command — it already supports GitHub Issues sync via `plan.json` when present.

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

Check and sync documentation to reflect the current project state. Two targets: **app docs** (`{app}/docs/`) for a specific Nextcloud app's users and admins, and **dev docs** (`.claude/docs/`) for Claude and developers.

**Usage:**
```
/sync-docs                       # prompts for target
/sync-docs app                   # prompts for which app, then syncs its docs/
/sync-docs app openregister      # sync docs for a specific app
/sync-docs dev                   # sync developer/Claude docs (.claude/docs/)
```

Before syncing, runs 4 preliminary checks in parallel — config.yaml rules vs writing-docs.md/writing-specs.md, Sources of Truth accuracy, writing-specs.md vs schema template alignment (`.claude/openspec/schemas/conduction/`), and forked schema drift from the upstream `spec-driven` schema. Reports gaps and asks whether to fix before proceeding.

**App docs mode** (`{app}/docs/`) — checks the app's `README.md` (root), `docs/features/`, `docs/ARCHITECTURE.md`, `docs/FEATURES.md`, `docs/GOVERNMENT-FEATURES.md`, and any other user-facing `.md` files against the app's current specs. Also loads all company-wide ADRs from `apps-extra/.claude/openspec/architecture/` and any app-level ADRs as auditing context (never as link targets in app docs). Flags outdated descriptions, missing features, stale `[Future]` markers (with full removal checklist), broken links, duplicated content, writing anti-patterns, ADR compliance gaps (screenshots, i18n, API conventions), and missing GEMMA/ZGW/Forum Standaardisatie standards references. Never inserts links into `.claude/` paths. Always shows a diff and asks for confirmation before writing.

**Dev docs mode** (`.claude/docs/`) — checks `commands.md`, `workflow.md`, `writing-specs.md`, `writing-docs.md`, `testing.md`, `getting-started.md`, `README.md`, plus the conduction schema (`.claude/openspec/schemas/conduction/schema.yaml`) and its `templates/spec.md` for alignment with `writing-specs.md`. Never changes intent without user confirmation. After syncing, runs a Phase 6 review of all commands and skills for stale references, outdated instructions, and redundant inline content — and asks whether to update them.

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

## App Management Commands

Commands for creating, configuring, and maintaining Nextcloud apps. These work together in a lifecycle: `/app-design` → `/app-create` → `/app-explore` → `/app-apply` → `/app-verify`.

For a full guide on the lifecycle, when to use each command, and how they relate to the OpenSpec workflow, see [App Lifecycle](app-lifecycle.md).

---

### `/app-design`

**Phase:** Setup / Design

Full upfront design for a new Nextcloud app — architecture research, competitor analysis, feature matrix, ASCII wireframes, and OpenSpec setup. Run this **before** `/app-create` for brand-new apps.

**Usage:**
```
/app-design
/app-design my-new-app
```

**What it does:**
1. Researches the problem domain and existing solutions
2. Produces architecture decisions, feature matrix, and ASCII wireframes
3. Sets up the `openspec/` structure with initial design docs

**Output:** Design documentation ready to hand off to `/app-create`.

**Model:** Checked at run time — stops on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for general design sessions. ✅ **Opus** recommended — competitive research, architecture decisions, and full design document creation benefit from stronger reasoning.

---

### `/app-create`

**Phase:** Setup

Bootstrap a new Nextcloud app from the ConductionNL template, or onboard an existing repo. Always creates an `openspec/` configuration folder that tracks all app decisions.

**Usage:**
```
/app-create
/app-create my-new-app
```

**What it does:**
1. Asks whether a local folder already exists — if yes, uses it as the base; if no, clones the template
2. Collects basic identity: app ID, name, goal, one-line summary, Nextcloud category
3. Asks about dependencies (OpenRegister, additional CI apps)
4. Creates `openspec/app-config.json` and `openspec/README.md`
5. Replaces all template placeholders (`AppTemplate`, `app-template`, etc.) across all files
6. Creates the GitHub repository and branches (`main`, `development`, `beta`)
7. Optionally sets branch protection and team access
8. Optionally installs dependencies and enables the app in the local Nextcloud environment

**Output:** Fully scaffolded app directory with correct identity, CI/CD workflows, and GitHub repo.

**Requires:** `gh` CLI authenticated (`gh auth login`)

---

### `/app-explore`

**Phase:** Design / Configuration

Enter exploration mode for a Nextcloud app. Think through its goals, architecture, features, and Architectural Decision Records (ADRs). Updates `openspec/` files to capture decisions.

**Usage:**
```
/app-explore
/app-explore openregister
```

**What it does:**
- Loads `openspec/app-config.json` for full context
- Acts as a **thinking partner** — draws diagrams, asks questions, challenges assumptions
- Captures decisions into `openspec/app-config.json`
- Never writes application code — only `openspec/` files

**Feature lifecycle:**
```
idea → planned → in-progress → done
```
When a feature moves to `planned` (has user stories + acceptance criteria), suggests `/opsx-ff {feature-name}` to create an OpenSpec change from it.

**Important:** Run this before implementing anything. Features defined here become the inputs for `/opsx-ff`.

**Model:** Checked at run time — stops on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for general app exploration. ✅ **Opus** recommended — feature strategy, ADRs, and competitive analysis benefit from stronger reasoning.

---

### `/app-apply`

**Phase:** Configuration

Applies `openspec/app-config.json` decisions back into the actual app files. The counterpart to `/app-explore`.

**Usage:**
```
/app-apply
/app-apply openregister
```

**What it does:**
1. Loads `openspec/app-config.json`
2. Compares current file values against config — builds a list of pending changes
3. Shows a clear diff summary of what would change
4. Asks for confirmation before applying any changes
5. Updates only the tracked values in each file (IDs, names, namespaces, CI parameters) — never touches feature code
6. Optionally runs `composer check:strict` to verify PHP changes are clean

**In scope:** `appinfo/info.xml`, CI/CD workflow parameters, PHP namespaces and app ID constants, `composer.json`/`package.json` names, `webpack.config.js` app ID, `src/App.vue` OpenRegister gate, `README.md` header.

**Out of scope:** Feature code, business logic, Vue components, PHP controllers. Use `/opsx-ff {feature-name}` for those.

---

### `/app-verify`

**Phase:** Review / Audit

Read-only audit. Checks every tracked app file against `openspec/app-config.json` and reports drift — without making any changes.

**Usage:**
```
/app-verify
/app-verify openregister
```

**What it does:**
- Loads `openspec/app-config.json` and reads every tracked file
- Reports each check as **CRITICAL** (will break CI or runtime), **WARNING** (wrong metadata), or **INFO** (cosmetic drift)
- Shows exact current value vs expected value for every failing check
- Recommends `/app-apply` if issues are found

**When to use:** After `/app-apply` to confirm changes landed, or at any time to check for drift.

---

### `/clean-env`

**Phase:** Setup / Reset

Fully resets the OpenRegister Docker development environment.

**Usage:**
```
/clean-env
```

**What it does:**
1. Stops all Docker containers from the OpenRegister docker-compose
2. Removes all containers and volumes (full data reset)
3. Starts containers fresh
4. Waits for Nextcloud to become ready
5. Installs core apps: openregister, opencatalogi, softwarecatalog, nldesign, mydash

**Important:** Destructive — removes all database data and volumes. Only use when a full reset is intended.

After completion, verify at `http://localhost:8080` (admin/admin).

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

## Team Role Commands

Specialist agents representing different roles on the development team. Useful for getting a focused perspective on a change — architecture review, QA, product sign-off, etc.

| Command | Role | Focus |
|---------|------|-------|
| `/team-architect` | Architect | API design, data models, cross-app dependencies |
| `/team-backend` | Backend Developer | PHP implementation, entities, services, tests |
| `/team-frontend` | Frontend Developer | Vue components, state management, UX |
| `/team-po` | Product Owner | Business value, acceptance criteria, priority |
| `/team-qa` | QA Engineer | Test coverage, edge cases, regression risk |
| `/team-reviewer` | Code Reviewer | Standards, conventions, security, code quality |
| `/team-sm` | Scrum Master | Progress tracking, blockers, sprint health |

**Usage:**
```
/team-architect    # review the API design for the active change
/team-qa          # get QA perspective on test coverage
```

**Model for `/team-architect`:** Checked at run time — stops if on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Opus** recommended — best multi-framework reasoning across NLGov, BIO2/NIS2, WCAG, Haven, AVG/GDPR. **Sonnet** not recommended — may miss nuances in complex compliance scenarios.

---

## Softwarecatalogus Commands (`/swc:*`)

Commands specific to the VNG Softwarecatalogus client project. See `Softwarecatalogus/` (never commit to this repo).

---

### `/swc-test`

**Phase:** Testing

Run automated tests for the GEMMA Softwarecatalogus — API tests (Postman/Newman), browser tests (persona agents), or both.

**Usage:**
```
/swc-test           # choose mode interactively
/swc-test api       # API tests only
/swc-test browser   # browser tests only
/swc-test personas  # all 8 persona agents
/swc-test all       # everything
```

---

### `/swc-update`

**Phase:** Maintenance

Sync GitHub issues from VNG-Realisatie/Softwarecatalogus, auto-generate acceptance criteria, and update test infrastructure to reflect current issue state.

**Usage:**
```
/swc-update
```

---

## Custom Conduction Commands

These commands are workspace-level and available from any project within `apps-extra/`. They extend OpenSpec with GitHub Issues integration and Ralph Wiggum loops.

---

### `/create-pr`

**Phase:** Git / Delivery

Create a Pull Request from a branch in any repo. Handles the full flow interactively.

**Usage:**
```
/create-pr
```

**What it does:**
1. **Selects the repository** — scans for available git repos in the workspace, asks you to pick one (never assumes the current directory)
2. **Confirms the source branch** — shows the current branch, lets you override
3. **Recommends a target branch** based on the branching strategy; checks GitHub for an existing open PR on the same branch pair — if found, offers to view or update it instead
4. **Checks for uncommitted or unpushed changes** — if any are found, offers to commit, stash, or continue; offers to push unpushed commits before continuing
5. **Verifies global settings version** *(claude-code-config repo only)* — delegates to `/verify-global-settings-version`; pauses and offers a fix if a VERSION bump is missing
6. **Discovers CI checks from `.github/workflows/`** — reads the repo's workflow files to determine exactly which checks CI will run, then mirrors them locally (never hardcodes a list)
7. **Installs missing dependencies** (`vendor/`, `node_modules/`) if needed before running checks
8. **Runs all discovered checks** — nothing skipped; slow checks (e.g. test suites) ask for confirmation first; shows a pass/fail table when done
9. **Reads all commits and diffs** on the branch to draft a PR title and description from the actual changes
10. **Shows the draft in chat** for review — you can ask to change or shorten it; the loop repeats until you approve
11. **Pushes the branch and creates the PR** via `gh pr create`
12. Reports the PR URL and next steps

**Branching strategy:**

| Source | Recommended target |
|---|---|
| `feature/*`, `bugfix/*` | `development` |
| `development` | `beta` |
| `beta` | `main` |
| `hotfix/*` | `main` (or `beta`/`development`) |

**Model:** Checked at run time — the command reads your active model from context and stops automatically if you're on Haiku (or anything weaker than Sonnet). Involves parsing CI workflows, detecting branch-protection rules, and reasoning about code diffs where mistakes have real consequences. **Sonnet** for most PRs. **Opus** when the repo uses reusable CI workflows, branch-protection rulesets, or a complex branching strategy — that's where it pays off most.

**Requires:** `gh` CLI authenticated (`gh auth login`)

---

### `/verify-global-settings-version`

**Phase:** Git / Delivery

Checks whether `global-settings/VERSION` has been correctly bumped after any changes to files in the `global-settings/` directory. Run this before creating a PR on the `ConductionNL/claude-code-config` repo.

**Usage:**
```
/verify-global-settings-version
```

**What it does:**
1. Fetches `origin/main` to get the latest published version
2. Diffs `global-settings/` between the current branch and `origin/main`
3. Compares the branch `VERSION` against the `origin/main` `VERSION`
4. Reports one of four outcomes:
   - ✅ No changes to `global-settings/` — no bump needed
   - ✅ Changes found and `VERSION` correctly bumped
   - ❌ Changes found but `VERSION` not bumped — suggests the next semver and the command to apply it
   - ⚠️ `VERSION` bumped but no other files changed — flags as unusual

**When to use:**
- Standalone: any time you modify a file in `global-settings/` and want to confirm the bump is in place before committing
- Automatically: called by `/create-pr` when the selected repo is `ConductionNL/claude-code-config` — no need to run it separately in that flow

**Semver rules for `global-settings/`:**
- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

### `/opsx-plan-to-issues`

**Phase:** Planning → GitHub

Converts an OpenSpec change's `tasks.md` into structured `plan.json` and creates corresponding GitHub Issues.

**Usage:**
```
/opsx-plan-to-issues
```

**Prerequisites:**
- A change with completed `tasks.md`
- GitHub MCP server active or `gh` CLI authenticated
- Git remote pointing to a ConductionNL repository

**What it does:**

1. **Finds the active change** in the current project's `openspec/changes/`
2. **Detects the GitHub repo** from `git remote get-url origin`
3. **Parses tasks.md** into structured JSON
4. **Creates GitHub Issues:**
   - One **tracking issue** (epic) with:
     - Title: `[OpenSpec] <change-name>`
     - Body: proposal summary + task checklist
     - Labels: `openspec`, `tracking`
   - One **issue per task** with:
     - Title: `[<change-name>] <task title>`
     - Body: description, acceptance criteria, spec ref, affected files
     - Labels: `openspec`, `<change-name>`
5. **Saves `plan.json`** with all issue numbers linked

**Output example:**
```
Created tracking issue: https://github.com/ConductionNL/opencatalogi/issues/42
Created 5 task issues: #43, #44, #45, #46, #47
Saved plan.json at: openspec/changes/add-search/plan.json

Run /opsx-ralph-start to begin implementation.
```

**The plan.json it creates:**
```json
{
  "change": "add-search",
  "project": "opencatalogi",
  "repo": "ConductionNL/opencatalogi",
  "created": "2026-02-15T10:00:00Z",
  "tracking_issue": 42,
  "tasks": [
    {
      "id": 1,
      "title": "Create SearchController",
      "description": "Add new controller for search API endpoint",
      "github_issue": 43,
      "status": "pending",
      "spec_ref": "openspec/specs/search/spec.md#requirement-search-api",
      "acceptance_criteria": [
        "GIVEN a search query WHEN GET /api/search?q=test THEN returns matching results"
      ],
      "files_likely_affected": [
        "lib/Controller/SearchController.php"
      ],
      "labels": ["openspec", "add-search"]
    }
  ]
}
```

---

### `/opsx-ralph-start` *(not yet implemented)*

**Phase:** Implementation

Starts a Ralph Wiggum implementation loop driven by `plan.json`. This is the core of our minimal-context coding approach.

**Usage:**
```
/opsx-ralph-start
```

**Prerequisites:**
- A `plan.json` in the active change (created by `/opsx-plan-to-issues`)

**What it does per iteration:**

1. **Reads plan.json** — finds the next task with `"status": "pending"`
2. **Sets status to `"in_progress"`** in plan.json
3. **Reads ONLY the referenced spec section** — uses `spec_ref` to load just the relevant requirement, NOT the entire spec file
4. **Implements the task** — following acceptance criteria and coding standards
5. **Verifies** — checks acceptance criteria are met
6. **Updates progress:**
   - Sets task to `"completed"` in plan.json
   - Checks off boxes in tasks.md
   - Closes the GitHub issue with a summary comment
   - Updates the tracking issue checklist
7. **Loops** — picks up the next pending task, or stops if all done

**Why minimal context matters:**

Each iteration loads only:
- `plan.json` (the task list — typically 1-2 KB)
- One spec section via `spec_ref` (the specific requirement — a few paragraphs)
- The affected files

It does NOT load:
- proposal.md
- design.md
- Other spec files
- The full tasks.md

This prevents context window bloat and keeps each iteration fast and focused.

**Resuming after interruption:**

If the loop is interrupted (context limit, error, etc.), simply run `/opsx-ralph-start` again. It reads `plan.json`, finds the first non-completed task, and continues from there.

---

### `/opsx-ralph-review` *(not yet implemented)*

**Phase:** Review

Verifies the completed implementation against all spec requirements and shared conventions. Creates a structured review report.

**Usage:**
```
/opsx-ralph-review
```

**Prerequisites:**
- All tasks in plan.json should be `"completed"`

**What it does:**

1. **Loads full context** — proposal, all delta specs, tasks, plan.json
2. **Checks completeness:**
   - All tasks completed?
   - All GitHub issues closed?
   - All task checkboxes checked?
3. **Checks spec compliance:**
   - For each ADDED requirement: does the implementation exist?
   - For each MODIFIED requirement: is the old behavior changed?
   - For each REMOVED requirement: is the deprecated code gone?
   - Do GIVEN/WHEN/THEN scenarios match the code behavior?
4. **Cross-references shared specs:**
   - `nextcloud-app/spec.md` — correct app structure, DI, route ordering
   - `api-patterns/spec.md` — URL patterns, CORS, error responses
   - `nl-design/spec.md` — design tokens, accessibility
   - `docker/spec.md` — environment compatibility
5. **Categorizes findings:**
   - **CRITICAL** — Spec MUST/SHALL requirement not met
   - **WARNING** — SHOULD requirement not met or partial compliance
   - **SUGGESTION** — Improvement opportunity
6. **Generates `review.md`** in the change directory
7. **Creates GitHub Issue** if CRITICAL/WARNING findings exist

**Output example:**
```
Review: add-search
Tasks completed: 5/5
GitHub issues closed: 5/5
Spec compliance: PASS (with warnings)

Findings:
- 0 CRITICAL
- 2 WARNING
  - Missing CORS headers on /api/search (api-patterns spec)
  - No pagination metadata in response (api-patterns spec)
- 1 SUGGESTION
  - Consider adding rate limiting

Review saved: openspec/changes/add-search/review.md
GitHub issue created: #48 [Review] add-search: 0 critical, 2 warnings
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

---

## Testing Commands

For detailed guidance on when to use each command, typical testing workflows, and situational advice, see [testing.md](testing.md).

> **Note on agentic browser testing:** `/test-app`, `/test-counsel`, and `/feature-counsel` use Playwright MCP browsers to explore live applications. Results may include false positives (elements not found due to timing) or false negatives (bugs missed due to exploration order). Always verify critical findings manually.

---

### `/test-app`

**Phase:** Testing

Run automated browser tests for any Nextcloud app in this workspace. Explores every page, button, and form guided by the app's documentation and specs.

**Usage:**
```
/test-app
/test-app procest
```

**Modes:**
- **Quick (1 agent)** — One agent walks through the entire app. Fast, good for smoke testing. Low cap impact.
- **Full (6 agents)** — Six parallel agents each with a different perspective: Functional, UX, Performance, Accessibility, Security, API. More thorough. High cap impact.

**What it does:**
1. Selects the app (from argument or prompt)
2. Chooses Quick or Full mode
3. Checks `{APP}/test-scenarios/` for active scenarios — asks whether to include them
4. Reads `{APP}/docs/features/` to understand what to test
5. Asks which model to use for agents (Haiku default, Sonnet, or Opus)
6. Launches agents, each reading docs, logging in, and testing from their perspective
7. Agents execute any included test scenario steps before free exploration
8. Writes per-perspective results to `{APP}/test-results/` and a summary to `{APP}/test-results/README.md`

**Model:** Asked at run time (applies to all sub-agents). **Haiku** (default) — fastest, lowest quota cost. **Sonnet** — more nuanced analysis, larger context window. **Opus** — deepest coverage; significant quota cost in Full mode. See [parallel-agents.md](parallel-agents.md) for context window sizes, subscription quota limits, and how they differ.

**Cap impact:** See [parallel-agents.md](parallel-agents.md).

---

### `/test-counsel`

**Phase:** Testing

Test a Nextcloud app from 8 persona perspectives simultaneously: Henk, Fatima, Sem, Noor, Annemarie, Mark, Priya, Jan-Willem.

**Usage:**
```
/test-counsel
```

**What it does:**
- Launches 8 parallel browser agents — one per persona (model is user-selected at run time; Haiku is the default)
- Each agent reads its persona card and relevant test scenarios before testing
- Tests from the perspective of that persona's role, technical level, and priorities
- Produces a combined report with findings per persona
- Writes results to `{APP}/test-results/`

**Model:** Asked at run time (applies to all 8 agents). **Haiku** (default) — fastest, lowest quota cost. **Sonnet** — more nuanced persona findings, larger context window. **Opus** — deepest analysis; significant quota cost with 8 agents. See [parallel-agents.md](parallel-agents.md) for context window sizes, subscription quota limits, and how they differ.

**Cap impact:** Very high — 8 parallel agents. Open a fresh Claude window before running. See [parallel-agents.md](parallel-agents.md).

---

### `/feature-counsel`

**Phase:** Discovery / Ideation

Analyse a Nextcloud app's OpenSpec from 8 persona perspectives and suggest additional features or improvements.

**Usage:**
```
/feature-counsel
```

**What it does:**
- Reads the app's OpenSpec, specs, and existing features
- Each of the 8 personas considers what's missing from their perspective
- Produces a consolidated list of suggested features and improvements
- Does not test the live app — reads specs and docs only

**Model:** Asked at run time (applies to all 8 agents). No browser required — agents read specs and docs only. **Sonnet** (default) — recommended; no context window concern without browser snapshots, and better reasoning produces more useful suggestions. **Haiku** — faster, lower quota, good for a quick broad pass. **Opus** — deepest reasoning for complex architectural gaps; use with full mode (8 agents) sparingly.

**Cap impact:** Very high — 8 parallel agents. See [parallel-agents.md](parallel-agents.md).

---

### Commands (Single-Agent)

---

### `/test-functional`

**Phase:** Testing

Feature correctness via browser — executes GIVEN/WHEN/THEN scenarios from specs against the live app.

**Usage:**
```
/test-functional
```

---

### `/test-api`

**Phase:** Testing

REST API endpoint testing. Checks endpoints, authentication, pagination, and error responses.

**Usage:**
```
/test-api
```

---

### `/test-accessibility`

**Phase:** Testing

WCAG 2.1 AA compliance using axe-core, plus manual keyboard and focus checks.

**Usage:**
```
/test-accessibility
```

---

### `/test-performance`

**Phase:** Testing

Load times, API response times, and network request analysis via browser timing APIs.

**Usage:**
```
/test-performance
```

---

### `/test-security`

**Phase:** Testing

OWASP Top 10, Nextcloud roles, authorization, XSS, CSRF, sensitive data exposure.

**Usage:**
```
/test-security
```

---

### `/test-regression`

**Phase:** Testing

Cross-feature regression — verifies changes don't break unrelated flows.

**Usage:**
```
/test-regression
```

---

### `/test-persona-*`

**Phase:** Testing

Single-persona deep dive. Use when you want one persona's full assessment without launching all eight:

| Command | Persona | Role |
|---------|---------|------|
| `/test-persona-henk` | **Henk Bakker** | Elderly citizen — low digital literacy |
| `/test-persona-fatima` | **Fatima El-Amrani** | Low-literate migrant citizen |
| `/test-persona-sem` | **Sem de Jong** | Young digital native |
| `/test-persona-noor` | **Noor Yilmaz** | Municipal CISO / functional admin |
| `/test-persona-annemarie` | **Annemarie de Vries** | VNG standards architect |
| `/test-persona-mark` | **Mark Visser** | MKB software vendor |
| `/test-persona-priya` | **Priya Ganpat** | ZZP developer / integrator |
| `/test-persona-janwillem` | **Jan-Willem van der Berg** | Small business owner |

**Usage:**
```
/test-persona-henk
/test-persona-priya
```

**Use when:** You know which persona is most affected by a change, or when you've run `/test-counsel` and want a deeper single-perspective follow-up. One agent instead of eight — lower cap cost.

**Cap impact:** Low — single agent. See [parallel-agents.md](parallel-agents.md).

---

## Test Scenario Commands

Test scenarios are reusable, Gherkin-style descriptions of user journeys that can be executed by any test command. They live in `{APP}/test-scenarios/TS-NNN-slug.md` and are automatically discovered by `/test-app`, `/test-counsel`, and `/test-persona-*` when they run.

> **Test scenario vs test case**: A scenario is a high-level, user-centered description of *what* to verify and *for whom* — one concrete flow, written in Given-When-Then. It is broader than a click-by-click test case but more specific than a spec requirement.

---

### `/test-scenario-create`

**Phase:** Testing

Guided wizard for creating a well-structured test scenario for a Nextcloud app.

**Usage:**
```
/test-scenario-create
/test-scenario-create openregister
```

**What it does:**
1. Determines the next ID (`TS-NNN`) by scanning existing scenarios
2. Asks for title, goal, category (functional/api/security/accessibility/performance/ux/integration), and priority
3. Shows relevant personas and asks which this scenario targets
4. Suggests which test commands should automatically include it
5. Auto-suggests tags based on category and title
6. Guides through Gherkin steps (Given/When/Then), test data, and acceptance criteria
7. Generates persona-specific notes for each linked persona
8. Saves to `{APP}/test-scenarios/TS-NNN-slug.md`

**Scenario categories and suggested personas:**

| Category | Suggested personas |
|---|---|
| functional | Mark Visser, Sem de Jong |
| api | Priya Ganpat, Annemarie de Vries |
| security | Noor Yilmaz |
| accessibility | Henk Bakker, Fatima El-Amrani |
| ux | Henk Bakker, Jan-Willem, Mark Visser |
| performance | Sem de Jong, Priya Ganpat |
| integration | Priya Ganpat, Annemarie de Vries |

---

### `/test-scenario-run`

**Phase:** Testing

Execute one or more test scenarios against the live Nextcloud environment using a browser agent.

**Usage:**
```
/test-scenario-run                        # list and choose
/test-scenario-run TS-001                 # run specific scenario
/test-scenario-run openregister TS-001    # run from specific app
/test-scenario-run --tag smoke            # run all smoke-tagged scenarios
/test-scenario-run --all openregister     # run all scenarios for an app
/test-scenario-run --persona priya-ganpat # run all Priya's scenarios
```

**What it does:**
1. Discovers scenario files in `{APP}/test-scenarios/`
2. Filters by tag, persona, or ID as specified
3. Asks which environment to test against (local or custom URL)
4. Asks whether to use Haiku (default, cost-efficient) or Sonnet (for complex flows)
5. Launches a browser agent per scenario (parallelised up to 5 for multiple)
6. Agent verifies preconditions, follows Given-When-Then steps, checks each acceptance criterion
7. Writes results to `{APP}/test-results/scenarios/`
8. Synthesises a summary report for multiple runs

**Model:** Asked at run time. **Haiku** (default) — fast, cost-efficient. **Sonnet** — for complex multi-step flows or ambiguous UI states where Haiku may misread the interface. Cap cost scales with the number of scenarios run in parallel.

**Cap impact:** Low for single scenario; medium for multiple. See [parallel-agents.md](parallel-agents.md).

**Result statuses**: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL / ⛔ BLOCKED

---

### `/test-scenario-edit`

**Phase:** Testing

Edit an existing test scenario — update any field (metadata or content) interactively.

**Usage:**
```
/test-scenario-edit                      # list all scenarios, pick one
/test-scenario-edit TS-001               # open specific scenario
/test-scenario-edit openregister TS-001  # open from specific app
```

**What it does:**
1. Locates the scenario file
2. Shows a summary of current values (status, priority, category, personas, tags, spec refs)
3. Asks what scope to edit: metadata only / content only / both / status only / tags only
4. Walks through each field in scope, showing the current value and asking for the new one
5. Supports `+tag` / `-tag` syntax for incremental tag changes, same for personas
6. Regenerates persona notes if the personas list changed
7. Optionally renames the file if the title changed
8. Writes the updated file and shows a diff-style summary

---

### How existing test commands use scenarios

| Command | Behaviour when scenarios exist |
|---|---|
| `/test-app` | Asks to include active scenarios before launching agents. Agents execute scenario steps before free exploration. |
| `/test-counsel` | Asks to include scenarios, grouped by persona. Each persona agent receives only the scenarios tagged with their slug. |
| `/test-persona-*` | Scans for scenarios matching that persona's slug. Asks to run them before free exploration in Step 2. |

---

## Tender & Ecosystem Intelligence Commands

These commands support the competitive analysis and ecosystem gap-finding workflow. They operate on the `concurrentie-analyse/intelligence.db` SQLite database and require the database to exist before running.

---

### `/tender-scan`

**Phase:** Intelligence Gathering

Scrape TenderNed for new tenders, import them into SQLite, and classify unclassified tenders by software category using a local Qwen model.

**Usage:**
```
/tender-scan
```

**What it does:**
1. Runs `concurrentie-analyse/tenders/scrape_tenderned.py` to fetch fresh data
2. Imports new tenders into the intelligence database
3. Classifies unclassified tenders using Qwen via `localhost:11434`
4. Reports new tenders found, classified, and any new gaps detected

**Requires:** Local Qwen model running on Ollama (`http://localhost:11434`)

---

### `/tender-status`

**Phase:** Intelligence Monitoring

Show a dashboard of the tender intelligence database — totals by source, category, status, gaps, and recent activity.

**Usage:**
```
/tender-status
```

**What it does:**
- Queries `concurrentie-analyse/intelligence.db` for live stats
- Shows tenders by source, status, and category (top 15)
- Highlights categories with Conduction coverage vs gaps
- Shows top integration systems and ecosystem gaps

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

### `/tender-gap-report`

**Phase:** Gap Analysis

Generate a gap analysis report — software categories that appear in government tenders but have no Conduction product.

**Usage:**
```
/tender-gap-report
```

**What it does:**
1. Queries the database for categories with tenders but no `conduction_product`
2. Generates a markdown report at `concurrentie-analyse/reports/gap-report-{date}.md`
3. Includes top 5 gaps with tender details, organisations, and key requirements
4. Cross-references with `application-roadmap.md` to flag already-tracked gaps
5. Recommends which gaps to investigate first

---

### `/ecosystem-investigate <category>`

**Phase:** Competitive Research

Deep-dive research into a software category — find and analyze open-source competitors using GitHub, G2, Capterra, AlternativeTo, and TEC.

**Usage:**
```
/ecosystem-investigate bookkeeping
```

**What it does:**
1. Loads category context and related tenders from the intelligence database
2. Uses the browser pool (browser-1 through browser-5) to scrape 5-10 competitors from multiple source types
3. Creates competitor profiles in `concurrentie-analyse/{category}/{competitor-slug}/`
4. Inserts competitors and feature data into the database with provenance tracking
5. Presents a comparison table and recommendation for Nextcloud ecosystem fit

**Model:** Checked at run time — stops if on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most categories. **Opus** for high-stakes or complex categories where strategic depth matters.

---

### `/ecosystem-propose-app <category>`

**Phase:** Product Planning

Generate a full app proposal for a software category gap, using tender requirements and competitor research as input.

**Usage:**
```
/ecosystem-propose-app bookkeeping
```

**What it does:**
1. Gathers all tenders, requirements, competitors, and integrations for the category
2. Generates a structured proposal following the template in `concurrentie-analyse/application-roadmap.md`
3. Appends the proposal to `application-roadmap.md`
4. Inserts the proposal into the `app_proposals` database table
5. Optionally bootstraps the app with `/app-create`

**Model:** Checked at run time — stops if on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most proposals. **Opus** for high-stakes proposals where architectural fit and market analysis need extra depth.

---

### `/intelligence-update [source]`

**Phase:** Intelligence Maintenance

Pull latest data from external sources into the intelligence database. Syncs sources that are past their scheduled interval.

**Usage:**
```
/intelligence-update              # sync all sources that are due
/intelligence-update all          # force sync every source
/intelligence-update wikidata-software  # sync one specific source
```

**Sources and intervals:**

| Source | Interval |
|--------|----------|
| `tenderned` | 24h |
| `wikidata-software` | 7 days |
| `wikipedia-comparisons` | 7 days |
| `awesome-selfhosted` | 7 days |
| `github-issues` | 7 days |
| `dpg-registry` | 7 days |
| `developers-italia` | 7 days |
| `gemma-release` | yearly |

**What it does:**
1. Checks `source_syncs` table for overdue sources
2. Runs `concurrentie-analyse/scripts/sync/sync_{source}.py` for each
3. Updates sync status, records count, and error messages
4. Displays a summary table of all sources with their sync status

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

### Tender Intelligence Workflow

```
/tender-scan              (fetch & classify new tenders)
       │
       ▼
/tender-status            (review dashboard)
       │
       ▼
/tender-gap-report        (identify gaps)
       │
       ▼
/ecosystem-investigate    (research competitors for top gap)
       │
       ▼
/ecosystem-propose-app    (generate app proposal)
       │
       ▼
/app-design          (design the new app)
```

**Keep data fresh:** Run `/intelligence-update` weekly and `/tender-scan` daily to keep the database current.

---

## Command Flow Cheat Sheet

```
/opsx-explore           (optional: investigate first)
       │
       ▼
/opsx-new <name>        (start a change)
       │
       ▼
/opsx-ff                (generate all specs at once)
       │                   OR
/opsx-continue          (generate specs one by one)
       │
       ▼
  [Human review & edit specs]
       │
       ▼
/feature-counsel        (optional: 8-persona feedback on specs)
       │
       ▼
/opsx-plan-to-issues    (optional: tasks → JSON + GitHub Issues)
       │
       ▼
/opsx-apply             (implement tasks)
       │
       ▼
/opsx-verify            (verify implementation against specs)
       │
       ▼
/test-functional   (confirm feature behaves as specced)
/test-counsel           (user acceptance — all 8 personas)
/test-app               (optional: full technical sweep)
       │
       ▼
/create-pr              (create PR on GitHub)
       │
       ▼
/opsx-archive           (complete & preserve)
```

See [testing.md](testing.md) for situational testing guidance and recommended testing order.

For the app lifecycle flow (`/app-design` → `/app-create` → `/app-explore` → `/app-apply` → `/app-verify`), see [app-lifecycle.md](app-lifecycle.md).
