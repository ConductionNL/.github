# Pipeline Overview

Hydra is a stateless, label-driven pipeline that builds code from OpenSpec specifications. All state lives on GitHub (labels, PRs, comments) — nothing in memory. If any step is interrupted (rate limit, crash, timeout), the next cron cycle picks up where it left off.

Since `openspec/changes/no-loop-review-pipeline`, the pipeline is **single-shot**: no review re-runs, no fix-iteration loop. Every outcome is terminal — merge or `needs-input`.

## State Machine

The pipeline is driven entirely by GitHub issue labels. The supervisor polls every cycle and decides what to do:

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  ready-to-build / build:queued                                    │
│    │                                                              │
│    ▼                                                              │
│  BUILD (Al Gorithm, Haiku)                                        │
│    implements spec → creates PR → runs quality + browser          │
│    fix-quality / fix-browser loops (pre-review) if checks red     │
│    │                                                              │
│    ▼                                                              │
│  build:pass  →  code-review:queued  (security NOT queued yet)     │
│                                                                   │
│  CODE REVIEW (Juan Claude van Damme, Sonnet)                      │
│    reads diff + ADRs → applies bounded fixes in-container →       │
│    posts inline [fixed:…]/[unfixed:…] comments + summary →        │
│    commits + pushes → sets code-review:pass/fail on issue         │
│    emits JSON verdict with fixes_applied[] + unfixed[]            │
│    │                                                              │
│    ▼  supervisor sees code-review verdict, queues security         │
│                                                                   │
│  SECURITY REVIEW (Clyde Barcode, Sonnet)                          │
│    same shape, plus Semgrep — reads POST-code-fix state            │
│    sets security-review:pass/fail on issue                        │
│    │                                                              │
│    ▼                                                              │
│  supervisor sees both verdicts → applier:queued                   │
│                                                                   │
│  APPLIER DECISION (orchestrate.sh)                                │
│    if both reviews passed AND zero fixes applied:                 │
│      → done (skip Axel — saves tokens)                            │
│    else:                                                          │
│      re-run deterministic checks (PHPCS/ESLint/PHPUnit/...)       │
│        ↳ red  → needs-input (a fix broke something)               │
│        ↳ green → dispatch Axel Pliér                              │
│                                                                   │
│  APPLIER (Axel Pliér, Sonnet, NO fix tools)                       │
│    reads final diff + hydra.json fixes_applied/unfixed +          │
│    reviewer PR comments                                           │
│    emits {pass, blocking[]} verdict                               │
│      ↳ applier:pass → done (or yolo merge)                        │
│      ↳ applier:fail → needs-input                                 │
│                                                                   │
│  MERGE (done label set)                                           │
│    PR undrafted, summary comment posted                           │
│    if yolo: approve + merge + close issue                         │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

Every failure path terminates in `needs-input`; there is no retry and no fix-iteration loop.

## Labels

| Label | On | Meaning | Set by | Removed by |
|-------|-----|---------|--------|------------|
| `ready-to-build` (configurable) | Issue | New spec, ready for initial build. Label name is configurable via `HYDRA_TRIGGER_LABEL` env var (default: `ready-to-build`). | Specter | Supervisor (start of build) |
| `build:queued` / `:running` / `:done` / `:failed` | Issue | Build stage states | Supervisor / Orchestrate | Supervisor |
| `code-review:queued` / `:running` / `:pass` / `:fail` | Issue | Code review states. Juan Claude may edit files. `:pass`/`:fail` triggers supervisor to queue security review. | Supervisor / Juan Claude | Supervisor (after applier queued) |
| `security-review:queued` / `:running` / `:pass` / `:fail` | Issue | Security review states. Queued only after code review completes. Clyde may edit files in PR mode. | Supervisor / Clyde Barcode | Supervisor (after applier queued) |
| `applier:queued` / `:running` / `:pass` / `:fail` | Issue | Final go/no-go stage. Orchestrate.sh decides whether to run Axel Pliér or skip straight to `done`. `:pass` → merge; `:fail` → `needs-input`. | Supervisor / Orchestrate / Axel Pliér | — (terminal) |
| `done` | Issue | All phases passed, ready for merge (or auto-merged on yolo) | Supervisor | Human (after merge) |
| `needs-input` | Issue | Escalated — needs human intervention (applier fail, reviewer max-out, post-review check failure) | Orchestrate / Supervisor | Human |
| `yolo` | Issue | Auto-approve and merge on `done` | Specter | Orchestrate (after merge) |
| `openspec` | Issue | Change driven by OpenSpec | Specter | — |
| `oversized` | Issue | Spec generation timed out — needs splitting | Specter | Human |
| `agent-maxed-out` | Issue/PR | Agent hit turn limit — output may be incomplete | Supervisor | Human |

**Deprecated labels** (removed by no-loop-review-pipeline; `migrate-labels.sh` clears these off in-flight PRs): `pipeline-active`, `building`, `ready-for-code-review`, `ready-for-security-review`, `ready-for-review`, `fix:queued`, `fix:running`, `fix:done`, `fix-iteration:1`, `fix-iteration:2`, `build-retry:1`.

