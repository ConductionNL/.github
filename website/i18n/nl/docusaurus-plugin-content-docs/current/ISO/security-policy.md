---
id: security-policy
title: Informatiebeveiligingsbeleid
sidebar_label: Beveiligingsbeleid
sidebar_position: 3
description: Informatiebeveiligingsbeleid van Conduction — ISO 27001:2022 §5.2
---

# Informatiebeveiligingsbeleid

## Toepassingsgebied (ISO 27001:2022 §4.3)

Dit Informatiebeveiligingsbeheersysteem heeft betrekking op **alle informatiemiddelen gerelateerd aan het ontwerp, de ontwikkeling, implementatie en ondersteuning van open-source softwareoplossingen voor de digitale overheidsinfrastructuur**, waaronder:

- Broncode en repositories op GitHub
- Klantgegevens verwerkt via software en hosting van Conduction
- Interne systemen (Google Workspace, Jira, Passwork, ontwikkelomgevingen)
- Apparaten van medewerkers (BYOD) die voor bedrijfswerk worden gebruikt

Geleverd vanuit Nederland door medewerkers en contractanten van Conduction B.V. — inclusief thuiswerkers.

## Doel

Conduction is toegewijd aan het beschermen van de vertrouwelijkheid, integriteit en beschikbaarheid van de informatie die het beheert — waaronder klantgegevens, interne systemen en de open-source software die het ontwikkelt en beheert.

Dit beleid vormt het kader voor het Informatiebeveiligingsbeheersysteem (ISMS) van Conduction conform ISO 27001:2022.

## Toepassingsgebied

Dit beleid is van toepassing op:
- Alle informatiemiddelen die eigendom zijn van of worden verwerkt door Conduction
- Alle medewerkers, contractors en derden met toegang tot Conduction-systemen
- Alle systemen, diensten en software ontwikkeld en beheerd door Conduction

## Beveiligingsdoelstellingen (ISO 27001:2022 §6.2)

| Doelstelling | Meetbaar doel | Verantwoordelijk | Evaluatie |
|---|---|---|---|
| Ongeautoriseerde toegang voorkomen | Nul ongeautoriseerde toegangsincidenten per jaar | Kwaliteits- & Veiligheidsmanager | Maandelijks (MT-kwaliteitsoverleg) |
| Systeembeschikbaarheid | Kritieke systemen ≥ 99,5% uptime | Operations Lead | Maandelijks |
| Incidentrespons | Beveiligingsincidenten bevestigd binnen 4 werkuren | Kwaliteits- & Veiligheidsmanager | Per incident |
| Kwetsbaarheidsbeheer | Kritieke/hoge CVE's gepatcht binnen 30 dagen | Development Lead | Continu (CI/CD) |
| Bewustwording medewerkers | Alle medewerkers voltooien jaarlijkse beveiligingsbewustzijnssessie | Kwaliteits- & Veiligheidsmanager | Jaarlijks |

Werkelijke prestaties worden bijgehouden in het interne monitoringsspreadsheet en besproken tijdens MT-kwaliteitsoverleggen.

## Rollen en Verantwoordelijkheden

| Rol | Verantwoordelijkheid |
|---|---|
| Management | ISMS goedkeuren en van middelen voorzien; jaarlijks herzien |
| Kwaliteits- & Veiligheidsmanager | ISMS beheren en onderhouden; audits en reviews coördineren |
| Alle medewerkers | Beveiligingsprocedures volgen; incidenten en vermoedens direct melden |
| Development Lead | Veilige ontwikkelpatronen toepassen bij alle softwareoplevering |

Zie [organisatie](../WayOfWork/organisation) voor volledige rolbeschrijvingen.

## Sleutelmaatregelen

De volgende maatregelen zijn van kracht (ISO 27001:2022 Bijlage A):

- **Toegangsbeheer** (A.5.15): Toegang tot systemen is rolgebaseerd en verleend op need-to-know basis
- **Acceptabel gebruik** (A.5.10): Bedrijfssystemen en -gegevens worden uitsluitend voor geautoriseerde doeleinden gebruikt
- **Cryptografie** (A.8.24): Gevoelige gegevens in transit en at rest zijn versleuteld
- **Leveranciersrelaties** (A.5.19): Externe leveranciers met datatoegang worden beoordeeld en contractueel gebonden
- **Incidentbeheer** (A.6.8): Alle vermoedens van incidenten moeten worden gemeld — zie [Incidentmelding](incident-reporting)
- **Bedrijfscontinuïteit** (A.5.29): Kritieke diensten hebben gedocumenteerde herstelprocedures

## Communicatie naar Medewerkers

Dit beleid wordt gecommuniceerd aan alle medewerkers via deze documentatiesite en tijdens onboarding. Van medewerkers wordt verwacht dat zij dit beleid erkennen. Vragen of opmerkingen kunnen worden gericht aan de Kwaliteits- & Veiligheidsmanager of ingediend via een [GitHub Issue](https://github.com/ConductionNL/.github/issues).

_ISO 27001:2022 referentie: §5.2 — Informatiebeveiligingsbeleid; Bijlage A.5.1_
_Laatste beoordeling: april 2026_
_Volgende beoordeling: jaarlijkse managementbeoordeling (februari 2027)_
