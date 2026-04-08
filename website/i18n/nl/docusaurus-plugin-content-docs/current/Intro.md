---
id: intro
title: "HowWeWork@Conduction"
sidebar_label: Medewerkershandboek
sidebar_position: 1
description: Het medewerkershandboek van Conduction — hoe we werken, wat we verwachten en waar je alles vindt
---

import ToolList from '@site/src/components/ToolList';
import {Val, Email} from '@site/src/components/SiteData';

# HowWeWork@Conduction

Het medewerkershandboek — wijzigingen? Submit een PR op [GitHub](https://github.com/ConductionNL/.github).

## Wie we zijn

Conduction helpt goede ideeen tot leven brengen. We werken democratisch, inclusief en transparant — niet als bedrijfswaarden op papier, maar als manier van werken. Ons doel: **in 2035 zorgt Conduction ervoor dat alle inwoners van Nederland automatisch de overheidsdiensten ontvangen waar ze recht op hebben.**

**Meer lezen:** [Onze missie & waarden](WayOfWork/way-of-work)

## Werken bij Conduction

**Je eerste dagen** — je krijgt een buddy: een ervaren collega die je door de onboarding begeleidt. Ze helpen je met toegang (<ToolList category="onboarding" />), je machine inrichten en je weg vinden. Schroom niet om te vragen — daar zijn ze voor.

**Werkritme** — we werken in <Val path="schedule.sprintLength" /> sprints. Standup om <Val path="schedule.standup" />, report-out om <Val path="schedule.reportOut" /> (in Slack <Val path="slack.general" />, bij code-werk altijd met een commit link). Prioriteiten komen van de Product Owner, inhoudelijke vragen gaan naar de dev lead.

**Verlof & ziekte** — vakantie minimaal <Val path="schedule.vacationNotice" /> van tevoren aanvragen via het HR-portaal en bespreken in **<Val path="slack.vacation" />**. Ziek? Bel HR voor <Val path="schedule.sickCallBefore" />. Te laat? Even een berichtje — twee keer per maand trakteer je op taart, de derde keer volgt een gesprek met HR.

**Spelregels** — behandel elkaar met respect. Praat *met* elkaar, niet *over* elkaar. Discriminatie, intimidatie of pesten wordt nooit geaccepteerd.

**Meer lezen:**
- [Onboarding & buddy systeem](WayOfWork/onboarding)
- [Organisatie](WayOfWork/organisation) — rollen, teams, structuur
- [Vacatures](WayOfWork/vacancies)
- [Code of Conduct(ion)](WayOfWork/code-of-conduct)

## Software bouwen

**Wat we bouwen** — open-source componenten voor de digitale overheidsinfrastructuur, gebouwd op Common Ground principes. Onze code leeft op [GitHub](https://github.com/ConductionNL).

**Hoe we bouwen** — werk bestaat uit issues. Schrijf ze zo dat een collega ze kan oppakken zonder extra uitleg. Vier-ogen-principe op alle code. Nooit API keys pushen. Tooling setup? Vraag je buddy.

**Projecten** — elk project start met een kick-off. Niet gehad? Vraag erom — ga nooit op aannames werken.

> *Assumption is the mother of all fuckups.*

Scope, budget en planning liggen vast in de offerte. Alles daarbuiten: bespreek eerst met je leidinggevende.

**Uren schrijven** — log uren in Tempo, altijd op een issue met het juiste account. Weet je niet hoe? Gewoon vragen.

**Meer lezen:**
- [Spec-driven development](WayOfWork/spec-driven-development) — OpenSpec, Claude Code, de vierfasen-pipeline
- [Ontwikkelstraat](WayOfWork/development-pipeline) — kwaliteitspoorten, securitychecks, geautomatiseerde releases
- [Werkwijze](WayOfWork/way-of-working) — sprints, issue flow, story points
- [Contributing guide](WayOfWork/contributing) — codestandaarden, branching, reviews
- [Release process](WayOfWork/release-process) — branchmodel, versiebeheer, deployment

## Support & veiligheid

**Klanten helpen** — support loopt via **<Email path="emails.support" />** (maakt automatisch een Jira-ticket). Snelle fix onder 5 minuten? Gewoon oplossen. Langer? Maak een issue. Klachten gaan naar **<Email path="emails.complaints" />**.

**Elkaar helpen** — ergens vastgelopen? Flag het als impediment, post in Slack met een link naar het issue, en breng het in bij de standup. Je buddy is je eerste aanspreekpunt.

**Incidenten** — herken je een beveiligings- of kwaliteitsincident? Overleg direct met je leidinggevende. Flag of maak een issue met het label "security incident" of "quality incident". Schrijf achteraf een memo met root cause analysis. Onthoud: **identificeer het risico -> beoordeel het risico -> beperk het risico -> herzie de maatregelen.**

**Security** — toegang via je Conduction Google-account, inloggegevens in Passwork. Behandel gevoelige data als je naaktfoto's — deel alleen met wie het nodig heeft. Nooit gevoelige data via Slack of mail. VPN voor kritieke servers. ESET altijd geactiveerd.

**Meer lezen:**
- [Klantenondersteuning](WayOfWork/customer-support) — supportproces en klachten
- [Incidentmelding](ISO/incident-reporting) — procedures en templates
- [Beveiligingsbeleid](ISO/security) — wachtwoorden, clean desk, BYOD, VPN, antivirus
- [Privacy & AVG](ISO/privacy-policy) — persoonsgegevens, AVG, rechten van betrokkenen

## Meer weten?

Voor wie het complete plaatje wil:

- [Missie & waarden](WayOfWork/way-of-work) — wie we zijn, wat ons drijft, KPI's
- [ISO & Kwaliteit](ISO/iso-intro) — ons certificeringstraject (ISO 9001 & 27001)
- [Producten & Diensten](Products/products-overview) — wat we bieden
- [Hoe deze manual werkt](WayOfWork/about-this-manual) — structuur, databronnen en hoe bij te dragen
