# Renaming an app

The fleet is moving onto the `-iq` / `-inq` suffix. The mapping of record —
which app becomes what, and how far each one has got — lives in
[app health](./app-health.md#renaming). This page is the *how*.

A rename happens in three phases, and they are deliberately separable: each
one is safe to ship on its own, and each later phase costs more and risks more
than the one before it.

| Phase | What changes | Risk |
| --- | --- | --- |
| 1. Display names | What people read: web properties, docs, `<name>` in `appinfo/info.xml`, READMEs | None — nothing resolves by these |
| 2. Repository name | The GitHub repo | Low — GitHub redirects old URLs, clones, and open PRs |
| 3. App id | `<id>`, PHP namespace, routes, l10n domain, frontend URLs | **A data migration** |

## Phase 1 and 2 are not the interesting part

Rename the repo with `gh repo rename`; GitHub keeps redirects, so remotes,
open PRs and CI keep working, and Pages keeps its `CNAME`. Then update the
display names — but only the display names. The rule that keeps this safe is:
**anything lowercase is an identifier, not a name.** `/apps/procest`,
`app="procest"`, `procest.conduction.nl`, glyph ids, register slugs and
`data-app` attributes all stay exactly as they are during phase 1.

Two traps worth naming, because both were hit:

- A green deploy job is not a deployed site. Check the live bytes. Both
  `www.conduction.nl` and `identity.conduction.nl` were serving stale content
  while their workflows reported success — one for a missing credential, one
  because a Cloudflare Worker route sat in front of the Pages deploy.
- Fix the brand *rule*, not just its instances. `brand/taalgebruik.md`
  documented "capital Q at the end" as policy, so correcting the 56 spellings
  without correcting the rule would have reintroduced them.

## Phase 3: the app id is a data migration

**There is no in-place app-id upgrade in Nextcloud.** Renaming `<id>` does not
rename anything — it makes the app ask for its data under a name nothing
answers to. The new id is simply a different app.

Everything below is what `planix` → `planninq`
([planninq#336](https://github.com/ConductionNL/planninq/pull/336), following
the earlier `scholiq` → `learniq`) had to handle. Start from that PR.

### What breaks, and what carries it across

| Store | Keyed by | Migration |
| --- | --- | --- |
| `oc_appconfig` | app id | `MigrateAppConfigKeys` |
| `oc_preferences` (per-user) | app id | `MigrateUserPreferences` |
| `oc_activity` | app id + type | none — old rows become invisible |
| OpenRegister register | slug | **do not rename the slug** |

Register both repair steps under **`<install>` as well as
`<post-migration>`**. `<install>` is the path a real deployment takes, because
Nextcloud discovers the new id as a new app. Order them **before**
`InitializeSettings`, which imports the register and would otherwise write
fresh values that a never-overwrite copy then silently discards.

Make every step idempotent, never overwriting a newer value, never deleting
the old rows (so a rollback still finds them), and logging-and-continuing
rather than aborting an install over one unreadable key.

### The one that hides

Per-user preferences are the trap, because the failure is silent. Reads carry
a default:

```php
$this->config->getUserValue($userId, Application::APP_ID, 'notify_due_reminder', 'true');
```

After the rename that lookup misses and returns the default — so a user who
explicitly turned a notification **off** starts receiving it again. Nothing
throws, nothing logs, no test fails. **A default-valued read turns missing
data into wrong behaviour rather than into an error**, which is exactly why it
needs a migration instead of a release note.

`IConfig` has no "list every key for every user", so enumerate by value:
`getUsersForUserValue(OLD_ID, $key, $value)` for each known key's possible
values, and keep that key list in a constant that new preferences get added
to. Anything ordered after it that asks `getUsersForUserValue(APP_ID, …)` —
a reconcile step, say — must run *after* the copy, or it queries the new id
and finds nobody.

### What to leave alone

Do **not** rename the OpenRegister register slug, its `tablePrefix`, or its
folder. OpenRegister's import handler matches registers by slug: rename it and
the import creates a fresh empty register while every existing object stays
behind, orphaned. The slug is an internal identifier no user ever sees. Leave
it on the old value and put a comment next to each literal saying why — future
readers will otherwise "finish the job" and orphan the data.

Same for archived `openspec/changes/` directories and the `@spec` paths that
point at them: they are history, and rewriting them breaks the paths.

## Verifying

`composer check:strict` and the unit suite are necessary but not sufficient —
they cannot see a preference that silently reverted. Write tests for the
migration steps, then **check the tests can fail**: break the step, watch them
go red, restore it. A migration test that passes against a broken migration is
decoration.

Afterwards, grep for the old id and justify every remaining hit in the PR
description. In practice the legitimate survivors are: the register slug, the
`OLD_APP_ID` constants, archived change directories, CHANGELOG history, and
the docs subdomain until DNS moves separately.

## What five apps taught us

The pilot documented the shape. Doing four more found the rest, and every
item below is a defect that shipped green somewhere first.

### The old id may be a substring of a real word

`procest` sits inside the Dutch ZGW vocabulary — `procestermijn`,
`procestype`, `selectielijstProcestype` — and inside Danish `procestrin`. A
blanket replace turns those into `dossiqermijn` across the rules engine, its
validators and the Postman suites. Around five hundred occurrences had to be
preserved by hand. `softwarecatalog` sits inside the VNG product
**Softwarecatalogus**; `nldesign` sits next to the **NL Design System**
standard.

This is the concrete reason scripted edits are banned for code. Before
renaming, grep the old id and ask of each hit what larger word it belongs to.

### Freeze the literal on both sides, not just where it is defined

One app correctly froze the Files folder holding every generated document —
with a comment explaining why, right next to the constant. The frontend was
renamed with the app anyway: forty-one path literals across the store, a
sidebar guard and a widget. The app then listed a folder that did not exist,
every existing document became invisible, and nothing errored. Only an e2e
assertion that a seeded document appears in the listing caught it.

After freezing anything, grep the **new** name across the whole repo and ask
of each hit whether it is really a different identifier. The definition site
will look right precisely because the explanation is sitting next to it.

### Put the reads inside the try, not just the write

Two apps shipped repair steps whose `getValueString()` calls sat outside the
`try` that was meant to contain them. Only the write was guarded, so an
unreadable value propagated out of `run()`.

That is worse than it sounds. These steps are registered under `<install>`,
so a repair step that throws does not merely fail an upgrade — **the app never
enables, and every route goes with it**. Both classes' own docblocks promised
"every failure is logged and the loop continues".

Neither app's test double could express it: the fake's failure switch only
refused *writes*. A fixture that cannot fail the way production fails will
not find this.

### Choose the enumeration strategy from the data

`getUsersForUserValue(app, key, value)` needs the value up front. That is fine
for a boolean opt-out and useless for an open-valued key — an administration
id, a session timeout, a secret type. Used there it migrates **nothing while
reporting success**. Walk `IUserManager::callForSeenUsers()` and ask
`getUserKeys()` instead, and pin the choice with a test asserting the
value-enumerating call is never made.

The pilot's implementation did not transfer to a single later app.

### The rename can hollow out a checker

One app's l10n validator hardcoded the old id in a regex that harvested
`t('<app>', …)` keys out of `src/`. After the rename it went on searching for
the old name, matched nothing, and reported its check as passing over an empty
set — a check that validates nothing looks exactly like one that passes. It
now derives the id from `appinfo/info.xml`. Grep your own tooling for the old
id, not just your source.

### Expect these in CI

- **gate-16** is diff-scoped, so a rename pulls every touched method into
  scope and you inherit that file's annotation debt. Annotate against the
  promoted `openspec/specs/…` path and verify the anchor resolves.
- **The coverage guard** will notice two new repair classes with thin tests,
  and it is right to. Write the tests, then break the class and confirm they
  go red — one app had a reserved-key test whose fixture returned the same
  value for both namespaces, so the never-overwrite guard suppressed the write
  and it passed with the reserved list emptied.
- **Generated files** drift: `docs/features.json`, component docs, manifest
  fixtures. Regenerate with the project's own generator; hand-editing them
  cannot satisfy a checker that regenerates and diffs.
- **Stale eslint suppressions** fail the job at zero errors. `--prune-suppressions`.
- **A seed script keyed on a frozen id** — `registers['<newid>']` — is a
  KeyError that aborts the entire e2e job before a single test runs.

### The docs subdomain moves with DNS, not with the code

`<old>.conduction.nl` is a live DNS record and a GitHub Pages CNAME. Renaming
it in the code just points readers at a host that does not exist: during the
dossiq rename, 43 `documentationUrl` entries were switched to
`dossiq.conduction.nl`, which answers HTTP 000 while `procest.conduction.nl`
still answers 200.

Freeze the subdomain — in the manifest, in `docs/static/CNAME`, and in the
documentation workflow's `cname:` — and move all three together in the DNS
pass. The quickest check is the honest one: `curl` both hostnames.

### Telling a register slug from an app id in a bare literal

A positional `'<oldid>'` argument is indistinguishable from an app id by grep.
It is the OpenRegister **register slug** — and stays — when it is:

- the first string argument to `ObjectService`/OR mapper calls (`getObject`,
  `find`, `findAll`, `saveObject`, `getObjects`)
- the segment after `objects/` in `/apps/openregister/api/objects/<slug>/<schema>`
- inside `registers: ['<slug>']` at boot, an `or-collection-<slug>-*` channel,
  or an `objectType: '<slug>-*'`
- the `components.registers.<slug>` key, or its `slug` / `tablePrefix` / `folder`

It is the **app id** — and moves — when it names this app to Nextcloud: a
route name, `/apps/<id>/`, an l10n domain, `Application::APP_ID`.

Rule of thumb: handed to OpenRegister or read back out of stored data, it
stays. When unsure, leave it and list it — a wrongly-renamed slug orphans
stored objects silently, while a wrongly-kept one is a visible cosmetic miss.
