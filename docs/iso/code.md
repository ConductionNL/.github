# ISO 9001:2015 ↔ Code-Quality Pipeline

This document maps every clause of ISO 9001:2015 (*Quality management systems — Requirements*) to concrete artefacts in the Conduction engineering pipeline. The pipeline itself has four cooperating layers — **Specter** (what & why), **Hydra** (how), the **Quality CI workflow** (gatekeeper), and the **human reviewer** (release authority). The goal here is honest coverage: for each clause we say what we actually do, rate it *Full / Partial / None / N/A*, and — when we fall short — describe the shortest path to closing the gap.

ISO 9001 is a generic quality-management standard. The software-specific interpretation lives in **ISO/IEC 90003:2018** (*Software engineering — Guidelines for the application of ISO 9001:2015 to computer software*). Where ISO/IEC 90003 adds software-specific guidance we note it inline.

---

## 0. The pipeline at a glance

```
What & Why                     How                       Gatekeeper             Human
──────────                     ───                       ──────────             ─────
Specter     ────proposal────▶  Hydra    ────draft PR──▶  quality.yml  ──────▶  Reviewer
(intel,      OpenSpec          (builder,  code + tests    (PHPCS,               (approve /
 tenders,    change             reviewer,                  Psalm,                request
 features)   in openspec/        security,                 PHPStan,              changes)
             changes/)           fixer)                    PHPMD,
                                                           ESLint,
                                                           Newman,
                                                           Playwright,
                                                           audits,
                                                           SBOM)
```

Every code line lands in the codebase via this sequence. Traceability is anchored by two cross-cuts: `@spec` PHPDoc tags in source files (enforced by ADR-003) and GitHub issue↔PR↔change-folder links.

Pipeline artefact reference (cited throughout below):

- **Hydra ADRs** — [hydra/openspec/architecture/](../../../hydra/openspec/architecture/) — 23 architecture decision records (adr-001 … adr-023).
- **OpenSpec changes** — `hydra/openspec/changes/` — active change proposals; `hydra/openspec/changes/archive/` for completed.
- **Quality workflow** — [.github/.github/workflows/quality.yml](../../.github/workflows/quality.yml) — reusable workflow invoked per app.
- **Branch-protection workflow** — [.github/.github/workflows/branch-protection.yml](../../.github/workflows/branch-protection.yml) — validates source→target branch pairings.
- **Hydra mechanical gates** — `scripts/run-hydra-gates.sh` in hydra/ — 9 gates: `spdx`, `forbidden-patterns`, `stub-scan`, `composer-audit`, `route-auth`, `orphan-auth`, `no-admin-idor`, `unsafe-auth-resolver`, `semantic-auth`.
- **Hydra record** — `openspec/changes/{slug}/hydra.json` — atomic stage-level journal written by `scripts/lib/hydra_record.py`.
- **Specter** — [concurrentie-analyse/](../../../concurrentie-analyse/) — market-intelligence platform that turns procurement data, competitor signals, and government standards into OpenSpec change proposals. Remote: private GitHub repo `ConductionNL/market-intelligence`. Detailed in § 0a below.
- **Org rulesets** — 3 GitHub org-level rulesets: development (1 review), beta (1 review), main (2 reviews). Not stored in-repo.

---

Specter and Hydra are peers. Neither is a subsystem of the other. Specter owns *what & why*; Hydra owns *how*; between them runs a learning bridge that feeds each half's outputs back into the other's inputs. The three sections below — § 0a, § 0b, § 0c — describe the two halves and the bridge.

---

## 0a. Specter — the intelligence → spec pipeline

Where Hydra is the "how," Specter is the "what and why." It is the evidence-gathering, requirement-tracking, competitor-scanning, spec-proposing half of the pipeline. Code lives at [concurrentie-analyse/](../../../concurrentie-analyse/) (remote: private repo `ConductionNL/market-intelligence`). The design principle, quoted from `concurrentie-analyse/README.md`:

> *"Every spec traces back to real tender requirements, real competitor gaps, and real government demand. No fiction."*

In ISO-9001 terms Specter operationalises the design-and-development *inputs* side of clause 8.3 (specifically 8.3.3), the customer/stakeholder-requirement side of 8.2, and — crucially for 8.5.2 — the *upstream* half of the traceability chain that ends at `@spec` tags in code.

### The raw material — the intelligence database

**Location.** `concurrentie-analyse/intelligence.db` — SQLite, generated from a PostgreSQL dump at `concurrentie-analyse/data/intelligence.pgdump`.

**Schema.** Django ORM migrations at `concurrentie-analyse/intelligence/migrations/0001_initial.py`. 58+ tables across 8 domains. Notable tables and their current row counts (from `README.md` sync-status block):

| Domain | Key tables | Rows |
|---|---|---|
| Tender intelligence | `tenders`, `requirements`, `tender_documents`, `tender_awards`, `tender_app_relevance` | 75.6K tenders / 151.4K requirements / 30K docs / 13K awards / 15.8K relevance rows |
| Canonical features | `canonical_features`, `canonical_feature_sources`, `tec_features`, `category_features` | 6.8K canonical / 7 062 TEC features / 422 category features |
| Competitors | `competitors`, `competitor_features`, `competitor_apps`, `github_repo_metrics` | 98 competitors / 938 features / 218 apps |
| App research | `domains`, `stakeholders`, `customer_journeys`, `user_stories`, `external_sources` | 92 stakeholders / 285 journeys / 1.9K user stories / 459 external sources |
| Legal / standards | `nl_standards`, `laws`, `law_articles`, `gemma_components`, `gemma_services` | 127 standards / 4.277K law articles / 254 components |
| Ecosystem | `ecosystem_gaps`, `apps`, `nextcloud_marketplace` | 53 gaps / ~22 apps / 620 NC marketplace apps |
| Procurement | `procurement_windows`, `source_syncs` | 833 windows / 36 source-sync records |
| Outputs | `app_specs` | per-change spec metadata incl. `status`, `depends_on_specs` |

(The numbers in the memory index — "39 591 tenders, 17 338 requirements, 303 features" — are stale; the figures here come from inspecting the current DB and README directly.)

**Traceability key.** `canonical_feature_sources` is the junction table that makes 8.5.2 work upstream: every canonical feature points back to a specific evidence row via `(source_table, source_id, confidence)`. One feature can have hundreds of sources. Example (from the audit): the *System Integration* feature has 221 tender sources, 89 competitor implementations, plus external-blog citations, aggregating to a `demand_score` of 8.7/10.

### The 7 `specter-*` skills

Under `concurrentie-analyse/.claude/skills/`:

| Skill | Job | Cadence |
|---|---|---|
| `specter-sync` | Fetch new tenders from specific sources (27 procurement portals, 19 ecosystem catalogues); classify; update README status. | Ad-hoc, also invoked by `specter-pipeline` |
| `specter-pipeline` | Main orchestrator — 13 global phases + 10 per-app phases: setup → sync → download → parse → analyse → cleanup → link → score → snapshot → context → report → dump → commit. | Weekly (Sun 02:00 UTC via GitHub Actions) |
| `specter-research-app` | Deep per-app research (9 phases: domains → stakeholder/journey → competitor → tender mining → external sources → sentiment → standards mapping → feature linking → briefs). Promotes an app from `concept` to `idea`. | Post-pipeline, per-app |
| `specter-prepare-context` | Query DB for an app (market, top-20 features, competitors, insights, standards, user stories) and produce a structured context markdown for `/opsx-explore` or `/app-design`. | Before spec writing |
| `specter-concept` | Exploratory — three parallel agents investigate market (competitors, demand, feasibility) for a rough product idea; recommends GO / EXPLORE / PARK. | Ad-hoc (ideation) |
| `specter-analyze-docs` | Download & parse tender documents for a specific app, extract requirements, link to user stories. Used within phase 4 of `specter-research-app`. | Within research-app |
| `specter-harvest` | Batch-fetch full text from external source URLs and re-extract features — full text yields ~3–4× more features than summaries. | Post-source discovery |

### Pipeline phases (the real ones)

Confirmed against [concurrentie-analyse/scripts/pipeline.py](../../../concurrentie-analyse/scripts/pipeline.py) and [concurrentie-analyse/.github/workflows/weekly-sync.yml](../../../concurrentie-analyse/.github/workflows/weekly-sync.yml):

1. **Intelligence → DB** — `specter-pipeline` phases 1-9 + the 46 "tendril" sync scripts. Weekly GitHub Actions on Sunday 02:00 UTC. 27 procurement sources + 19 ecosystem sources; Italy ANAC is slow (3–60 s/request); 5 endpoints currently dead and skipped.
2. **Per-app spec building** — `specter-pipeline` per-app phases + `specter-research-app` (promotes concept → idea).
3. **Spec-to-Git push** — `concurrentie-analyse/scripts/push_spec_pipeline.py` reads briefs from DB, runs `/opsx-ff` per spec, writes artefacts into `concurrentie-analyse/openspec/changes/{slug}/` (21 completed specs in this directory as of the audit). `concurrentie-analyse/scripts/push_roadmap_issues.py` opens GitHub issues, labelled `ready-to-build` (all deps met), `blocked` (unmet deps), or `yolo` (auto-merge candidate).
4. **Hydra pickup** — Hydra's supervisor polls for `ready-to-build` issues and runs the builder. Traceability continues in `hydra.json`.

**Container layout.** `concurrentie-analyse/Dockerfile.llm-worker` runs AI scripts (clean, classify, generate schemas) in isolated containers with the Claude Code CLI and no project-context injection. `Dockerfile.analysis` and `Dockerfile.spec-writer` are also present in the repo — their scopes are named in the filenames; their wiring into the pipeline should be verified before citing them as load-bearing.

### What Specter records that is directly consumable

For clause 9.1.1 (monitoring) and 9.3 (management review) the interesting DB views are:

- `source_syncs.records_synced` + `source_syncs.last_sync` — per-source intake per week.
- `canonical_feature_sources` group-by `source_table` — new feature evidence per source per week.
- `competitor_features` filter on `category IN ('release-*', 'enhancement-issue')` — competitor signal volume.
- `tender_awards.contract_value` JOIN `tender_app_relevance` — addressable market per app, in euros.
- `app_specs.status` — spec-pipeline throughput (`draft` / `created` / `pushed` / `merged`).
- `ecosystem_gaps` — demand areas with no matching product. Directly consumable for roadmap prioritisation.

The README at `concurrentie-analyse/README.md` already renders a "Sync Status" section auto-populated by `scripts/update_readme_status.py` — the scaffolding for a management dashboard at the Specter end exists.

### Traceability — the upstream half of 8.5.2

**Evidence chain that works today:**

