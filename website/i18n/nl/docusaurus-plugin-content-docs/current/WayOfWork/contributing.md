---
id: contributing
title: Bijdragen aan Conduction
sidebar_label: Bijdragen
sidebar_position: 6
description: Hoe je kunt bijdragen aan de open-source projecten van Conduction — code, docs, vertalingen en meer
---

# Bijdragen aan Conduction

Bedankt voor je interesse in bijdragen! Conduction bouwt open-source componenten voor de digitale overheidsinfrastructuur. Elke bijdrage — code, documentatie, vertaling, bugreport of idee — helpt ons dichter bij ons doel: ervoor zorgen dat elke inwoner van Nederland automatisch de overheidsdiensten ontvangt waar hij of zij recht op heeft.

Dit document geldt voor alle repositories onder [ConductionNL](https://github.com/ConductionNL).

## Gedragscode

Dit project valt onder onze [Code of Conduct(ion)](code-of-conduct). Door deel te nemen wordt verwacht dat je je hieraan houdt. Meld onacceptabel gedrag aan [info@conduction.nl](mailto:info@conduction.nl).

## Manieren om bij te dragen

Je hoeft geen code te schrijven om bij te dragen:

| Type bijdrage | Waar |
|---|---|
| Bug melden | GitHub Issues |
| Feature voorstellen | GitHub Issues |
| Documentatie verbeteren | PR naar de relevante repo |
| Inhoud vertalen | PR naar `.github` (deze docs-site) |
| Pull request reviewen | GitHub PR review |
| Vragen beantwoorden | GitHub Discussions / Issues |
| Beveiligingsprobleem melden | Zie [Beveiligingsbeleid](../ISO/security) |

## Eerste bijdragers

Nieuw bij open source of bij Conduction? Zoek naar issues met het label [`good first issue`](https://github.com/search?q=org%3AConductionNL+label%3A%22good+first+issue%22&type=issues) — deze zijn geschikt voor mensen zonder diepe contextkennis.

Twijfel je waar te beginnen? Open een discussie of laat een reactie achter op een issue. We helpen je op weg.

## Bugs melden

Controleer eerst bestaande issues — misschien is het al gemeld. Vermeld bij een bugreport:

- Een duidelijke, beschrijvende titel
- Exacte stappen om het probleem te reproduceren
- Verwacht vs. daadwerkelijk gedrag
- Screenshots, logs of foutmeldingen waar relevant
- Versie van de app en Nextcloud (indien van toepassing)

**Voor beveiligingsproblemen: maak GEEN openbaar issue aan. Zie [Beveiligingsbeleid](../ISO/security).**

## Verbeteringen voorstellen

Verbetervoorstellen worden bijgehouden als GitHub Issues. Vermeld:

- Een duidelijke, beschrijvende titel
- Het probleem dat je probeert op te lossen (niet alleen de oplossing)
- Huidig vs. gewenst gedrag
- Waarom dit nuttig zou zijn voor anderen

## Code bijdragen

### Externe bijdragers (fork & PR)

1. Fork de repository
2. Maak een branch aan vanaf `development`: `git checkout -b feature/jouw-feature-naam`
3. Maak je wijzigingen en commit met [Conventional Commits](#commit-berichten)
4. Onderteken je commits (zie [DCO](#developer-certificate-of-origin-dco))
5. Push naar je fork en open een PR naar `development`
6. Wacht tot CI slaagt en vraag een review aan

### Conduction-teamleden (directe branch)

1. Maak een branch aan vanaf `development`: `feature/*`, `bugfix/*`
2. Open een PR naar `development` wanneer je klaar bent

### PR-checklist

- [ ] CI-kwaliteitschecks slagen lokaal (`composer cs:check`, `composer phpstan`, `npm run lint`)
- [ ] Nieuwe code heeft tests waar van toepassing
- [ ] Documentatie bijgewerkt als gedrag wijzigt
- [ ] PR gelabeld met `major`, `minor` of `patch` (bepaalt versieverhoging)
- [ ] DCO sign-off op alle commits (`git commit -s`)

## Branch Model

Alle branches zijn beschermd via organisatiebrede rulesets. Directe pushes zijn niet toegestaan. Elke wijziging gaat via een pull request met peer review en CI.

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘                    ↑
                                 └── (hotfix kan direct naar beta of main)
```

| Doel | Toegestane bronnen | Reviews vereist | CI vereist |
|---|---|---|---|
| `development` | `feature/*`, `bugfix/*` | 1 | Quality CI |
| `beta` | `development`, `hotfix/*` | 1 | Quality CI |
| `main` | `beta`, `hotfix/*` | 2 | Branch Protection CI |

Alle rulesets vereisen: geen force pushes, geen branch-verwijdering, stale reviews vervallen bij nieuwe pushes, alle threads opgelost voor merge.

## Kwaliteitsworkflow

Elke PR triggert geautomatiseerde kwaliteitschecks. **Alle moeten slagen voor merge.**

### PHP

| Check | Tool |
|---|---|
| Syntax | `php -l` |
| Codestijl | PHPCS (PSR-12) |
| Statische analyse | PHPStan (level 5) + Psalm |
| Mess detection | PHPMD |

### Frontend

| Check | Tool |
|---|---|
| JavaScript/Vue | ESLint |
| CSS/SCSS | Stylelint |

### Dependencies

- Licentiecontrole (npm + composer)
- Kwetsbaarheidsscan (npm audit + composer audit)

**Lokaal uitvoeren:**

```bash
# PHP
composer cs:check
composer cs:fix
composer phpstan
composer psalm
composer phpmd

# Frontend
npm run lint
npx stylelint "src/**/*.{css,scss,vue}"
```

## Commit-berichten

We gebruiken [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: proactieve servicematching toevoegen
fix: null pointer in namespace parser oplossen
docs: contributing-gids bijwerken
chore: PHPStan upgraden naar v2
refactor: classifier naar eigen klasse verplaatsen
```

- Gebruik de **imperatieve wijs** ("toevoegen" niet "toegevoegd")
- Eerste regel maximaal 72 tekens
- Verwijs naar issues met `Closes #123` in de berichttekst

## Developer Certificate of Origin (DCO)

Alle bijdragen moeten ondertekend zijn. Dit bevestigt dat je de code hebt geschreven of het recht hebt om deze in te dienen:

```bash
git commit -s -m "feat: jouw commit-bericht"
```

Dit voegt `Signed-off-by: Jouw Naam <jouw@email.com>` toe. Door te ondertekenen ga je akkoord met het [Developer Certificate of Origin](https://developercertificate.org/).

Vergeten? Wijzig je laatste commit: `git commit --amend -s`

## Releaseproces

Releases zijn volledig geautomatiseerd via GitHub Actions bij merge naar `beta` (nightly) of `main` (stable). Versienummers worden berekend op basis van PR-labels:

| Label | Effect |
|---|---|
| `major` | `1.0.0` → `2.0.0` |
| `minor` | `1.0.0` → `1.1.0` |
| `patch` (standaard) | `1.0.0` → `1.0.1` |

Zie het [Releaseproces](release-process) voor volledige details.

## Ontwikkelomgeving instellen

1. Installeer PHP 8.1+ en Node.js 20+
2. Installeer Composer
3. Clone de repository (of je fork)
4. Voer `composer install && npm install` uit
5. Stel een [Nextcloud-ontwikkelomgeving](https://github.com/ConductionNL/nextcloud-docker-dev) in

## Documentatie

De documentatiebron leeft in `website/` (deze repo) en wordt gepubliceerd op [docs.conduction.nl](https://docs.conduction.nl).

Om bij te dragen aan de docs:
1. Bewerk de relevante Markdown-bestanden onder `website/docs/`
2. Voor Nederlandse vertalingen, bewerk het bijbehorende bestand onder `website/i18n/nl/`
3. Test lokaal: `cd website && npm install && npm run start`

## Community

- [Common Ground Slack](https://commonground.nl)
- [LinkedIn](https://www.linkedin.com/company/conduction/)
- [GitHub Discussions](https://github.com/orgs/ConductionNL/discussions)

## Licentie

Door bij te dragen ga je ermee akkoord dat jouw bijdragen worden gelicenseerd onder dezelfde licentie als het project (EUPL-1.2 tenzij anders vermeld in de repository).
