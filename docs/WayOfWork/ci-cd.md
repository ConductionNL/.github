---
id: ci-cd
title: CI/CD and Code Standards
sidebar_label: CI/CD and Code Standards
sidebar_position: 4
description: What our pipeline runs, where the configuration lives, and how we stay strictly compatible with Nextcloud's own app CI/CD
---

# CI/CD and Code Standards

We build Nextcloud apps, so we hold ourselves to Nextcloud's rules:

> **Conduction code must pass Nextcloud's own checks unchanged. We may be
> stricter than Nextcloud; we may not be different from it.**

"Stricter" means adding a rule Nextcloud has no opinion on. It never means giving
one of their rules a different value — code that satisfies us must still satisfy
them. Where a difference exists today it is a defect, not a dialect, and this page
is where each one is tracked.

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

## PHP

### Formatting — one standard, and it is Nextcloud's

**Conduction code must pass `nextcloud/coding-standard` unchanged. We may be
stricter than Nextcloud; we may not be different from it.**

That rule is newer than most of the code. Measured 2026-08-12 against
openregister's `lib/`, **all 1,427 files failed** Nextcloud's standard:

| php-cs-fixer rule | files affected |
| --- | ---: |
| `curly_braces_position` | 1,427 — 100% |
| `indentation_type` | 1,409 — 98.7% |
| `phpdoc_align` | 1,221 — 85.6% |
| `binary_operator_spaces` | 1,104 — 77.4% |
| `trailing_comma_in_multiline` | 693 — 48.6% |
| `cast_spaces` | 676 — 47.4% |
| `concat_space` | 583 — 40.9% |

The fleet had been formatting with a PEAR-derived PHPCS ruleset — four spaces,
next-line braces, `(int) $x`, `'a'.'b'` — which is not a stricter standard but a
different dialect. Under the rule above it has to go, and it has.

#### Two tools, disjoint jurisdiction

