---
id: about-this-manual
title: Hoe Deze Manual Werkt
sidebar_label: Over Deze Manual
sidebar_position: 99
description: Hoe het medewerkershandboek is opgezet, waar data leeft en hoe je bijdraagt
---

# Hoe Deze Manual Werkt

Dit medewerkershandboek is een [Docusaurus](https://docusaurus.io/)-site gehost op GitHub Pages. De bron leeft in de [ConductionNL/.github](https://github.com/ConductionNL/.github)-repository onder `website/`.

## Structuur

Het handboek is georganiseerd in vier thema's:

| Thema | Wat het behandelt |
|---|---|
| **Werken bij Conduction** | Onboarding, organisatie, gedragscode, vacatures |
| **Software Bouwen** | Sprints, bijdragen, releases |
| **Support & Veiligheid** | Klantenondersteuning, incidenten, beveiligingsbeleid |
| **Over Conduction** | Missie, ISO, producten |

De landingspagina ([Medewerkershandboek](/docs/intro)) geeft een compleet overzicht. Diepere pagina's werken elk onderwerp verder uit.

## Talen

De site ondersteunt Engels (standaard) en Nederlands. Engelse docs staan in `website/docs/`, Nederlandse vertalingen in `website/i18n/nl/docusaurus-plugin-content-docs/current/`.

## Gecentraliseerde data

Om te voorkomen dat waarden die veranderen (toolnamen, e-mailadressen, roosters) hardcoded in meerdere bestanden staan, gebruiken we een centraal databestand:

**`website/src/data/site-data.json`**

Dit bestand bevat:
- **`tools`** — toollijsten per categorie (onboarding, security, development)
- **`emails`** — bedrijfs-e-mailadressen (support, klachten, security, algemeen)
- **`slack`** — Slack-kanaalnamen
- **`schedule`** — standup-tijd, report-out-tijd, ziekmelddeadline, sprintlengte
- **`links`** — URLs van externe tools (Passwork, NordLayer, ESET)

Pagina's refereren naar deze data via React-componenten:

```jsx
import ToolList from '@site/src/components/ToolList';
import {Val, Email} from '@site/src/components/SiteData';

// Rendert: "Google Workspace, GitHub, Jira, Slack, Passwork"
<ToolList category="onboarding" />

// Rendert: "10:00"
<Val path="schedule.standup" />

// Rendert: een mailto-link
<Email path="emails.support" />
```

**Als een tool, e-mailadres of rooster verandert — pas `site-data.json` eenmaal aan. Alle pagina's updaten automatisch.**

## Gesynchroniseerde bestanden

Drie bestanden in de repo-root worden gespiegeld als docs-pagina's:

| Repo root | Docs-pagina |
|---|---|
| `CONTRIBUTING.md` | `docs/WayOfWork/contributing.md` |
| `SECURITY.md` | `docs/ISO/security.md` |
| `CODE_OF_CONDUCT.md` | `docs/WayOfWork/code-of-conduct.md` |

Een CI-workflow (`.github/workflows/docs-sync-check.yml`) checkt bij elke PR of deze bestanden nog in sync zijn. Bij afwijkingen geeft de workflow een waarschuwing.

## Hoe bijdragen

1. Maak een branch aan vanaf `development`
2. Bewerk markdown-bestanden onder `website/docs/` (Engels) of `website/i18n/nl/` (Nederlands)
3. Test lokaal: `cd website && npm install && npm run start`
4. Open een PR

Zie de [Contributing guide](contributing) voor details.
