---
id: release-process
title: Releaseproces
sidebar_label: Releaseproces
sidebar_position: 4
description: Hoe Conduction versies beheert, branches hanteert en Nextcloud-apps uitbrengt
---

# Releaseproces


## Branch Model

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘                    ↑
                                 └── (hotfix kan rechtstreeks)
```

- **`development`**: Integratiebranch — geen builds
- **`beta`**: Nachtelijke builds voor testdoeleinden
- **`main`**: Stabiele releases

## Versiebeheer

We gebruiken [Semantic Versioning](https://semver.org). De versie wordt **nooit handmatig aangepast** — hij wordt automatisch berekend op basis van PR-labels:

| Label | Effect |
|---|---|
| `patch` | 1.0.0 → 1.0.1 |
| `minor` | 1.0.0 → 1.1.0 |
| `major` | 1.0.0 → 2.0.0 |

Zonder label: standaard `patch`.

## Hotfixes

Kritieke fixes kunnen de normale flow omzeilen en rechtstreeks naar `beta` of `main` worden gemerged. Gebruik het prefix `hotfix/` voor de branchnaam.

## Meer Lezen

- **Gecentraliseerde workflows**: [github.com/ConductionNL/.github](https://github.com/ConductionNL/.github/tree/main/.github/workflows)
- **Semantic Versioning**: [semver.org](https://semver.org)
- [Volledige Engelse documentatie](/docs/WayOfWork/release-process) voor setup-instructies en FAQ
