# Retrofit Playbook — bringing legacy apps under ADR-008

This playbook walks through retrofitting an app that predates the spec ↔ code annotation convention defined in [hydra/openspec/architecture/adr-008-testing.md](../../../hydra/openspec/architecture/adr-008-testing.md).

The convention: every method that materially implements a REQ carries a `@spec {capability}#{REQ-ID}` PHPDoc/JSDoc tag, and every file's leading block carries `@implements` listing the union of those tags. Apps built spec-first via `/opsx-apply` get this for free. Apps that already exist need a one-time retrofit pass.

## When to retrofit

- App was built before the convention existed
- App has `openspec/specs/**/spec.md` but no `@spec` annotations in code
- `/opsx-verify` falls back to keyword-based REQ matching for this app

If the app has full annotations already, skip this — `/opsx-verify` handles it.

## The three skills, in order

| Skill | What it does | Writes |
|---|---|---|
| [`/opsx-coverage-scan {app}`](../../../hydra/.claude/skills/opsx-coverage-scan/SKILL.md) | Audit only — produces a report bucketing every code unit | `{app}/openspec/coverage-report.md` |
| [`/opsx-annotate {app}`](../../../hydra/.claude/skills/opsx-annotate/SKILL.md) | Applies file `@implements` + method `@spec` tags from Bucket 1 | Annotation-only PR |
| [`/opsx-reverse-spec {app} --cluster X` or `--extend Y`](../../../hydra/.claude/skills/opsx-reverse-spec/SKILL.md) | Drafts retrofit spec for one Bucket 2a or 2b entry, registers with Specter, re-scans, annotates | Spec PR |

Run them in this exact order. Don't skip the audit step.

## Prerequisites

- App has `openspec/specs/**/spec.md` files (at least one capability defined). If not, run `/app-explore` and `/app-design` first.
- App working tree is clean. `/opsx-annotate` refuses dirty trees.
- You are on a feature branch off `development` (per project branching policy).
- Specter DB migration is applied: `python3 concurrentie-analyse/scripts/migrate_app_specs_retrofit.py`. The Sunday cron also runs this idempotently.

## Step-by-step

### 1. Scan

```
/opsx-coverage-scan opencatalogi
```

Produces `openspec/coverage-report.md` with six buckets:

- **1** — Files where method maps cleanly to an existing REQ-ID. **High confidence** matches only.
- **2a** — Files belonging to an existing capability but performing behavior NO existing REQ describes. Need to extend the spec.
- **2b** — Files with no existing capability owner. Need a brand-new spec.
- **3a** — REQ-IDs whose code clearly used to exist but is now broken (route registered, handler removed). Fix the code.
- **3b** — REQ-IDs whose implementation never existed. Mark `status: deferred` or remove the REQ.
- **4** — ADR conformance issues spotted while scanning (missing EUPL header, hardcoded strings, etc.). Surface only — don't block.

**Read the report manually before proceeding.** The scan is heuristic — false positives in Bucket 1 produce wrong annotations downstream.

### 2. Annotate Bucket 1

```
/opsx-annotate opencatalogi
```

This applies the file-header `@implements` block and per-method `@spec` tags for everything in Bucket 1, opens an annotation-only PR, and updates `.git-blame-ignore-revs` so blame still surfaces real authors. The skill is idempotent — re-running on already-annotated code produces no diff.

If a linter rejects the annotation block (PHPCS rule requires specific tag order), the skill stops. Fix the linter config rather than reordering — the convention from ADR-008 is fixed.

### 3. Reverse-spec Bucket 2 entries, one at a time

For each Bucket 2a entry (extend existing capability):

```
/opsx-reverse-spec opencatalogi --extend admin-settings
```

For each Bucket 2b entry (new capability):

```
/opsx-reverse-spec opencatalogi --cluster app-lifecycle
```

The skill drafts the spec (or extension), invokes `/opsx-ff` for proposal/design/tasks, calls `python3 concurrentie-analyse/scripts/register_spec.py` to push the new spec/REQs into Specter's `app_specs` table, then re-runs scan + annotate so the freshly written REQ-IDs get tagged in the same pass.

**Bias toward `--extend`** — extending a capability is cheaper than minting a new one. Only use `--cluster` when the cluster is genuinely new behavior territory.

### 4. Address Bucket 3

- **3a** — Open separate PRs to fix or remove the broken code. Don't bundle with annotation PRs.
- **3b** — Open a PR that either marks the REQs `status: deferred` in spec.md, or removes them. Document the decision in the PR.

### 5. Address Bucket 4

ADR conformance issues are noise during retrofit but worth tracking. Open a follow-up issue per app: "ADR cleanup pass — see `openspec/coverage-report.md` Bucket 4". Address in a separate cycle.

## What goes back to Specter

- `register_spec.py` runs synchronously during `/opsx-reverse-spec`, so retrofit specs are visible in Specter dashboards within seconds.
- Sunday's `spec_crawler.py` is the safety net — picks up any specs created outside the retrofit flow (hand-edited, missed, etc.).
- Retrofit specs are filterable in dashboards via `/tender-status --retrofit-only` and `/readiness-report --retrofit-only`. They're necessarily lossy (capture observed behavior, not original intent) and warrant periodic re-review against current ADRs.

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
