# Retrofit Playbook — bringing legacy apps under ADR-003

This playbook walks through retrofitting an app that predates the spec ↔ code annotation convention defined in [ADR-003 §Spec traceability](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-003-backend.md).

The convention: every class and every public method that implements a task carries a `@spec openspec/changes/{change-name}/tasks.md#task-N` PHPDoc/JSDoc tag pointing at the task it implements. The file's leading docblock carries one `@spec` tag per distinct task the file participates in (so a file touched by three tasks has three `@spec` tags in its header). Apps built spec-first via `/opsx-apply` get this for free. Apps that already exist need a one-time retrofit pass.

## When to retrofit

- App was built before the convention existed
- App has `openspec/specs/**/spec.md` but no `@spec` annotations in code
- `/opsx-verify` falls back to keyword-based REQ matching for this app

If the app has full annotations already, skip this — `/opsx-verify` handles it.

## The three skills, in order

| Skill | What it does | Writes |
|---|---|---|
| [`/opsx-coverage-scan {app}`](https://github.com/ConductionNL/hydra/blob/main/.claude/skills/opsx-coverage-scan/SKILL.md) | Audit only — produces a report bucketing every code unit | `{app}/openspec/coverage-report.md` + `.json` |
| [`/opsx-annotate {app}`](https://github.com/ConductionNL/hydra/blob/main/.claude/skills/opsx-annotate/SKILL.md) | Applies file + method `@spec` tags for Bucket 1 via a ghost change | Annotation-only PR |
| [`/opsx-reverse-spec {app} --cluster X` or `--extend Y`](https://github.com/ConductionNL/hydra/blob/main/.claude/skills/opsx-reverse-spec/SKILL.md) | Drafts a retrofit spec for one Bucket 2a/2b cluster, annotates its methods inline, registers with Specter, and archives the change | Spec PR |

Run them in this exact order. Don't skip the audit step.

## How ghost changes work

Legacy code doesn't have a real change to point at — the `@spec openspec/changes/{change}/tasks.md#task-N` convention assumes a change exists. Retrofit skills solve this by creating a **ghost change** per run: a scaffold that gets archived immediately so annotations have something to reference.

- `/opsx-annotate` creates `retrofit-annotate-{app}-{YYYY-MM-DD}` — one task per REQ with Bucket 1 matches, **empty spec delta** (all REQs already exist in `openspec/specs/`). All tasks arrive `[x]` because the code is pre-existing.
- `/opsx-reverse-spec` creates `retrofit-{capability-or-cluster}-{YYYY-MM-DD}` — a spec delta (new REQs appended to an existing capability for `--extend`, or a whole new capability for `--cluster`) plus one task per new REQ. Annotations on the cluster's methods point at those tasks.

Both are archived immediately after creation, so they land in `openspec/changes/archive/`. The `@spec` tag paths remain valid because they are textual references, not live lookups.

## Prerequisites

- App has `openspec/specs/**/spec.md` files (at least one capability defined). If not, run `/app-explore` and `/app-design` first.
- App working tree is clean. `/opsx-annotate` and `/opsx-reverse-spec` refuse dirty trees.
- You are on the branch that carries the specs — usually `development`, but some apps keep specs on `beta` (e.g. decidesk). The skills create their own `retrofit/…` feature branch off that one.
- Specter DB migration is applied: `python3 concurrentie-analyse/scripts/migrate_app_specs_retrofit.py` (idempotent — safe to re-run).

## Step-by-step

### 1. Scan

```
/opsx-coverage-scan opencatalogi
```

Produces `openspec/coverage-report.md` and a machine-readable `coverage-report.json` sidecar. The report categorises every code unit into one of six actionable buckets:

- **1** — Files where method maps cleanly to an existing REQ-ID. **High confidence** matches only.
- **2a** — Files belonging to an existing capability but performing behavior NO existing REQ describes. Need to extend the spec.
- **2b** — Files with no existing capability owner. Need a brand-new spec.
- **3a** — REQ-IDs whose code clearly used to exist but is now broken (route registered, handler removed). Fix the code.
- **3b** — REQ-IDs whose implementation never existed. Mark `status: deferred` or remove the REQ.
- **4** — ADR conformance issues spotted while scanning (missing EUPL header, hardcoded strings, etc.). Surface only — don't block.

Plus two meta-buckets the report lists but that need no retrofit action: `annotated` (methods already carrying `@spec` tags) and `plumbing` (framework glue — empty constructors, listener dispatch, thin controllers — which never carries `@spec`).

**Read the report manually before proceeding.** The scan is heuristic — false positives in Bucket 1 produce wrong annotations downstream.

### 2. Annotate Bucket 1

```
/opsx-annotate opencatalogi
```

This creates the `retrofit-annotate-{app}-{YYYY-MM-DD}` ghost change, applies file-header and per-method `@spec openspec/changes/retrofit-annotate-.../tasks.md#task-N` tags for everything in Bucket 1, opens an annotation-only PR, and updates `.git-blame-ignore-revs` so blame still surfaces real authors. The skill is idempotent — re-running on already-annotated code produces no code diff (it will detect an existing dated ghost change and ask whether to reuse or create a fresh one).

If a linter rejects the annotation block (PHPCS rule requires specific tag order), the skill stops. Fix the linter config rather than reordering — the convention from ADR-003 is fixed.

### 3. Reverse-spec Bucket 2 entries, one at a time

For each Bucket 2a entry (extend existing capability):

```
/opsx-reverse-spec opencatalogi --extend admin-settings
```

For each Bucket 2b entry (new capability):

```
/opsx-reverse-spec opencatalogi --cluster app-lifecycle
```

The skill reads the cluster from `coverage-report.json`, drafts REQs that describe **observed behavior** (not aspirational intent), writes a spec delta in a ghost change (`retrofit_extensions: [...]` for `--extend`, `retrofit: true` for `--cluster`), invokes `/opsx-ff` to fill in the design.md, annotates the cluster's methods inline with `@spec` tags pointing at the ghost change's tasks, runs `python3 concurrentie-analyse/scripts/sync_spec_content.py {app}` to register with Specter's `app_specs` table, and archives the change so the delta merges into the main spec.

**One cluster per run** — never batch, and cap at 5 REQs per run. Each cluster is its own review cycle because REQ language is the review surface.

**Bias toward `--extend`** — extending a capability is cheaper than minting a new one. Only use `--cluster` when the cluster is genuinely new behavior territory.

### 4. Address Bucket 3

- **3a** — Open separate PRs to fix or remove the broken code. Don't bundle with annotation PRs.
- **3b** — Open a PR that either marks the REQs `status: deferred` in spec.md, or removes them. Document the decision in the PR.

### 5. Address Bucket 4

ADR conformance issues are noise during retrofit but worth tracking. Open a follow-up issue per app: "ADR cleanup pass — see `openspec/coverage-report.md` Bucket 4". Address in a separate cycle.

## What goes back to Specter

- `sync_spec_content.py` runs synchronously during `/opsx-reverse-spec`, so retrofit specs are visible in Specter dashboards within seconds. If the script fails (typically missing DB column), the skill stops and surfaces the error — don't leave a spec in-tree but missing from Specter.
- Retrofit cohorts are tracked in dedicated columns: `app_specs.retrofit` (set for `--cluster` runs that create a whole new capability) and `app_specs.retrofit_extensions` (list of REQ-IDs added by `--extend` runs). The skill writes these via spec frontmatter; `sync_spec_content.py` picks them up after archive.
- Retrofit specs are necessarily lossy — they capture observed behavior, not original design intent. They warrant periodic re-review against current ADRs as the app evolves.

## Common gotchas (from the opencatalogi pilot)

- **Helper methods are easy to miss.** Private helpers that implement a discrete REQ scenario step (e.g. `isObjectPublished()`) get the SAME REQ-ID as their primary caller, not their own. The scan flags these now; older runs may not have.
- **Listener methods are not always plumbing.** `EventListener::handle()` is plumbing IF it only dispatches to a service. It's business logic IF it transforms data, filters events, or makes decisions. Read the body — listeners are small.
- **Bucket 1 vs 2a for single-method gaps.** When in doubt, default to Bucket 1 with a NOTE recommending the spec be tightened later. Don't churn Specter with one-off REQ proposals.
- **ElasticSearch-style "never implemented" REQs.** Bucket 3b. Don't try to reverse-spec them — the gap is a feature decision, not a documentation one.
- **Nextcloud `appinfo/`** typically contains only auto-generated `routes.php` + `info.xml`. Empty of code units is normal — not an error.
- **`.git-blame-ignore-revs`** must be configured on each cloning developer's machine: `git config blame.ignoreRevsFile .git-blame-ignore-revs`. The `/opsx-annotate` skill suggests this once but won't run it without confirmation.

## When the retrofit is done

- `/opsx-verify {app}` succeeds without falling back to keyword search
- `app_specs.retrofit` and `app_specs.retrofit_extensions` columns populated for the app's retrofit cohort
- Annotation-only PR + per-cluster reverse-spec PRs all merged
- Bucket 3 issues triaged
- Bucket 4 follow-up issue opened

## Roll-out order

Recommended sequence:

1. **opencatalogi** (pilot — done)
2. **openregister** (foundation — high stakes, second after opencatalogi proves out)
3. docudesk
4. openconnector
5. nldesign
6. mydash
7. softwarecatalog
8. larpingapp
9. zaakafhandelapp
10. procest
11. pipelinq

ExApp Python wrappers (openklant, openzaak, opentalk, valtimo, n8n-nextcloud) need a parallel Python-flavored variant of these skills (module + function docstrings instead of PHPDoc). Defer until PHP roll-out is complete.
