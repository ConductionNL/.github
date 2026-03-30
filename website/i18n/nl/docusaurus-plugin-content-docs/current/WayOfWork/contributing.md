---
id: contributing
title: Bijdragen aan Conduction
sidebar_label: Bijdragen
sidebar_position: 6
description: Hoe je kunt bijdragen aan de open-source projecten van Conduction — code, docs, vertalingen en meer
---

# Bijdragen aan Conduction

Bedankt voor je interesse in bijdragen! Elke bijdrage — code, documentatie, vertaling, bugreport of idee — helpt ons dichter bij ons doel: ervoor zorgen dat elke inwoner van Nederland automatisch de overheidsdiensten ontvangt waar hij of zij recht op heeft.

Deze gids geldt voor alle repositories onder [ConductionNL](https://github.com/ConductionNL). De gezaghebbende bron is [CONTRIBUTING.md](https://github.com/ConductionNL/.github/blob/main/CONTRIBUTING.md) in onze organisatie `.github`-repository.

---

## Manieren om bij te dragen

Je hoeft geen code te schrijven om bij te dragen:

| Type bijdrage | Waar |
|---|---|
| 🐛 Bug melden | GitHub Issues |
| 💡 Feature voorstellen | GitHub Issues |
| 📖 Documentatie verbeteren | PR naar de relevante repo |
| 🌐 Inhoud vertalen | PR naar `.github` (deze docs-site) |
| 🔍 Pull request reviewen | GitHub PR review |
| 💬 Vragen beantwoorden | GitHub Discussions / Issues |
| 🔒 Beveiligingsprobleem melden | Zie [Beveiligingsbeleid](../ISO/security) |

---

## Eerste bijdragers

Nieuw bij open source of bij Conduction? Zoek naar issues met het label [`good first issue`](https://github.com/search?q=org%3AConductionNL+label%3A%22good+first+issue%22&type=issues) — deze zijn geschikt voor mensen zonder diepe contextkennis.

Laat gerust een reactie achter op een issue dat je aanspreekt. We helpen je op weg.

---

## Code bijdragen

### Externe bijdragers (fork & PR)

1. Fork de repository
2. Maak een branch aan vanaf `development`: `git checkout -b feature/jouw-feature-naam`
3. Maak je wijzigingen en commit met [Conventional Commits](#commit-berichten)
4. Onderteken je commits (zie [DCO](#developer-certificate-of-origin))
5. Push naar je fork en open een PR naar `development`

### Conduction-teamleden (directe branch)

1. Maak een branch aan vanaf `development`: `feature/*` of `bugfix/*`
2. Open een PR naar `development` wanneer je klaar bent

### PR-checklist

- [ ] CI-kwaliteitschecks slagen lokaal
- [ ] Nieuwe code heeft tests waar van toepassing
- [ ] Documentatie bijgewerkt als gedrag wijzigt
- [ ] PR gelabeld met `major`, `minor` of `patch`
- [ ] DCO sign-off op alle commits (`git commit -s`)

---

## Branch Model

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘
```

| Doel | Toegestane bronnen | Reviews vereist |
|---|---|---|
| `development` | `feature/*`, `bugfix/*` | 1 |
| `beta` | `development`, `hotfix/*` | 1 |
| `main` | `beta`, `hotfix/*` | 2 |

Geen force pushes. Geen directe pushes. Alle wijzigingen via pull request. Zie het volledige [Releaseproces](release-process) voor details.

---

## Kwaliteitsworkflow

Elke PR triggert geautomatiseerde kwaliteitschecks — alle moeten slagen voor merge.

**PHP:** syntax lint, PHPCS (PSR-12), PHPStan (level 5), Psalm, PHPMD

**Frontend:** ESLint, Stylelint

**Dependencies:** licentiecontrole, kwetsbaarheidsscan

```bash
# Lokaal uitvoeren
composer cs:check && composer phpstan && composer psalm
npm run lint
```

---

## Commit-berichten

We gebruiken [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: proactieve servicematching toevoegen
fix: null pointer in namespace parser oplossen
docs: contributing-gids bijwerken
chore: PHPStan upgraden naar v2
```

- Imperatieve wijs ("toevoegen" niet "toegevoegd")
- Eerste regel maximaal 72 tekens
- Verwijs naar issues met `Closes #123` in de berichttekst

---

## Developer Certificate of Origin

Alle bijdragen moeten ondertekend zijn:

```bash
git commit -s -m "feat: jouw commit-bericht"
```

Dit voegt `Signed-off-by: Jouw Naam <email>` toe en bevestigt dat je het recht hebt de bijdrage in te dienen onder de projectlicentie. Zie [developercertificate.org](https://developercertificate.org/).

---

## Ontwikkelomgeving instellen

1. Installeer PHP 8.1+ en Node.js 20+
2. Installeer Composer
3. Clone de repository (of je fork)
4. Voer `composer install && npm install` uit
5. Stel een [Nextcloud-ontwikkelomgeving](https://github.com/ConductionNL/nextcloud-docker-dev) in

---

## Community

- [Common Ground Slack](https://commonground.nl)
- [LinkedIn](https://www.linkedin.com/company/conduction/)
- [GitHub Discussions](https://github.com/orgs/ConductionNL/discussions)

---

## Licentie

Door bij te dragen ga je ermee akkoord dat jouw bijdragen worden gelicenseerd onder dezelfde licentie als het project (EUPL-1.2 tenzij anders vermeld in de repository).
