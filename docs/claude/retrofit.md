# Retrofit Playbook — bringing legacy apps under ADR-003's `@spec` convention

This playbook walks through retrofitting an app that predates the spec ↔ code annotation convention defined in [hydra/openspec/architecture/adr-003-backend.md](../../../hydra/openspec/architecture/adr-003-backend.md).

**The convention** (also enforced by [hydra-gate-spdx](../../../hydra/.claude/skills/hydra-gate-spdx/SKILL.md)): every PHP file's main docblock and every public method's docblock carries one or more `@spec openspec/changes/{change-name}/tasks.md#task-N` tags pointing at the task(s) it implements. Apps built spec-first via `/opsx-apply` get this for free — the builder writes the tag as part of implementation. Apps that already exist need a one-time retrofit pass.

## Ghost changes

Legacy code was never written against a change, so there's no `tasks.md#task-N` for `@spec` to point at. Retrofit bridges this with **ghost changes**:

- **`/opsx-annotate`** creates one ghost change per run: `retrofit-{YYYY-MM-DD}-annotate-{app}` with an empty spec delta and one task per Bucket 1 REQ.
- **`/opsx-reverse-spec`** creates one ghost change per cluster: `retrofit-{YYYY-MM-DD}-{capability-or-cluster}` with a spec delta (new REQs) + one task per new REQ.

Naming convention: `retrofit-{YYYY-MM-DD}-{descriptor}` (date right after `retrofit-`). This matches the date-prefix convention used by non-retrofit OpenSpec changes (e.g. `2026-03-25-contacts-actions/`) so retrofit and non-retrofit changes sort chronologically together when the archive is listed alphabetically.

Both changes are archived at the end of the run; annotations reference the ghost change's tasks.md by path. Because `@spec` is a textual reference rather than a live lookup, the path remains valid after archive. Retrofit cohort membership is flagged in spec.md frontmatter (`retrofit: true` or `retrofit_extensions: [REQ-NNN, ...]`) and synced to Specter via `sync_spec_content.py`.

## When to retrofit

- App was built before the convention existed
- App has `openspec/specs/**/spec.md` but no `@spec` annotations in code (or only partial)
- `/opsx-verify` falls back to keyword-based REQ matching for this app

If the app has full annotations already, skip this — `/opsx-verify` handles it.

## The three skills, in order

| Skill | What it does | Writes |
|---|---|---|
| [`/opsx-coverage-scan {app}`](../../../hydra/.claude/skills/opsx-coverage-scan/SKILL.md) | Audit only — produces a report bucketing every code unit | `{app}/openspec/coverage-report.md` + `.json` sidecar |
| [`/opsx-annotate {app}`](../../../hydra/.claude/skills/opsx-annotate/SKILL.md) | Creates ghost change + applies `@spec` tags from Bucket 1 | Annotation-only PR |
| [`/opsx-reverse-spec {app} --cluster X` or `--extend Y`](../../../hydra/.claude/skills/opsx-reverse-spec/SKILL.md) | Drafts REQs for one Bucket 2 entry via ghost change (spec delta + tasks + annotations), syncs to Specter | Spec PR |

Run them in this exact order. Don't skip the audit step.

## Prerequisites

- App has `openspec/specs/**/spec.md` files (at least one capability defined). If not, run `/app-explore` and `/app-design` first.
- App working tree is clean. `/opsx-annotate` and `/opsx-reverse-spec` refuse dirty trees.
- You are on a branch that contains the specs. Some apps keep specs on `beta` rather than `development` (e.g. decidesk) — check before scanning. The skills create their own `retrofit/…` feature branch off that one.
- Specter DB migration applied: `python3 concurrentie-analyse/scripts/migrate_app_specs_retrofit.py`. Adds `retrofit` + `retrofit_extensions` + `spec_hash` columns to `app_specs`. Idempotent.
- Optional: `{app}/.opsx-ignore` — one glob per line (`#` for comments) for paths the scan should skip. Useful for vendor code, deliberately-unspec'd internal tools, demo/example files, generated code. Honored by `/opsx-coverage-scan` (which filters buckets 1/2a/2b/4 — Bucket 3 is REQ-level and unaffected). `/opsx-annotate` and `/opsx-reverse-spec` honor it transitively via the report — if entries change, re-scan before annotating. See `openregister/.opsx-ignore` for a worked example.

## Step-by-step

### 1. Scan

```
/opsx-coverage-scan procest
```

Produces `openspec/coverage-report.md` (human) + `openspec/coverage-report.json` (parseable) with six buckets:

- **1** — Method maps cleanly to an existing REQ-ID. High confidence (≥ 0.85) or flagged `NEEDS-REVIEW` (0.70–0.85).
- **2a** — File belongs to an existing capability but observed behavior is not covered by any REQ. Needs to extend the spec.
- **2b** — File has no capability owner. Needs a brand-new spec.
- **3a** — REQs with no code, but git history has matching keywords in removed lines (probably broken). Triage manually.
- **3b** — REQs with no code and no historical trace. Never implemented — mark `status: deferred` or remove.
- **4** — ADR conformance findings (missing license header, hardcoded strings, etc.). Surface only — non-blocking.