## hydra.json — Pipeline Metadata Per Change

Each spec change has a `hydra.json` in `openspec/changes/{name}/`. This is Hydra-specific metadata — not part of the OpenSpec standard.

```json
{
  "spec_slug": "accounts-payable-receivable",
  "title": "Accounts Payable & Receivable",
  "app": "shillinq",
  "repo": "https://github.com/ConductionNL/shillinq",
  "depends_on": ["core", "access-control-authorisation"],
  "issue": "https://github.com/ConductionNL/shillinq/issues/49",
  "pipeline": {
    "code_review": {
      "pass": true,
      "fixes_applied": [
        { "file": "lib/Service/LedgerService.php", "line": 42, "rule": "PHPCS/PSR12", "note": "Added missing blank line after namespace" }
      ],
      "unfixed": []
    },
    "security_review": {
      "pass": true,
      "fixes_applied": [
        { "file": "lib/Db/InvoiceMapper.php", "line": 77, "rule": "CWE-89", "note": "Replaced string concatenation with prepared statement" }
      ],
      "unfixed": []
    },
    "applier": {
      "ran": true,
      "pass": true,
      "blocking": []
    },
    "build_count": 1,
    "findings_fixed": 2,
    "findings_open": 0,
    "suggestions_open": 1,
    "total_cost_usd": 0.42,
    "total_cost_eur": 0.39,
    "total_turns": 87,
    "last_code_review_pass": true,
    "last_security_review_pass": true
  }
}
```

The `pipeline` section is auto-maintained by `update_hydra_summary()` in `scripts/lib/review-results.sh`, which delegates to `scripts/lib/aggregate-hydra-summary.py`. It aggregates the latest `reviews/*.json` + `applier.json` + `builds/*.json`. Legacy fields `review_rounds` and `fix_iterations` are no longer written (no-loop pipeline has exactly one review round and no fix iterations).

| Field | Set by | Purpose |
|-------|--------|---------|
| `spec_slug` | Specter | Change identifier |
| `title` | Specter | Human-readable name |
| `app` | Specter | Target app |
| `repo` | Specter | GitHub repo URL |
| `depends_on` | Specter | Build order enforcement — list of spec slugs that must merge first |
| `issue` | Specter | GitHub issue URL — updated after issue creation |
| `pipeline` | Orchestrate | Running summary — updated after each build/review cycle |

The `pipeline` section is auto-maintained by `update_hydra_summary()` in `scripts/lib/review-results.sh`. It aggregates data from all `reviews/*.json` and `builds/*.json` files.

### Related files per change

```
openspec/changes/{name}/
├── proposal.md          ← OpenSpec standard
├── design.md            ← OpenSpec standard
├── tasks.md             ← OpenSpec standard
├── specs/               ← OpenSpec standard (optional)
├── hydra.json           ← Hydra pipeline metadata (pipeline.* aggregated summary)
├── reviews/             ← Hydra review results (single round in the no-loop pipeline)
│   └── 1.json           ← code_review + security_review blocks with fixes_applied[] and unfixed[]
├── applier.json         ← Axel Pliér verdict: {ran, pass, blocking[]}
├── builds/              ← Hydra build results per phase
│   └── build.json
└── pipeline-logs/       ← Gzipped raw JSONL transcripts for every phase (self-learning)
    ├── build.jsonl.gz
    ├── code-review-1.jsonl.gz
    ├── security-review-1.jsonl.gz
    └── applier.jsonl.gz
```

## Dependency Enforcement

Before dispatching a build, the cron checks if each dependency's implementation issue is closed (meaning its code was merged to development). If any dependency is unmerged, the build is skipped — no tokens burned.

This enforces build order automatically:
- Layer 0: `core` (no deps) — builds first
- Layer 1: specs depending on core — build after core merges
- Layer 2: specs depending on layer 1 — and so on

## Concurrency

A shared slot pool (`/tmp/hydra-slots/`) limits all containers to **5 concurrent** across every type:

| Container | Image | Purpose |
|-----------|-------|---------|
| Builder (build) | `hydra-builder` | Generate code from spec |
| Builder (fix-quality) | `hydra-builder` | Fix linting/test failures during the build phase (pre-review) |
| Builder (fix-browser) | `hydra-builder` | Fix browser test failures during the build phase (pre-review) |
| Code Reviewer (Juan Claude van Damme) | `hydra-reviewer` | Review PR for code quality + apply bounded in-container fixes |
| Security Reviewer (Clyde Barcode) | `hydra-security` | Review PR for security issues + apply bounded in-container fixes (PR mode) |
| Applier (Axel Pliér) | `hydra-applier` | Binary go/no-go gate — NO fix authority |

The post-review `Builder (fix)` container was removed by `openspec/changes/no-loop-review-pipeline` — reviewers now own fix authority.

