<!--
SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
SPDX-License-Identifier: EUPL-1.2
-->

# Moving off your vendored check-l10n.js

Gate 117 runs `hydra-gates/scripts/check-l10n.js` on every app. You do not have to
do anything for the gate to work. This note is for the second step: deleting the
copy in your own repository, so there is one checker instead of fifteen.

## Why the copies have to go

Twenty-one apps vendored this script. By 2026-09-19 those copies had drifted into
thirteen distinct versions across fifteen repositories. Three apps ship none at
all. Three carry two copies each, at two different paths.

Drift was not the worst of it. Every one of the thirteen computed `missing` the
same way:

```js
const missing = [...usedKeys].filter((k) => !keys.has(k))
```

`usedKeys` came from walking `src/` for `t()` calls. PHP and schema JSON, where
the better copies read them at all, only ever cleared an "unused" warning. So a
`->t('Approve')` with no key in `en.json` could not be reported by any app in the
fleet. On opencatalogi that hid 49 PHP strings and 319 register and schema
strings, with the local check green throughout.

## What the shared checker reads

| Source | Where | Feeds |
|---|---|---|
| `SRC` | `src/**/*.{vue,js,ts}`, `t()` and `n()` | missing and unused |
| `PHP` | `lib/`, `templates/`, `appinfo/`, `->t()` and `->n()` | missing and unused |
| `MANIFEST` | `src/manifest.json` and `src/manifest.d/*.json` | missing and unused |
| `SCHEMA` | `lib/Settings/**/*.json`, register and schema `title` and `description` | missing and unused |

A PHP array value under a rendered field name, such as `'description' => '...'`,
clears an unused warning but never raises a missing one. A `->t()` call is an
unambiguous claim that a string is user facing. An array key is not.

## Migrating your app

1. Run the shared checker against your working tree and read the count:

   ```bash
   node vendor/conduction/hydra-gates/hydra-gates/scripts/check-l10n.js .
   ```

   Findings print one per line, each tagged `SRC`, `PHP`, `MANIFEST` or `SCHEMA`.
   Exit code 1 means findings, 4 means there was nothing to check, 9 means the
   checker could not read something and judged nothing.

2. Compare it against your vendored copy. The `SRC` counts should agree. If they
   do not, say so in your PR: that is drift worth knowing about, not a reason to
   stop.

3. Fix what belongs to your current change. Everything else is inherited debt:
   report it in one sentence in the PR body and leave it to the debt sweep.

4. Park the findings you are not fixing today in `l10n/.l10n-source-ignore.json`,
   a flat map of string to reason:

   ```json
   {
     "Geospatial": "a taxonomy value from the source register, not app copy"
   }
   ```

   A reason is required. An entry with an empty reason is ignored, so the file
   cannot quietly become a suppression list.

5. Delete your own `scripts/check-l10n.js` or `tests/l10n/check-l10n.js`, and
   point the `check:l10n` script in `package.json` at the shared one.

6. Leave `check-l10n-parity.js` alone. It compares `nl.json` to the generated
   `nl.js` and answers a different question.

## Blocking, later

Gate 117 warns. It does not fail a build, because fourteen of twenty-one repos
carry inherited findings and openregister alone carries 1,273. A blocking launch
would redden most of the fleet the minute it merged.

Promotion to blocking is two deliberate edits in `scripts/run-hydra-gates.sh`:
drop `--warn-only` from the invocation, and swap `_warn` for `_fail`. Do it when
the fleet count is low enough that the next red is a regression rather than a
backlog. The l10n debt sweep owns that call.