1. Tender or external source → ingested row in `tenders` / `external_sources` / `requirements`.
2. Feature extraction → `canonical_features` row + one or more `canonical_feature_sources` junction rows (`source_table`, `source_id`, `confidence`).
3. Brief assembly → `app_specs.brief_data` JSON embeds feature IDs; `generate_spec_content.py` (DB-only, no LLM) writes `context-brief.md`.
4. Spec push → `openspec/changes/{slug}/proposal.md` + `design.md` + `tasks.md`.
5. Issue push → `push_roadmap_issues.py` opens issue with body linking to the change directory.

**Then Hydra picks up** — issue → change folder → builder → `@spec` tag in source → tasks.md line.

**Where the chain is broken:**

- **No `feature_id` tag on the GitHub issue.** The issue body mentions the brief in prose, but there is no machine-readable link back to `canonical_features.id`. Walking backwards from a merged PR through `Closes #N` lands on the issue — and the thread goes cold there.
- **No automated Hydra → Specter feedback sync.** `concurrentie-analyse/scripts/sync_hydra_feedback.py` exists but is not wired into a cron or workflow. So review findings, resolved-vs-unresolved counts, and cost-per-feature never flow back into the intelligence DB. Specter cannot currently answer "which feature categories are hardest to ship?"

### Specter in ISO-9001 terms

| Clause | How Specter serves it |
|---|---|
| 4.1 Context of the organization | Weekly ingestion of 27 procurement sources + 19 ecosystem sources makes "external issues" a *measured* quantity, not an opinion. |
| 4.2 Interested parties | `stakeholders`, `customer_journeys`, `user_stories` tables name parties and what they require. |
| 6.1 Risks and opportunities | `ecosystem_gaps` + `competitor_features` together are the opportunity register. `tender_awards` is the addressable-market quantifier. |
| 8.2.2 Determining requirements | `requirements` table (151.4K rows) is the authoritative requirement source for tender-driven work. |
| 8.3.3 D&D inputs | `canonical_features` + `canonical_feature_sources` furnish inputs with traceability to evidence. |
| 8.5.2 Identification and traceability | Upstream half of the chain — see above. Gap at the issue-tagging step. |

### Gaps and closure proposals (Specter-side)

Raised as OpenSpec changes in `concurrentie-analyse/openspec/changes/` (tracked on `spec/*` branches):

1. **`embed-feature-id-in-issues`** — `push_roadmap_issues.py` already has the feature IDs in scope. Emit them in issue body front-matter / as labels so the 8.5.2 reverse-traceability chain closes.
2. **`link-findings-to-features`** — Extend `HydraPipeline` (see § 0c) with `canonical_feature_id` FK; enrichment phase in `ingest_hydra_logs` recovers feature IDs from brief_data / proposal.md. Unlocks "cost per feature category" and "findings density per feature".
3. **`add-spec-pipeline-throughput-view`** — The `intelligence/` dashboard already covers most of Board-5 (addressable market per app, ecosystem gaps, new tenders last 7d, competitor activity last 7d, source-sync health). What's still missing: a throughput view over `app_specs` + `HydraPipeline` showing proposed → created → pushed → merged per week with mean change age.

Not raised as changes:

- The `sync_hydra_feedback.py` script still exists but is superseded by the `hydra_learning` ingest pipeline (see § 0c). Its role is unclear — either it is redundant or it covers a narrower slice than `hydra_learning.ingest_hydra_logs`. Worth a clean-up pass but not a blocking gap.
- `Dockerfile.analysis` and `Dockerfile.spec-writer` are present in the repo; their pipeline wiring should be verified before citing them as load-bearing, but this is a documentation tidy rather than an ISO gap.

---

## 0b. Hydra — the spec → code pipeline

Where Specter is the *what & why*, Hydra is the *how*. It takes an OpenSpec change (proposal.md + design.md + tasks.md + context-brief.md) and turns it into merged, reviewed, gate-passed code on the target app repo. Code lives at [hydra/](../../../hydra/).

### Pipeline stages

Four agent personas, each with its own container-pool budget (ADR-013):

| Stage | Persona | Input | Output | Key ADR |
|---|---|---|---|---|
| Build | `builder` | change folder + target repo | draft PR with code + tests | ADR-003, ADR-015 |
| Review | `reviewer` | builder's PR | findings with `[fixed:…]` / `[unfixed:…]` markers | ADR-020, ADR-021 |
| Security review | `security-reviewer` | builder's PR | OWASP / auth findings | ADR-005, ADR-023 |
| Fix | `fixer` | `[unfixed:…]` markers | bounded-scope corrections | ADR-021 |

### The 9 mechanical gates

Run by `hydra/scripts/run-hydra-gates.sh`, invoked by the builder before push and by the reviewer as mandatory first step:

`spdx` · `forbidden-patterns` · `stub-scan` · `composer-audit` · `route-auth` · `orphan-auth` · `no-admin-idor` · `unsafe-auth-resolver` · `semantic-auth`

Four of the nine (`orphan-auth`, `no-admin-idor`, `unsafe-auth-resolver`, `semantic-auth`) were authored in April 2026 after specific decidesk incidents — the worked example of the corrective-action loop in clause 10.2.

### The per-change journal — `hydra.json`

Written by `hydra/scripts/lib/hydra_record.py` (exclusive `fcntl.flock` + write-temp-and-rename for atomic concurrent-safe updates), located at `hydra/openspec/changes/{slug}/hydra.json`. Schema v2, validated in code (no external JSON schema file).

Fields per cycle:

- `trigger`, `started_at`, `ended_at`, `outcome`, `outcome_reason`
- `pattern_tags[]` — free-form tags (e.g. `turn-budget-exhausted`, `recheck-caught-new-findings`, `container-crashed-mid-stage`)
- `stages[]` — one entry per run of builder / reviewer / security-reviewer / fixer

Fields per stage:

- `stage`, `persona`, `model`, `turns_used`, `turns_budget`, `cost_usd`
- `checks_run[]`, `checks_skipped[]`, `verdict`
- `findings[]` — each finding carries `id`, `severity`, `gate`, `file`, `line`, `rule`, `status` (`fixed_in_stage` / `open` / `fixed_later` / `wontfix`), `autofixable`
- `decisions[]` — fixer resolutions

Plus the committed legacy-compatible sibling files: `reviews/*.json`, `builds/*.json`, `pipeline-logs/*.jsonl.gz` (gzipped agent transcripts), and the per-change `hydra.json` summary of costs.

### Supervisor + cron

- `hydra/scripts/hydra-supervisor.sh` — continuous 5-worker pool.
- `watchdog-supervisor.sh` — every minute; restarts the supervisor if dead.
- `reconcile.sh` — every 10 minutes; label validation + auto-recovery sweep.
- `cron-audit.sh` — every 30 minutes; full codebase audits.
- `cron-spec-from-issue.sh` — every 10 minutes; reverse pipeline (issue → spec).

### Non-conforming outputs — `needs-input`

Terminal label set on specific triggers (detailed in 8.7); once applied, every handler short-circuits before any side effect. The invariant is pinned in `hydra/CLAUDE.md` lines 580–598.

### Hydra in ISO-9001 terms

| Clause | How Hydra serves it |
|---|---|
| 8.3.4 D&D controls | 9 mechanical gates + reviewer + security-reviewer + fixer; bounded fix scope (ADR-021). |
| 8.5.1 Control of production | Quality.yml bank + gates + PHPUnit matrix. |
| 8.5.2 Identification and traceability (downstream half) | `@spec` tags (ADR-003) anchor every source line to `tasks.md#task-N`; `Closes #N` closes the issue chain. |
| 8.7 Control of non-conforming outputs | Fixer for in-scope findings; `needs-input` terminal state with handler short-circuit for out-of-scope. |
| 9.1.1 Monitoring (per-PR) | quality-report.md + `hydra.json` at every stage. |
| 10.2 Corrective action | New mechanical gate per recurring class; ADR iteration. |

### Gaps and closure proposals (Hydra-side)

These map directly to ISO clause gaps:

1. **`needs-input` digest** — data is in `HydraPipeline.final_status` (see § 0c) but there is no dedicated grouping view. A `/hydra/needs-input/` page in the Specter dashboard would close 8.7's aggregate dimension.
2. **Link findings to canonical features** — raised as the `link-findings-to-features` OpenSpec change (see § 0a and § 0c). Same gap, Hydra side.

---

## 0c. The learning bridge — `hydra_learning` Django app

The clauses ISO 9001 treats as a connected loop — 9.1.1 monitoring, 9.1.3 analysis & evaluation, 10.2 corrective action, 10.3 continual improvement — are served by a single subsystem: the `hydra_learning` Django app, shipped 2026-04-17, living inside Specter but operating on Hydra's outputs.

This section describes it in some detail because it is where the most important ISO-9001 work happens, and because earlier drafts of this document described it as "designed, not shipped" — which is no longer true.

### Why it lives in Specter

`hydra_learning` is analytics *about* Hydra's pipeline output, not part of Hydra's runtime. It belongs where Specter's infrastructure already exists: PostgreSQL at port 5433, Django 5 admin, Jazzmin sidebar, AdminLTE + Chart.js templates, management-command cron pattern, `StaffRequiredMixin` auth.

Code:

- [concurrentie-analyse/hydra_learning/](../../../concurrentie-analyse/hydra_learning/) — Django app.
- [concurrentie-analyse/hydra_learning/management/commands/](../../../concurrentie-analyse/hydra_learning/management/commands/) — 5 management commands.
- [concurrentie-analyse/docs/hydra-learning/README.md](../../../concurrentie-analyse/docs/hydra-learning/README.md) — operator runbook.
- Original proposal: [concurrentie-analyse/openspec/changes/hydra-learning-pipeline/proposal.md](../../../concurrentie-analyse/openspec/changes/hydra-learning-pipeline/proposal.md).

### Data model — 5 PostgreSQL tables

All prefixed `hydra_` to stay in their namespace. Django-managed.

| Table | Grain | Role in ISO |
|---|---|---|
| `hydra_pipelines` | one row per pipeline run (build + fixes + reviews for one issue) | 9.1.1 monitoring anchor; 8.7 `final_status` captures needs-input |
| `hydra_phases` | one row per phase of a pipeline (turns, cost, tokens, model, terminal reason) | 9.1.1 cost + duration metrics |
| `hydra_findings` | one row per reviewer finding (severity, file, line, title, description, status, fixed_in_round) | 10.2 corrective-action evidence |
| `hydra_finding_clusters` | normalised group of similar findings across pipelines (fingerprint, pipeline_count, first/last_seen, coverage flags) | 9.1.3 analysis; 10.3 continual improvement signal |
| `hydra_suggestions` | LLM-generated improvement proposal per cluster (proposed patch, rationale, evidence, review status) | 10.2 / 10.3 automated corrective-action proposals |

