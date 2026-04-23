# App-tagline library — 11 core apps

Eén-regel-taglines per core app, MKB-direct, bilingual (NL primair, EN secundair). Gebruikt voor app-catalogus-kaarten, app-detail-hero's, social-media-previews, en meta-descriptions.

**Bron:** `concurrentie-analyse/intelligence.db` (Postgres, 1.088 competitors). Per app zijn de top-features naar `demand_score` gerankt; de tagline dekt de #1–#3 features en laat het specialistische werk aan de app-detail-pagina. Synthese gegroepeerd per app: *wat het oplost* + *wat het je bespaart* + *wat onderscheidend is*.

Zie [BRAND.md §Apps & Solutions](../../BRAND.md#apps--solutions--onze-terminologie) voor de taalregel: noem een app nooit naar een solution (*"onze WOO-app"* is fout; OpenCatalogi ondersteunt WOO maar *is* geen WOO-app).

## Conventie

Elke entry heeft:

- **Tagline (NL)** — exact zoals ze op de homepage/catalogus mag verschijnen
- **Tagline (EN)** — vertaling die de toon behoudt, niet letterlijk
- **Wat het oplost** — één zin voor zoekmachines en voor de onderkant van de app-card
- **Categorie** (uit DB `apps.categories`) — voor filter-functionaliteit

Verboden in taglines: *transformatie*, *synergie*, *ketensamenwerking*, *waardevol*, *toekomstbestendig*, *platform dat*, *state-of-the-art*. Elk zo'n woord is één herschrijving waard.

---

## OpenRegister

- **Categorie:** `database-software`, `dms`, `objectregistratie`
- **Top features (DB):** informatieobjecttype-management, document-object-koppeling, export voor publicatie, zoek-op-zaaknummer
- **Tagline (NL):** *Alle objecten, registers en documenten op één plek — die jij zelf beheert.*
- **Tagline (EN):** *One place for every record, object and document — fully under your control.*
- **Wat het oplost:** *Fragmented registers and silo'd objects become one queryable datastore, hosted on your Nextcloud.*

## OpenCatalogi

- **Categorie:** `catalogus`, `data-catalogue`
- **Top features (DB):** cross-silo search, functionele categorie-zoek, harvesting, API management
- **Tagline (NL):** *Maak je data vindbaar en herbruikbaar — ook buiten je organisatie.*
- **Tagline (EN):** *Make your data discoverable and reusable — beyond your organisation too.*
- **Wat het oplost:** *Federated catalogue for publishing structured data, metadata and assets across organisations.*

## OpenConnector

- **Categorie:** `api-management`, `integratie`, `ipaas`
- **Top features (DB):** API gateway, API analytics, API versioning, API designer
- **Tagline (NL):** *Koppel alles met alles — zonder vendor lock-in of dure integrator.*
- **Tagline (EN):** *Connect anything to anything — without vendor lock-in or pricey integrators.*
- **Wat het oplost:** *Open-source API gateway and iPaaS for wiring apps, data sources and external systems together.*

## DocuDesk

- **Categorie:** `archivering`, `data-anonymization`, `document-generation`
- **Top features (DB):** document-generation, multi-party signing, anonymisatie-redactie, PDF 2.0 / DocMDP-compliance
- **Tagline (NL):** *Brieven, contracten en exporten genereren zonder je documenten uit handen te geven.*
- **Tagline (EN):** *Generate, sign and anonymise documents — without handing them to a third party.*
- **Wat het oplost:** *Document generation, signing and anonymisation inside your own Nextcloud — no SaaS detour.*

## NL Design

- **Categorie:** `ontwerp`
- **Top features (DB):** component library, design tokens, responsive grid, design patterns
- **Tagline (NL):** *Geef je Nextcloud de officiële uitstraling van NL Design System.*
- **Tagline (EN):** *Bring the official look and feel of NL Design System to your Nextcloud.*
- **Wat het oplost:** *NL Design System integration for Nextcloud — consistent, accessible, WCAG-compliant theming across Conduction apps.*

## MyDash

- **Categorie:** `dashboard`
- **Top features (DB):** dashboard builder, access control, dashboard profiles, flow/workflow automation
- **Tagline (NL):** *Bouw dashboards uit je eigen data — zonder dat IT eraan te pas komt.*
- **Tagline (EN):** *Build dashboards from your own data — no IT ticket required.*
- **Wat het oplost:** *Self-service dashboard builder wired into your Nextcloud data sources, with access control per user or team.*

## SoftwareCatalog

- **Categorie:** `itam`
- **Top features (DB):** software catalog, change management, per-component tracking, contract management
- **Tagline (NL):** *Krijg grip op welke software je draait — en welke je kwijt wilt.*
- **Tagline (EN):** *See exactly which software you run — and which you can retire.*
- **Wat het oplost:** *IT-asset and software-inventory catalogue with per-component, contract and vendor insight.*

## LarpingApp

- **Categorie:** `worldbuilding`
- **Top features (DB):** API access, export, search, event registration, item transfer
- **Tagline (NL):** *Bouw je LARP-wereld, personages en campagnes — samen, en open source.*
- **Tagline (EN):** *Build your LARP world, characters and campaigns — together, open source.*
- **Wat het oplost:** *Complete toolkit for LARP organisers: worlds, plots, characters, events, item transfers.*

## ZaakAfhandelApp

- **Categorie:** `zaaksysteem`
- **Top features (DB):** case lifecycle, assignment & routing, SLA & deadline, performance dashboard
- **Tagline (NL):** *Laat je inwoners zelf hun zaken volgen — zonder extra bel-rondjes.*
- **Tagline (EN):** *Let your citizens track their own cases — no more phone calls.*
- **Wat het oplost:** *Citizen-facing case status portal plugged into your existing zaaksysteem.*

## Procest

- **Categorie:** `vth`, `zaaksysteem`
- **Top features (DB):** PDOK/QGIS integratie, Basisregistratie-koppeling, CPV-code integration, safety-region integratie
- **Tagline (NL):** *Een zaaksysteem dat past bij jouw team — geen jaar-lang implementatietraject.*
- **Tagline (EN):** *A case-management system that fits your team — not a year-long rollout.*
- **Wat het oplost:** *Case management, VTH, and forms with ready-made integrations for PDOK, Basisregistraties, and CPV codes.*

## PipelinQ

- **Categorie:** `crm`
- **Top features (DB):** contacts, accounts, quotations, invoicing, membership management
- **Tagline (NL):** *Houd bij wie je klanten zijn en wat er speelt — in Nextcloud, zonder per-user-prijs.*
- **Tagline (EN):** *Track your customers and deals — in Nextcloud, without per-user pricing.*
- **Wat het oplost:** *Open-source CRM with contacts, accounts, quotations and invoicing, hosted on your own Nextcloud.*

---

## Hoe deze taglines te reviewen

Op elk van de 11 onderstaande criteria moet een tagline "groen" scoren. Zo niet: herschrijven.

| Criterium | Ja / Nee |
|---|---|
| ≤ 16 woorden | … |
| Geen woord uit de verbannen-lijst (transformatie, synergie, …) | … |
| "Je/jij" of imperatief, geen "u" of 3e persoon | … |
| Leidt met resultaat, niet met proces | … |
| Reflecteert ten minste één top-feature uit de DB | … |
| Geen claim die voor alle CRM/ECM/ERP-producten geldt | … |

## Open vragen

- Moeten app-*namen* zelf vertaald worden (OpenCatalogi = English, geen NL-variant)? Huidig: nee, namen blijven internationaal, alleen de tagline wisselt.
- Willen we per app een "fallback" tweeregelige tagline voor OG-images waar meer plek is? Later beslissen.
- ZaakAfhandelApp heeft in de DB slechts 32 canonical_features (jonger dan de rest). Tagline leunt daarom meer op de categorie-definitie dan op feature-data. Heroverwegen zodra er ~200+ features zijn.
