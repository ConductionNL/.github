# Conduction Conventions

Cross-app conventions for repositories under the [ConductionNL](https://github.com/ConductionNL) organisation. These are the rules every Conduction Nextcloud app should follow so that org-wide tooling (CI, security, docs, releases) keeps working uniformly.

## Workflows

### Central Quality workflow

There is **one** Quality workflow for the entire org: [`.github/workflows/quality.yml`](./.github/workflows/quality.yml) in this repo (`ConductionNL/.github`). It is a [reusable workflow](https://docs.github.com/en/actions/using-workflows/reusing-workflows) that runs the full quality matrix — PHPCS, PHPMD, Psalm, PHPStan, ESLint, Stylelint, license check, security audit, PHPUnit, Newman, Playwright, SBOM, coverage report.

Every Conduction app **must** consume the central workflow via a thin wrapper. **Do not duplicate quality logic in per-app workflows.**

#### Wrapper convention

| Property | Required value |
|---|---|
| Filename | `.github/workflows/code-quality.yml` |
| `uses` | `ConductionNL/.github/.github/workflows/quality.yml@main` |
| Trigger | `push` to `main` / `development` / `feature/**` / `bugfix/**` / `hotfix/**` + `pull_request` to `main` / `beta` / `development` |
| Inputs | At minimum `app-name`. Optionally toggle the per-tool `enable-*` flags. |

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
