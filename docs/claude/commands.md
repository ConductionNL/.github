# Command Reference

Complete reference for all commands available in the spec-driven development workflow. Commands are organized by domain — click through to the detailed reference for each area.

## OpenSpec Commands

Full spec-driven workflow: create changes, generate artifacts, implement, verify, and archive.

For the complete reference, see [commands-openspec.md](commands-openspec.md).

| Command | Phase | Description |
|---------|-------|-------------|
| `/opsx-new <name>` | Spec | Start a new change |
| `/opsx-ff` | Spec | Fast-forward all artifacts (proposal → specs → design → tasks) |
| `/opsx-continue` | Spec | Create next artifact in dependency chain |
| `/opsx-explore` | Pre-spec | Investigate before starting a formal change |
| `/opsx-apply` | Implement | Implement tasks from plan.json |
| `/opsx-verify` | Review | Verify implementation against specs |
| `/opsx-sync` | Archive | Merge delta specs into main specs |
| `/opsx-archive` | Archive | Complete and preserve change |
| `/opsx-bulk-archive` | Archive | Archive multiple completed changes at once |
| `/opsx-apply-loop` | Full Lifecycle | Automated apply→verify loop in Docker container |
| `/opsx-pipeline` | Full Lifecycle | Parallel multi-change lifecycle (up to 5 agents) |
| `/opsx-onboard` | Setup | Overview of current OpenSpec setup |

**Retrofit commands** (bringing legacy apps under [ADR-003 §Spec traceability](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-003-backend.md)): `/opsx-coverage-scan`, `/opsx-annotate`, `/opsx-reverse-spec` — see [retrofit.md](retrofit.md) for the full playbook.

