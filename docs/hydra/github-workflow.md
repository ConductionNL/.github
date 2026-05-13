# GitHub Workflow

Hydra uses GitHub labels as its state machine. All pipeline state lives on GitHub — labels, PRs, comments. No in-memory state. If any step is interrupted, the next cron cycle resumes from the current label state.

## Label State Machine

```
                    ┌─────────────────────────────────────┐
                    │  <trigger-label>                      │
                    │  (default: ready-to-build)            │
                    │  (configurable via HYDRA_TRIGGER_LABEL)│
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  pipeline-active + building           │
                    │  (builder container running)          │
                    │  Creates PR, runs quality checks      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  pipeline-active                      │
                    │  + ready-for-code-review (on PR)      │
                    │  + ready-for-security-review (on PR)  │
                    │  (review agents running)              │
                    └──────────────┬──────────────────────┘
                                   │
                        ┌──────────┴──────────┐
                        │                     │
                 ┌──────▼──────┐    ┌────────▼────────┐
                 │ verdicts     │    │ verdicts         │
                 │ all pass     │    │ any fail         │
                 └──────┬──────┘    └────────┬────────┘
                        │                     │
                 ┌──────▼──────┐    ┌────────▼────────┐
                 │ ready-for-   │    │ pipeline-active  │
                 │ review       │    │ + building       │
                 │ (or auto-    │    │ (fix iteration)  │
                 │  merge if    │    │ then re-trigger  │
                 │  yolo)  │    │ reviews          │
                 └─────────────┘    └────────┬────────┘
                                             │
                                    (loops back to review)
                                    max 3 fix iterations
                                    then → needs-input
```

## Label Reference

| Label | Applied to | Meaning | Set by | Removed by |
|-------|-----------|---------|--------|------------|
| `ready-to-build` (configurable) | Issue | New spec, ready for build. Label name configurable via `HYDRA_TRIGGER_LABEL` env var (default: `ready-to-build`). | Specter push script | Orchestrate (build start) |
| `pipeline-active` | Issue | In-progress — cron re-dispatches each cycle | Orchestrate (build start) | Orchestrate (merge or escalation) |
| `building` | Issue | Container actively running — blocks concurrent dispatch | Orchestrate (before build/fix) | Orchestrate (after build/fix) |
| `ready-for-code-review` | PR | Code review agent should run | Orchestrate (after build/fix) | Supervisor (successful completion) |
| `ready-for-security-review` | PR | Security review agent should run | Orchestrate (after build/fix) | Supervisor (successful completion) |
| `ready-for-review` | Issue | All AI reviews passed — human review or auto-merge | Orchestrate (verdicts pass) | Human (after merge) |
| `needs-input` | Issue | Escalated to human — fix budget exhausted or build failure | Orchestrate | Human |
| `yolo` | Issue | Skip human review — auto-merge when AI reviews pass | Specter push script | Orchestrate (after merge) |
| `openspec` | Issue | Change is spec-driven | Specter push script | — |
| `oversized` | Issue | Spec generation exceeded turn limit — needs splitting | Specter push script | Human |

## How Cron Reads Labels

**cron-hydra.sh** (every 5 minutes):
1. Searches for issues with the trigger label (default: `ready-to-build`, configurable via `HYDRA_TRIGGER_LABEL`) OR `pipeline-active`
2. Skips issues with `building` label (another instance working)
3. Checks `hydra.json` — skips if dependency issues aren't closed
4. Dispatches to orchestrate.sh

**hydra-supervisor.sh** (continuous daemon):
1. Searches for PRs with `ready-for-code-review` or `ready-for-security-review`
2. Skips if already locked (same PR being reviewed)
3. Caps at 3 attempts per PR — then removes labels and adds `needs-input`
4. Uses shared slot pool (max 5 concurrent with builders)

## Concurrency Control

A shared slot pool (`/tmp/hydra-slots/`) governs all container launches:
- Max **5 slots** across builds, fixes, and reviews
- `cron-hydra.sh` and the supervisor's review dispatcher share the same pool
- `building` label on GitHub provides distributed locking across multiple Hydra instances
- If no slots available, work is deferred to the next cron cycle

## Board Structure

The project board has four columns:

| Column | What lives here | How cards arrive |
|--------|----------------|-----------------|
| **Todo** | Issues with trigger label (default: `ready-to-build`) | Specter creates issue |
| **In Progress** | Issues with `pipeline-active` or `building` | Orchestrate moves card |
| **Review** | Issues with `ready-for-review` | Orchestrate moves card (all checks pass) |
| **Archived** | Merged changes | Human or yolo merge |

## Standalone Reviews

Review agents work independently from the build pipeline. Add a label to **any PR** in the org:

| Label on PR | What happens |
|-------------|-------------|
| `ready-for-code-review` | Code Reviewer runs, posts findings + verdict |
| `ready-for-security-review` | Security Reviewer runs, posts findings + verdict |
| Both labels | Both run sequentially in one slot |

Labels are only removed on successful completion. Failed reviews keep labels for retry on next cron cycle (max 3 attempts).

## Branch Strategy

- Spec branches: `spec/{slug}` (merged to development by Specter, no review needed)
- Feature branches: `feature/{issue-number}/{change-name}` (created by builder)
- PRs target `development`
- `development` → `beta` → `main` via release process

## Dependency Enforcement

Each spec includes `openspec/changes/{name}/hydra.json`:

```json
{ "depends_on": ["core", "access-control-authorisation"] }
```

Before dispatching a build, the cron verifies all dependencies have closed implementation issues. This enforces build order without burning tokens:

```
Layer 0: core (no deps)         → builds immediately
Layer 1: access-control (core)  → builds after core merges
Layer 2: accounts-payable       → builds after layer 1 merges
         (core + access-control)
```

## Findings

Review agents may discover issues unrelated to the current spec:
- **CRITICAL** findings block the PR — must be fixed by builder
- **WARNING** findings are posted as comments and may generate separate `finding`-labelled issues
- **SUGGESTION** findings are informational — no action required

## Cron Schedule

| Script | Interval | Purpose |
|--------|----------|---------|
| `cron-hydra.sh` | `*/5 * * * *` | Discover + dispatch builds, resume active pipelines |
| `hydra-supervisor.sh` | daemon (1-min watchdog) | Run code + security reviews on labelled PRs |
