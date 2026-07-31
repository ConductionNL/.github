# Conduction Conventions

Cross-app conventions for repositories under the [ConductionNL](https://github.com/ConductionNL) organisation. These are the rules every Conduction Nextcloud app should follow so that org-wide tooling (CI, security, docs, releases) keeps working uniformly.

## Workflows

### Central Quality workflow

There is **one** Quality workflow for the entire org: [`.github/workflows/quality.yml`](./.github/workflows/quality.yml) in this repo (`ConductionNL/.github`). It is a [reusable workflow](https://docs.github.com/en/actions/using-workflows/reusing-workflows) that runs the full quality matrix — PHPCS, PHPMD, Psalm, PHPStan, ESLint, Stylelint, license check, security audit, PHPUnit, Newman, Playwright, SBOM, coverage report.

Every Conduction app **must** consume the central workflow via a thin wrapper. **Do not duplicate quality logic in per-app workflows.**

#### Wrapper convention

| Property | Required value                                                                                                                  |
| -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Filename | `.github/workflows/code-quality.yml`                                                                                            |
| `uses`   | `ConductionNL/.github/.github/workflows/quality.yml@main`                                                                       |
| Trigger  | `push` to `main` / `development` / `feature/**` / `bugfix/**` / `hotfix/**` + `pull_request` to `main` / `beta` / `development` |
| Inputs   | At minimum `app-name`. Optionally toggle the per-tool `enable-*` flags.                                                         |

Reference template (use as-is, just change `app-name`):

```yaml
name: Code Quality

on:
  push:
    branches: [main, development, feature/**, bugfix/**, hotfix/**]
  pull_request:
    branches: [main, beta, development]
  workflow_dispatch:

jobs:
  quality:
    uses: ConductionNL/.github/.github/workflows/quality.yml@main
    with:
      app-name: <app-id>
      php-version: "8.3"
      enable-psalm: true
      enable-phpstan: true
      enable-phpmetrics: true
      enable-frontend: true
      enable-eslint: true
```

#### Why one workflow, not per-app variants

- **Single source of truth** — improvements (new linter, security gate, dependency scan) ship to every app immediately by updating one file.
- **No drift** — apps can't quietly fall behind on quality coverage.
- **Reviewable in one place** — auditors and clients see one canonical CI definition for the whole platform.

#### Anti-patterns to avoid

- ❌ Per-app `quality-check.yml`, `quality.yml`, `tests.yml`, `lint.yml` files that duplicate central workflow logic. They cause silent divergence and miss central improvements.
- ❌ Inline quality jobs (PHPCS / Psalm / etc.) defined directly in app repos rather than via the central reusable workflow.
- ❌ Renaming the wrapper to anything other than `code-quality.yml`. Filename consistency lets contributors and tools find the wrapper without per-repo guesswork.

#### JS-only repos (`enable-php: false`)

Repos without a `composer.json` (component libraries, themes — e.g. `nextcloud-vue`, `conduction-theme`) use the same wrapper with the PHP toolchain switched off:

```yaml
    with:
      app-name: <repo-name>
      enable-php: false        # skips php-quality, PHPUnit and the composer legs of security/license
      enable-frontend: true
      enable-eslint: true
      node-version: "24"       # optional, defaults to "20"
```

The skipped PHP checks still report (as "skipped"), which satisfies required status checks — so the same org-wide required contexts work for PHP apps and JS-only repos alike.

#### Custom frontend checks (`frontend-checks`)

Repo-specific quality gates (unit tests, build verification, docs coverage, …) run through the `frontend-checks` input — a JSON array of **npm script names**. Each entry becomes its own `quality / Frontend Check (<script>)` job.

```yaml
    with:
      frontend-setup-command: "cd docusaurus && npm ci"   # optional, runs AFTER the root npm ci (never replaces it)
      frontend-checks: '["test", "check:build", "check:docs"]'
```

**Requirements for every script you list:**

1. **It must exist in the repo's `package.json` `scripts`** — the leg fails fast with an explicit annotation (`npm script '<name>' is listed in this repo's frontend-checks input but does not exist in package.json`) before anything is installed.
2. **It must be self-contained.** Every leg is an independent job with a fresh checkout + `npm ci`; nothing from another leg (like `dist/`) is available. Bundle order-dependent steps into one script:
   ```json
   "check:build": "npm run build && npm run check:css-entry"
   ```
   (`check:css-entry` needs `dist/`, so it must live in the same script as the build.)
3. **Multi-command checks become named scripts.** Inline shell sequences can't be expressed in the JSON list — wrap them, e.g.:
   ```json
   "check:docs-fresh": "cd docusaurus && npm run prebuild:docs && cd .. && git diff --exit-code docs/components/_generated/"
   ```

All `frontend-checks` legs feed into the `Quality Report` gate, so a failing custom check fails the org-required `quality / Quality Report` context.

#### Peer-dependency policy (`.npmrc`, not CLI flags)

The central workflow runs plain `npm ci` — it does **not** pass `--legacy-peer-deps`, and it never will. Peer-resolution behaviour is owned by each repo via its committed `.npmrc`, so CI behaves exactly like every local and production install, and real conflicts surface in CI instead of being masked org-wide.

Do not ask for the flag to be re-hardcoded in `quality.yml`; that silently disables peer checking for every repo in the fleet at once.

##### `legacy-peer-deps` is an emergency brake, not a setting

**The default is: never use it.** Not on the command line, not in `.npmrc`, not "just to get CI green".

What the flag actually does: it reverts npm to its pre-v7 behaviour where peer dependencies are *advisory* — npm stops checking whether the packages in your tree are compatible with each other and simply installs whatever the lockfile says. The error you silenced does not describe a problem with npm; it describes a real incompatibility between two libraries you ship.

Why that always comes back to bite you:

- **It moves the failure from install-time to runtime.** A strict `npm ci` failure is loud, early, and points at the exact packages in conflict. With the flag, the same conflict ships — and resurfaces as `export 'X' was not found`, a second copy of Vue with broken reactivity, or a component that silently renders nothing. Those bugs cost days instead of minutes and are found by users instead of CI.
- **It compounds silently.** Every `npm install` run under the flag can bake further unresolvable combinations into the lockfile. The longer it stays on, the bigger the eventual cleanup — you are not deferring one conflict, you are accumulating them.
- **It hides the fix.** The moment the error is gone, the pressure to actually align the versions is gone with it. Flags like this have a way of becoming permanent; the openconnector `.npmrc` exists since the vue2/vue3 migration and is still there.
- **It desynchronises the fleet.** A repo running legacy resolution produces lockfiles that strict repos can't reproduce, so the same dependency bump behaves differently across apps — the exact drift the central quality workflow exists to prevent.

##### The only acceptable use

A release or critical merge is blocked **right now**, the real fix (aligning the conflicting versions, upgrading the offending dependency, or removing it) is genuinely not achievable on that timeline, and shipping matters more than waiting. Under those circumstances — and only those:

1. Set `legacy-peer-deps=true` in the repo's **`.npmrc`** (never as an ad-hoc CLI flag, so at least the behaviour is committed, visible, and identical everywhere).
2. Add a comment directly above it stating **why** it is needed, **which packages** conflict, **who** set it and **when**.
3. Open a tracking issue for the real fix and link it in that comment.
4. Remove the flag as soon as the conflict is resolved. Treat it like a `TODO` with interest: every week it survives makes the eventual removal harder.

A `.npmrc` containing `legacy-peer-deps=true` without a dated explanation and a linked issue should be treated as a bug and flagged in review.

## SBOM (Software Bill of Materials)

Each app's SBOM is published exclusively as a **release asset** via the central Quality workflow's SBOM job. Per-app `sbom.yml` workflows are not allowed — they were removed in [`ConductionNL/.github#34`](https://github.com/ConductionNL/.github/pull/34).

See [SECURITY.md](./SECURITY.md#software-bill-of-materials-sbom) for the consumer contract (stable URLs, format, verification gates).

## Branch flow

Every Conduction app uses three protected branches with this promotion direction:

```
feature/* → development → beta → main
```

- **`development`** — integration branch. Open feature/bugfix/hotfix PRs against it.
- **`beta`** — pre-release. Periodically refreshed from `development` via the standard release PR.
- **`main`** — production. Refreshed from `beta` after sign-off. Every push to `main` (= every release) generates a release tag, which the SBOM job attaches the SBOM to.

Branch protection on each branch (per the org-wide ruleset):

- `development` — 1 review required
- `beta` — 1 review required
- `main` — 2 reviews required

PRs always target `development` unless they are explicitly a release-promotion PR.

## OpenSpec

Specs and ADRs live under `openspec/` in each app. Cross-app shared specs and ADRs live at [`ConductionNL/hydra/openspec/`](https://github.com/ConductionNL/hydra). See the per-app `CLAUDE.md` for the current workflow.

## Documentation

App-specific docs live in `docs/` per app. Cross-org developer docs live at [`ConductionNL/.github/docs/`](./docs/). The conventions in this file complement (not replace) the docs there.