**OpenSpec CLI** (terminal commands, not slash commands): `openspec init`, `openspec list`, `openspec validate`, etc. — see [commands-openspec.md](commands-openspec.md#openspec-cli-commands).

---

## App Management Commands

Commands for creating, configuring, and maintaining Nextcloud apps: `/app-design` → `/app-create` → `/app-explore` → `/app-apply` → `/app-verify`.

For the full lifecycle guide, see [app-lifecycle.md](app-lifecycle.md).

| Command | Phase | Description |
|---------|-------|-------------|
| `/app-design` | Design | Full upfront design — architecture, competitors, wireframes |
| `/app-create` | Setup | Bootstrap or onboard a Nextcloud app |
| `/app-explore` | Design | Think through goals, features, and ADRs |
| `/app-apply` | Configuration | Apply `app-config.json` to tracked files |
| `/app-verify` | Audit | Read-only check for config drift |
| `/clean-env` | Reset | Fully reset Docker development environment |

---

## Testing Commands

All testing commands — persona-based sweeps, perspective-based sweeps, single-agent tests, and test scenario management.

For the complete reference, workflows, and when-to-use guidance, see [testing.md](testing.md).

| Command | Type | Description |
|---------|------|-------------|
| `/test-counsel` | Skill (8 agents) | Persona-based testing — all 8 personas in parallel |
| `/test-app` | Skill (1 or 6) | Perspective-based sweep (functional, UX, a11y, perf, security, API) |
| `/feature-counsel` | Skill (8 agents) | Pre-build spec analysis from 8 persona perspectives |
| `/test-functional` | Command (1 agent) | Feature correctness via GIVEN/WHEN/THEN |
| `/test-api` | Command (1 agent) | REST API endpoint testing |
| `/test-accessibility` | Command (1 agent) | WCAG 2.1 AA compliance |
| `/test-performance` | Command (1 agent) | Load times and API response |
| `/test-security` | Command (1 agent) | OWASP Top 10, roles, authorization |
| `/test-regression` | Command (1 agent) | Cross-feature regression |
| `/test-persona-*` | Command (1 agent) | Single-persona deep dive |
| `/test-scenario-create` | Command | Create a reusable test scenario |
| `/test-scenario-run` | Command | Execute test scenarios against live env |
| `/test-scenario-edit` | Command | Edit an existing test scenario |

---

## Team Role Commands

Specialist agents for focused perspectives on a change. For full details, see [workflow.md](workflow.md#team-role-commands).

| Command | Role | Focus |
|---------|------|-------|
| `/team-architect` | Architect | API design, data models, cross-app dependencies |
| `/team-backend` | Backend Developer | PHP implementation, entities, services, tests |
| `/team-frontend` | Frontend Developer | Vue components, state management, UX |
| `/team-po` | Product Owner | Business value, acceptance criteria, priority |
| `/team-qa` | QA Engineer | Test coverage, edge cases, regression risk |
| `/team-reviewer` | Code Reviewer | Standards, conventions, security, code quality |
| `/team-sm` | Scrum Master | Progress tracking, blockers, sprint health |

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

These commands are workspace-level and available from any project within `apps-extra/`. They extend OpenSpec with GitHub Issues integration.

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
5. **Verifies global settings version** *(.github repo only)* — delegates to `/verify-global-settings-version`; pauses and offers a fix if a VERSION bump is missing
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

### `/review-pr`

**Phase:** Delivery / Code Review

Review one or more GitHub Pull Requests. Fetches the diff, detects prior reviews (skips if nothing has changed since last review), asks for strictness level, posts inline findings with emoji severity markers (🔴 blocker / 🟡 warning / 🟢 suggestion), and submits a formal APPROVE or REQUEST_CHANGES decision.

**Usage:**
```
/review-pr 123                                               # single PR, infer repo from git remote
/review-pr https://github.com/org/repo/pull/123             # single PR, explicit URL
/review-pr 123 456                                           # batch: two PRs reviewed in parallel
/review-pr https://github.com/org/repo/pull/123 https://github.com/org/repo/pull/456
```

**Strictness modes:**

| Mode | Use when |
|------|----------|
| **Quick** | Hotfix or trivial change — check for obvious blockers only |
| **Standard** | Everyday feature PR — balanced depth |
| **Thorough** | Large or complex PR — full analysis |
| **Strict** | Security-sensitive code (auth, RBAC, CI) — maximum depth; auto-suggested when sensitive code is detected |

**What it does:**
1. **Detects re-reviews** — checks if anything has changed since your last review; skips if not
2. **Classifies sensitivity** — auto-detects auth/RBAC/CI code and recommends Strict mode
3. **Asks strictness** — Quick, Standard, Thorough, or Strict
4. **Analyzes the diff** — runs in parallel sub-agents for batch mode; looks for bugs, null-safety issues, SQL parity, test coverage gaps, and more
5. **Posts inline comments** — one finding per comment, severity marked with 🔴/🟡/🟢; never bundles multiple findings in one comment
6. **Checks CI** — blocks APPROVE if required CI checks are failing
7. **Submits formal review** — APPROVE (no blockers) or REQUEST_CHANGES (one or more 🔴 findings)
8. **Resolves addressed threads** — replies "✅ Resolved in {sha}" to previously raised comments now fixed, and marks threads closed

**Model:** Requires Sonnet or Opus — stops immediately on Haiku. Batch mode lets you choose the model for parallel analysis agents (Sonnet default, Opus for security-sensitive batches).

**Requires:** `gh` CLI authenticated (`gh auth login`)

---

### `/verify-global-settings-version`

**Phase:** Git / Delivery

Checks whether `global-settings/VERSION` has been correctly bumped after any changes to files in the `global-settings/` directory. Run this before creating a PR on the `ConductionNL/.github` repo.

**Usage:**
```
/verify-global-settings-version
```

**What it does:**
1. Fetches `origin/main` to get the latest published version
2. Diffs `global-settings/` between the current branch and `origin/main`
3. Compares the branch `VERSION` against the `origin/main` `VERSION`
4. Reports one of four outcomes:
   - No changes to `global-settings/` — no bump needed
   - Changes found and `VERSION` correctly bumped
   - Changes found but `VERSION` not bumped — suggests the next semver and the command to apply it
   - `VERSION` bumped but no other files changed — flags as unusual

**When to use:**
- Standalone: any time you modify a file in `global-settings/` and want to confirm the bump is in place before committing
- Automatically: called by `/create-pr` when the selected repo is `ConductionNL/.github` — no need to run it separately in that flow

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

Run /opsx-apply to begin implementation.
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

### `/skill-creator`

**Phase:** Maintenance / Meta

Create new skills, modify and improve existing skills, and measure skill performance with evals. Use when you want to build a new skill from scratch, refine an existing skill's behavior, or benchmark a skill's accuracy with quantitative evaluation runs.

**Usage:**
```
/skill-creator
```

**What it does:**
1. Helps you decide what the skill should do and roughly how
2. Drafts the SKILL.md
3. Generates a small set of test prompts and runs them against `claude-with-access-to-the-skill`
4. Drafts quantitative evals (or uses existing ones) and reports the metrics
5. Iterates on the skill based on qualitative and quantitative feedback
6. Optionally expands the test set for larger-scale benchmarking
7. Can also optimize a skill's `description` field for better triggering accuracy

**When to use:** When adding a new capability, when an existing skill is misfiring or producing inconsistent results, or when you want to verify a recent skill change hasn't regressed behavior.

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

## Tender & Ecosystem Intelligence Commands

Competitive analysis and ecosystem gap-finding workflow. For the complete reference, see [commands-tender.md](commands-tender.md).

| Command | Phase | Description |
|---------|-------|-------------|
| `/tender-scan` | Intelligence | Scrape TenderNed, import, classify by category |
| `/tender-status` | Monitoring | Dashboard of tender intelligence database |
| `/tender-gap-report` | Gap Analysis | Categories with tenders but no Conduction product |
| `/ecosystem-investigate` | Research | Deep-dive into a software category's competitors |
| `/ecosystem-propose-app` | Planning | Generate full app proposal for a gap |
| `/intelligence-update` | Maintenance | Pull latest data from external sources |

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
