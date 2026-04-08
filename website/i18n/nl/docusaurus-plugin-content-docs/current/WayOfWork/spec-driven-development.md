---
id: spec-driven-development
title: Spec-Driven Development
sidebar_label: Spec-Driven Development
sidebar_position: 2
description: Hoe Conduction OpenSpec en Claude Code gebruikt om van idee naar implementatie te gaan
---

# Spec-Driven Development

Bij Conduction beginnen we niet met coderen voordat we weten wat we bouwen. We gebruiken een **spec-driven workflow** waarbij elke wijziging als gestructureerde artefacten wordt gedefinieerd voor de implementatie begint. Specs leven naast de code en blijven bewaard over sessies heen — continuiteit en traceerbaarheid gegarandeerd.

## De Pipeline

Alle ontwikkeling volgt vier fasen:

| Fase | Wat er gebeurt | Output |
|---|---|---|
| **1. Obtain** | Requirements verzamelen — uit issues, aanbestedingen, app-onderzoek, documentatie | Begrip van wat te bouwen |
| **2. Specify** | Gestructureerde specs schrijven die de wijziging definiëren | proposal.md → specs.md → design.md → tasks.md → GitHub Issues |
| **3. Build** | Implementeren door componenten, schema's en workflows samen te stellen | Werkende software |
| **4. Validate** | Kwaliteit verifiëren, tests draaien, checken tegen specs | Vertrouwen om te shippen |

## OpenSpec

OpenSpec is ons specificatieformaat. Elke wijziging levert een keten van artefacten op:

```
proposal.md ──► specs.md ──► design.md ──► tasks.md ──► GitHub Issues
```

- **Proposal** — wat en waarom (probleemstelling, scope, stakeholders)
- **Specs** — gedetailleerde eisen met GIVEN/WHEN/THEN acceptatiecriteria
- **Design** — technische aanpak, componentselectie, datamodel
- **Tasks** — opgesplitst in implementeerbare eenheden
- **Issues** — taken worden traceerbare GitHub Issues met een epic

Organisatiebrede specs (test coverage baselines, API-patronen, NL Design System compliance, i18n-eisen) staan in de [`openspec/`](https://github.com/ConductionNL/.github/tree/main/openspec)-directory van deze repository. Individuele apps breiden deze uit met app-specifieke specs.

## Claude Code

We gebruiken [Claude Code](https://docs.anthropic.com/en/docs/claude-code) als onze ontwikkelorchestrator. Claude fungeert als **architect en samensteller** — het definieert, configureert en valideert, maar delegeert de implementatie aan de bouwblokken van het platform:

| Laag | Tool | Wat Claude doet |
|---|---|---|
| **Frontend** | `@conduction/nextcloud-vue` | Componenten selecteren en configureren, views en routing definiëren |
| **Backend data** | OpenRegister | Schema's, registers, objectstructuren en validatieregels definiëren |
| **Backend logica** | n8n workflows | Workflowlogica ontwerpen, triggers configureren, data mappen |

Een gedeelde configuratie-repository ([`claude-code-config`](https://github.com/ConductionNL/claude-code-config)) levert alle commando's, skills en workflow-instructies. Het wordt als git submodule toegevoegd op `.claude/` in elke app-repository.

## Belangrijkste Commando's

| Commando | Fase | Doel |
|---|---|---|
| `/opsx-explore` | Obtain | Een onderwerp of probleem onderzoeken |
| `/opsx-new` | Specify | Een nieuwe wijziging starten met een voorstel |
| `/opsx-ff` | Specify | Alle spec-artefacten in één keer genereren |
| `/opsx-plan-to-issues` | Specify | Taken omzetten naar GitHub Issues |
| `/opsx-apply` | Build | Taken uit de specs implementeren |
| `/opsx-verify` | Validate | Implementatie checken tegen specs |
| `/opsx-archive` | Done | Voltooide wijziging archiveren |
