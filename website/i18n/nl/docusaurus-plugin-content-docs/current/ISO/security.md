---
id: security
title: Beveiligingsbeleid
sidebar_label: Beveiligingsbeleid
sidebar_position: 5
description: Hoe je kwetsbaarheden meldt, onze responstijden en safe harbor-verklaring
---

# Beveiligingsbeleid

Dit beveiligingsbeleid geldt voor alle repositories onder de [ConductionNL](https://github.com/ConductionNL)-organisatie.

## Een Kwetsbaarheid Melden

**Maak GEEN openbaar GitHub-issue aan voor beveiligingskwetsbaarheden.**

### 1. GitHub Private Vulnerability Reporting (voorkeur)

Gebruik de ingebouwde privémeldingsfunctie van GitHub direct in de betreffende repository:

> **Repository → Security-tabblad → "Report a vulnerability"**

Dit maakt een end-to-end versleuteld beveiligingsadvies aan, zichtbaar alleen voor beheerders.

### 2. E-mail

Stuur je melding naar **security@conduction.nl**. Voor gevoelige communicatie kun je onze PGP-sleutel opvragen per e-mail.

## Wat te Vermelden

- **Beschrijving** — wat is kwetsbaar en waarom
- **Reproductiestappen** — minimale stappen om het probleem te triggeren
- **Impact** — wat een aanvaller zou kunnen bereiken
- **Getroffen versies** — welke releases zijn getroffen
- **Suggestie voor oplossing** — optioneel, maar welkom

## Responstijden

| Mijlpaal | Streefdatum |
|---|---|
| Bevestiging | Binnen **48 uur** |
| Initiële beoordeling en ernst | Binnen **5 werkdagen** |
| Fix voor kritiek / hoog | Binnen **30 dagen** |
| Fix voor gemiddeld | Binnen **90 dagen** |
| Publieke bekendmaking | Na release van de fix, of na **90 dagen** vanaf melding |

## Ernsttyclassificatie

We gebruiken [CVSSv3](https://www.first.org/cvss/calculator/3.1):

| Ernst | CVSS-score | Respons |
|---|---|---|
| **Kritiek** | 9,0–10,0 | Fix binnen 14 dagen |
| **Hoog** | 7,0–8,9 | Fix binnen 30 dagen |
| **Gemiddeld** | 4,0–6,9 | Fix binnen 90 dagen |
| **Laag** | 0,1–3,9 | Opgelost in volgende geplande release |

## Toepassingsgebied

### Binnen scope

- Alle broncode onder [github.com/ConductionNL](https://github.com/ConductionNL)
- API's en integraties van onze apps
- Authenticatie- en autorisatielogica
- Gegevensverwerking en privacycontroles
- Dependencies met bekende CVE's die nog niet gepatcht zijn

### Buiten scope

- Kwetsbaarheden in Nextcloud core → meld bij [Nextcloud](https://nextcloud.com/security/)
- Kwetsbaarheden in externe dependencies → meld eerst upstream
- Social engineering of phishing tegen Conduction-medewerkers
- Fysieke beveiliging
- Problemen die onwaarschijnlijk of onrealistisch gebruikersgedrag vereisen
- Denial-of-service-aanvallen op gehoste infrastructuur
- Reeds publiek bekende problemen

## Ondersteunde Versies

We leveren beveiligingsupdates voor de **laatste stabiele release** van elke app. Oudere versies ontvangen geen beveiligingspatches tenzij expliciet vermeld in de repository.

## Safe Harbor

Conduction zal geen juridische stappen ondernemen tegen beveiligingsonderzoekers die:

- Kwetsbaarheden te goeder trouw via dit beleid melden
- Geen gegevens inzien, wijzigen of verwijderen verder dan nodig om de kwetsbaarheid aan te tonen
- Productiediensten niet verstoren of gebruikerservaring niet verslechteren
- De kwetsbaarheid niet exploiteren verder dan nodig om het bestaan ervan te bevestigen
- Ons redelijke tijd geven om het probleem op te lossen voor publieke bekendmaking

We beschouwen beveiligingsonderzoek te goeder trouw als een publiek goed en werken liever met je samen dan tegen je.

## Bug Bounty

Conduction heeft momenteel geen betaald bug bounty-programma. Geldige meldingen ontvangen:

- Publieke vermelding in release notes (met toestemming)
- Erkenning in het GitHub Security Advisory

## Interne Incidentmelding

Conduction-medewerkers: zie de [Incidentmelding](incident-reporting)-procedure voor het melden van beveiligingsincidenten en kwaliteitsafwijkingen.

## Beveiligingspraktijken voor Medewerkers

De onderstaande secties gelden voor alle medewerkers van Conduction.

### Wachtwoorden

Alle Conduction-wachtwoorden moeten minimaal **10 tekens** bevatten en bestaan uit:

- Een letter
- Een cijfer
- Een speciaal teken

Sla alle inloggegevens op in [Passwork](https://www.passwork.me/). Deel wachtwoorden nooit via Slack, e-mail of andere communicatiekanalen.

### Omgang met Data

- Sla nooit persoonlijke of vertrouwelijke data van Conduction of klanten lokaal op
- Push nooit API keys of omgevingsvariabelen naar GitHub
- Deel bestanden alleen via Google Drive of Passwork — nooit via USB, e-mail of Slack
- Als je gevoelige data lokaal moet opslaan, versleutel met **BitLocker**
- Gedownloade documenten met privacygevoelige data moeten binnen **5 dagen** van je laptop verwijderd worden

### Clean Desk & Clear Screen

- Vergrendel altijd je apparaat als je wegloopt — ook voor koffie
- Laat je apparaat nooit onbeheerd achter
- Berg je apparaat op in een locker aan het einde van de dag, of neem het mee
- Laat geen notities, printjes of randapparatuur rondslingeren

### Bring Your Own Device (BYOD)

Je kiest zelf je ontwikkelmachine. De enige eisen:

1. Het kan de vereiste lokale tooling draaien
2. Het voldoet aan de beveiligingseisen op deze pagina (antivirus, encryptie, VPN)

### VPN

Thuiswerken — zeker met gevoelige data — vereist een VPN-verbinding.

- [NordLayer VPN](https://nordlayer.com/) — installeer en activeer bij thuiswerken
- Twijfel je of je het nodig hebt? Vraag je teamlead

### Antivirus

ESET moet op alle apparaten voor Conduction-werk altijd geactiveerd zijn. Vraag een uitzondering aan bij je teamlead indien nodig.

- [ESET Business Edition — installatie en downloads](https://www.eset.com/int/business/)
- Neem contact op met IT voor je licentiesleutel en 2FA-instelling

### AI Tooling (Claude Code)

We gebruiken Claude Code voor development. AI-tooling erft de rechten van de gebruikerssessie waarin het draait. De volgende maatregelen zijn verplicht (gebaseerd op gedocumenteerde afwijking ISO-723):

- **Gescheiden accounts** — Claude Code moet een dedicated GitHub-account gebruiken met standaard developer-rechten. Gebruik nooit een admin-account in dezelfde sessie als Claude Code
- **Git-restricties** — `settings.json` moet Git-operaties beperken: Claude mag alleen pushen naar `feature/*`-branches. Direct pushen naar `development`, `beta` of `main` is geblokkeerd
- **Vier-ogenprincipe geldt** — alle door AI geproduceerde code is onderworpen aan dezelfde peer review-eisen als door mensen geschreven code. Geen uitzonderingen
- **Geen bypass van branchbeveiliging** — zelfs als je account admin-rechten heeft, mag Claude branchbeveiligingen niet kunnen omzeilen

Deze maatregelen worden afgedwongen via de gedeelde [`claude-code-config`](https://github.com/ConductionNL/claude-code-config)-repository (toegevoegd als `.claude/`-submodule in elke app).

_ISO 27001:2022 referentie: A.8.2 — Geprivilegieerde toegangsrechten_