Plus two meta-buckets the report lists but that need no retrofit action: `annotated` (methods already carrying `@spec` tags) and `plumbing` (framework glue — empty constructors, listener dispatch, thin controllers — which never carry `@spec`).

**Read the report manually before proceeding.** The scan is heuristic — false positives in Bucket 1 produce wrong annotations downstream.

### 2. Annotate Bucket 1

```
/opsx-annotate procest
```

Creates the ghost change `retrofit-{date}-annotate-procest`, generates one task per REQ, adds `@spec openspec/changes/retrofit-{date}-annotate-procest/tasks.md#task-N` tags to every Bucket 1 file + method, archives the ghost change, updates `.git-blame-ignore-revs`, opens an annotation-only PR.

Idempotent: re-running with no code changes produces no new annotations. If a dated ghost change already exists, the skill asks whether to reuse it or create a fresh one. Re-running after code changes creates a new dated ghost change.

If the PHPCS ruleset rejects the tag order or placement, the skill stops. **Fix the PHPCS config, never reorder tags** — the ADR-003 + hydra-gate-spdx format is fixed.

### 3. Reverse-spec Bucket 2 entries, one at a time

For each Bucket 2a entry (extend existing capability):

```
/opsx-reverse-spec procest --extend admin-settings
```

For each Bucket 2b entry (new capability):

```
/opsx-reverse-spec procest --cluster app-lifecycle
```

The skill reads the cluster's code, drafts REQs describing observed behavior (capped at 5 REQs per run — split larger clusters), creates a ghost change with the spec delta + tasks, invokes `/opsx-ff` to fill in `design.md`, annotates the cluster's methods, runs `python3 concurrentie-analyse/scripts/sync_spec_content.py {app}` to register with Specter's `app_specs` table, archives the change, opens one PR.

**Bias toward `--extend`** — extending a capability is cheaper than minting a new one. Only use `--cluster` when the cluster is genuinely new behavior territory.

### 4. Address Bucket 3

- **3a** — Open separate PRs to fix or remove broken code. Don't bundle with annotation PRs.
- **3b** — Open a PR that marks REQs `status: deferred` in spec.md or removes them. Document the decision in the PR.

### 5. Address Bucket 4

ADR conformance issues are noise during retrofit but worth tracking. Open a follow-up issue per app: "ADR cleanup pass — see `openspec/coverage-report.md` Bucket 4". Address in a separate cycle.

## What goes back to Specter

- `sync_spec_content.py {app}` runs synchronously during `/opsx-reverse-spec` and reads `retrofit: true` / `retrofit_extensions: [...]` from spec.md frontmatter (applied post-archive when the delta merges). Retrofit specs are visible in Specter dashboards within seconds. If the script fails (typically a missing DB column), the skill stops and surfaces the error — don't leave a spec in-tree but missing from Specter.
- Retrofit cohorts are tracked in dedicated columns: `app_specs.retrofit` (set for `--cluster` runs that create a whole new capability) and `app_specs.retrofit_extensions` (list of REQ-IDs added by `--extend` runs). The skill writes these via spec frontmatter; `sync_spec_content.py` picks them up after archive.
- The existing Sunday sync picks up any specs created outside the retrofit flow as the safety net.
- Prereq for the retrofit columns: `python3 concurrentie-analyse/scripts/migrate_app_specs_retrofit.py` (idempotent).
- Retrofit specs are filterable via `/tender-status --retrofit-only` and `/readiness-report --retrofit-only`. They're necessarily lossy (capture observed behavior, not original intent) and warrant periodic re-review.

## Documentation-only retrofits

Not every retrofit ghost change adds new REQs. Three sub-patterns produce a ghost change without any spec delta — they are deliberate, supported, and **do not require cohort frontmatter** on the affected capabilities (the cohort flag is for tracking REQ provenance, not annotation provenance):

| Pattern | When | Example |
|---|---|---|
| **Cross-capability annotation patch** | Bucket 2 cluster's methods turn out to map to *existing* REQs in *other* capabilities. The ghost change is one task per cross-cap reference; annotations point at those existing tasks. | `retrofit-{date}-b2b-crossrefs` — 33 tasks pointing across 15 sibling capabilities. |
| **Private-helper inheritance** | Scanner couldn't follow the call chain into private helpers. Ghost change documents which existing parent task each helper belongs to. No new REQs. | `retrofit-{date}-schema-hooks` — 7 private helpers inherit parent annotate tasks 65/67/68/69. |
| **Scanner misclassification cleanup** | Scanner placed methods under the wrong capability. Ghost change re-routes them to their actual home capabilities (whose REQs already cover the behavior). | `retrofit-{date}-tenant-isolation-audit` — 3 methods actually belong to `tenant-lifecycle` and `tenant-quotas`. |