Builds use Opus (better quality, separate rate limit pool on Max). Reviews and fixes use Sonnet. Quality checks (PHPCS, Psalm, PHPStan, ESLint) and browser tests (Playwright) run as host processes — no Claude tokens, no slots consumed.

`cron-hydra.sh` (legacy, manual) and the supervisor (continuous daemon) share the same pool. If all slots are busy, new work is deferred to the next cycle.

## Self-Healing

The pipeline is designed to recover from interruptions automatically:

- **Rate limits**: `run_container_with_fallback()` tries the work token first, falls back to personal. Only checks the final result line — mid-session rate limit warnings from Claude CLI don't trigger false fallbacks.
- **Crash recovery**: All state is on GitHub labels. If a container crashes, the next cron cycle sees `pipeline-active`, finds the PR, checks verdicts, and picks up from the right stage.
- **Auth failures**: Token failures are treated like rate limits — fallback to next token.
- **Review dedup**: Round tracking prevents re-reviewing the same round. Attempt cap (3 max) prevents infinite retries.
- **Build dedup**: `building` label prevents concurrent dispatch. Set BEFORE dispatch (not after).

**What can still require manual intervention:**
- `needs-input` label — set when fix budget exhausted (3 iterations) or all tokens fail
- `agent-maxed-out` label — set when an agent hits its turn limit (incomplete output)
- `oversized` label — set when spec generation times out

## Authentication

All credentials in `secrets/credentials.json` (single source of truth):

```json
{
  "claude_accounts": [
    { "name": "work", "token": "sk-ant-...", "priority": 1 },
    { "name": "personal", "token": "sk-ant-...", "priority": 2 }
  ],
  "git_tokens": {
    "builder": "gho_...",
    "reviewer": "gho_...",
    "security": "gho_..."
  }
}
```

- Up to 3 Claude Max accounts in priority order
- Per-container Git PATs (builder, reviewer, security can use different GitHub accounts)
- `run_container_with_fallback()` handles token rotation on failure

## Review Reliability

- Reviews are capped at **3 attempts** per PR. After 3 failures, labels are removed and `needs-input` is added.
- Labels are only removed on **successful** completion. Failed reviews keep their labels for retry.
- Review verdicts are posted as JSON code blocks: `{ "pass": true/false, "blocking": [...] }`

## Relationship to Specter

Specter produces specs and pushes them to target repositories:

1. Specter generates spec artifacts (proposal.md, design.md, tasks.md, hydra.json)
2. Pushes to a `spec/{slug}` branch, merges to `development`
3. Creates a GitHub issue with the trigger label + `openspec` + `yolo` labels
4. Hydra cron discovers the issue and starts the pipeline

## Codebase Audit

Full codebase security and quality scanning, independent of PRs. Creates GitHub issues with checkbox findings.

**Trigger:** Create an issue with label `ready-for-audit` on any repo in the org.

**Flow:**
1. `cron-audit.sh` discovers issues with `ready-for-audit` label
2. Runs code reviewer + security reviewer in audit mode (`AUDIT_MODE=full`)
3. Agents scan the entire codebase (not just PR diffs)
4. Agents output structured findings JSON
5. `audit-results.sh` creates/updates GitHub issues with checkboxes per finding
6. Trigger issue closed, labelled `audit-complete`

**Output:** Two issues per audit (code quality + security), each with:
- CRITICAL findings: must fix (checkbox)
- WARNING findings: should fix (checkbox)
- SUGGESTION findings: may fix (checkbox)

Subsequent audits update existing issues — no duplicates.

## Issue → Spec Flow (Reverse Pipeline)

Generate specs from existing issues, enabling: Issue → Spec → Build → Review → Merge.

**Trigger:** Label any issue with `needs-spec`.

**Flow:**
1. `cron-spec-from-issue.sh` discovers issues with `needs-spec` label
2. Clones the repo, runs Claude CLI with `/opsx-new` + `/opsx-ff`
3. Generates proposal.md, design.md, tasks.md from the issue description
4. Writes `hydra.json` linking back to the original issue (`"source": "issue"`)
5. Commits to development, relabels issue with the trigger label + `openspec` + `yolo`
6. Normal build pipeline takes over — the original issue tracks completion

**Use cases:**
- Bug reports that need implementation specs
- Feature requests from users
- Audit findings that need code changes
- Manual observations that should become specs

## Cron Schedule

| Cron | Script | Interval | Purpose |
|------|--------|----------|---------|
| `cron-hydra.sh` | Build pipeline | Every 5 min | Discover + dispatch builds, resume active pipelines |
| `hydra-supervisor.sh` | Review pipeline | Continuous daemon | Run code + security reviews on labelled PRs |
| `cron-audit.sh` | Codebase audit | Every 30 min | Full codebase scan on repos with `ready-for-audit` |
| `cron-spec-from-issue.sh` | Issue→Spec | Every 10 min | Generate specs from issues with `needs-spec` |