| Concern | Tool | Where the config lives |
| --- | --- | --- |
| **Formatting** — whitespace, braces, imports, quotes, casts | php-cs-fixer | [`conduction/coding-standard`](https://github.com/ConductionNL/coding-standard) |
| **Semantics** — named parameters, `@spec`, banned functions, removed NC APIs, line length | PHP_CodeSniffer | [`quality-config/`](https://github.com/ConductionNL/.github/tree/main/quality-config) |
| **Types** | Psalm + PHPStan | `quality-config/` |

`Conduction\CodingStandard\Config` **extends** Nextcloud's and merges a private
`ADDITIONS` array onto `parent::getRules()`. The package's invariant test fails
the build if `ADDITIONS` shares a single key with the parent set, if any parent
rule is dropped, or if any parent rule's *value* changed. The policy is therefore
enforced by construction, not by review — and each assertion carries a positive
control, because a suite that cannot fail is indistinguishable from one that
passes.

`ADDITIONS` is currently **empty**, which is a result rather than an omission.
Every rule this fleet wants beyond Nextcloud's is semantic, not typographic, and
php-cs-fixer cannot express any of them.

#### Why PHPCS had to be cut back, not just re-pointed

Left alone, the two tools contradict each other and the app becomes unfixable —
`composer cs:fix` and `composer phpcs` demand opposite things and neither can be
satisfied. That was the fleet's real state. Running the old ruleset over
php-cs-fixer-formatted code produced **111,932 findings, 111,747 of them
auto-fixable formatting**:

```
Generic.WhiteSpace.DisallowTabIndent                62,123
Generic.WhiteSpace.ScopeIndent                      35,030
Generic.Arrays.ArrayIndent                           3,726
PEAR.Commenting.FunctionComment (param spacing)      2,797
PEAR.Functions.FunctionDeclaration (indent + brace)  2,576
Generic.Formatting.MultipleStatementAlignment        1,132
Generic.Formatting.SpaceAfterCast                      909
Squiz.Strings.ConcatenationSpacing                     534
Squiz.ControlStructures.ElseIfDeclaration               31
```

That last line is the shape of the whole problem: Squiz's sniff **forbids** the
`elseif` keyword Nextcloud's `elseif` fixer **requires**. Two tools cannot both be
right about one token.

With every formatting sniff removed, the same measurement yields **185 findings,
all semantic** — 181 missing `@spec`, 2 over the 150-character line limit, 2 SPDX
end-char. The named-parameter and legacy-accessor sniffs fire **zero** times,
which is what stricter-but-compatible looks like when it is true rather than
assumed.

Docblock *presence* stays; docblock *layout* is `phpdoc_align`'s. The alignment
codes are excluded individually rather than by dropping the sniff — losing the
presence requirement would be a real regression.

`quality-config/tests/compatibility.sh` makes this permanent: format a fixture,
run PHPCS over the result, fail on any formatting sniff.

#### What migrating an app looks like

Proven end-to-end on `nextcloud-app-template`
([PR #141](https://github.com/ConductionNL/nextcloud-app-template/pull/141)):

```
php-cs-fixer   Found 0 of 23 files that can be fixed
phpcs          39 violations, ALL WARNINGS (35 @spec, 4 SPDX). Zero errors.
```

:::warning `cs:check` and `cs:fix` used to lie

They are the script names `nextcloud/coding-standard` defines, and what
Nextcloud's own `lint-php-cs.yml` invokes. In this fleet they were **aliases for
PHPCS** — so a contributor running the documented Nextcloud command got four-space
PEAR reformatting. Worse, 17 of 18 apps carried `nextcloud/coding-standard` in
`require-dev` with no `.php-cs-fixer.dist.php` and no invocation anywhere: loaded,
and ready to reformat the whole codebase for whoever found it.

They now run php-cs-fixer, and the direct dependency is dropped — it arrives
transitively at a version `conduction/coding-standard` has tested against.
:::

:::danger A missing autoloader reports as a clean tree

`.php-cs-fixer.dist.php` **must** start with `require_once __DIR__ . '/vendor/autoload.php';`.
php-cs-fixer includes the config before your autoloader runs, so without it the
run dies with `Class not found` — and in `--format=json` that fatal is reported as
**zero files needing changes**. It reads exactly like a pass.
:::

### The `.editorconfig` gap

**No fleet app shipped an `.editorconfig`.** Nextcloud core does. An editor
opening one of our PHP files fell back to whatever the user configured — and for
anyone whose defaults came from Nextcloud work, that is tabs, which the old PHPCS
ruleset then rejected.

Nextcloud's `.editorconfig` is now copied **verbatim** into every app
(`indent_style = tab`, `indent_size = 4`, two-space YAML and `package*.json`). It
agrees with the formatter instead of fighting it.

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

## Package registry

Shared configuration only stops drifting if every app pulls it the same way, so
the distribution channel is part of the standard, not an implementation detail.

| Package | Registry | Contains | Consumed by |
| --- | --- | --- | --- |
| [`conduction/coding-standard`](https://packagist.org/packages/conduction/coding-standard) | Packagist | php-cs-fixer config extending Nextcloud's | every app, `require-dev` |
| [`conduction/hydra-gates`](https://packagist.org/packages/conduction/hydra-gates) | Packagist | the mechanical gates **and** `quality-config/` (PHPCS, PHPMD, PHPStan base, custom sniffs) | every app, `require-dev` |
| [`@conduction/nextcloud-vue`](https://www.npmjs.com/package/@conduction/nextcloud-vue) | npm | shared Vue components **and** the ESLint / Stylelint config | every app, `dependencies` |

Both composer packages are built from repositories that also do other things —
`conduction/hydra-gates` is the root package of `ConductionNL/.github`, which also
hosts this documentation site. One repository can publish exactly one composer
package, which is why the coding standard needed a repository of its own.

### Registration is not cosmetic

Before registration, an app consuming `conduction/hydra-gates` needed this in its
own `composer.json`:

```jsonc
"repositories": [
    { "type": "vcs", "url": "https://github.com/ConductionNL/.github.git", "no-api": true }
]
```

That block is a per-app file, and per-app files are what drift — it is the same
failure mode the shared config exists to end. `no-api: true` also made composer
clone the **entire** `.github` repository, docs site included, on every install.
Registration deletes the block from all 18 apps.

### Constraints float; they are not pinned

Apps require `^1.0`, not an exact version. A pin is a silent expiry date: 22 repos
once sat on gate package `v1.0.1` while 16 gates were dead fleet-wide and every one
of them reported PASS. Hold a package still only for a stated reason, in that app,
with the reason written next to the constraint.

### Publishing, and how to tell it actually published

Submitting a repository creates a push webhook on it automatically —
`https://packagist.org/api/github`, `push` events. There is nothing to wire up by
hand and nothing for `gh` to configure; GitHub Apps cannot be installed through
the API in any case.

**Verify against the endpoint Composer actually reads.** Packagist serves package
metadata from two places, and they do not update together:

| endpoint | who reads it | freshness |
| --- | --- | --- |
| `repo.packagist.org/p2/<vendor>/<pkg>.json` | **Composer** | current |
| `packagist.org/packages/<vendor>/<pkg>.json` | the website | lags, sometimes by tens of minutes |

Measured 2026-08-12: `conduction/hydra-gates` `v1.7.0` was tagged and pushed. The
web endpoint showed `v1.6.0` as the newest tag for the next half hour, while the
p2 endpoint already had `v1.7.0` — and `composer require conduction/hydra-gates:^1.0`
resolved to `v1.7.0 (b9c6520a)` throughout. Nothing was broken. The instrument was.

That mistake is worth naming because it produced a confident, wrong diagnosis: a
webhook returning `202`, a package that "had not updated", and a missing Packagist
GitHub App all pointed at a publishing failure that was not happening.

So the check is one command, and it is the one Composer would make:

```bash
curl -s https://repo.packagist.org/p2/<vendor>/<pkg>.json \
  | jq -r '.packages | to_entries[0].value[0] | "\(.version)  \(.source.reference[0:8])"'
```

Compare that SHA to `git rev-parse HEAD`. Three things that are **not** evidence:
a `ping` delivery (Packagist sends one on install, it proves only that the
endpoint answers a handshake), an HTTP `202` (it means *accepted for processing*),
and `package.time` on the web endpoint (that is the package's **creation**
timestamp and never moves).

### npm

`@conduction/nextcloud-vue` was already published, so homing the frontend config
there adds export paths to an existing package rather than creating a new one.
Note its dist-tags: apps consume **`vue3`**, currently `2.2.0-vue3.x`. The `latest`
tag is `1.0.0-beta.3`, an old Vue 2 build — installing without a tag or an explicit
version gets the wrong library.

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
