---
id: development-pipeline
title: Automated Development Pipeline
sidebar_label: Development Pipeline
sidebar_position: 3
description: How code flows from branch to production — quality gates, security checks, and automated releases
---

# Automated Development Pipeline

Every line of code at Conduction passes through an automated pipeline before it reaches production. The pipeline enforces quality, security, and compliance — no exceptions.

## Branch Flow

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘
```

All branches are protected. No direct pushes. Every change flows through a pull request with peer review and CI.

| Target        | Reviews required | What triggers             |
| ------------- | ---------------- | ------------------------- |
| `development` | 1 reviewer       | Quality CI                |
| `beta`        | 1 reviewer       | Quality CI + beta release |
| `main`        | 2 reviewers      | Full CI + stable release  |

## Quality Gates

Every PR triggers the shared quality pipeline — all applicable gates must pass before merge.
The four groups below are the core of it; the full set is 18 job groups, including PHPUnit,
Playwright, Newman, axe-core, SBOM and the Hydra gates. See
[CI/CD and Code Standards](ci-cd.md#one-pipeline-eighteen-thin-callers) for the complete table.

### PHP Quality

| Check           | Tool            |
| --------------- | --------------- |
| Syntax          | `php -l`        |
| Code style      | PHPCS ([Conduction standard](ci-cd.md#formatting--the-important-one)) |
| Static analysis | PHPStan + Psalm |
| Mess detection  | PHPMD           |
| Code metrics    | PHPMetrics      |

### Frontend Quality

| Check          | Tool      |
| -------------- | --------- |
| JavaScript/Vue | ESLint    |
| CSS/SCSS       | Stylelint |

### Dependency Checks

| Check              | What it catches                                 |
| ------------------ | ----------------------------------------------- |
| License compliance | Copyleft or restricted licenses in dependencies |
| Vulnerability scan | Known CVEs in composer and npm packages         |
| SBOM generation    | CycloneDX bill of materials for audit trail     |

### Security

| Check            | What it catches                      |
| ---------------- | ------------------------------------ |
| `composer audit` | Known PHP dependency vulnerabilities |
| `npm audit`      | Known JS dependency vulnerabilities  |

## Automated Releases

Releases are fully automated via GitHub Actions:

- **Merge to `beta`** → beta release (nightly channel)
- **Merge to `main`** → stable release

Version numbers are calculated from PR labels:

| Label             | Version bump  |
| ----------------- | ------------- |
| `major`           | 1.0.0 → 2.0.0 |
| `minor`           | 1.0.0 → 1.1.0 |
| `patch` (default) | 1.0.0 → 1.0.1 |

## Hydra — Agentic Development Pipeline

:::info

**Hydra** is Conduction's agentic spec-driven development pipeline: it builds applications from
structured specifications with government-grade traceability, SBOM generation, and audit trails.
Its mechanical quality gates run on every PR in all 18 core apps today (`enable-hydra-gates: true`)
and are published as the open-source composer package
[`conduction/hydra-gates`](https://github.com/ConductionNL/.github/tree/main/hydra-gates).

:::

## Further Reading

- [CI/CD and Code Standards](ci-cd.md) — what the pipeline runs, and where we diverge from Nextcloud's own app CI/CD
- [Contributing guide](contributing.md) — PR checklist, commit conventions, DCO
- [Release process](release-process.md) — full versioning and deployment details
- [Spec-driven development](spec-driven-development.md) — how specs feed the pipeline
