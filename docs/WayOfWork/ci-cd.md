---
id: ci-cd
title: CI/CD and Code Standards
sidebar_label: CI/CD and Code Standards
sidebar_position: 4
description: What our pipeline actually runs, where the configuration lives, and exactly where we diverge from Nextcloud's own app CI/CD
---

# CI/CD and Code Standards

We build Nextcloud apps, and Nextcloud has its own app CI/CD conventions. Ours is
not the same. Most of the differences are deliberate; a few are accidents worth
knowing about before they bite you. This page states both, so that a contributor
arriving from the Nextcloud ecosystem — or an auditor asking why our checks look
unfamiliar — can see the whole picture in one place.

Two companion pages stay authoritative for what they cover:
[Development Pipeline](development-pipeline.md) for the branch flow and
[Release Process](release-process.md) for versioning.

## One pipeline, eighteen thin callers

Every core app's `.github/workflows/code-quality.yml` is a caller. The pipeline
itself is one reusable workflow:

```yaml
jobs:
  quality:
    uses: ConductionNL/.github/.github/workflows/quality.yml@main
    with:
      app-name: myapp
      # …feature flags…
```

Consumed at `@main`, deliberately. A pinned ref is a silent expiry date: 22 repos
once sat on gate package `v1.0.1` while 16 gates were dead fleet-wide and every
one of them reported PASS.

`quality.yml` emits up to **18 job groups**, not the four the older docs describe:

| Group | Jobs |
| --- | --- |
| PHP Quality | `lint`, `phpcs`, `phpmd`, `psalm`, `phpstan`, `phpmetrics` (matrix) |
| Vue Quality | `eslint`, `stylelint` (matrix) |
| Frontend | `Frontend Build`, `Frontend Tests (unit)`, `Frontend Check (…)` per declared npm script |
| Tests | `PHPUnit` (PHP × Nextcloud matrix), `Integration Tests (Newman)`, `E2E Tests (Playwright)` |
| Accessibility | `axe-core` (opt-in) |
| Supply chain | `Security (composer)`, `Security (npm)`, `License (composer)`, `License (npm)`, `SBOM` |
| Governance | `Hydra Gates`, `Coverage Baseline Protection`, `Features Extract`, `Journeydoc Capture` |
| Rollup | `Quality Report` |

### Nextcloud's equivalent

Nextcloud ships **workflow templates**, not a reusable workflow: an app copies
`lint-php-cs.yml`, `psalm.yml`, `lint-eslint.yml`, `node-test.yml`,
`phpunit-*.yml`, `appstore-build-publish.yml` and so on from `nextcloud/.github`
into its own repo, and a `sync-workflow-templates` job keeps them refreshed.

| | Conduction | Nextcloud |
| --- | --- | --- |
| Shape | one reusable workflow, thin callers | ~40 copied templates per app |
| Update path | change `@main`, all 18 apps follow | sync job re-copies templates |
| Action pinning | tags (`actions/checkout@v4`) | commit SHAs |
| Trigger | `push` + `pull_request` | `pull_request`, with `dorny/paths-filter` change detection and a `summary` job so branch protection still matches when skipped |

Neither shape is wrong. Ours propagates a fix instantly and gives a single rollup;
theirs survives the org repo being unavailable and pins its supply chain harder.
**Action SHA-pinning is the one we should adopt** — it is a supply-chain control,
not a style preference.

## PHP: where we diverge, and how much

### Formatting — the important one

Nextcloud formats PHP with **php-cs-fixer** via `nextcloud/coding-standard`, whose
`Config` calls `setIndent("\t")`. Nextcloud core's `.editorconfig` says
`indent_style = tab`, `indent_size = 4`.

We format PHP with **PHP_CodeSniffer** against a PEAR-derived ruleset that sets
`indent=4, tabIndent=false`. All 18 apps agree on this.

| Rule | Conduction (PHPCS) | Nextcloud (php-cs-fixer) |
| --- | --- | --- |
| Indentation | **4 spaces** | **tabs** |
| Class / function opening brace | next line (PEAR) | same line (`curly_braces_position`) |
| Cast spacing | `(int) $x` (`Generic.Formatting.SpaceAfterCast`) | `(int)$x` (`cast_spaces: none`) |
| Concatenation | `'a'.'b'` (`Squiz.Strings.ConcatenationSpacing`) | `'a' . 'b'` (`concat_space: one`) |
| Line length | hard limit 150 | not enforced |
| Yoda conditions | disallowed | disallowed ✅ agree |
| Named parameters on internal calls | **required** (custom sniff) | no such rule |

These are not reconcilable file-by-file. **A file cannot satisfy both**, so an app
must wire up exactly one formatter.

:::warning `cs:check` and `cs:fix` do not mean here what they mean upstream

