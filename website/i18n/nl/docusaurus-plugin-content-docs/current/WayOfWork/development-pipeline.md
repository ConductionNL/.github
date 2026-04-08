---
id: development-pipeline
title: Geautomatiseerde Ontwikkelstraat
sidebar_label: Ontwikkelstraat
sidebar_position: 3
description: Hoe code van branch naar productie stroomt — kwaliteitspoorten, securitychecks en geautomatiseerde releases
---

# Geautomatiseerde Ontwikkelstraat

Elke regel code bij Conduction passeert een geautomatiseerde pipeline voordat het productie bereikt. De pipeline handhaaft kwaliteit, veiligheid en compliance — geen uitzonderingen.

## Branch Flow

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘
```

Alle branches zijn beschermd. Geen directe pushes. Elke wijziging gaat via een pull request met peer review en CI.

| Doel | Reviews vereist | Wat triggert |
|---|---|---|
| `development` | 1 reviewer | Quality CI |
| `beta` | 1 reviewer | Quality CI + beta release |
| `main` | 2 reviewers | Volledige CI + stabiele release |

## Kwaliteitspoorten

Elke PR triggert **vier parallelle kwaliteitspoorten** — alle moeten slagen voor merge:

### PHP-kwaliteit
| Check | Tool |
|---|---|
| Syntax | `php -l` |
| Codestijl | PHPCS (PSR-12) |
| Statische analyse | PHPStan + Psalm |
| Mess detection | PHPMD |
| Codemetrics | PHPMetrics |

### Frontend-kwaliteit
| Check | Tool |
|---|---|
| JavaScript/Vue | ESLint |
| CSS/SCSS | Stylelint |

### Dependency-checks
| Check | Wat het vangt |
|---|---|
| Licentiecontrole | Copyleft of beperkte licenties in dependencies |
| Kwetsbaarheidsscan | Bekende CVE's in composer- en npm-pakketten |
| SBOM-generatie | CycloneDX bill of materials voor audittrail |

### Security
| Check | Wat het vangt |
|---|---|
| `composer audit` | Bekende PHP-dependency-kwetsbaarheden |
| `npm audit` | Bekende JS-dependency-kwetsbaarheden |

## Geautomatiseerde Releases

Releases zijn volledig geautomatiseerd via GitHub Actions:

- **Merge naar `beta`** → beta release (nightly kanaal)
- **Merge naar `main`** → stabiele release

Versienummers worden berekend op basis van PR-labels:

| Label | Versieverhoging |
|---|---|
| `major` | 1.0.0 → 2.0.0 |
| `minor` | 1.0.0 → 1.1.0 |
| `patch` (standaard) | 1.0.0 → 1.0.1 |

## Hydra — Agentische Ontwikkelstraat

:::info Binnenkort beschikbaar

Conduction ontwikkelt **Hydra**, een agentische spec-driven ontwikkelstraat die applicaties bouwt vanuit gestructureerde specificaties met overheidswaardige traceerbaarheid, SBOM-generatie en audittrails. Deze sectie wordt bijgewerkt zodra Hydra publiek beschikbaar is.

:::

## Meer Lezen

- [Contributing guide](contributing) — PR-checklist, commitconventies, DCO
- [Releaseproces](release-process) — volledige versie- en deploymentdetails
- [Spec-driven development](spec-driven-development) — hoe specs de pipeline voeden
