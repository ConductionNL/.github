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
   - Seed data (ADR-001) is created/updated during apply as required
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

## Retrofit Commands

Used to bring legacy apps under the `@spec` annotation convention defined in [ADR-003 §Spec traceability](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-003-backend.md). Apps built spec-first via `/opsx-apply` already carry the tags — retrofit is the one-time pass for apps that predate the convention. Run the three skills in order: scan → annotate → reverse-spec. See the [Retrofit Playbook](retrofit.md) for prerequisites, bucket definitions, and roll-out order.

---

### `/opsx-coverage-scan`

**Phase:** Retrofit (experimental)

Audits an app for spec ↔ code coverage. **Read-only** — writes two report files and never touches code. Buckets every method into one of six categories to plan the retrofit work. Run this before `/opsx-annotate` or `/opsx-reverse-spec`.

**Usage:**
```
/opsx-coverage-scan                 # prompts for app (lists apps with populated specs)
/opsx-coverage-scan opencatalogi    # scan a specific app
```

**Writes:**
- `{app}/openspec/coverage-report.md` — human-readable report
- `{app}/openspec/coverage-report.json` — machine-readable sidecar consumed by `/opsx-annotate`

**Buckets produced:**
- **1** — Methods cleanly matched to an existing REQ (high confidence ≥0.85). Ready to annotate.
- **2a** — Methods in an existing capability but no REQ covers the behavior. Extend the spec.
- **2b** — Methods with no capability owner. New capability spec needed.
- **3a** — REQs whose implementation appears to have been removed (git history evidence).
- **3b** — REQs never implemented.
- **4** — ADR conformance issues (missing headers, hardcoded strings) — surfaced only.

**When to use:** Before starting a retrofit pass on any app. Re-run after each reverse-spec merge to refresh the picture.

**Guardrails:**
- Refuses to run on Haiku — REQ-matching needs Sonnet or Opus reasoning.
- Does not touch code or commit anything.
- `NEEDS-REVIEW` flag surfaces matches in the 0.70–0.85 confidence window.

**Model:** Sonnet or Opus. Haiku stops immediately.

---

### `/opsx-annotate`

**Phase:** Retrofit (experimental)

Applies the Bucket 1 matches from a recent coverage report as `@spec` tags. Creates a single **ghost change** (`retrofit-annotate-{app}-{YYYY-MM-DD}`) whose `tasks.md` is what the annotations point at, then opens an **annotation-only PR** — no logic changes, no refactors, no formatting.

**Usage:**
```
/opsx-annotate opencatalogi
```

**What it does:**
1. Reads `coverage-report.json` (must exist and be <24h old)
2. Refuses dirty working trees
3. Creates ghost change with one task per REQ with Bucket 1 matches
4. Edits each file in a single pass — file-docblock `@spec` tags + per-method `@spec` tags
5. Runs `composer phpcs` / `npm run lint` + `/hydra-gates`
6. Commits, appends the annotation commit to `.git-blame-ignore-revs`
7. Archives the ghost change
8. Pushes `retrofit/annotate-{app}-{YYYY-MM-DD}` and opens a PR (labels: `retrofit`, `annotation-only`)

**When to use:** Immediately after reviewing a coverage report's Bucket 1. Do not mix with logic changes.

**Guardrails:**
- Idempotent on already-annotated code (detects and asks before creating a fresh ghost change).
- Skips `NEEDS-REVIEW` entries — human triage first.
- Never reorders existing tags to satisfy the linter — fix the PHPCS config instead.
- Prefers Edit tool; falls back to full-file Write if a hook reverts. Never sed/awk.

**Model:** Sonnet or Opus. Haiku stops immediately.

---

### `/opsx-reverse-spec`

**Phase:** Retrofit (experimental)

Drafts a retrofit spec from observed code for **one Bucket 2 cluster per run**. Creates a ghost change with the spec delta + tasks + inline annotations in a single PR. Cap: 5 REQs per run — split larger clusters across multiple runs.

**Usage:**
```
/opsx-reverse-spec opencatalogi --extend admin-settings   # add REQs to an existing capability
/opsx-reverse-spec opencatalogi --cluster app-lifecycle   # create a brand-new capability spec
/opsx-reverse-spec opencatalogi                           # prompts — lists Bucket 2 clusters from report
```

**Flags (mutually exclusive, one required):**
- `--extend <capability>` — append REQs to an existing capability spec. Use for Bucket 2a clusters.
- `--cluster <name>` — create a new capability spec. Use for Bucket 2b clusters.

**Bias toward `--extend`.** Minting a new capability is a design decision; extending is cheaper and safer.

**What it does:**
1. Validates coverage report (<24h, matching branch)
2. Reads the cluster's methods — captures observed inputs, outputs, pre/postconditions, failure modes
3. Drafts REQs that describe **observed behavior, not aspirational intent** (bugs stay bugs; notes flag them)
4. Creates ghost change with spec delta (`retrofit_extensions: [...]` for extend, `retrofit: true` for cluster)
5. Runs `/opsx-ff` to fill in design.md
6. Annotates the cluster's methods inline (does NOT call `/opsx-annotate` — that would create a parallel ghost change)
7. Runs `sync_spec_content.py` to register with Specter's `app_specs` table
8. Archives the change (merges delta into main specs)
9. Pushes and opens a PR (labels: `retrofit`, `reverse-spec`)

**When to use:** After `/opsx-annotate` has merged. One cluster per run — each cluster is its own review cycle because REQ language is the review surface.

**Guardrails:**
- Refuses to batch clusters.
- Caps at 5 REQs per run — split larger clusters.
- Fails loudly if Specter sync fails — don't leave specs in-tree but missing from dashboards.
- Writes `retrofit: true` / `retrofit_extensions: [...]` to spec frontmatter so dashboards can filter retrofit cohorts.

**Model:** Sonnet or Opus. Haiku stops immediately — drafting REQs from code is the highest-reasoning step in the retrofit flow.

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