The cluster table carries `covered_by_claude_md` + `covered_by_adr` flags — important: if a pattern is *already* documented in an ADR or CLAUDE.md, it won't be re-proposed.

### The 5 management commands

| Command | Role |
|---|---|
| `ingest_hydra_logs` | Reads `../hydra/logs/pipeline-*/`, target repos' `openspec/changes/*/hydra.json`, `reviews/*.json`, `pipeline-logs/*.jsonl.gz`, and GitHub issue events. Upserts into the `hydra_*` tables. Idempotent (unique_together on `repo, issue_num, log_dir`). |
| `analyze_pipelines` | Fingerprints finding titles, updates `HydraFindingCluster` with pipeline_count / severity_mix / first_seen / last_seen. Grep-based coverage detection against Hydra's current CLAUDE.md + ADRs. |
| `suggest_improvements` | For uncovered high-frequency clusters (default threshold: 15% frequency, max 5 per run), invokes local `claude -p` with a scoped prompt carrying Hydra's CLAUDE.md + the cluster's example findings. Writes `HydraSuggestion` rows with `status='proposed'`. |
| `apply_hydra_suggestion` | When a human clicks "Apply" on an accepted suggestion, clones Hydra, branches `learning/suggestion-<id>-<slug>`, applies the patch, opens a PR to development. |
| `hydra_nightly` | Orchestrates the three analytical commands. Registered as host cron at 03:00 UTC daily. Exits non-zero on any failure. |

### Dashboard — the user-facing half

- **Dashboard home** `/hydra/` — KPI grid (total pipelines, % done, % needs-input, median turns, median time-to-done), weekly first-pass-success rate chart, weekly findings-per-pipeline chart, top-10 recurring clusters, pending suggestions count.
- **Pipeline list** `/hydra/pipelines/` — per-pipeline rows with repo, issue, spec, duration, turns, cost, fix_iterations, status.
- **Pipeline detail** `/hydra/pipelines/<id>/` — phase timeline, findings by round, links to issue + PR + raw archives.
- **Finding clusters** `/hydra/findings/` — ranked by `pipeline_count`; filter by severity + coverage status.
- **Suggestions queue** `/hydra/suggestions/` — accept / reject / apply workflow.

### As-shipped numbers (2026-04-17 initial backfill)

- 978 existing Hydra log dirs scanned
- 481 pipelines imported
- 1 145 phases
- 800 findings
- 752 finding clusters (627 uncovered by existing CLAUDE.md/ADRs — these are the candidates for new gates or ADR updates)
- First LLM-generated suggestion produced

### The loop in one picture

```
Hydra produces:  hydra.json + reviews/*.json + pipeline-logs/*.jsonl.gz
                     │
                     ▼  ingest_hydra_logs  (nightly)
Specter DB:      hydra_pipelines, hydra_phases, hydra_findings
                     │
                     ▼  analyze_pipelines  (nightly)
                 hydra_finding_clusters  (with coverage flags)
                     │
                     ▼  suggest_improvements  (nightly, LLM-assisted)
                 hydra_suggestions  (status='proposed')
                     │
                     ▼  human review in /hydra/suggestions/
                 accepted → apply_hydra_suggestion
                     │
                     ▼
                 PR opened on Hydra repo with proposed CLAUDE.md / ADR patch
                     │
                     ▼  human review & merge on Hydra
                 Hydra's behaviour improves  ─── feeds back into the next Hydra run
```

### What the learning bridge does for ISO clauses

| Clause | What's satisfied |
|---|---|
| 9.1.1 Monitoring and measurement | `hydra_pipelines` + `hydra_phases` = cross-change cost, duration, turn count, findings density. Rendered on `/hydra/` dashboard. |
| 9.1.3 Analysis and evaluation | `analyze_pipelines` + `hydra_finding_clusters` = automated cross-pipeline pattern analysis. Weekly trend charts. |
| 10.2 Corrective action | `suggest_improvements` + `apply_hydra_suggestion` = automated proposal loop with HITL approval. |
| 10.3 Continual improvement | Success metric: 30%+ drop in average reviewer findings per pipeline; 25%+ drop in median time-to-done; first-pass success from ~40% to >60%. Measured from `HydraPipeline.findings.count()` and `HydraPipeline.ended_at - started_at`. |

### What's still missing

Three honest gaps remain. All are narrow. Each has an OpenSpec change raised under `concurrentie-analyse/openspec/changes/` on `spec/*` branches:

1. **`link-findings-to-features`** — `HydraPipeline` has no FK to `canonical_features`. So we know "cluster X recurred on 7 pipelines" but not "on pipelines building these 3 feature categories." Closes the analysis-side of 9.1.3 for feature-level queries.
2. **`embed-feature-id-in-issues`** — complementary: have `push_roadmap_issues.py` emit `feature_id` on issues so the enrichment phase in change 1 has a machine-readable anchor.
3. **`add-spec-pipeline-throughput-view`** — a view on `/specs/throughput/` showing `app_specs.status` transitions (proposed → created → pushed → merged) per week, joined to `hydra_pipelines` for mean change age. Closes Board-1 / Board-2 of the § 9.1.1 management metrics panel.

A smaller residual gap: the operator cron entry ("0 3 * * * cd … python3 manage.py hydra_nightly …") sits in the host crontab, not in a reproducible Ansible / Docker Compose manifest. Spelled out in `docs/hydra-learning/README.md` but not automated. This is 7.5.3 (control of documented information) adjacent — worth adding to the 27001 track.

---

# Clause 4 — Context of the Organization

## 4.1 Understanding the organization and its context

*What the standard asks.* Determine external and internal issues relevant to the organization's purpose and its ability to achieve intended QMS results.

**Our implementation.** Conduction's context — open-source ecosystem serving Dutch public administration — is recorded in the company-wide CLAUDE.md, in [.github/docs/claude/](../claude/), and in the roadmap at [.github/docs/ROADMAP.md](../ROADMAP.md). External context is *measured* — the Specter intelligence DB (see § 0a) currently holds 75.6K tenders, 151.4K requirements, 6.8K canonical features and 98 tracked competitors, refreshed weekly by the Sunday 02:00 UTC GitHub Actions sync.

**Coverage.** *Partial.*

**Gap & how to close.** There is no single "context of the organization" document. The information is spread across CLAUDE.md, the roadmap, and the intelligence DB. Closing the gap: produce one short summary (1–2 pages) at `.github/docs/iso/context.md` that names internal issues (team size, multi-repo sprawl, shared stack), external issues (VNG standards, EU tender directives, Nextcloud upstream), and links out to the authoritative sources.

## 4.2 Needs and expectations of interested parties

*What the standard asks.* Identify interested parties relevant to the QMS and their requirements.

**Our implementation.** Interested parties are captured across three channels:

- **Specter's DB** (§ 0a) — 92 `stakeholders`, 285 `customer_journeys`, 1.9K `user_stories`, 127 `nl_standards` rows. This is an interested-parties register in all but name.
- **Persona skills** — eight `test-persona-*` agents (Henk, Fatima, Sem, Annemarie, Jan-Willem, Mark, Priya, Noor) that name end-user archetypes used for testing.
- **Standards** — VNG, Logius, Forum Standaardisatie surface in the 127 imported `nl_standards` rows plus the `gemma_components` / `gemma_services` / `laws` / `law_articles` tables.

**Coverage.** *Partial.*

**Gap & how to close.** The data exists but is not presented as a single party register that names (a) the party, (b) the requirement they impose, (c) where we evidence satisfying it. A view / script against the existing DB — `scripts/specter-interested-parties.py` — could render the table directly. Low effort, no new data.

## 4.3 Determining the scope of the quality management system

*What the standard asks.* Define boundaries and applicability of the QMS.

**Our implementation.** Implicit scope: the apps under `apps-extra/` plus the shared platforms (OpenRegister, Hydra, nextcloud-vue). External components such as `Softwarecatalogus/` (VNG client repo) are explicitly out of scope per the CLAUDE.md instruction *"NEVER commit"*.

**Coverage.** *Partial.*

**Gap & how to close.** The scope is known in practice but not written down as a QMS scope statement. One paragraph naming the apps in scope, the shared infrastructure, and the explicit exclusions (e.g. client repos, third-party submodules) would close this.

## 4.4 Quality management system and its processes

*What the standard asks.* Establish, implement, maintain and continually improve a QMS, including the processes needed and their interactions.

**Our implementation.** The QMS *is* the pipeline in § 0. The processes and their interactions are specified by the 23 Hydra ADRs and the `/opsx-*` skill chain. Process ownership: Hydra owns code-review and security-review; Specter owns intelligence→spec; CI workflow owns quality gates; human reviewers own release.

**Coverage.** *Full.*

---

# Clause 5 — Leadership

## 5.1 Leadership and commitment (5.1.1 General / 5.1.2 Customer focus)

*What the standard asks.* Top management must demonstrate leadership and commitment to the QMS and to customer focus.

**Our implementation.** Leadership commitment shows up in the ADRs themselves — ADR-014 mandates EUPL-1.2 licensing + SPDX headers on every file; ADR-015 codifies a 15-point pre-commit checklist evolved from 77 real review findings ([project_hydra-adr-iteration.md](../../../.claude/memory/project_hydra-adr-iteration.md)). Customer focus is embodied in the 8 persona testers and the tender-driven roadmap.

**Coverage.** *Partial.*

**Gap & how to close.** We have actions but no explicit quality-commitment artefact. A signed-off one-pager from leadership — "we commit to these ADRs, this pipeline, this review cadence" — would take this to Full.

## 5.2 Policy (5.2.1 Establish / 5.2.2 Communicate)

*What the standard asks.* A quality policy appropriate to the organization's purpose, providing a framework for objectives, documented, communicated, understood, applied, available to interested parties.

**Our implementation.** None explicit.

**Coverage.** *None.*

**Gap & how to close.** Write and publish `.github/docs/iso/quality-policy.md`. It should be short (half a page), link into this folder, and be referenced from the top-level README. ISO/IEC 90003 §5.2 does not add software-specific requirements beyond 9001's.

## 5.3 Organizational roles, responsibilities and authorities

*What the standard asks.* Assign, communicate and understand responsibilities and authorities for QMS roles.

**Our implementation.** Roles are expressed through Hydra agent roles (builder, reviewer, security-reviewer, fixer) and the Scrum-team skills (`team-po`, `team-architect`, `team-backend`, `team-frontend`, `team-reviewer`, `team-qa`, `team-sm`). Branch-protection rulesets encode authority: who can approve for development / beta / main.