`cs:check` and `cs:fix` are the script names that `nextcloud/coding-standard`
defines, and they are what Nextcloud's own `lint-php-cs.yml` invokes. In this
fleet those same two names are **aliases for PHPCS**:

```json
"cs:check": "./vendor/bin/phpcs --standard=phpcs.xml",
"cs:fix":   "./vendor/bin/phpcbf --standard=phpcs.xml"
```

So a contributor who runs the documented Nextcloud command gets our 4-space PEAR
reformatting, not Nextcloud's tabs. Worse, **17 of 18 apps also list
`nextcloud/coding-standard:^1.4` in `require-dev`** while shipping no
`.php-cs-fixer.dist.php` and never invoking php-cs-fixer anywhere in CI. It is a
dead dependency that pulls `php-cs-fixer/shim` into every `vendor/` tree, and it
is loaded and ready to reformat the entire codebase the wrong way for anyone who
finds it.

Either drop the dependency or adopt the standard. Do not keep both.
:::

### The `.editorconfig` gap

**No fleet app ships an `.editorconfig`.** Nextcloud core does. An editor opening
one of our PHP files therefore falls back to whatever the user configured — and
for anyone whose defaults came from Nextcloud work, that is tabs, which PHPCS then
rejects. This is a one-file fix and it belongs in every app.

### Static analysis and the Nextcloud version it is analysing against

Nextcloud's `psalm.yml` does two things ours does not:

```yaml
- uses: icewind1991/nextcloud-version-matrix   # reads appinfo/info.xml
- run: grep 'phpVersion="${{ steps.versions.outputs.php-min }}' psalm.xml
- run: composer remove nextcloud/ocp --dev --no-scripts
- run: composer require --dev nextcloud/ocp:dev-${{ steps.versions.outputs.branches-max }}
```

The analysed API surface is **derived from what the app declares it supports**, and
the run fails if `psalm.xml` does not pin the minimum PHP version.

Ours is static, and as of 2026-08-12 it is inconsistent with itself:

| | Declared in `appinfo/info.xml` | Analysed against | Tested against |
| --- | --- | --- | --- |
| 16 apps | NC **32–34** | `nextcloud/ocp:^31.0` (15 apps) | `stable32` and/or `stable33` |

Three consequences, in increasing order of seriousness:

1. No app is tested on **NC 34**, which all of them claim to support.
2. Static analysis runs one major **below** the declared minimum, so nothing added
   in 32/33/34 is visible to it.
3. Nothing **removed** in 32/33/34 can be reported either. That is why the removal
   of `\OC::$server` in NC 34 needed a hand-written PHPCS sniff to catch — the type
   checker was looking at NC 31 and could not see it.

No app's `psalm.xml` sets `phpVersion`, so our configs would fail Nextcloud's own
psalm gate outright. Adopting version-matrix derivation removes the whole class of
problem: the matrix can no longer drift from `info.xml`, because it is computed
from it.

### What Psalm is actually checking

