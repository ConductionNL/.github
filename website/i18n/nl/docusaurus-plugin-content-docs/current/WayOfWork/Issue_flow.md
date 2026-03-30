---
id: way-of-working
title: Issue Flow en Sprintplanning
sidebar_label: Werkwijze
sidebar_position: 3
description: Hoe Conduction sprints plant, issues beheert en software oplevert
---

# Issue Flow en Sprintplanning


## Epics aanmaken en inschatten

1. Maak Epics aan in Jira, gekoppeld aan specifieke doelen
   - Epics vertegenwoordigen complete functionele features
   - Elke epic levert zelfstandige bedrijfswaarde op
2. De Product Owner voert uit:
   - T-shirt sizing van epics
   - Prioriteitstelling
   - Deadline-afstemming met gerelateerde doelen

### T-shirt Sizing Referentietabel

| Grootte | Uren | Complexiteit |
|---------|------|--------------|
| XS | 1–4 | Zeer klein, eenvoudige taak |
| S | 4–8 | Kleine taak, recht-toe-recht-aan |
| M | 8–16 | Gemiddelde complexiteit |
| L | 16–32 | Grote, complexe taak |
| XL | 32–80 | Zeer groot, hoog complex |
| XXL | 80+ | Grote onderneming, opbreken nodig |

## Roadmapplanning

1. De Scrum Master maakt een initiële roadmap op basis van:
   - Epic T-shirt sizes
   - Deadlines
   - Teamcapaciteit
   - Epic prioriteiten
2. De Product Owner beoordeelt en keurt de roadmap goed

## User Story Ontwikkeling

1. Developers maken user stories voor geplande epics, begeleid door de Scrum Master
2. Issue flow:
   - Scrum Master beoordeelt stories op issuecriteria
   - Bij goedkeuring: status wordt "Ready for Development" (toegewezen aan Product Owner)
   - Product Owner beoordeelt op aansluiting bij de gewenste functionaliteit
   - Product Owner geeft feedback terug, of zet de status op "Selected for Development" en verwijdert de toewijzing

## Code Ontwikkeling

1. Developers pakken ontoegewezen issues op met status "Selected for Development"
2. Na voltooiing en merge naar de `development`-branch:
   - Status wordt "Review"
   - Tester kan testen via het beta-kanaal (merges naar `beta` triggeren een betabuild)
3. Na succesvol testen worden voltooide issues:
   - Gepresenteerd aan de Product Owner tijdens de sprintreview (vrijdag)
   - Maandagochtend gereleased naar `main` na succesvolle review (triggert een stabiele release)

### PR-labels voor Versiebeheer

Elk pull request moet worden gelabeld met `major`, `minor` of `patch` om de versieverhoging te bepalen. Zonder label is de standaard `patch`. Zie het [Releaseproces](release-process) voor uitleg over branching, versiebeheer en deployment.

## Sprint Afsluiting

1. De Scrum Master bereidt een sprintreviewvoorstel voor met:
   - Lijst van voltooide issues
   - Overzicht van onvoltooide issues
   - Aanbeveling per onvoltooid issue (aanhouden of terug naar backlog)
2. Tijdens de sprintreview (vrijdag):
   - Team beoordeelt onvoltooide issues
   - Per issue wordt besloten: aanhouden of terug naar backlog
   - Beslissingen worden genomen in lijn met roadmapprioriteiten