The proposal must explicitly say "no new REQs" / "no new REQs needed" / "no new REQs drafted" / "behaviors are fully covered" so `/opsx-verify --app` can detect the pattern. These ghost changes have no `specs/` folder.

## How Bucket 2 handles un-spec'd methods

Bucket 2 is the whole reason retrofit is a three-step flow rather than one. `/opsx-annotate` deliberately does **not** touch methods without a REQ match — it would have nothing to point at. `/opsx-reverse-spec` handles those, one cluster at a time:

| Situation | Which flag | What happens |
|---|---|---|
| Method belongs to an existing capability, no REQ covers it | `--extend <capability>` | Drafts new REQs appended to the capability spec, creates ghost change with delta + task per REQ, annotates the methods |
| Method has no capability owner at all | `--cluster <name>` | Drafts whole new spec, creates ghost change with new spec + tasks, annotates the methods |
| Method is plumbing (listener dispatch, framework `__call`) | — | Never annotated. Scanner flags as `plumbing`. |
| Method is a private helper of an annotated method | — | Inherits caller's REQ(s). Annotated in the same pass as its caller. |
| Method should deliberately never be specified (debug tooling, internal optimization) | — | Add to `{app}/.opsx-ignore` — scanner suppresses in future runs. |

After Bucket 2 is drained, Bucket 1 is empty on the next scan, and all code units are either annotated, plumbing, or explicitly ignored. That's the success state.

## Common gotchas

- **Helper methods are easy to miss.** Private helpers that implement a discrete REQ scenario step get the SAME REQ-ID as their primary caller, not their own. The scan resolves these in Pass B after Pass A buckets primary methods.
- **Listener methods are not always plumbing.** `EventListener::handle()` is plumbing IF it only dispatches to a service. It's business logic IF it transforms data, filters events, or makes decisions. Read the body.
- **Bucket 1 vs 2a for single-method gaps.** When in doubt, default to Bucket 1 with a `NEEDS-REVIEW` flag — manual triage is cheaper than churning Specter with one-off REQ proposals.
- **ElasticSearch-style "never implemented" REQs.** Bucket 3b. Don't reverse-spec them — the gap is a feature decision, not a documentation one.
- **Nextcloud `appinfo/`** typically contains only `routes.php` + `info.xml`. Empty of code units is normal.
- **`.git-blame-ignore-revs`** must be enabled on each cloning developer's machine once: `git config blame.ignoreRevsFile .git-blame-ignore-revs`. `/opsx-annotate` suggests this but won't run it without confirmation.

## When the retrofit is done

Run `/opsx-verify --app {app}` and confirm a green report. App Mode is the canonical retrofit DoD audit — it walks every retrofit ghost change under `{app}/openspec/changes/archive/retrofit-*`, scans for dangling `@spec` paths, audits cohort frontmatter, validates naming convention, and prints a single pass/fail report. Do **not** use plain `/opsx-verify {change-name}` for this — that mode verifies a single (active) change against `openspec status`, which doesn't see archived retrofits.

A retrofit is done when App Mode shows ✅ on every row of:

- Retrofit ghost changes — all archived
- Tasks completion — every retrofit's tasks all `[x]`
- Dangling `@spec` paths — 0
- Symlinks under `{app}/openspec/changes/` — 0
- Naming convention — every retrofit folder matches `retrofit-{YYYY-MM-DD}-{descriptor}`
- Cohort frontmatter — every retrofitted capability carries `retrofit:` or `retrofit_extensions:` on its master spec, in block-YAML form with bare REQ-IDs
- Frontmatter format — block YAML, no inline lists, no full-text values

Plus the workflow items that App Mode doesn't check:

- Annotation-only PR + per-cluster reverse-spec PRs all merged
- Bucket 3 issues triaged (deferred / fixed / re-classified)
- Bucket 4 follow-up issue opened
- After all the above: re-run `python3 concurrentie-analyse/scripts/sync_spec_content.py {app}` so Specter's `app_specs.retrofit` / `app_specs.retrofit_extensions` columns are populated for every retrofitted capability

## Roll-out order

Recommended sequence:

1. **procest** (current testbed — 40+ specs, clean)
2. **pipelinq** (second testbed — similar shape to procest, validates generality)
3. opencatalogi
4. openregister (foundation — high stakes; do after testbeds prove out)
5. docudesk
6. openconnector
7. nldesign
8. mydash
9. softwarecatalog
10. larpingapp
11. zaakafhandelapp
12. decidesk (specs on `beta` rather than `development` — resolve branch alignment first)

ExApp Python wrappers (openklant, openzaak, opentalk, valtimo, n8n-nextcloud) need a parallel Python-flavored variant of these skills (module + function docstrings instead of PHPDoc). Defer until PHP roll-out is complete.
