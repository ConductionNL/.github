# Conduction Product Roadmap

Centraal overzicht van geplande verbeteringen en toekomstige features voor het Conduction app-ecosysteem. Items hier zijn goedgekeurd als richting maar nog niet ingepland als OpenSpec change.

## OpenRegister

| Item | Beschrijving | Status | Referentie |
|------|-------------|--------|------------|
| Setup wizards | Apps bieden bij eerste installatie de keuze: "Start met voorbeelddata" of "Start leeg". Vervangt het huidige gedrag waarbij seed data altijd geladen wordt. | Gepland | ADR-016 |
| Seed related items | ImportHandler uitbreiden zodat seed data ook bestanden, notities, taken en contacten kan aanmaken die gekoppeld zijn aan objecten via `@relations`. | In ontwerp | `openregister/openspec/changes/seed-related-items/` |

## Cross-App

| Item | Beschrijving | Status | Referentie |
|------|-------------|--------|------------|
| Seed data backfill | Bestaande apps (Pipelinq, Procest, Docudesk, Softwarecatalog, LarpingApp, ZaakAfhandelApp) voorzien van seed data in hun `_register.json` | Te doen | ADR-016 |
| Playwright E2E in CI | `enable-playwright` input in quality.yml, parallel aan Newman. Pipelinq en Procest hebben tests + test flows. | Gereed | quality.yml |
| LLM test flows per app | Elke app heeft `tests/flows/` met markdown test flows die zowel door Playwright als LLM agents gebruikt worden. | In uitvoering | Pipelinq (7 flows), Procest (4 flows) |

---

*Laatste update: 2026-03-23*
*Nieuwe items toevoegen: maak een regel in de juiste tabel. Wanneer een item als OpenSpec change wordt opgepakt, verwijs naar de change directory en update de status.*
