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