**Coverage.** *Partial.*

**Gap & how to close.** Write a short RACI-style table of human roles — who approves ADRs, who owns Hydra config, who signs off on a release — alongside the agent-role map.

---

# Clause 6 — Planning

## 6.1 Actions to address risks and opportunities

*What the standard asks.* Consider issues (4.1) and requirements (4.2), determine risks and opportunities, plan actions, evaluate effectiveness.

**Our implementation.** Risk-based thinking is baked into the pipeline: 9 mechanical Hydra gates address specific OWASP/CWE risks (e.g. `no-admin-idor` for A01:2021 IDOR, `unsafe-auth-resolver` for silent-fail-open auth, `semantic-auth` for annotation/body mismatch). Each new gate typically springs from a concrete incident — e.g. `semantic-auth` from decidesk#44 (2026-04-23). This is exactly the "plan actions to address risks" cycle, just executed at skill-definition level.

**Coverage.** *Full* for technical code-level risks; *Partial* for business/organizational risks (no risk register).

**Gap & how to close.** A lightweight risk register at `.github/docs/iso/risks.md` capturing non-code risks: dependency on Nextcloud upstream, Cyso hosting, single-maintainer bus factor per app, EU tender deadlines. Re-evaluate quarterly.

## 6.2 Quality objectives and planning to achieve them

*What the standard asks.* Establish measurable quality objectives at relevant functions; document them; plan what, who, when, resources, how evaluated.

**Our implementation.** Implicit objectives: `composer check:strict` passes, 75 % spec-to-test coverage threshold (per [project_testing-architecture.md](../../../.claude/memory/project_testing-architecture.md)), Newman + Playwright both green, license allowlist clean, zero Psalm errors. These live in the quality.yml job definitions, not in a separate objectives document.

**Coverage.** *Partial.*

**Gap & how to close.** Extract the implicit objectives into `.github/docs/iso/objectives.md` with the 9001 format: objective, target, measurement method, review cadence. The numbers already exist; they just need collecting.

## 6.3 Planning of changes

*What the standard asks.* When the QMS needs change, plan it — purpose, consequences, integrity, resources, responsibilities.

**Our implementation.** The OpenSpec *change* format. `hydra/openspec/changes/{slug}/` contains proposal.md (purpose), design.md (consequences), tasks.md (work breakdown). The `/opsx-*` skill chain enforces that every change goes through propose → plan → apply → verify → archive. ADR changes follow the same flow.

**Coverage.** *Full.*

---

# Clause 7 — Support

## 7.1 Resources

### 7.1.1 General

*What.* Determine and provide resources needed for the QMS.

**Our implementation.** Resources = compute (Docker Compose dev env, CI runners), tooling (Composer, npm, Playwright, Psalm, PHPStan), data (intelligence DB, seed data), agents (Hydra, Specter). All tracked in `.github/docker-compose.yml`, `composer.json`, `package.json`, and the skills inventory.

**Coverage.** *Full.*

### 7.1.2 People

*What.* Determine and provide persons necessary.

**Our implementation.** Combination of human engineers and AI agents (the 9 Scrum-team skills, 8 persona testers, 7 testing-team agents). The agent inventory is the clearest record.

**Coverage.** *Full.*

### 7.1.3 Infrastructure

*What.* Determine, provide and maintain infrastructure (buildings, equipment, ICT, transport).

**Our implementation.** ICT infrastructure: GitHub (code + CI + issues + PRs), Cyso hosting (production, ISAE 3402), Docker Compose (dev/test), 7 Playwright MCP browser sessions (browser-1 … browser-7), Ollama + Qwen 3.5 for local LLM inference. Documented in CLAUDE.md and [.github/docs/claude/](../claude/).

**Coverage.** *Full.*

### 7.1.4 Environment for the operation of processes

*What.* Provide and maintain the environment needed for operation.

**Our implementation.** Dev environment reproducible via `bash clean-env.sh` / `/clean-env` skill. CI environment defined in quality.yml job containers (matrix of PHP × Nextcloud versions).

**Coverage.** *Full.*

### 7.1.5 Monitoring and measuring resources

*What.* Ensure resources are suitable for the monitoring/measurement activity and are maintained (in classic ISO 9001 this is about calibrating rulers and scales).

**Our implementation.** Software analogue: the test suites, linters, and static analysers are themselves "measuring instruments". We pin their versions (composer.lock, package-lock.json), update them deliberately, and the PHPUnit baseline guard in quality.yml detects regressions in the measurement itself.

**Coverage.** *Partial — with interpretation.* ISO/IEC 90003 §7.1.5 explicitly allows this software reinterpretation; we do pin versions but do not formally document a tool-suitability check.

**Gap & how to close.** A short "tool-suitability" note in `objectives.md` or a dedicated file: which tools we rely on, how we know the version is fit for purpose, how we handle updates.

### 7.1.6 Organizational knowledge

*What.* Determine the knowledge necessary for operating processes, maintain it, make it available, and consider how to acquire additional knowledge.

**Our implementation.** This is one of our strongest clauses. Knowledge lives in:

- **23 ADRs** in `hydra/openspec/architecture/` — every architectural decision recorded with context and consequences.
- **CLAUDE.md files** — layered (root, per-repo, per-app) — provide instructions to both humans and agents.
- **[.github/docs/](../)** — developer docs, pipeline overview, container architecture, deployment models, retrospectives.
- **Shared OpenSpec** — i18n specs, schemas, cross-app changes at `hydra/openspec/specs/`.
- **Memory index** — per-user memory under `~/.claude/projects/…/memory/MEMORY.md` preserves project-specific facts across sessions.
- **Retrospectives** — `hydra/docs/retrospectives/`.

**Coverage.** *Full.*

## 7.2 Competence

*What.* Determine required competence; ensure persons are competent; take actions to acquire it; evaluate effectiveness.

**Our implementation.** For humans: no formal competence matrix. For agents: each skill has an explicit description and — where applicable — a worked example. The Hydra pipeline is itself a forcing function: if an agent-produced PR fails the gates, the agent's "competence" is measured objectively.

**Coverage.** *Partial* (humans) / *Full* (agents).

**Gap & how to close.** A skills matrix for humans listing required competences per role (backend PHP, Vue, pipeline ops, security review) and recorded training. Not heavy — one table.

## 7.3 Awareness

*What.* Persons doing work under the QMS are aware of the quality policy, relevant objectives, their contribution, implications of non-conformity.

