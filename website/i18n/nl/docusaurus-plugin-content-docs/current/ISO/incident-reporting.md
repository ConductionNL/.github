---
id: incident-reporting
title: Incidentmelding
sidebar_label: Incidentmelding
sidebar_position: 4
description: Hoe je beveiligingsincidenten en kwaliteitsafwijkingen meldt bij Conduction
---

# Incidentmelding

Conduction heeft de plicht om incidenten te detecteren, te melden en ervan te leren — zowel beveiligingsincidenten (ISO 27001:2022 A.6.8) als kwaliteitsafwijkingen (ISO 9001:2015 §10.2).

**Vermoed je dat er iets mis is? Meld het direct. Er is geen straf voor melden te goeder trouw.**

## Classificatie

We onderscheiden drie typen bevindingen, elk met een eigen procedure:

| Type | Wat is het | Voorbeelden | Procedure |
|---|---|---|---|
| **Incident** | Onverwachte gebeurtenis met directe impact op continuïteit, veiligheid of kwaliteit | Systeemstoring, ongeautoriseerde toegang, datalek, defecte productiedeployment | Registreren, impactanalyse, direct oplossen, evalueren |
| **Afwijking** | Niet-naleving van een standaard zonder directe impact | Ontwikkelprocedure niet volledig gevolgd, document verkeerd opgeslagen, teststap overgeslagen | Registreren, analyseren of structureel, corrigerende/preventieve maatregel indien nodig |
| **Tekortkoming** | Structurele of ernstige afwijking die compliance, certificering of wettelijke verplichtingen raakt | Beveiligingsprotocol structureel niet gevolgd, audit onthult ontbrekende maatregelen, contractuele verplichting geschonden | Registreren, oorzaakanalyse, verbeterplan, effectiviteit monitoren |

## Wat Te Melden

### Beveiligingsincidenten (ISO 27001:2022 A.6.8)

Meld elk vermoeden of bevestiging van:

- Ongeautoriseerde toegang tot systemen, accounts of gegevens
- Datalek of gegevensverlies (klantgegevens, medewerkergegevens, inloggegevens)
- Malware, phishing of social engineering pogingen
- Blootstelling van geheimen, API-sleutels of inloggegevens (bijv. per ongeluk in Git geplaatst)
- Verlies of diefstal van een apparaat met toegang tot bedrijfssystemen
- Ongewone of verdachte activiteit op een bedrijfsaccount of -systeem

### Kwaliteitsafwijkingen / Bijna-Ongelukken (ISO 9001:2015 §10.2)

Meld elk geval van:

- Opgeleverde software die niet voldeed aan overeengekomen eisen
- Procesfout die tot klantimpact had kunnen leiden
- Bijna-ongeluk: iets dat mis had kunnen gaan maar gelukkig niet is misgegaan

## Hoe Te Melden

**Maak of flag een issue in Jira** en label het als **`security-incident`** of **`quality-incident`**. Dit is de enige juiste manier om een incident te melden.

Weet je niet hoe? Vraag een teamlid, je leidinggevende of iemand van het management — zij helpen je het issue aan te maken.

Het labelen van een issue als incident triggert automatisch een Slack-flow die vraagt om een **root cause analysis template** in te vullen.

**Verwachte reactietijd:**
- Beveiligingsincidenten: bevestigd binnen **4 werkuren**
- Kwaliteitsafwijkingen: bevestigd binnen **1 werkdag**

## Wat Er Na Je Melding Gebeurt

1. De Kwaliteits- & Veiligheidsmanager bevestigt de melding
2. Ernst wordt bepaald (kritiek / hoog / gemiddeld / laag)
3. Zo nodig worden inperkingsacties genomen
4. Oorzaak wordt onderzocht
5. Corrigerende maatregel wordt gedocumenteerd en gevolgd tot afsluiting
6. Lessen worden gedeeld met het team

## Jouw Verantwoordelijkheden

- Meld incidenten **zodra je ze ontdekt** — vertraging vergroot de impact
- Probeer een beveiligingsincident niet zelf te onderzoeken of op te lossen voordat je het hebt gemeld
- Bewaar bewijsmateriaal (logbestanden, screenshots) indien mogelijk
- Werk mee aan het onderzoek

_ISO 27001:2022 referentie: A.6.8 — Melden van informatiebeveiligingsgebeurtenissen_
_ISO 9001:2015 referentie: §10.2 — Afwijking en corrigerende maatregel_