Every app runs `errorLevel="4"` and suppresses ~34 issue types. The suppression
list includes `InvalidArgument`, `InvalidReturnType`, `InvalidReturnStatement`,
`InvalidMethodCall`, `UndefinedInterfaceMethod`, `TypeDoesNotContainType`,
`InvalidArrayOffset` and `EmptyArrayAccess`, plus `UndefinedClass` for the whole
`OCP\` namespace. Read a green Psalm leg accordingly.

PHPStan is level 5 fleet-wide, which the older docs state correctly.

### Checks Nextcloud runs that we do not

| Nextcloud check | What it catches | Our coverage |
| --- | --- | --- |
| `lint-info-xml.yml` | `appinfo/info.xml` validated against the App Store XSD | **none** — `quality.yml` never reads `info.xml` |
| `occ app:check-code` | use of private / deprecated server APIs | **partial** — one custom sniff for `\OC::$server` only |
| `occ integrity:sign-app` | writes `appinfo/signature.json` into the package | **none** — see below |
| `reuse.yml` | REUSE / SPDX compliance as a CI job | partial — a PHPCS sniff and a hydra gate, not the REUSE tool |
| PHPUnit on mariadb / mysql / oci / sqlite | database-portability bugs | pgsql only (one app opts into pgsql explicitly; the shared default is pgsql) |

### Release and signing

Both paths build a tarball, attach it to a GitHub release and POST it to the App
Store. One step differs and it is not cosmetic:

- **Nextcloud** runs `occ integrity:sign-app --privateKey --certificate`, which
  writes `appinfo/signature.json` **inside** the package, then uploads.
- **We** sign only the tarball (`openssl dgst -sha512`) for the App Store API.
  There is no `integrity:sign-app` step in `release.yml`, `release-beta.yml` or
  `release-stable.yml`.

The upload is accepted either way, but an installed app with no
`appinfo/signature.json` cannot be verified by Nextcloud's integrity checker.

We also package with `rsync` rather than `krankerl`; no app ships a
`krankerl.toml`. Nextcloud's template supports both, so this is a free choice.

## Frontend

Here we are much closer to Nextcloud than on the backend — we use their configs
directly.

| | Conduction | Nextcloud (current apps) |
| --- | --- | --- |
| ESLint config | `@nextcloud/eslint-config@^8.4.1` (17/18 apps) | `@nextcloud/eslint-config@^9.0.1` |
| ESLint | `^8.56` — resolves to 8.57.1, **end of life** | 9.x / 10.x |
| Stylelint config | `@nextcloud/stylelint-config@^2.4.0` | `@nextcloud/stylelint-config@^3.2.2` |
| Stylelint | 15.x | 16.x |
| Unit tests | vitest (11 apps), jest (6), **none (3)** | vitest |
| E2E | Playwright | Cypress |
| Node in CI | hardcoded `20` | read from `package.json` `engines`, fallback `^24` |

Four things to fix, in order of how quietly they fail:

1. **Unquoted globs in the `stylelint` script.** Thirteen apps run
   `stylelint src/**/*.vue src/**/*.scss src/**/*.css` without quotes, so the
   *shell* expands the glob and — without `globstar` — `src/**/` matches only one
   directory level. Nested components are silently not linted. The four apps that
   quote it (`procest`, `pipelinq`, `shillinq`, `doriath`) check strictly more
   files than the other fourteen. A passing stylelint job does not currently mean
   the same thing in two apps.
2. **`npm run lint` is `eslint src` with no `--max-warnings`.** Warnings never fail
   a build, so they accumulate indefinitely. (ESLint itself *is* running: the flat
   config loads correctly under 8.57.1 — verified from a live job log, not
   assumed.)
3. **Three apps have no unit test script at all** — `scholiq`, `portaliq`,
   `hermiq`. The shared workflow detects this honestly and records a skip, which
   renders as a pass in the rollup.
4. **`.prettierrc` exists in 14 apps and `prettier` is a dependency in none.** No
   `format` script invokes it either. It is inert in CI but not in editors, where
   it tells Prettier to use 2-space indentation and double quotes for `.ts` files
   — both of which `@nextcloud/eslint-config` then flags. Delete it or wire it up.

## Where the configuration lives

As of this change, the PHP quality configuration has **one** home:
[`quality-config/`](https://github.com/ConductionNL/.github/tree/main/quality-config)
in this repository, shipped inside the existing `conduction/hydra-gates` composer
package. An app pulls it with `composer install` and reduces its own files to
stubs:

```xml
<ruleset name="myapp">
    <file>lib</file>
    <rule ref="vendor/conduction/hydra-gates/quality-config/phpcs.xml"/>
</ruleset>
```

Same config in CI and on a laptop, which is the point — a config only CI sees
becomes its own drift source.

The drift this replaces, measured across all 18 core apps on 2026-08-12:

| File | Distinct variants across 18 apps |
| --- | ---: |
| `psalm.xml`, `phpstan.neon`, `playwright.config.ts`, `code-quality.yml` | **18 each** |
| `eslint.config.js` | 17 |
| `phpmd.xml` | 15 |
| `vitest.config.js` | 14 |
| `phpcs.xml`, `stylelint.config.js` | 6 each |
| `NamedParametersSniff.php` (a *custom rule*) | 6 |
| `.prettierrc` | 1 |

`psalm.xml` and the frontend configs are not stub-able yet — Psalm has no config
inheritance and ESLint flat config resolves plugins relative to the config file.
Both are covered in the [`quality-config/` README](https://github.com/ConductionNL/.github/tree/main/quality-config#not-yet-centralised-and-why).

## Corrections to older pages

- "**Code style — PHPCS (PSR-12)**", in
  [development-pipeline.md](development-pipeline.md) and
  [contributing.md](contributing.md), is wrong. The ruleset is PEAR-derived. Four
  PSR-2/PSR-12 sniffs are pulled in individually; the standard as a whole is not.
- "**four parallel quality gates**" understates the pipeline by an order of
  magnitude — see the table at the top of this page.
- "**Hydra … coming soon**" is stale: `enable-hydra-gates: true` is set in all 18
  core apps today.
- "**There are no development builds**", in
  [release-process.md](release-process.md), is contradicted by
  `release-development.yml`, which exists in 14 of 18 apps and calls the shared
  beta release workflow with `channel: dev`.

## Further reading

- [Development Pipeline](development-pipeline.md) — branch flow and release triggers
- [Contributing](contributing.md) — PR checklist and commit conventions
- [`quality-config/` README](https://github.com/ConductionNL/.github/tree/main/quality-config) — the mechanism, and the phpcs behaviour it was built on
- [nextcloud/.github workflow templates](https://github.com/nextcloud/.github/tree/master/workflow-templates)
- [nextcloud/coding-standard](https://github.com/nextcloud/coding-standard)
