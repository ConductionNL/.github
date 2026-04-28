# Conduction app-architectuur — zes component-cards rondom Nextcloud-kernel

> **Update 2026-04-28** — Architecturele reframe: weg van "vier lagen" naar **zes component-cards rondom de Nextcloud-kernel**, in lijn met Honeycomb's pattern. Strategische narrative: ConNext is Conduction's propositie die Nextcloud doorontwikkelt van *office suite* naar *workspace*. Onderstaande tekst beschrijft nog de oude 4-laag-versie; volledige doc-rewrite naar 6-component volgt zodra alle openstaande beslissingen (NLDesign-placement, App Builder pills, etc.) zijn bevestigd.
>
> **Korte definitieve mapping (canoniek per 2026-04-28):**
>
> | Component-card | Pills |
> |---|---|
> | **Nextcloud-kernel** *(centraal)* | Files · Mail · Calendar · Contacts · Talk · Office · Apps & SSO |
> | **Technical Core** | OpenRegister (data) · OpenConnector (integratie) · DocuDesk (documenten) · **NLDesign Theme** (theming) · **MyDash** (dashboards) |
> | **Workplace App** | OpenCatalogi · PipelinQ · Procest · ZaakAfhandelApp · DeciDesk · ShillinQ · LarpingApp · OpenWoo · SoftwareCatalog |
>
> **NLDesign — twee dingen, niet verwarren:** *NLDesign-de-design-system* (NL Design System tokens, accessibility) is identiteits-overlay over alles, **geen** component-card. *NLDesign Theme app* is wél een component (in Workplace App), een echte Conduction-app voor theming/customization van je Nextcloud-instance.
> | **AI** | Automation · Agents · Intelligence |
> | **Integrated Apps** | OpenTalk · Matrix · n8n · OpenProject · XWiki · GitLab · Mattermost |
> | **App Builder** *(Coming soon)* | `Build your own` · `Customize ConNext apps` · `No code, just configure` |
>
> **App Builder strategische narrative:** een UI die de Technical Core gebruikt om klanten zelf (mini) Nextcloud-apps te laten bouwen of ConNext-apps te customizen. Tagline: *"The client is always right — and now they have the tools to make it true."*
> | **Admin Tools** *(gedempt)* | App-versions · Crontab |
> | **Side-box links** | BAG · BRK · PDOK · BRP · KvK · DSO + Nextcloud-Files / -Contacts |
>
> ---