**Our implementation.** CLAUDE.md loads on every session; MEMORY.md reinforces preferences; ADRs are referenced in issue templates and PR reviews. Non-conformity implications are very visible (the PR doesn't merge).

**Coverage.** *Partial* — awareness of the implicit objectives is high; awareness of a formal *policy* is impossible because one doesn't yet exist (see 5.2).

**Gap & how to close.** Closes automatically once 5.2 (policy) and 6.2 (objectives) are written.

## 7.4 Communication

*What.* Determine internal and external communications (what, when, with whom, how, who).

**Our implementation.** GitHub issues, PR comments, and review threads form the primary communication channel. Hydra comments are labelled with stage markers (`[fixed:…]`, `[unfixed:…]`). Specter-produced issues carry `ready-to-build` labels. Labels are the protocol.

**Coverage.** *Full* internally; *Partial* externally (no external-communication plan).

**Gap & how to close.** If we begin communicating QMS status to external parties (customers, auditors), add an external-communication matrix. Until then this is fine.

## 7.5 Documented information

### 7.5.1 General

*What.* The QMS shall include documented information required by the standard and information determined necessary for QMS effectiveness.

**Our implementation.** Documented information sits in predictable locations:

- Standards-mandated: policies/objectives (currently gaps — see 5.2, 6.2).
- Process-mandated: ADRs, OpenSpec changes, specs.
- Evidence: `hydra.json` per change, quality.yml artefacts, PR reviews.

**Coverage.** *Partial* pending the 5.2/6.2 artefacts.

### 7.5.2 Creating and updating

*What.* Ensure appropriate identification, description, format, review, approval.

**Our implementation.** All documented information is versioned via Git. The standard file layout (ADR naming `adr-NNN-name.md`, changes `changes/{slug}/`, specs `specs/{area}/spec.md`) provides identification. Review/approval = PR approval.

**Coverage.** *Full.*

### 7.5.3 Control of documented information (availability, protection, distribution, retention, obsolete handling)

*What.* Control it — availability where needed, protection from loss, distribution, retention, handling of obsolete information.

**Our implementation.** Availability: Git + GitHub. Protection: org rulesets, 2-review gate on main. Retention: Git history is permanent; archived changes go to `changes/archive/`. Obsolete handling: `opsx-archive` skill; superseded ADRs are marked rather than deleted (convention).

**Coverage.** *Full.*

---

# Clause 8 — Operation

This is where the weight of the mapping sits. Clause 8 covers planning, requirements, design & development, supply, production, release, and non-conformity — in software terms: the whole engineering loop.

## 8.1 Operational planning and control

*What.* Plan, implement and control the processes needed to meet requirements for products and services.

**Our implementation.** The pipeline in § 0 is the operational plan, made executable by skill chains (`/opsx-new`, `/opsx-ff`, `/opsx-apply`, `/opsx-verify`, `/opsx-archive`). Quality.yml is the per-PR runtime control.

**Coverage.** *Full.*

## 8.2 Requirements for products and services

### 8.2.1 Customer communication

*What.* Provide product information, handle enquiries/contracts/orders/amendments, obtain feedback/complaints, handle customer property, establish contingency actions.

**Our implementation.** GitHub Issues + PR comments + labels serve as the primary customer-communication surface. Each OpenSpec change is linked to one or more issues (`opsx-plan-to-issues` skill). Tender intake is automated — Specter ingests tender data into the intelligence DB weekly (GitHub Actions Sunday 02:00 UTC sync).

**Coverage.** *Full* for software-project communication.

### 8.2.2 Determining requirements for products and services

*What.* Ensure requirements, including applicable statutory/regulatory, are defined.

**Our implementation.** Specter's `requirements` table (151.4K rows) is the authoritative source for tender-driven requirements. `canonical_features` (6.8K rows) de-duplicates and scores them; `canonical_feature_sources` links every canonical feature back to the specific tender / competitor / external evidence rows with a confidence score. Statutory / regulatory inputs come from the Forum Standaardisatie imports (127 `nl_standards` rows), the `laws` / `law_articles` tables (4.277K law articles), and the `gemma_components` / `gemma_services` tables (254 + 422 rows).

**Coverage.** *Full.*

### 8.2.3 Review of requirements for products and services

*What.* Review requirements before committing to provide; ensure requirements are resolved, organization has the capability, differences understood.

**Our implementation.** Two review gates: the `openspec-propose` / `opsx-ff` step forces a proposal document before any code is written; the human PO (via `team-po` skill or real person) approves the change before it leaves the `proposed` state.

**Coverage.** *Full.*

### 8.2.4 Changes to requirements for products and services

*What.* When requirements change, ensure documented information is amended and relevant persons are aware.

**Our implementation.** OpenSpec changes are first-class objects; amendments flow through the same lifecycle. `opsx-sync` syncs delta specs to main specs on archive. Awareness propagates via issue comments and label changes.

**Coverage.** *Full.*

## 8.3 Design and development of products and services

This is the central clause for software engineering and the one ISO/IEC 90003 expands on most.

### 8.3.1 General

*What.* Establish, implement and maintain a design and development process appropriate to ensure subsequent provision of products and services.

**Our implementation.** The Specter → Hydra → CI → reviewer chain *is* the D&D process. It is maintained by the ADR set and evolved via the ADR iteration loop (see 10.3).

**Coverage.** *Full.*

### 8.3.2 Design and development planning

*What.* Plan stages, reviews, verification, validation, responsibilities, resources, interfaces, customer involvement, documented information needs.

**Our implementation.**

- **Stages** — propose → design → plan → apply → verify → archive. Each stage has a named skill.
- **Reviews** — code-review + security-review agents, human approval.
- **Verification** — `/opsx-verify` checks implementation against tasks.md.
- **Validation** — Playwright E2E + Newman API tests + persona testers validate user-facing behaviour.
- **Responsibilities** — agent roles in `hydra.json`; human roles via org rulesets.
- **Resources** — container-pool model (ADR-013) bounds compute per stage.
- **Interfaces** — ADR-002 (API), ADR-022 (apps consume OR abstractions).
- **Documented information** — proposal.md, design.md, tasks.md per change.

**Coverage.** *Full.*

### 8.3.3 Design and development inputs

*What.* Determine requirements essential to the types being designed; consider functional/performance, applicable statutory/regulatory, standards, potential consequences of failure.

**Our implementation.** Inputs are assembled by `concurrentie-analyse/scripts/generate_spec_content.py` (pure DB → markdown, no LLM) into a `context-brief.md` per app, then carried into `hydra/openspec/changes/{slug}/proposal.md` + `design.md`. The brief draws from: `canonical_features` + `canonical_feature_sources` (functional requirements with evidence trail), `nl_standards` / `gemma_*` / `laws` (statutory & regulatory), `competitor_features` (what peers ship), `ecosystem_gaps` (what is missing), ADR-005 (consequences-of-failure thinking for security-sensitive paths).

**Coverage.** *Full.*

### 8.3.4 Design and development controls

*What.* Apply controls to ensure D&D results meet input requirements; reviews, verifications, validations, actions on problems.

**Our implementation.** This is where the bulk of the pipeline lives.

- **Reviews**: Hydra `reviewer` agent posts findings with `[fixed:…]` / `[unfixed:…]` markers; security-reviewer runs separately; human PR review gates merge.
- **Verifications**: 9 mechanical Hydra gates (`spdx`, `forbidden-patterns`, `stub-scan`, `composer-audit`, `route-auth`, `orphan-auth`, `no-admin-idor`, `unsafe-auth-resolver`, `semantic-auth`). Quality.yml static-analysis bank: PHPCS, PHPMD, Psalm, PHPStan, ESLint, Stylelint.
- **Validations**: PHPUnit (unit), Newman (integration), Playwright (E2E), persona testing (`test-persona-*` agents).
- **Actions on problems**: `needs-input` escalation pattern — on container crash or unresolvable finding, issue leaves the queue and is surfaced to humans. Fixer agent applies `[unfixed:…]` item resolutions within bounded scope (ADR-021).

**Coverage.** *Full* — this is the clause our pipeline was architected around.

### 8.3.5 Design and development outputs

*What.* Ensure outputs meet input requirements; adequate for subsequent processes; include/reference monitoring & measurement requirements and acceptance criteria; specify characteristics essential for intended purpose and safe/proper provision.

**Our implementation.** Outputs of each stage are named files: `proposal.md`, `design.md`, `tasks.md`, source files with `@spec` tags, tests, `hydra.json`. Acceptance criteria are the gate set + tasks.md checkboxes + reviewer approval. ADR-003 mandates `@spec` PHPDoc tags at file/class/method level — the traceability anchor.

**Coverage.** *Full.*

### 8.3.6 Design and development changes

*What.* Identify, review and control changes made during or after D&D to avoid adverse impact; retain documented information on the changes, the results of reviews, authorisation, actions to prevent adverse impact.

**Our implementation.** OpenSpec changes are the unit of change. `hydra.json` stages record every action (locked writer, atomic via `scripts/lib/hydra_record.py`). Superseded ADRs are marked rather than deleted. `opsx-archive` + `opsx-sync` handle post-archive integrity.

**Coverage.** *Full.*

## 8.4 Control of externally provided processes, products and services

### 8.4.1 General

*What.* Ensure externally provided processes/products/services conform to requirements.

**Our implementation.** External dependencies flow through Composer (PHP) and npm (JS). Two controls: `composer audit` / `npm audit` at critical-level in quality.yml (a gate), and license checks against `.license-allowlist.json` with explicit overrides in `.license-overrides.json`. SBOM generation (CycloneDX) provides the external-inventory trail. External hosting: Cyso (ISAE 3402 Type II) provides the inherited control.

**Coverage.** *Full.*

### 8.4.2 Type and extent of control

*What.* Ensure externally provided processes remain within control of the QMS; define controls; consider impact on ability to meet requirements; take account of effectiveness of external provider's own controls; determine verification.

**Our implementation.** Type-of-control is tiered: runtime libraries (Composer/npm) → automated audit + license gate; hosting (Cyso) → contractual ISAE 3402; shared upstream (Nextcloud) → version-pinning + PHPUnit matrix testing across supported NC versions.

**Coverage.** *Full.*

### 8.4.3 Information for external providers

*What.* Communicate requirements to the external provider for processes/products/services, approval, competence, interactions, control and monitoring, verification activities, activities at provider premises.

**Our implementation.** Not a strong suit — we mostly *consume* external providers rather than commissioning bespoke work from them. The information flow to Nextcloud upstream (bug reports, patches) is ad-hoc.

**Coverage.** *Partial.*

**Gap & how to close.** Short process note for the cases where it matters: how we interact with Nextcloud upstream, how we raise CVE issues with Composer package maintainers. Low priority — our external-provider surface is narrow.

## 8.5 Production and service provision

### 8.5.1 Control of production and service provision

*What.* Implement production and service provision under controlled conditions: availability of documented information, monitoring & measuring resources, monitoring & measurement activities, suitable infrastructure & environment, competence of persons, validation of processes where output cannot be verified, actions to prevent human error, release/delivery/post-delivery activities.

**Our implementation.** Controlled conditions for each PR: the 4-layer pipeline, the 9 mechanical gates, the full quality.yml bank, the PHPUnit matrix (PHP × Nextcloud backends). Actions to prevent human error: *everything* the pipeline catches before a human looks — the 15-point pre-commit checklist (ADR-015), the gate set, the forbidden-patterns scanner.

**Coverage.** *Full.*

### 8.5.2 Identification and traceability

*What.* Identify outputs by suitable means; identify the status of outputs with respect to monitoring & measurement requirements; control unique identification of outputs when traceability is a requirement; retain documented information necessary for traceability.

**Our implementation.** The full evidence chain end-to-end — from tender in Brussels to a line of PHP in a Nextcloud app:

```
tenders / external_sources / requirements     (raw evidence)
        │
        ▼  Specter feature extraction
canonical_features  ◀──  canonical_feature_sources  (source_table, source_id, confidence)
        │
        ▼  app_specs.brief_data (JSON)
context-brief.md                                (generate_spec_content.py, DB-only)
        │
        ▼  /opsx-ff
hydra/openspec/changes/{slug}/proposal.md + design.md + tasks.md
        │
        ▼  push_roadmap_issues.py
GitHub issue  (labels: ready-to-build | blocked | yolo)
        │
        ▼  Hydra supervisor picks up
hydra.json cycles[], stages[], findings[]        (atomic, locked writer)
        │
        ▼  builder stage writes code with @spec tag
source file: @spec openspec/changes/{slug}/tasks.md#task-N
        │
        ▼  commit with (#N), PR with "Closes #N"
merged code on main
```

- **Unique IDs** — slug at the change level; `canonical_features.id` at the evidence level; `@spec` tag at the source-line level; GitHub issue number at the workflow level.
- **Status tracking** — at the evidence level: `app_specs.status` (`draft` / `created` / `pushed` / `merged`). At the workflow level: issue labels (`proposed`, `in-progress`, `code-review:queued`, `needs-input`, `ready-to-merge`, etc.). At the code level: `findings[].status` in `hydra.json`.
- **Reverse chain works**: `git blame` → commit `(#N)` → PR `Closes #N` → issue → change folder → `@spec` tag matches tasks.md line.

**Where the chain breaks (honest).** Walking *backward* from a merged PR through the GitHub issue lands at a change folder — but the link to `canonical_features.id` is in prose in the issue body, not as a machine-readable label or front-matter key. So today the last hop from "change folder" back to "the specific canonical feature and its source evidence" is a human step, not an automated one.

**Coverage.** *Full* for forward traceability from any point in the chain onward. *Partial* for automated reverse traceability from code to the originating canonical-feature row (breaks at the issue ↔ feature_id hop).

**Gap & how to close.** Two OpenSpec changes raised: `embed-feature-id-in-issues` (Specter-side: `push_roadmap_issues.py` emits `feature_id` in issue body front-matter / as a label) + `link-findings-to-features` (DB-side: `HydraPipeline.canonical_feature_id` FK + enrichment). Either alone closes the forward walk; together they close both directions and make feature-level metrics queryable.

### 8.5.3 Property belonging to customers or external providers

*What.* Exercise care with property belonging to the customer or external providers while under the organization's control.

**Our implementation.** Customer property in the software sense is the data users store in Nextcloud instances. Data-handling is out of scope for *code quality* and belongs in a future `security.md` (ISO 27001). Where customer repositories are involved (e.g. `Softwarecatalogus/`), the CLAUDE.md rule is explicit: *NEVER commit*.

**Coverage.** *N/A* for this document — covered under 27001 scope.

### 8.5.4 Preservation

*What.* Preserve outputs during production and service provision to the extent necessary to maintain conformity.

**Our implementation.** Git preserves source. Build artefacts preserved via CI artefact upload. `hydra.json` preserves pipeline state atomically. Container images pinned by tag/digest.

**Coverage.** *Full.*

### 8.5.5 Post-delivery activities

*What.* Meet post-delivery requirements associated with the products/services; consider statutory/regulatory, potential consequences, nature/use/lifetime, customer requirements, customer feedback.

**Our implementation.** Bug fixes flow through the same pipeline as new work. Security CVEs in dependencies are surfaced by `composer audit` / `npm audit` at each CI run (not only on new work). Hotfix branch pattern is encoded in `branch-protection.yml` (`hotfix/*` allowed into main and beta).

**Coverage.** *Full.*

### 8.5.6 Control of changes

*What.* Review and control changes for production or service provision to ensure continuing conformity.

**Our implementation.** Same as 8.3.6 — change is the unit of production. Every production change is an OpenSpec change.

**Coverage.** *Full.*

## 8.6 Release of products and services

*What.* Implement planned arrangements at appropriate stages to verify product/service requirements are met; retain documented information on release — evidence of conformity, traceability to authorising person.

**Our implementation.**

- **Release gates**: quality.yml green + Hydra `ready-for-code-review` complete + `ready-for-security-review` complete + human approval (1 reviewer for development, 1 for beta, 2 for main per org rulesets).
- **Conformity evidence**: quality-report.md + SBOM (CycloneDX) + Newman reports + Playwright reports + `hydra.json`.
- **Authoriser traceability**: PR approvals are GitHub-signed and retained.

**Coverage.** *Full.*

## 8.7 Control of nonconforming outputs

*What.* Ensure outputs not conforming to requirements are identified and controlled to prevent unintended use/delivery; take action based on nature; verify conformity after correction; retain documented information describing the nonconformity and actions taken.

**Our implementation.** Non-conformity handling is one of the pipeline's defining features. It operates at two levels: *automated correction* of in-scope findings, and *terminal-state escalation* for anything the automation cannot handle safely.

**Identification.** Multiple detectors:

- 9 mechanical Hydra gates and the quality.yml static bank emit findings with `severity`, `gate`, `rule`, `file`, `line`.
- Reviewer agent emits `[fixed:…]` / `[unfixed:…]` markers in PR comments.
- Playwright / Newman failures surface as failed CI jobs.
- Orchestrator emits `pattern_tags` on abnormal runs: `turn-budget-exhausted`, `recheck-caught-new-findings`, `container-crashed-mid-stage`.

**Control — the `needs-input` terminal state.** When automation cannot safely proceed, the issue is labelled `needs-input` and all automated handlers short-circuit before emitting further side-effects. The triggers, confirmed from `hydra/scripts/orchestrate.sh` and `hydra/CLAUDE.md`:

| Trigger | Meaning |
|---|---|
| Reviewer verdict = `fail` | Reviewer could not approve after the fixer's best attempt. |
| Applier verdict = `fail` | The code applier failed to apply the proposed change. |
| Quality recheck post-review fails | `recheck-caught-new-findings` — the post-fix gate pass surfaced new issues. |
| Container crashes mid-stage | `container-crashed-mid-stage` — infrastructure fault, not a code fault. |
| Label-state contradiction | Both `:pass` and `:fail` present on the issue — internally inconsistent state. |

The terminal-state invariant is encoded repeat-offender-proof in `hydra/CLAUDE.md` (lines 580–598):

> *"Labels like `needs-input`, `*:fail`, `*:pass`, `applier:*` are terminal — once set, the pipeline has made a decision and further state-machine side effects must not fire on that issue. Every handler that might emit a side effect (comment post, label swap, container dispatch) MUST short-circuit before the side effect if the issue is already in a terminal state."*

This rule exists because of the decidesk#44/#45 incident (2026-04-23) where 134+ duplicate escalation comments were posted by handlers re-entering on an already-terminal issue (fixed in hydra PR #133).

**Action.** In-scope findings are resolved by the fixer agent, bounded by change-shape per ADR-021 so the fixer cannot widen the blast radius. Out-of-scope findings, infrastructure faults, and unresolvable reviewer verdicts escalate to `needs-input` and wait for human intervention.

**Verify after correction.** Re-running the gate bank; reviewer re-runs after fixer passes.

**Documented information.** `hydra.json` records every finding (with `status` transitions: `open` → `fixed_in_stage` / `fixed_later` / `wontfix`) and every fixer decision. Per-change records are atomic (locked writer).

**Coverage.** *Full* for the per-issue handling of a single non-conformity.

*Partial* for the **aggregate** handling. The standard in 8.7 asks us to take action "based on the nature" of the non-conformity — at single-issue granularity we do; across issues we don't yet see the pattern. There is no register of `needs-input` incidents, no recurrence analysis, no "this trigger fired N times last month in N apps."

**Gap & how to close.** A `/hydra/needs-input/` view on the Specter `hydra_learning` dashboard: query `hydra_pipelines.final_status='needs-input'` grouped by `outcome_reason`. The data already exists (ingested nightly); only the view is missing. Small residual noted in the gap shortlist; could be folded into any of the three raised OpenSpec changes.

---

# Clause 9 — Performance Evaluation

## 9.1 Monitoring, measurement, analysis and evaluation

### 9.1.1 General

*What.* Determine what needs monitoring & measurement, methods, when, when results analysed.

**Our implementation — per-PR (works today).** Monitored and published per PR: gate pass/fail, PHPUnit coverage, spec-to-test coverage (75 % threshold), Newman pass rate, Playwright pass rate, `composer audit` findings, `npm audit` findings, license-compliance result, SBOM. Measurements land in `quality-report.md` per PR and in `hydra.json` per change.

**Our implementation — cross-change (gap).** The single-PR view is complete. The cross-change view — what management should actually look at — does not exist today. The data is in `hydra.json` but no script aggregates it.

**Management metrics panel.** Five boards. Most are already rendered — Boards 1-3 land in the `hydra_learning` dashboard at `/hydra/` (§ 0c); most of Board 5 lands in the Specter intelligence dashboard (82 views, including addressable-market-per-app, ecosystem-gaps top-N, last-7-day tenders, competitor activity, source-sync health). Gaps are narrow and named below.

**Board 1 — Throughput**

| Metric | Definition | Source | Status |
|---|---|---|---|
| Specs closed per week | Count of changes moving `proposed` → `archived` per week | `app_specs.status` transitions + `HydraPipeline.ended_at` | **gap — raised as `add-spec-pipeline-throughput-view`** |
| Mean change age | Median days from first `HydraPipeline.started_at` to archive | `HydraPipeline.started_at` → archive event | **gap — same change** |
| Clean-archive rate | % of changes archived without ever entering `needs-input` | `HydraPipeline.final_status` history | **gap — same change** |
| Cycles per change | Median count of `HydraPipeline` rows per `repo,issue_num` | `HydraPipeline` group-by | today via dashboard |

**Board 2 — Cost**

| Metric | Definition | Source | Status |
|---|---|---|---|
| Tokens per pipeline | Sum of `HydraPhase.turns` across a pipeline | `hydra_phases.turns` | today via dashboard |
| USD per pipeline | Sum of `HydraPhase.cost_usd` | `hydra_phases.cost_usd` | today via dashboard |
| USD per feature category | USD aggregated by the feature category the pipeline built | `hydra_phases.cost_usd` + *(new)* `HydraPipeline.canonical_feature_id` | **gap — raised as `link-findings-to-features`** |
| Budget-exhaustion rate | % of phases with `terminal_reason='max_turns'` | `hydra_phases.terminal_reason` | today via dashboard |

**Board 3 — Quality**

| Metric | Definition | Source | Status |
|---|---|---|---|
| Findings per pipeline | Weekly trend of `hydra_findings` count per pipeline | `hydra_findings` | today — rendered on `/hydra/` |
| First-pass success rate | % of pipelines reaching `final_status='done'` on first iteration | `hydra_pipelines` + `hydra_phases` | today — rendered on `/hydra/` |
| Autofix success rate | % of `hydra_findings` with `status='fixed'` and `fixed_in_round=1` | `hydra_findings.status`, `fixed_in_round` | today via dashboard |
| Cluster recurrence top-10 | Top 10 `HydraFindingCluster` rows by `pipeline_count` | `hydra_finding_clusters` | today — rendered on `/hydra/findings/` |
| `needs-input` incidence | Count of `HydraPipeline` rows with `final_status='needs-input'` grouped by trigger | `hydra_pipelines.final_status` + `outcome_reason` | **gap — dashboard view not yet built** |
| Suggestion accept/reject ratio | `HydraSuggestion.status` histogram over trailing 30 days | `hydra_suggestions.status` | today via dashboard |

**Board 4 — Adoption**

| Metric | Definition | Source | Status |
|---|---|---|---|
| Active instances per app | Count of NC instances with app installed and used in last 30 days | **New telemetry required** | not today |
| Feature-usage within app | Controller-level hit counts per feature | **New telemetry required** | not today |
| Time to first use after release | Days from app update to first production invocation | **New telemetry required** | not today |

**Board 5 — Intelligence (Specter-side)**

| Metric | Definition | Source | Status |
|---|---|---|---|
| Sources synced per week | Successful `source_syncs` rows in the last 7 days | `source_syncs.last_sync`, `records_synced` | today |
| Requirements ingested per week | New rows in `requirements` per week | `requirements` timestamp | today |
| Features discovered per source | `canonical_feature_sources` grouped by `source_table` over last 30 days | `canonical_feature_sources` | today |
| Competitor signals processed | Rows in `competitor_features` with `category` like `release-*` or `enhancement-issue`, weekly | `competitor_features` | today |
| Addressable market per app | Sum `tender_awards.contract_value` joined to `tender_app_relevance` | `tender_awards`, `tender_app_relevance` | today |
| Spec-pipeline throughput | Count by `app_specs.status` (`draft` / `created` / `pushed` / `merged`) | `app_specs` | today |
| Open ecosystem gaps | Count of `ecosystem_gaps` without a matching app | `ecosystem_gaps` | today |

**Where each board lives today.**

- Boards 2 & 3 (cost & quality) — `/hydra/` dashboard (§ 0c) renders them off the `hydra_*` tables. Shipped 2026-04-17.
- Most of Board 5 (Specter intelligence) — rendered on the intelligence home dashboard at `/` (82 views; KPIs for addressable market per app, ecosystem gaps, last-7-day tenders, competitor activity, source-sync health).
- Board 1 (throughput) — **not yet rendered**. Data exists across `app_specs.status` + `hydra_pipelines` but no view joins them. OpenSpec change raised: `add-spec-pipeline-throughput-view`.
- Board 2 cost-per-feature-category — **not yet possible**. Needs `HydraPipeline.canonical_feature_id` FK. Raised as `link-findings-to-features`.
- Board 3 `needs-input` incidence — **not yet rendered**. Data is in `hydra_pipelines.final_status`; a `/hydra/needs-input/` view would close it.
- Board 4 (adoption) — requires opt-in NC-instance telemetry. Separate roadmap decision; GDPR + user-trust tradeoffs.

**Coverage.** *Full* for per-PR monitoring. *Full* for cross-change monitoring on Boards 2, 3, and most of 5 (via `hydra_learning` + intelligence dashboards). *Partial* on Boards 1 and Board-2 feature-level (pending the three OpenSpec changes listed above). *None* on Board 4 (adoption).

**Gap & how to close.** The three OpenSpec changes listed above close Boards 1 and the feature-level slice of Board 2. The `needs-input` dashboard view is a small residual. Board 4 stays a separate decision.

### 9.1.2 Customer satisfaction

*What.* Monitor customers' perceptions of the degree to which their needs and expectations have been met.

**Our implementation.** Partial — persona testers serve as a proxy; real user feedback is not systematically gathered per release.

**Coverage.** *Partial.*

**Gap & how to close.** This is a genuinely harder clause for open-source projects. A minimal closure: track GitHub issues tagged `user-report` and `feature-request`; review trend quarterly. A stronger closure: embed feedback in the apps themselves and aggregate.

### 9.1.3 Analysis and evaluation

*What.* Analyse and evaluate data from monitoring; use results to evaluate conformity, customer satisfaction, QMS performance/effectiveness, effectiveness of actions, external providers, need for improvement.

**Our implementation.** Analysis runs automatically via the `hydra_learning` learning bridge (§ 0c):

- `analyze_pipelines` management command runs nightly at 03:00 UTC, fingerprints `hydra_findings` titles, updates `hydra_finding_clusters` with `pipeline_count`, `severity_mix`, `first_seen`, `last_seen`.
- Coverage detection is grep-based against Hydra's current CLAUDE.md + ADRs, setting `covered_by_claude_md` / `covered_by_adr` on each cluster.
- Uncovered high-frequency clusters flow into `suggest_improvements` → `hydra_suggestions`.

Human-authored retrospectives live at `hydra/docs/retrospectives/` and complement the automated pass — 77 review findings (project_hydra-adr-iteration.md) drove the original ADR evolution.

**Coverage.** *Full* — automated cross-pipeline pattern analysis ships with `hydra_learning` (2026-04-17 backfill produced 752 clusters from 481 pipelines; 627 uncovered clusters flagged for potential gate / ADR updates).

One residual gap — analysis by feature category is currently blocked because `hydra_pipelines` has no FK to `canonical_features`. Raised as `link-findings-to-features`.

## 9.2 Internal audit

*What.* Conduct internal audits at planned intervals to provide information on whether the QMS conforms to its own requirements and to this standard, and is effectively implemented and maintained.

**Our implementation.**

- **Automated**: `opsx-coverage-scan` audits legacy apps for spec↔code coverage (the retrofit pipeline).
- **Workflow-internal**: quality.yml itself is a continuous audit running on every PR.
- **Process-level**: no planned-interval internal audit of the QMS as a whole.

**Coverage.** *Partial.*

**Gap & how to close.** Schedule a quarterly QMS-audit pass: pick 5 merged PRs at random, walk them back from merged code → `@spec` → tasks.md → change → issue → Specter intelligence row, and confirm every link holds. Output: a short audit note per quarter in `.github/docs/iso/audits/`.

## 9.3 Management review

*What.* Top management shall review the QMS at planned intervals; inputs and outputs as specified; retain documented information.

**Our implementation.** None as a formal activity.

**Coverage.** *None.*

**Gap & how to close.** Institute a quarterly (or whatever cadence fits) management review with a fixed agenda. Cadence and discipline matter more than length — ~2 hours per quarter is enough. Proposed agenda template, with each input tied back to its generating clause and, where relevant, the automation that feeds it:

### Management review — agenda template

**Inputs** (read before the meeting):

1. **Status of actions from previous review** — prior-quarter decisions and their state.
2. **Changes in external/internal issues** — roadmap shifts, new tender-driven priorities, Nextcloud upstream movements (feeds 4.1).
3. **QMS performance** — screenshot of `/hydra/` dashboard (cost, quality, trends) + intelligence home dashboard (addressable market, ecosystem gaps, source-sync health). Feeds 9.1.1.
4. **Non-conformities & corrective actions** — `hydra_pipelines` filter on `final_status='needs-input'` grouped by `outcome_reason` + list of new gates / ADRs shipped as corrective actions (feeds 8.7, 10.2).
5. **Monitoring & measurement results** — `/hydra/findings/` top-10 `HydraFindingCluster` ranked by `pipeline_count` with coverage flags; this is the most important input because it names the next potential gates.
6. **Audit results** — summary of any internal-audit notes from § 9.2 (quarterly 5-PR traceability walk) and results of the continuous per-PR audit implicit in quality.yml.
7. **External provider performance** — CVE exposure from `composer audit` / `npm audit` trends; Cyso (hosting) incident log if any.
8. **Adequacy of resources** — are the container pool budgets right (ADR-013)? Runner capacity? Maintainer bandwidth per app?
9. **Effectiveness of actions taken to address risks and opportunities** — status of risk-register items (feeds 6.1).
10. **Opportunities for improvement** — `/hydra/suggestions/` queue: pending suggestions + accept/reject ratio for the quarter.

**Outputs** (one short note per review, filed at `.github/docs/iso/reviews/YYYY-Qx.md`):

- Decisions on opportunities for improvement (new ADRs, new gates, new skills).
- Decisions on changes needed to the QMS (scope, roles, process).
- Decisions on resource needs (budgets, people, infra).

All ten inputs are already backed by shipped dashboards or queryable tables. Running the first review is purely a scheduling decision — no engineering prerequisite.

Coverage upgrade path: *None → Full* after the first review is held and the note is filed. No intermediate *Partial* step needed given the inputs are available.

---

# Clause 10 — Improvement

## 10.1 General

*What.* Determine and select opportunities for improvement; implement necessary actions to meet customer requirements and enhance customer satisfaction; improving products/services, correcting/preventing/reducing undesired effects, improving QMS performance/effectiveness.

**Our implementation.** Opportunities surface through: Specter-driven feature extraction, retrospectives, gate-failure patterns, user issues. Actions are implemented via new ADRs (e.g. ADR-020, ADR-021, ADR-022, ADR-023 all post-date the first 19), new gates (`semantic-auth` 2026-04-23), or new specs.

**Coverage.** *Full.*

## 10.2 Nonconformity and corrective action

*What.* React to the nonconformity; evaluate the need for action to eliminate the causes so it does not recur; implement actions; review effectiveness; update risks/opportunities; change the QMS if necessary; retain documented information on the nature of nonconformities, actions taken, results.

**Our implementation.** This is the clearest pattern we have.

- **React** — fixer agent (in-scope) or `needs-input` escalation (out-of-scope).
- **Cause-elimination** — when a class of finding recurs, a new mechanical gate is added. Worked example (all in April 2026): a reviewer-found IDOR on `decidesk#44` (2026-04-21) triggered `no-admin-idor`; a silent-fail-open auth resolver on `decidesk#45` (2026-04-21) triggered `unsafe-auth-resolver`; orphan auth methods on `decidesk#60` (2026-04-21) triggered `orphan-auth`; the `NoAdminRequired` annotation / `requireAdmin()` body mismatch on `decidesk#44` (2026-04-23) triggered `semantic-auth`. Four new gates in three weeks, each preventing recurrence of the specific class across the whole app portfolio.
- **Effectiveness review** — new gates run against subsequent PRs; false-positive and miss rates become visible over time in the `hydra.json` history.
- **Documented information** — gate skill definitions themselves record the triggering incident in their description. `hydra.json` records the resolved findings.

**Systematic recurrence detection — automated as of 2026-04-17.** Human-spotting still works but is no longer the only path. The `hydra_learning` learning bridge (§ 0c) fingerprints every finding, aggregates into `hydra_finding_clusters`, flags those not yet covered by existing CLAUDE.md or ADRs, and feeds the high-frequency uncovered ones into `suggest_improvements` which drafts a proposed CLAUDE.md or ADR patch using local `claude -p`. Humans review accept/reject in `/hydra/suggestions/`; `apply_hydra_suggestion` opens the PR on Hydra when accepted.

As-shipped: 752 clusters from 481 pipelines (2026-04-17 backfill); 627 uncovered. First LLM-generated suggestion produced at the same backfill.

**Coverage.** *Full.*

One residual slice: analysis *by feature category* is currently not possible because `hydra_pipelines` has no FK to `canonical_features`. Raised as `link-findings-to-features`.

## 10.3 Continual improvement

*What.* Continually improve the suitability, adequacy and effectiveness of the QMS.

**Our implementation.** The ADR iteration loop. 77 review findings → ADR set grew from an initial sketch to 23 ADRs. Gate set grew to 9. Skills inventory continues to grow. The *continual* part is evidenced in dated memory entries (`feedback_*.md`) tracking where the QMS bent to absorb an incident.

**The loop in one sentence:** incident → `hydra.json` evidence → `hydra_findings` row → fingerprint → cluster → nightly `analyze_pipelines` → coverage check against CLAUDE.md/ADRs → `suggest_improvements` drafts patch → human accept/reject in `/hydra/suggestions/` → `apply_hydra_suggestion` opens PR on Hydra → human merges → Hydra's behaviour improves on next run.

**Discovery is automated; design stays human.** `hydra_learning` automates the discovery half (recurrence counting, cluster fingerprinting, coverage detection) while leaving the design half (patch wording, false-positive tolerance, scope) firmly with humans through the accept/reject/apply queue. That split is deliberate — gate design is judgment; recurrence counting is not.

**Coverage.** *Full.*

Residual: the loop measures itself via the target success metrics (30 %+ drop in average reviewer findings per pipeline; 25 %+ drop in median time-to-done; first-pass success from ~40 % to >60 %; ≥5 merged suggestion PRs after 4 weeks of operation). These are the effectiveness metrics 10.3 asks for. Tracking them formally becomes easier once the quarterly management review (9.3) is running.

---

# Coverage summary

| Clause | Title | Coverage |
|--------|-------|----------|
| 4.1 | Understanding the organization and its context | Partial |
| 4.2 | Needs and expectations of interested parties | Partial |
| 4.3 | Scope of the QMS | Partial |
| 4.4 | QMS and its processes | Full |
| 5.1 | Leadership and commitment | Partial |
| 5.2 | Policy | **None** |
| 5.3 | Roles, responsibilities, authorities | Partial |
| 6.1 | Risks and opportunities | Full (tech) / Partial (business) |
| 6.2 | Quality objectives | Partial |
| 6.3 | Planning of changes | Full |
| 7.1.1 | Resources — general | Full |
| 7.1.2 | People | Full |
| 7.1.3 | Infrastructure | Full |
| 7.1.4 | Environment | Full |
| 7.1.5 | Monitoring/measuring resources | Partial |
| 7.1.6 | Organizational knowledge | Full |
| 7.2 | Competence | Partial (humans) / Full (agents) |
| 7.3 | Awareness | Partial |
| 7.4 | Communication | Full internal / Partial external |
| 7.5.1 | Documented information — general | Partial |
| 7.5.2 | Creating and updating | Full |
| 7.5.3 | Control of documented information | Full |
| 8.1 | Operational planning and control | Full |
| 8.2.1 | Customer communication | Full |
| 8.2.2 | Determining requirements | Full |
| 8.2.3 | Review of requirements | Full |
| 8.2.4 | Changes to requirements | Full |
| 8.3.1 | D&D — general | Full |
| 8.3.2 | D&D planning | Full |
| 8.3.3 | D&D inputs | Full |
| 8.3.4 | D&D controls | Full |
| 8.3.5 | D&D outputs | Full |
| 8.3.6 | D&D changes | Full |
| 8.4.1 | Externally provided — general | Full |
| 8.4.2 | Type and extent of control | Full |
| 8.4.3 | Information for external providers | Partial |
| 8.5.1 | Control of production | Full |
| 8.5.2 | Identification and traceability | Full (forward) / Partial (reverse, breaks at issue ↔ feature_id) |
| 8.5.3 | Property of customers / providers | N/A here (27001) |
| 8.5.4 | Preservation | Full |
| 8.5.5 | Post-delivery activities | Full |
| 8.5.6 | Control of changes | Full |
| 8.6 | Release | Full |
| 8.7 | Non-conforming outputs | Full (per-issue) / Partial (aggregate — `needs-input` dashboard view pending) |
| 9.1.1 | Monitoring — general | Full (per-PR + cross-change via hydra_learning) / Partial (throughput view pending) / None (adoption telemetry) |
| 9.1.2 | Customer satisfaction | Partial |
| 9.1.3 | Analysis and evaluation | Full (automated via `analyze_pipelines`; feature-level pending `link-findings-to-features`) |
| 9.2 | Internal audit | Partial |
| 9.3 | Management review | **None** (inputs now exist; just needs the first meeting) |
| 10.1 | Improvement — general | Full |
| 10.2 | Nonconformity and corrective action | Full (automated via `suggest_improvements` + HITL) |
| 10.3 | Continual improvement | Full (measured via hydra_learning success metrics) |

**Totals.** 51 clauses/subclauses. Clauses fully None: 2 (5.2 Policy, 9.3 Management review — both close with documentation/scheduling, no engineering). N/A-here: 1 (8.5.3 customer property, covered under 27001 scope). The shipping of `hydra_learning` (§ 0c) on 2026-04-17 upgraded 9.1.3, 10.2, and 10.3 from Partial to Full. The remaining Partial ratings are nearly all documentation gaps (5.x policy/roles, 6.x objectives, 4.x context) or narrow items covered by the three raised OpenSpec changes.

## Gap priority shortlist (close these first)

**Documentation-only closures (no engineering work):**

1. **5.2 Policy** (None) — write `.github/docs/iso/quality-policy.md`. Half a page. Unblocks 7.3 Awareness.
2. **6.2 Quality objectives** (Partial) — extract implicit numbers (75 % coverage, strict-check clean, audit-clean) into `.github/docs/iso/objectives.md`.
3. **4.1 / 4.2 / 4.3** (Partial) — one consolidated `context.md` covering context, interested parties, and scope. Drawn from existing material.

**Process closures (scheduling, no code):**

4. **9.3 Management review** (None) — institute a quarterly review with the agenda template from § 9.3. ~2 hours per quarter.
5. **9.2 Internal audit** (Partial) — quarterly 5-PR traceability walk-back, one note per quarter in `.github/docs/iso/audits/`.

**Pipeline gaps — raised as OpenSpec changes** (the learning-bridge automation is shipped per § 0c; these are the narrow residuals):

6. **[`link-findings-to-features`](../../../concurrentie-analyse/openspec/changes/link-findings-to-features/)** — add `canonical_feature_id` FK to `HydraPipeline`; enrichment phase in `ingest_hydra_logs`. Lifts 9.1.3 feature-level analysis and 8.5.2 reverse-traceability (DB side).
7. **[`embed-feature-id-in-issues`](../../../concurrentie-analyse/openspec/changes/embed-feature-id-in-issues/)** — `push_roadmap_issues.py` emits `feature_id` on the issue. Complementary to item 6; closes 8.5.2 reverse-traceability end-to-end.
8. **[`add-spec-pipeline-throughput-view`](../../../concurrentie-analyse/openspec/changes/add-spec-pipeline-throughput-view/)** — new view rendering Board-1 throughput metrics. Closes the cross-change throughput gap in 9.1.1.

**Small residual cleanups** (documentation / tidy):

9. **`/hydra/needs-input/` view** — a grouping over `hydra_pipelines.final_status='needs-input'`. Would close the aggregate slice of 8.7. Not raised as a formal change; small enough to add to one of the three changes above.
10. **`sync_hydra_feedback.py` cleanup** — redundant with `hydra_learning.ingest_hydra_logs`; either remove or document its narrower role.
11. **`Dockerfile.analysis` / `Dockerfile.spec-writer` wiring check** — confirm how they are invoked or remove them.
12. **Memory refresh** — intelligence-DB row counts in the memory index are stale (see § 0a numbers).

**Board-4 (adoption) telemetry** — a separate roadmap decision about whether to build opt-in telemetry from installed NC instances. GDPR and user-trust trade-offs need leadership sign-off before any engineering.

Items 1–5 are pure documentation / scheduling. Items 6–8 are tracked OpenSpec changes on `spec/*` branches in `concurrentie-analyse`, each PR'd to `development`. Items 9–12 are small cleanups. Together, closing 1–8 moves the document from two hard Nones and several Partials to a handful of deliberate Partials (7.1.5, 8.4.3, 9.1.2 — see below).

## Gaps that will stay *Partial* for good reason

- **7.1.5 Monitoring/measuring resources** — we pin tool versions and run a PHPUnit baseline; formal "tool suitability" audits add more ceremony than value.
- **8.4.3 Information for external providers** — our external-provider surface is narrow (Composer, npm, Nextcloud upstream). Formal protocols here would be overkill.
- **9.1.2 Customer satisfaction** — open-source end-users are hard to survey. Issue-trend tracking is a reasonable proxy; a full satisfaction programme is not proportionate.

## References

### ISO 9001:2015 clause sources

The clause titles used in this document were cross-referenced from open summaries at [techqualitypedia.com](https://techqualitypedia.com/clauses-of-iso-9001/) and [Auditor Training Online](https://blog.auditortrainingonline.com/blog/understanding-iso-90012015-clause-8.3-design-and-development). The ISO text itself is copyrighted and not reproduced here — for formal audit work, obtain the standard from [iso.org](https://www.iso.org/standard/62085.html). The software-specific interpretation is **ISO/IEC 90003:2018**.

### In-repo artefacts — Hydra side

- [hydra/openspec/architecture/](../../../hydra/openspec/architecture/) — 23 ADRs (adr-001 … adr-023).
- [.github/.github/workflows/quality.yml](../../.github/workflows/quality.yml) — quality gate workflow.
- [.github/.github/workflows/branch-protection.yml](../../.github/workflows/branch-protection.yml) — branch-transition rules.
- `hydra/scripts/run-hydra-gates.sh` — 9 mechanical gates entry point.
- `hydra/scripts/lib/hydra_record.py` — atomic stage record writer.
- `hydra/scripts/lib/aggregate-hydra-summary.py` — per-change cost/findings roll-up.
- `hydra/scripts/orchestrate.sh` — state-machine (terminal-state guards, `needs-input` escalation).
- `hydra/openspec/changes/{slug}/hydra.json` — per-change journal.
- [.github/docs/ROADMAP.md](../ROADMAP.md) — product roadmap.
- [.github/docs/claude/](../claude/) — developer + agent documentation.

### In-repo artefacts — Specter side

- [concurrentie-analyse/README.md](../../../concurrentie-analyse/README.md) — pipeline overview, live sync status.
- [concurrentie-analyse/intelligence/migrations/0001_initial.py](../../../concurrentie-analyse/intelligence/migrations/0001_initial.py) — 58-table Django ORM schema.
- [concurrentie-analyse/scripts/pipeline.py](../../../concurrentie-analyse/scripts/pipeline.py) — main 13 + 10-phase orchestrator.
- [concurrentie-analyse/scripts/push_spec_pipeline.py](../../../concurrentie-analyse/scripts/push_spec_pipeline.py) — reads DB briefs, runs `/opsx-ff`, writes change artefacts.
- [concurrentie-analyse/scripts/push_roadmap_issues.py](../../../concurrentie-analyse/scripts/push_roadmap_issues.py) — opens GitHub issues with `ready-to-build` / `blocked` / `yolo` labels.
- [concurrentie-analyse/scripts/generate_spec_content.py](../../../concurrentie-analyse/scripts/generate_spec_content.py) — DB-only context-brief assembly.
- [concurrentie-analyse/scripts/update_readme_status.py](../../../concurrentie-analyse/scripts/update_readme_status.py) — populates sync-status dashboard.
- [concurrentie-analyse/.github/workflows/weekly-sync.yml](../../../concurrentie-analyse/.github/workflows/weekly-sync.yml) — Sunday 02:00 UTC intelligence refresh.
- [concurrentie-analyse/.claude/skills/](../../../concurrentie-analyse/.claude/skills/) — 7 `specter-*` skills.
- `concurrentie-analyse/intelligence.db` — SQLite DB (generated from pgdump).
- `concurrentie-analyse/scripts/sync_hydra_feedback.py` — feedback sync (exists, not wired into cron).

### Memory / context files referenced

- [project_hydra-adr-iteration.md](../../../.claude/memory/project_hydra-adr-iteration.md) — ADR evolution from review findings.
- [project_testing-architecture.md](../../../.claude/memory/project_testing-architecture.md) — 75 % spec-to-test coverage threshold, Playwright + Newman parallel.
- [reference_conduction-roadmap.md](../../../.claude/memory/reference_conduction-roadmap.md) — roadmap pointer.

---

*Last reviewed: 2026-04-23. Review trigger: any new ADR, new Hydra gate, change in branch-protection rulesets, or material change to quality.yml.*