Hoe alle Conduction-apps in elkaar passen, in vier duidelijke lagen. Deze indeling vervangt de ad-hoc 6-categorie-mapping die eerder in [`visual-motifs.md`](./visual-motifs.md) stond, en is de canonieke architectuur die we hanteren in alle communicatie (homepage-hero, app-detail-pagina's, About, presentaties, drukwerk).

## De vier lagen

```
                     ┌─────────────────────────────────────┐
                     │           Implementations           │  ← User-facing apps voor concrete use cases
                     │    (OpenCatalogi, PipelinQ, …)      │
                     └─────────────────┬───────────────────┘
                                       │ gebruiken
                     ┌─────────────────▼───────────────────┐
                     │              Core                   │  ← De gedeelde fundering
                     │  (OpenRegister, OpenConnector,      │
                     │   DocuDesk)                         │
                     └─────────────────┬───────────────────┘
                                       │ leunen op
        ┌──────────────────────────────┼─────────────────────────────────┐
        ▼                                                                ▼
┌──────────────┐                                                ┌──────────────┐
│ Extra apps   │                                                │ Integrations │
│ (OpenTalk,   │                                                │ (Nextcloud   │
│  Matrix, n8n)│                                                │  Mail, Cal,  │
└──────────────┘                                                │  OpenProject,│
                                                                │  XWiki, BAG, │
                                                                │  BRK, PDOK)  │
                                                                └──────────────┘
```

## Laag 1 — **Core** (de fundering)

Drie apps die door alle andere apps gebruikt worden. Wie een Implementation gebruikt, gebruikt **automatisch** ook de Core. Dit is de gedeelde gereedschaps-laag.

| App | Verantwoordelijkheid | Wat het levert aan Implementations |
|---|---|---|
| **OpenRegister** | Data-foundation: schema-beheer, object-opslag, audit-trail | "Sla iets op met een schema" |
| **OpenConnector** | Integration-gateway: API-koppelingen, transformaties, webhook-fan-out | "Praat met dat externe systeem" |
| **DocuDesk** | Documents: generatie, anonimisering, sjablonen, signing | "Maak / bewerk een document" |

**Visuele behandeling op de homepage-hero**: drie hex-prisms in het centrum van het diagram, samen één centrale cluster. Cobalt-dominant. Iconisch — dit zijn de drie pijlers die alles dragen.

## Laag 2 — **Implementations** (de oplossingen)

Apps die gebouwd zijn **op** de Core en specifieke use-cases oplossen. Dit zijn de apps die eindgebruikers daadwerkelijk openen en waar ze klikken. Elke Implementation is een "applicatie van een vraagstuk".

| App | Categorie / use-case | Leunt op (Core) |
|---|---|---|
| **OpenCatalogi** | Federated data-catalogus, publicatie, harvester, WOO | OpenRegister + OpenConnector + DocuDesk |
| **PipelinQ** | CRM, contacts, accounts, quotations | OpenRegister + OpenConnector |
| **ZaakAfhandelApp** | Citizen-facing case-status portal | OpenRegister + OpenConnector |
| **Procest** | Case-management, VTH, formulieren | OpenRegister + OpenConnector |
| **MyDash** | Dashboard-builder, access-control, workflow-automation | OpenRegister + OpenConnector |
| **SoftwareCatalog** | IT-asset-management, software-inventory, contracts | OpenRegister + OpenConnector + DocuDesk |
| **LarpingApp** | Worldbuilding, campaign-management voor LARP | OpenRegister |
| **DeciDesk** | Decision-support, voting, board-management | OpenRegister + DocuDesk |
| **ShillinQ** | ERP-functionaliteit (boekhouding, facturatie) | OpenRegister + OpenConnector + DocuDesk |
| **OpenWoo** | WOO-publicatieflow (kan deels overlappen met OpenCatalogi) | OpenRegister + DocuDesk |
| **NLDesign** *[?]* | NL Design System theming voor Conduction-stack | Geen directe core-afhankelijkheid — eerder een styling-overlay over alle apps |

**Apps in groei / status onbekend** (uit DB-slug-lijst, maar onduidelijk of ze gepland of actief zijn):
*AssetDesk, BudgetQ, CareDesk, ContractDesk, EduDesk, FormulierenApp, ForumDesk, GoviQ, GovScanner, LearniQ, PlaniQ* — bevestigen welke hier thuishoren.

**Visuele behandeling op de homepage-hero**: ring van hex-prisms rondom de Core. Elk een eigen pastel-tint (per categorie of per app), iconisch met app-logo en pill-labels voor sub-features. Wanneer een gebruiker hovert komt die hex naar voren (zie [`honeycomb-teardown.md §6.5`](./honeycomb-teardown.md) — de spotlight-techniek).

## Laag 3 — **Extra apps** (uitbreiding van het ecosysteem)

Apps die het ecosysteem **uitbreiden** met functionaliteit die niet primair Conduction's verantwoordelijkheid is, maar die we wel verspreiden / aanbevelen / packagen voor klanten. Veelal open-source-apps van anderen die we in de stack opnemen.

| App | Wat het toevoegt | Bron |
|---|---|---|
| **OpenTalk** | Video-conferencing (alternatief voor Zoom/Teams) | OpenTalk.eu — extern open-source |
| **Matrix** | Federated chat, messaging | matrix.org — extern open-source |
| **n8n** | Workflow-automation, no-code-flows | n8n.io — extern open-source |

**Mogelijk later toe te voegen** (open vraag): NextcloudOffice / Collabora als extra app, ook al is het Nextcloud-native? Bevestigen.

**Visuele behandeling**: kleinere hex-tegels, off-center geplaatst t.o.v. de Core+Implementations cluster. Eigen pastel-paletje (bv. teal of grijs). Aangegeven met een visuele "afstand" — ze zijn eromheen, niet erin.

## Laag 4 — **Integrations** (waarmee we koppelen)

Externe systemen waarmee Conduction-apps samenwerken via OpenConnector. Geen Conduction-product, maar wel essentieel voor het verhaal "hoe werkt onze stack in jouw bestaande omgeving".

### 4a. Nextcloud-platform-integraties

Conduction draait IN Nextcloud, dus alle Nextcloud-functies zijn inherent beschikbaar:

| Functie | Hoe Conduction het gebruikt |
|---|---|
| **Nextcloud Mail** | E-mail integratie via OpenConnector; notificaties uit apps |
| **Nextcloud Calendar** | Agenda's, afspraken in zaken/projects |
| **Nextcloud Files** | Document-storage substraat voor DocuDesk |
| **Nextcloud Talk** | Chat/calls binnen apps (alternatief voor Matrix) |
| **Nextcloud Office (Collabora)** | Document-bewerken in browser |
| **Nextcloud Contacts** | Contactgegevens-bron voor PipelinQ etc. |

### 4b. Externe productivity-platforms

Open-source-tools die we ondersteunen via OpenConnector-integraties:

| Platform | Typische rol |
|---|---|
| **OpenProject** | Project-management |
| **XWiki** | Wiki / kennisbank |
| **GitLab** / **Gitea** | Source-control voor dev-teams |
| **Mattermost** | Alternative chat (naast Matrix/Talk) |

### 4c. Nederlandse overheids-bron-systemen

Voor onze gov-doelgroep direct relevant; via OpenConnector aan de "input"-kant van de architectuur:

| Bron | Wat het levert |
|---|---|
| **BAG** (Basisregistratie Adressen en Gebouwen) | Adressen, gebouwen |
| **BRK** (Basisregistratie Kadaster) | Eigendoms-data |
| **PDOK** | Geo-data, kaarten |
| **Basisregistratie Personen (BRP)** | Personen-data |
| **Handelsregister (KvK)** | Bedrijven-data |
| **DSO** (Digitaal Stelsel Omgevingswet) | Omgevings-data |

**Visuele behandeling op de homepage-hero**: twee externe rechthoeken — links "Bron-systemen" (BAG/BRK/PDOK + Nextcloud-storage), rechts "Output-integraties" (Nextcloud Mail/Cal, OpenProject, XWiki, …). Stippeltjes-flow-lijnen tonen data-flow van links naar Core, en van Core naar rechts. Net zoals Honeycomb's "Your Data Sources" / "60+ Integrations" boxes.

## De **complete** Honeycomb-style mapping voor de homepage-hero

Met alle vier de lagen, hier is hoe het diagram er uit moet zien:

```
┌──────────────────┐                                                          ┌──────────────────┐
│  BRON-SYSTEMEN   │                                                          │   INTEGRATIONS   │
│                  │                                                          │                  │
│  Nextcloud       │ ╌╌╌╌╌╌╌╌╌╌╌╌▶  ┌─────────────────────────────┐  ╌╌╌╌╌╌╌▶ │  Nextcloud Mail  │
│  storage         │                │           CORE              │           │  Nextcloud Cal   │
│  BAG  · BRK      │                │  ┌─────────┐ ┌─────────┐    │           │  OpenProject     │
│  PDOK · BRP      │ ╌╌╌╌╌╌╌╌╌╌╌╌▶  │  │OpenReg- │ │OpenConn-│    │  ╌╌╌╌╌╌╌▶ │  XWiki           │
│  KvK  · DSO      │                │  │ister    │ │ector    │    │           │  GitLab          │
│                  │                │  └─────────┘ └─────────┘    │           │  Mattermost      │
└──────────────────┘                │       ┌─────────┐           │           │                  │
                                    │       │DocuDesk │           │           └──────────────────┘
                                    │       └─────────┘           │
                                    └──────────────┬──────────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          ▼                        ▼                        ▼
                   ┌─────────────┐         ┌─────────────┐          ┌─────────────┐
                   │ IMPLEMENTA- │         │ IMPLEMENTA- │          │ IMPLEMENTA- │
                   │   TIONS     │         │   TIONS     │          │   TIONS     │
                   │             │         │             │          │             │
                   │OpenCatalogi │         │   PipelinQ  │          │ ZaakAfhand- │
                   │  WOO, harv- │         │  CRM, quote │          │  elApp      │
                   │  ester      │         │             │          │  Mijn Zaken │
                   └─────────────┘         └─────────────┘          └─────────────┘

                   ┌─────────────┐         ┌─────────────┐          ┌─────────────┐
                   │   Procest   │         │   MyDash    │          │ SoftwareCat │
                   │  zaaksysteem│         │  dashboards │          │ ITAM        │
                   │  VTH        │         │             │          │             │
                   └─────────────┘         └─────────────┘          └─────────────┘

                   ┌─────────────┐         ┌─────────────┐          ┌─────────────┐
                   │   DeciDesk  │         │   ShillinQ  │          │ LarpingApp  │
                   │  besluit-   │         │  ERP        │          │  worldbld.  │
                   │  vorming    │         │             │          │             │
                   └─────────────┘         └─────────────┘          └─────────────┘

                                ┌─────────────────────────────────┐
                                │         EXTRA APPS              │
                                │                                 │
                                │  OpenTalk   ·  Matrix  ·  n8n   │
                                │  video         chat    automate │
                                └─────────────────────────────────┘
```

## Wat dit betekent voor de website

### Homepage-hero

De [`scène 1` in illustration-batch-1.md](./illustration-batch-1.md#sc%C3%A8ne-1-homepage-hero--platform-overview) wordt geüpdatet om deze 4-laagse architectuur te reflecteren in plaats van de eerder geplande 6-categorie-grouping.

### Apps-catalogus (`/apps`)

Filter-categorieën op de catalogus-pagina worden:

- **Core** (3 apps)
- **Implementations** (~9–15 apps; precies aantal afhankelijk van wat er live is)
- **Extra apps** (~3 apps)
- **Toon ook integraties** als sub-filter (toont waarmee elke Implementation kan koppelen)

Plus secundaire filters:

- **Status**: stable / beta / experimental
- **Solution**: WOO / registers / zaakafhandeling / etc. (cross-cutting, een Implementation kan voor meerdere solutions relevant zijn)
- **NLDS-compliant**: ja / nee

### App-detail-pagina

Op elke app-pagina (sectie "Where this fits"):

- **Core-apps tonen**: "Deze 3 apps gebruiken jou" → links naar Implementations die op deze Core leunen
- **Implementations tonen**: "Deze app leunt op Core: OpenRegister + OpenConnector" + "Integreert met: …"
- **Extra apps tonen**: "Deze app werkt naast Conduction-core; geen directe afhankelijkheid"

### Solution-pagina (bv. WOO-compliance)

De "stack-diagram" per solution wordt visueel overgenomen uit dit architectuur-model: toon de Core-cluster + de relevante Implementations + de specifieke Integrations.

## Open punten voor jou om te bevestigen

1. **ShillinQ vs ShellinQ** — ik heb voor *Shillinq* gekozen op basis van de DB (122 entries onder dit product_line). Klopt dat?
2. **NLDesign** — als Implementation (theming-app) of als cross-cutting layer (geldt voor *alle* apps)? Ik heb 'm voorlopig in Implementations met een `[?]`-flag.
3. **Status van AssetDesk, BudgetQ, CareDesk, ContractDesk, EduDesk, FormulierenApp, ForumDesk, GoviQ, GovScanner, LearniQ, OpenWoo, PlaniQ** — welke zijn live, welke zijn op-de-roadmap, welke zijn gestopt? Niet alles hoort op de website.
4. **Nextcloud Talk vs Matrix** — beide voor chat. Is Matrix de "Conduction-aanbevolen" optie en Talk een built-in fallback, of allebei volwaardig? Bepaalt visuele plek (Talk in Integrations, Matrix in Extra apps zoals nu).
5. **Nextcloud Office (Collabora)** — Extra app of Integration? Het is Nextcloud-native maar kan ook stand-alone worden gepackaged.
6. **Bron-systemen** (BAG/BRK/PDOK/etc.) — welke zijn al via OpenConnector ondersteund en welke zijn op de roadmap? Voor de homepage-hero wil je waarschijnlijk alleen de **gerealiseerde** integraties tonen.
7. **OpenWoo + OpenCatalogi** — overlap. OpenWoo lijkt op een dedicated WOO-app; OpenCatalogi heeft ook WOO als use-case. Eén schrappen of beiden behouden? Belangrijk voor narrative-helderheid.

Zodra deze 7 punten beantwoord zijn, finaliseren we de architectuur-tabel en update ik scène 1 in `illustration-batch-1.md` + de visuele richting in `visual-motifs.md`.
