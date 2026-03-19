# ConductionNL Repository Archive Plan

**Date:** 2026-03-19
**Total repositories:** 366
**Already archived:** 8
**Recommendation:** Archive + privatise 270, Delete 17, Keep 60

## Context

Conduction has completed its migration from the custom Symfony-based Common Ground / Open Gateway platform to Nextcloud. This document inventories all 366 ConductionNL repositories and recommends which to keep, archive, or delete.

## Strategy: Archive, Privatise, and Hide

### Goal

A clean GitHub organisation page where developers only see the ~60 active repositories. All legacy repos become archived, private, and invisible to non-admin members.

### How it works

Each legacy repository will be:

1. **Archived** — read-only, no pushes, no new issues, no PRs
2. **Made private** — hidden from the public internet
3. **Hidden from non-admin members** — via GitHub's base permission system

The code, issues, and history remain intact inside each repo. Admins can still access everything. If a repo is ever needed again, an admin can unarchive and change its visibility back.

### Visibility control via base permissions

GitHub's organisation **base permission** setting controls what members see by default:

| Setting | Effect |
|---|---|
| **Current (likely "Read")** | All members see all repos, including archived ones |
| **"No permission"** | Members only see repos they have explicit access to via a Team |

**The plan:**

1. Set **Organization Settings > Member privileges > Base permissions** to **"No permission"**
2. The existing **`developers`** Team gets explicit access to the ~60 KEEP repos
3. All archived + private repos become invisible to non-admin members
4. Admins (org owners) always see everything regardless of base permissions

> **Important:** After changing base permissions, verify that the `developers` team already has access to all active repos. Any repo not assigned to a team becomes invisible to regular members.

### Execution plan

| Phase | Action | Effort |
|---|---|---|
| **1. Audit team access** | Verify the `developers` team has access to all 60 KEEP repos. Add any missing ones | 1 hour |
| **2. Change base permissions** | Set org base permissions to "No permission" | 5 min |
| **3. Verify access** | Have a non-admin member confirm they can still see all active repos and nothing else | 15 min |
| **4. Archive repos** | Run `gh repo archive ConductionNL/{name}` for all ARCHIVE repos | 1 hour |
| **5. Privatise repos** | Run `gh repo edit ConductionNL/{name} --visibility private` for all ARCHIVE repos | 1 hour |
| **6. Delete repos** | Delete the empty test/stub repos (after final confirmation) | 30 min |
| **7. Clean up** | Update org profile, remove stale submodule references, pin active repos on org page | 1 hour |

### Script to execute phases 4-5

```bash
# Archive and privatise all repos in one pass
for repo in repo1 repo2 repo3; do
  echo "Processing $repo..."
  gh repo archive "ConductionNL/$repo" --yes
  gh repo edit "ConductionNL/$repo" --visibility private
done
```

The full repo lists per phase are generated from the tables below.

### Rollback

Everything is reversible:
- **Unarchive:** `gh repo unarchive ConductionNL/{name} --yes`
- **Make public again:** `gh repo edit ConductionNL/{name} --visibility public`
- **Restore base permissions:** Set back to "Read" in org settings

---

## Category 1: KEEP — Active Nextcloud Apps (13 repos)

These are the core apps that run on the Nextcloud platform. Actively developed and deployed.

| Repository | Argumentation |
|---|---|
| [openregister](https://github.com/ConductionNL/openregister) | Foundation repository for all Conduction apps — owns schemas, docker-compose, shared specs |
| [opencatalogi](https://github.com/ConductionNL/opencatalogi) | Catalogi app for federated metadata exchange — core product |
| [openconnector](https://github.com/ConductionNL/openconnector) | Gateway/service bus for mapping, translation, and data synchronisation |
| [docudesk](https://github.com/ConductionNL/docudesk) | Document generation and anonymisation — GDPR/WCAG compliant |
| [nldesign](https://github.com/ConductionNL/nldesign) | NL Design System theme for Nextcloud — government theming |
| [mydash](https://github.com/ConductionNL/mydash) | Custom dashboard app for Nextcloud |
| [softwarecatalog](https://github.com/ConductionNL/softwarecatalog) | GEMMA Softwarecatalogus Nextcloud app |
| [larpingapp](https://github.com/ConductionNL/larpingapp) | Larping app — demo/reference app and active product |
| [zaakafhandelapp](https://github.com/ConductionNL/zaakafhandelapp) | Zaak handling for Dutch governmental institutions |
| [procest](https://github.com/ConductionNL/procest) | Case management — thin client on OpenRegister |
| [pipelinq](https://github.com/ConductionNL/pipelinq) | CRM/pipeline management — thin client on OpenRegister |
| [nextcloud-vue](https://github.com/ConductionNL/nextcloud-vue) | Shared Vue component library for all Conduction Nextcloud apps |
| [tilburg-woo-ui](https://github.com/ConductionNL/tilburg-woo-ui) | Tilburg WOO frontend — active deployment, used as submodule |

## Category 2: KEEP — ExApp Wrappers & Integrations (8 repos)

Nextcloud External App (ExApp) wrappers that integrate third-party services into Nextcloud.

| Repository | Argumentation |
|---|---|
| [openklant](https://github.com/ConductionNL/openklant) | OpenKlant customer interaction management — ExApp wrapper |
| [opentalk](https://github.com/ConductionNL/opentalk) | OpenTalk video conferencing — ExApp wrapper |
| [openzaak](https://github.com/ConductionNL/openzaak) | OpenZaak ZGW API integration — ExApp wrapper |
| [valtimo](https://github.com/ConductionNL/valtimo) | Valtimo BPM/case management — ExApp wrapper |
| [n8n-nextcloud](https://github.com/ConductionNL/n8n-nextcloud) | n8n workflow automation — ExApp wrapper |
| [keycloak-nextcloud](https://github.com/ConductionNL/keycloak-nextcloud) | Keycloak identity management — ExApp wrapper |
| [ollama-nextcloud](https://github.com/ConductionNL/ollama-nextcloud) | Ollama local LLM — ExApp wrapper |
| [open-webui-nextcloud](https://github.com/ConductionNL/open-webui-nextcloud) | Open WebUI chat — ExApp wrapper |

## Category 3: KEEP — Infrastructure & Tooling (21 repos)

Repos that support the build, deploy, and operations pipeline.

| Repository | Argumentation |
|---|---|
| [.github](https://github.com/ConductionNL/.github) | Organization profile, community health files, this archive plan |
| [claude-code-config](https://github.com/ConductionNL/claude-code-config) | Shared Claude Code configuration — active daily use (private) |
| [Nextcloud-base](https://github.com/ConductionNL/Nextcloud-base) | Base Nextcloud image — updated Mar 2026 |
| [nextcloud-images](https://github.com/ConductionNL/nextcloud-images) | Custom Nextcloud images — updated Mar 2026 |
| [nextcloud-release-actions](https://github.com/ConductionNL/nextcloud-release-actions) | GitHub Actions for Nextcloud app store releases |
| [cluster-infra](https://github.com/ConductionNL/cluster-infra) | GitOps K8s controllers and operators — updated Mar 2026 |
| [monitoring](https://github.com/ConductionNL/monitoring) | ArgoCD, Prometheus, Grafana — updated Mar 2026 (private) |
| [toolchain](https://github.com/ConductionNL/toolchain) | Build toolchain — updated Mar 2026 (private) |
| [conduction-theme](https://github.com/ConductionNL/conduction-theme) | Conduction design tokens — updated Mar 2026 |
| [conduction-components](https://github.com/ConductionNL/conduction-components) | Component library — updated Feb 2026 |
| [Configurations](https://github.com/ConductionNL/Configurations) | Configuration management (private) |
| [KeyCloak](https://github.com/ConductionNL/KeyCloak) | KeyCloak configuration (private) |
| [gitops-postgres](https://github.com/ConductionNL/gitops-postgres) | Zalando Postgres operator config (private) |
| [Cloud_pgAdmin](https://github.com/ConductionNL/Cloud_pgAdmin) | pgAdmin config (private) |
| [SovereignWorkplace](https://github.com/ConductionNL/SovereignWorkplace) | Sovereign Workplace specs — active (private) |
| [UptimeRobot_reconciler](https://github.com/ConductionNL/UptimeRobot_reconciler) | Uptime monitoring automation |
| [ggm-openregister](https://github.com/ConductionNL/ggm-openregister) | GGM → OpenRegister schema configs — updated Feb 2026 |
| [Conduction-Workflows](https://github.com/ConductionNL/Conduction-Workflows) | GitHub → Slack notifications (fork, active) |
| [woo-website-template](https://github.com/ConductionNL/woo-website-template) | WOO website base template — updated Feb 2026 |
| [woo-website-template-apiv2](https://github.com/ConductionNL/woo-website-template-apiv2) | WOO website API v2 template — updated Mar 2026 |
| [woo-website-migratie](https://github.com/ConductionNL/woo-website-migratie) | WOO website migration tooling |

## Category 4: KEEP — Active Research & Supporting (18 repos)

Repos that are actively used or referenced but are not core apps.

| Repository | Argumentation |
|---|---|
| [Softwarecatalogus](https://github.com/ConductionNL/Softwarecatalogus) | VNG client repo (fork) — actively synced, NEVER commit directly |
| [anonymization-experiments](https://github.com/ConductionNL/anonymization-experiments) | LLM vs ML anonymization research |
| [OpenAnonymiser](https://github.com/ConductionNL/OpenAnonymiser) | Anonymisation API (fork) — updated Mar 2026 |
| [OpenAnonymiser_light](https://github.com/ConductionNL/OpenAnonymiser_light) | Light anonymiser (fork) — updated Mar 2026 |
| [NL_doc](https://github.com/ConductionNL/NL_doc) | Documentation — updated Jan 2026 |
| [LLM-configuratie](https://github.com/ConductionNL/LLM-configuratie) | LLM configuration |
| [n8n](https://github.com/ConductionNL/n8n) | n8n repo |
| [GDPRdesk](https://github.com/ConductionNL/GDPRdesk) | GDPR tooling |
| [waardepapieren](https://github.com/ConductionNL/waardepapieren) | Blockchain certificates — updated Jan 2026 |
| [fallback-page](https://github.com/ConductionNL/fallback-page) | Fallback page for infrastructure |
| [sec-issue-bot](https://github.com/ConductionNL/sec-issue-bot) | Security issue Slack bot |
| [content-bot](https://github.com/ConductionNL/content-bot) | Content generation Slack bot (fork) |
| [docurag](https://github.com/ConductionNL/docurag) | Python RAG document search |
| [Woo-AVL](https://github.com/ConductionNL/Woo-AVL) | WOO anonymisation via LLM |
| [archimate-diagram-engine](https://github.com/ConductionNL/archimate-diagram-engine) | ArchiMate diagram fork — used for architecture docs |
| [Gemeentelijk-Gegevensmodel](https://github.com/ConductionNL/Gemeentelijk-Gegevensmodel) | GGM fork — reference for schema generation |
| [product-website-template](https://github.com/ConductionNL/product-website-template) | Product page template for open-source projects |
| [openwoo-app-website](https://github.com/ConductionNL/openwoo-app-website) | OpenWoo.app website |

## Category 5: ARCHIVE — Common Ground Gateway (The Old Platform) (5 repos)

The Symfony-based Common Ground Gateway that has been fully replaced by the Nextcloud platform.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [commonground-gateway](https://github.com/ConductionNL/commonground-gateway) | 91 | **The old platform itself** — Symfony bundle + K8s wrapper, fully replaced by OpenRegister + OpenConnector |
| [commonground-gateway-frontend](https://github.com/ConductionNL/commonground-gateway-frontend) | 3 | React frontend for the old gateway — replaced by Nextcloud UI |
| [commonground-gateway-ui](https://github.com/ConductionNL/commonground-gateway-ui) | 2 | Earlier iteration of the gateway UI — replaced by Nextcloud UI |
| [gateway-ui](https://github.com/ConductionNL/gateway-ui) | 5 | Most recent gateway UI — replaced by Nextcloud UI |
| [api-connector](https://github.com/ConductionNL/api-connector) | 0 | Ajax/NLX connector for the old platform — replaced by OpenConnector |

## Category 6: ARCHIVE — Symfony Bundles (15 repos)

Symfony bundles that were part of the old Common Ground framework. All functionality now lives in Nextcloud apps.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [CommonGroundBundle](https://github.com/ConductionNL/CommonGroundBundle) | 3 | Core CG toolkit for Symfony — replaced by Nextcloud platform |
| [ConductionCommonGroundBundle](https://github.com/ConductionNL/ConductionCommonGroundBundle) | 1 | Conduction's CG Symfony bundle — replaced |
| [DigiDBundle](https://github.com/ConductionNL/DigiDBundle) | 0 | DigiD Symfony bundle — authentication now via Keycloak ExApp |
| [digid-bundle](https://github.com/ConductionNL/digid-bundle) | 0 | DigiD bundle v2 — same as above |
| [IdVaultBundle](https://github.com/ConductionNL/IdVaultBundle) | 0 | ID Vault Symfony bundle — replaced by Keycloak |
| [saml-bundle](https://github.com/ConductionNL/saml-bundle) | 0 | SAML login bundle — replaced by Keycloak |
| [WooBundle](https://github.com/ConductionNL/WooBundle) | 0 | WOO publications bundle (fork) — replaced by OpenWoo on Nextcloud |
| [ApplicationBundle](https://github.com/ConductionNL/ApplicationBundle) | 1 | Example Symfony app bundle — obsolete |
| [AtlantisBundle](https://github.com/ConductionNL/AtlantisBundle) | 0 | Atlantis theme bundle — replaced by NL Design |
| [BalanceBundle](https://github.com/ConductionNL/BalanceBundle) | 0 | Balance bundle — obsolete |
| [FlatlandBundle](https://github.com/ConductionNL/FlatlandBundle) | 1 | Flatland template bundle — obsolete |
| [LandkitBundle](https://github.com/ConductionNL/LandkitBundle) | 1 | Landkit template bundle — obsolete |
| [ListyBundle](https://github.com/ConductionNL/ListyBundle) | 1 | Listy template bundle — obsolete |
| [MisterWolfBundle](https://github.com/ConductionNL/MisterWolfBundle) | 4 | MisterWolf template bundle (private) — obsolete |
| [NLDesignBundle](https://github.com/ConductionNL/NLDesignBundle) | 1 | NL Design template bundle — replaced by nldesign Nextcloud app |
| [RocketBundle](https://github.com/ConductionNL/RocketBundle) | 1 | Rocket theme bundle — obsolete |
| [SpacesBundle](https://github.com/ConductionNL/SpacesBundle) | 0 | Spaces template bundle — obsolete |

## Category 7: ARCHIVE — Common Ground Components (35 repos)

API components built on the old Symfony platform. All replaced by OpenRegister schemas.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [Authorization-component](https://github.com/ConductionNL/Authorization-component) | 7 | Authorization — now handled by Nextcloud's built-in auth |
| [Challenge-component](https://github.com/ConductionNL/Challenge-component) | 5 | Challenges — replaced by OpenRegister schema |
| [ContactMoment-Component](https://github.com/ConductionNL/ContactMoment-Component) | 4 | Contact moments — replaced by Pipelinq on OpenRegister |
| [EAV-component](https://github.com/ConductionNL/EAV-component) | 0 | Entity-Attribute-Value — **this IS OpenRegister's predecessor** |
| [Notification-component](https://github.com/ConductionNL/Notification-component) | 4 | Notifications — replaced by Nextcloud notifications + n8n |
| [Queue-Component](https://github.com/ConductionNL/Queue-Component) | 4 | Queue — replaced by n8n workflows |
| [balance-registration](https://github.com/ConductionNL/balance-registration) | 4 | Balance registration — obsolete |
| [besmettingregistratiecomponent](https://github.com/ConductionNL/besmettingregistratiecomponent) | 8 | COVID-19 contact tracing — pandemic is over |
| [checkin-component](https://github.com/ConductionNL/checkin-component) | 4 | Horeca check-in — COVID-era, no longer needed |
| [checkinservice](https://github.com/ConductionNL/checkinservice) | 4 | Check-in service — COVID-era, no longer needed |
| [contactregistratiecomponent](https://github.com/ConductionNL/contactregistratiecomponent) | 8 | Contact registration — replaced by Pipelinq |
| [education-component](https://github.com/ConductionNL/education-component) | 8 | Education — obsolete, never deployed to production |
| [environment-component](https://github.com/ConductionNL/environment-component) | 9 | K8s environment descriptions — replaced by cluster-infra |
| [export-component](https://github.com/ConductionNL/export-component) | 4 | Export files — replaced by DocuDesk |
| [issue-component](https://github.com/ConductionNL/issue-component) | 8 | Issue handling — replaced by GitHub issues + Nextcloud |
| [loggingcomponent](https://github.com/ConductionNL/loggingcomponent) | 0 | Logging — replaced by Nextcloud audit logging |
| [memo-component](https://github.com/ConductionNL/memo-component) | 5 | Memos — replaced by OpenRegister objects |
| [portfolio-component](https://github.com/ConductionNL/portfolio-component) | 5 | Portfolio — obsolete |
| [review-component](https://github.com/ConductionNL/review-component) | 5 | Reviews — replaced by OpenRegister schema |
| [story-component](https://github.com/ConductionNL/story-component) | 0 | Stories — obsolete |
| [taken-component](https://github.com/ConductionNL/taken-component) | 5 | Tasks — replaced by Procest on OpenRegister |
| [token-registration-component](https://github.com/ConductionNL/token-registration-component) | 4 | Token registration — replaced by Keycloak |
| [user-component](https://github.com/ConductionNL/user-component) | 7 | User management — replaced by Nextcloud user management |
| [wallet-component](https://github.com/ConductionNL/wallet-component) | 3 | Wallet — updated Jan 2026 but functionality moved to Nextcloud |
| [very-small-chatbot-component](https://github.com/ConductionNL/very-small-chatbot-component) | 1 | Chatbot — replaced by Open WebUI ExApp |
| [installation-management-component](https://github.com/ConductionNL/installation-management-component) | 5 | Cluster installation management (private) — replaced by cluster-infra |
| [server-analysis-service](https://github.com/ConductionNL/server-analysis-service) | 0 | Server analysis — replaced by monitoring stack |
| [Environment-management-component](https://github.com/ConductionNL/Environment-management-component) | 3 | Environment management (private) — replaced by GitOps |
| [instemming-registratie-component](https://github.com/ConductionNL/instemming-registratie-component) | 5 | Consent registration — replaced by OpenRegister schema |
| [procesregistratiecomponent](https://github.com/ConductionNL/procesregistratiecomponent) | 4 | Process registration — replaced by Procest |
| [orderregistratiecomponent](https://github.com/ConductionNL/orderregistratiecomponent) | 5 | Order registration — replaced by OpenRegister schema |
| [Commongroundregistratiecomponent](https://github.com/ConductionNL/Commongroundregistratiecomponent) | 8 | CG component registry — replaced by OpenCatalogi |
| [zaak-registratie-component](https://github.com/ConductionNL/zaak-registratie-component) | 47 | Case registration — replaced by Procest + OpenZaak ExApp |
| [grafregistratiecomponent](https://github.com/ConductionNL/grafregistratiecomponent) | 0 | Grave registration (fork) — municipality-specific, obsolete |
| [verzoekregistratiecomponent](https://github.com/ConductionNL/verzoekregistratiecomponent) | 6 | Request registration — replaced by Pipelinq |

## Category 8: ARCHIVE — Common Ground Services (21 repos)

Business logic services built on the old platform. Replaced by n8n workflows or Nextcloud app logic.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [adresservice](https://github.com/ConductionNL/adresservice) | 7 | Address/BAG enrichment — replaced by OpenConnector source |
| [agendaservice](https://github.com/ConductionNL/agendaservice) | 10 | Agenda/appointments — replaced by Nextcloud Calendar |
| [begrafenisservice](https://github.com/ConductionNL/begrafenisservice) | 5 | Funeral service — municipality-specific, obsolete |
| [begraven-service](https://github.com/ConductionNL/begraven-service) | 9 | Burial service — municipality-specific, obsolete |
| [berichtservice](https://github.com/ConductionNL/berichtservice) | 7 | Messaging (email/SMS) — replaced by n8n workflows |
| [betaalservice](https://github.com/ConductionNL/betaalservice) | 5 | Payment processing — replaced by OpenConnector integration |
| [brpservice](https://github.com/ConductionNL/brpservice) | 6 | BRP (national person registry) proxy — replaced by OpenConnector source |
| [instemmingservice](https://github.com/ConductionNL/instemmingservice) | 5 | Consent processing — replaced by n8n workflow |
| [kvkservice](https://github.com/ConductionNL/kvkservice) | 5 | KVK (chamber of commerce) proxy — replaced by OpenConnector source |
| [logicservice](https://github.com/ConductionNL/logicservice) | 0 | BRP logic — replaced by OpenConnector mapping |
| [stufservice](https://github.com/ConductionNL/stufservice) | 5 | StUF protocol bridge — replaced by OpenConnector |
| [taalhuizen-service](https://github.com/ConductionNL/taalhuizen-service) | 2 | Language school service — project-specific, obsolete |
| [taalhuizen-logic](https://github.com/ConductionNL/taalhuizen-logic) | 0 | Language school notification logic — project-specific, obsolete |
| [trouw-service](https://github.com/ConductionNL/trouw-service) | 6 | Marriage business logic — municipality-specific, obsolete |
| [verhuis-service](https://github.com/ConductionNL/verhuis-service) | 5 | Moving service — municipality-specific, obsolete |
| [verzoekconversieservice](https://github.com/ConductionNL/verzoekconversieservice) | 6 | Request-to-case converter — replaced by n8n workflow |
| [vsbe-service](https://github.com/ConductionNL/vsbe-service) | 4 | Very Small Business Engine — replaced by Procest |
| [westfrieslandservice](https://github.com/ConductionNL/westfrieslandservice) | 7 | West-Friesland-specific logic — municipality-specific, obsolete |
| [document-creation-service](https://github.com/ConductionNL/document-creation-service) | 0 | Document creation — replaced by DocuDesk |
| [bundle-runner](https://github.com/ConductionNL/bundle-runner) | 0 | Symfony bundle runner — obsolete with platform migration |
| [generic-commonground-bl](https://github.com/ConductionNL/generic-commonground-bl) | 0 | Generic business logic layer — replaced by OpenConnector |

## Category 9: ARCHIVE — Common Ground Catalogues (10 repos)

Domain catalogues from the old platform. All replaced by OpenRegister schemas.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [locatiecatalogus](https://github.com/ConductionNL/locatiecatalogus) | 4 | Location catalogue — replaced by OpenRegister location schema |
| [medewerkercatalogus](https://github.com/ConductionNL/medewerkercatalogus) | 6 | Employee catalogue — replaced by Nextcloud users + OpenRegister |
| [procestypecatalogus](https://github.com/ConductionNL/procestypecatalogus) | 6 | Process type catalogue — replaced by Procest |
| [productenendienstencatalogus](https://github.com/ConductionNL/productenendienstencatalogus) | 14 | Products & services catalogue — replaced by OpenRegister schema |
| [verzoektypecatalogus](https://github.com/ConductionNL/verzoektypecatalogus) | 4 | Request type catalogue — replaced by Pipelinq schemas |
| [webresourcecatalogus](https://github.com/ConductionNL/webresourcecatalogus) | 8 | Web resource catalogue — replaced by Nextcloud Files |
| [landelijketabellencatalogus](https://github.com/ConductionNL/landelijketabellencatalogus) | 4 | National GBA tables — replaced by OpenConnector source |
| [contactcatalogus](https://github.com/ConductionNL/contactcatalogus) | 0 | Contact catalogue — already archived, replaced by Pipelinq |
| [componentenoverzicht](https://github.com/ConductionNL/componentenoverzicht) | 1 | Component overview — replaced by OpenCatalogi |
| [love-common-ground](https://github.com/ConductionNL/love-common-ground) | 42 | CG developer community platform — replaced by OpenCatalogi |

## Category 10: ARCHIVE — Proto Applications & Generators (7 repos)

Template generators and proto applications for the old platform.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [Proto-component-commonground](https://github.com/ConductionNL/Proto-component-commonground) | 35 | Component generator — the old `yo commonground` scaffolder, replaced by Nextcloud app scaffolder |
| [Proto-application-NLDesign](https://github.com/ConductionNL/Proto-application-NLDesign) | 6 | NL Design proto app — replaced by nldesign Nextcloud app |
| [Proto-application-flatland](https://github.com/ConductionNL/Proto-application-flatland) | 1 | Flatland proto app — obsolete |
| [Proto-application-listy](https://github.com/ConductionNL/Proto-application-listy) | 1 | Listy proto app — obsolete |
| [Proto-application-mister-wolf](https://github.com/ConductionNL/Proto-application-mister-wolf) | 1 | MisterWolf proto app — obsolete |
| [proto-application-commonground](https://github.com/ConductionNL/proto-application-commonground) | 1 | CG proto PHP app — obsolete |
| [commonground-example](https://github.com/ConductionNL/commonground-example) | 7 | CG example project — obsolete |

## Category 11: ARCHIVE — Old Process Engines & Dashboards (4 repos)

Process/case management from before Procest existed.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [procces-engine](https://github.com/ConductionNL/procces-engine) | 42 | Headless process/business engine — **direct predecessor to Procest**, high issue count has historical value |
| [processenDashboard](https://github.com/ConductionNL/processenDashboard) | 6 | Process dashboard — replaced by Procest UI |
| [commonground-dashboard](https://github.com/ConductionNL/commonground-dashboard) | 4 | CG dashboard — replaced by MyDash |
| [checking](https://github.com/ConductionNL/checking) | 3 | Checking app — obsolete |

## Category 12: ARCHIVE — Publiccode Metadata Repos (19 repos)

`publiccode.yaml` repos that made components findable in the old component registry. All superseded by OpenCatalogi.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [bag_publiccode](https://github.com/ConductionNL/bag_publiccode) | 0 | BAG API publiccode — superseded by OpenCatalogi listing |
| [brc_publiccode](https://github.com/ConductionNL/brc_publiccode) | 0 | Besluiten API publiccode — superseded |
| [brp_publiccode](https://github.com/ConductionNL/brp_publiccode) | 0 | BRP API publiccode — superseded |
| [contactmomenten_publiccode](https://github.com/ConductionNL/contactmomenten_publiccode) | 0 | Contactmomenten publiccode — superseded |
| [drc_publiccode](https://github.com/ConductionNL/drc_publiccode) | 0 | Document registration publiccode — superseded |
| [elastic_search_publiccode](https://github.com/ConductionNL/elastic_search_publiccode) | 0 | Elasticsearch publiccode — superseded |
| [handels_register_publiccode](https://github.com/ConductionNL/handels_register_publiccode) | 0 | Handelsregister publiccode — superseded |
| [klanten_publiccode](https://github.com/ConductionNL/klanten_publiccode) | 0 | Klanten API publiccode — superseded |
| [logging-verwerking-read_publiccode](https://github.com/ConductionNL/logging-verwerking-read_publiccode) | 0 | Logging read publiccode — superseded |
| [logging-verwerking-write_publiccode](https://github.com/ConductionNL/logging-verwerking-write_publiccode) | 0 | Logging write publiccode — superseded |
| [MRC_publiccode](https://github.com/ConductionNL/MRC_publiccode) | 0 | Medewerkers publiccode — superseded |
| [nrc_publiccode](https://github.com/ConductionNL/nrc_publiccode) | 0 | Notifications publiccode — superseded |
| [PDC_publiccode](https://github.com/ConductionNL/PDC_publiccode) | 0 | PDC publiccode — superseded |
| [PUB_publiccode](https://github.com/ConductionNL/PUB_publiccode) | 0 | Publications publiccode — superseded |
| [productaanvraag_publiccode](https://github.com/ConductionNL/productaanvraag_publiccode) | 0 | Product request publiccode — superseded |
| [referentielijsten_publiccode](https://github.com/ConductionNL/referentielijsten_publiccode) | 1 | Reference lists publiccode — superseded |
| [verzoeken_publiccode](https://github.com/ConductionNL/verzoeken_publiccode) | 0 | Requests publiccode — superseded |
| [zrc_publiccode](https://github.com/ConductionNL/zrc_publiccode) | 0 | Cases API publiccode — superseded |
| [ztc_publiccode](https://github.com/ConductionNL/ztc_publiccode) | 0 | Catalogi API publiccode — superseded |

## Category 13: ARCHIVE — Old Frontends & UIs (26 repos)

Frontend applications from the old platform era. All replaced by Nextcloud UIs or no longer needed.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [commonground-ui](https://github.com/ConductionNL/commonground-ui) | 42 | common-ground.dev website — replaced by OpenCatalogi |
| [conduction-ui](https://github.com/ConductionNL/conduction-ui) | 6 | Old Conduction website — replaced by current website |
| [huwelijksplanner-ui](https://github.com/ConductionNL/huwelijksplanner-ui) | 7 | Marriage planner UI — municipality project ended |
| [begrafenisplanner](https://github.com/ConductionNL/begrafenisplanner) | 0 | Funeral planner UI — municipality project ended |
| [verhuizen-interface](https://github.com/ConductionNL/verhuizen-interface) | 0 | Moving process UI — municipality project ended |
| [instemmingen-interface](https://github.com/ConductionNL/instemmingen-interface) | 2 | Consent interface — obsolete |
| [eherkenning-ui](https://github.com/ConductionNL/eherkenning-ui) | 1 | eHerkenning spoof UI — replaced by Keycloak |
| [digispoof](https://github.com/ConductionNL/digispoof) | 1 | DigiD spoof — replaced by Keycloak |
| [digispoof-interface](https://github.com/ConductionNL/digispoof-interface) | 8 | DigiD spoof UI — replaced by Keycloak |
| [digispoof-old](https://github.com/ConductionNL/digispoof-old) | 1 | Old DigiD spoof — obsolete |
| [bisc-frontend](https://github.com/ConductionNL/bisc-frontend) | 0 | BISC frontend — project ended |
| [mijnapp-frontend](https://github.com/ConductionNL/mijnapp-frontend) | 0 | MijnApp (fork) — project ended |
| [mijndenhaag-pwa](https://github.com/ConductionNL/mijndenhaag-pwa) | 0 | MijnDenHaag PWA (fork) — project ended |
| [waardepapieren-frontend](https://github.com/ConductionNL/waardepapieren-frontend) | 0 | Waardepapieren UI — project ended |
| [waardepapieren-ballie](https://github.com/ConductionNL/waardepapieren-ballie) | 5 | Waardepapieren desk app — project ended |
| [waardepapieren-scan-app](https://github.com/ConductionNL/waardepapieren-scan-app) | 0 | Waardepapieren scan app — project ended |
| [larping](https://github.com/ConductionNL/larping) | 2 | Old larping frontend — replaced by larpingapp |
| [larping-ui](https://github.com/ConductionNL/larping-ui) | 1 | Old larping UI — replaced by larpingapp |
| [corona-interface](https://github.com/ConductionNL/corona-interface) | 1 | Corona info UI for Utrecht — COVID-era, obsolete |
| [challenges-ui](https://github.com/ConductionNL/challenges-ui) | 1 | Challenges UI — obsolete |
| [formulieren-ui](https://github.com/ConductionNL/formulieren-ui) | 1 | Forms UI — obsolete |
| [ggd-ui](https://github.com/ConductionNL/ggd-ui) | 1 | GGD UI — obsolete |
| [stages-ui](https://github.com/ConductionNL/stages-ui) | 1 | Stages/internships UI — obsolete |
| [vrijwilligers-ui](https://github.com/ConductionNL/vrijwilligers-ui) | 1 | Volunteers UI — obsolete |
| [utrecht-huwelijksplanner](https://github.com/ConductionNL/utrecht-huwelijksplanner) | 0 | Utrecht marriage planner (fork) — project ended |
| [kiss-frontend-dit](https://github.com/ConductionNL/kiss-frontend-dit) | 1 | KISS frontend (fork) — evaluation completed |

## Category 14: ARCHIVE — PWA Skeletons & Templates (10 repos)

Progressive Web App templates from the Gatsby era. All replaced by Nextcloud-based frontends.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [skeleton-app](https://github.com/ConductionNL/skeleton-app) | 2 | Gatsby skeleton — replaced by Nextcloud app scaffolding |
| [skeleton-gatsby](https://github.com/ConductionNL/skeleton-gatsby) | 5 | Gatsby skeleton — same |
| [skeleton-pip](https://github.com/ConductionNL/skeleton-pip) | 2 | PIP skeleton — obsolete |
| [nl-design-skeleton-gatsby](https://github.com/ConductionNL/nl-design-skeleton-gatsby) | 2 | NL Design Gatsby skeleton — replaced by nldesign app |
| [pwa-ballie-hoorn](https://github.com/ConductionNL/pwa-ballie-hoorn) | 0 | Hoorn PWA — municipality project ended |
| [pwa-nijmegen](https://github.com/ConductionNL/pwa-nijmegen) | 0 | Nijmegen PWA — municipality project ended |
| [pwa-pip-nijmegen](https://github.com/ConductionNL/pwa-pip-nijmegen) | 1 | Nijmegen PIP POC — project ended |
| [pwa-verhuizen-denbosh](https://github.com/ConductionNL/pwa-verhuizen-denbosh) | 4 | Den Bosch moving PWA — project ended |
| [proto-pwa-next](https://github.com/ConductionNL/proto-pwa-next) | 0 | Next.js PWA prototype — obsolete |
| [pwa-5](https://github.com/ConductionNL/pwa-5) | 0 | PWA test — obsolete |

## Category 15: ARCHIVE — Municipality-Specific Projects (13 repos)

One-off projects for specific municipalities. All projects have concluded.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [utrecht-trouwen](https://github.com/ConductionNL/utrecht-trouwen) | 70 | Utrecht marriage app (private) — project ended, **high issue count worth preserving** |
| [zaakonline](https://github.com/ConductionNL/zaakonline) | 68 | Online case system sketch (private) — predecessor to zaakafhandelapp, **high issue count** |
| [huwelijksplanner](https://github.com/ConductionNL/huwelijksplanner) | 0 | Marriage planner backend — project ended |
| [verhuizen](https://github.com/ConductionNL/verhuizen) | 0 | Moving process — project ended |
| [OpenPDD-Beuningen](https://github.com/ConductionNL/OpenPDD-Beuningen) | 0 | Beuningen products — project ended |
| [OpenWooApp](https://github.com/ConductionNL/OpenWooApp) | 0 | Open WOO app docs/config — migrated to Nextcloud |
| [poc-zaaksysteem-nijmegen-master](https://github.com/ConductionNL/poc-zaaksysteem-nijmegen-master) | 0 | Nijmegen case system POC — project ended |
| [hackathon-eerste-inschrijving](https://github.com/ConductionNL/hackathon-eerste-inschrijving) | 0 | Hackathon project — event ended |
| [pip-demodam](https://github.com/ConductionNL/pip-demodam) | 0 | Demodam PIP — demo project ended |
| [stage-platform](https://github.com/ConductionNL/stage-platform) | 4 | Internship platform — project ended |
| [Verhuizen-implementatie](https://github.com/ConductionNL/Verhuizen-implementatie) | 4 | Moving implementation script (private) — project ended |
| [docparser](https://github.com/ConductionNL/docparser) | 5 | OAS/publiccode analyser — replaced by OpenCatalogi validation |
| [Klantinteractie-Servicesysteem](https://github.com/ConductionNL/Klantinteractie-Servicesysteem) | 0 | KIS specification (private) — superseded by Pipelinq |

## Category 16: ARCHIVE — WOO Municipality Websites (43 repos)

Per-municipality WOO website deployment repos. The templates are kept (Category 3); these are frozen instances.

> **Note:** Before archiving, verify with ops which municipalities still have active contracts. Active deployments may need to stay unarchived for maintenance access.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [woo-website](https://github.com/ConductionNL/woo-website) | 18 | Base WOO website — check if still active |
| [woo-website-baarn](https://github.com/ConductionNL/woo-website-baarn) | 0 | Baarn instance |
| [woo-website-barneveld](https://github.com/ConductionNL/woo-website-barneveld) | 0 | Barneveld v1 |
| [woo-website-barneveld-v2](https://github.com/ConductionNL/woo-website-barneveld-v2) | 0 | Barneveld v2 |
| [woo-website-bct](https://github.com/ConductionNL/woo-website-bct) | 0 | BCT instance |
| [woo-website-beek](https://github.com/ConductionNL/woo-website-beek) | 0 | Beek instance |
| [woo-website-buren](https://github.com/ConductionNL/woo-website-buren) | 0 | Buren instance |
| [woo-website-conduction](https://github.com/ConductionNL/woo-website-conduction) | 0 | Conduction's own instance |
| [woo-website-conduction-apiv2](https://github.com/ConductionNL/woo-website-conduction-apiv2) | 0 | Conduction API v2 instance |
| [woo-website-dinkelland](https://github.com/ConductionNL/woo-website-dinkelland) | 0 | Dinkelland v1 |
| [woo-website-dinkelland-v2](https://github.com/ConductionNL/woo-website-dinkelland-v2) | 0 | Dinkelland v2 |
| [woo-website-ede](https://github.com/ConductionNL/woo-website-ede) | 0 | Ede instance |
| [woo-website-epe](https://github.com/ConductionNL/woo-website-epe) | 0 | Epe v1 |
| [woo-website-epe-apiv2](https://github.com/ConductionNL/woo-website-epe-apiv2) | 0 | Epe API v2 |
| [woo-website-epe-v2](https://github.com/ConductionNL/woo-website-epe-v2) | 0 | Epe v2 |
| [woo-website-gooisemeren](https://github.com/ConductionNL/woo-website-gooisemeren) | 0 | Gooise Meren v1 |
| [woo-website-gooisemeren-v2](https://github.com/ConductionNL/woo-website-gooisemeren-v2) | 0 | Gooise Meren v2 |
| [woo-website-gouda](https://github.com/ConductionNL/woo-website-gouda) | 0 | Gouda instance |
| [woo-website-helmond](https://github.com/ConductionNL/woo-website-helmond) | 0 | Helmond instance |
| [woo-website-hoekschewaard](https://github.com/ConductionNL/woo-website-hoekschewaard) | 0 | Hoeksche Waard instance |
| [woo-website-hofvantwente](https://github.com/ConductionNL/woo-website-hofvantwente) | 0 | Hof van Twente v1 |
| [woo-website-hofvantwente-apiv2](https://github.com/ConductionNL/woo-website-hofvantwente-apiv2) | 0 | Hof van Twente API v2 |
| [woo-website-koophulpje](https://github.com/ConductionNL/woo-website-koophulpje) | 0 | Koophulpje instance |
| [woo-website-lansingerland](https://github.com/ConductionNL/woo-website-lansingerland) | 0 | Lansingerland instance |
| [woo-website-leiden](https://github.com/ConductionNL/woo-website-leiden) | 0 | Leiden instance |
| [woo-website-moerdijk](https://github.com/ConductionNL/woo-website-moerdijk) | 0 | Moerdijk v1 |
| [woo-website-moerdijk-v2](https://github.com/ConductionNL/woo-website-moerdijk-v2) | 0 | Moerdijk v2 |
| [woo-website-noaberkracht](https://github.com/ConductionNL/woo-website-noaberkracht) | 0 | Noaberkracht v1 |
| [woo-website-noaberkracht-v2](https://github.com/ConductionNL/woo-website-noaberkracht-v2) | 0 | Noaberkracht v2 |
| [woo-website-noordwijk](https://github.com/ConductionNL/woo-website-noordwijk) | 0 | Noordwijk v1 |
| [woo-website-noordwijk-apiv2](https://github.com/ConductionNL/woo-website-noordwijk-apiv2) | 0 | Noordwijk API v2 |
| [woo-website-odmh](https://github.com/ConductionNL/woo-website-odmh) | 0 | ODMH instance |
| [woo-website-oude-ijsselstreek](https://github.com/ConductionNL/woo-website-oude-ijsselstreek) | 0 | Oude IJsselstreek instance |
| [woo-website-roosendaal](https://github.com/ConductionNL/woo-website-roosendaal) | 0 | Roosendaal v1 |
| [woo-website-roosendaal-v2](https://github.com/ConductionNL/woo-website-roosendaal-v2) | 0 | Roosendaal v2 |
| [woo-website-rotterdam](https://github.com/ConductionNL/woo-website-rotterdam) | 0 | Rotterdam instance |
| [woo-website-sloterburg](https://github.com/ConductionNL/woo-website-sloterburg) | 0 | Sloterburg instance |
| [woo-website-soest](https://github.com/ConductionNL/woo-website-soest) | 0 | Soest instance |
| [woo-website-stichtsevecht](https://github.com/ConductionNL/woo-website-stichtsevecht) | 0 | Stichtse Vecht instance |
| [woo-website-tubbergen](https://github.com/ConductionNL/woo-website-tubbergen) | 0 | Tubbergen v1 |
| [woo-website-tubbergen-v2](https://github.com/ConductionNL/woo-website-tubbergen-v2) | 0 | Tubbergen v2 |
| [woo-website-xxllnc](https://github.com/ConductionNL/woo-website-xxllnc) | 0 | XXLlnc integration instance |
| [woo-website-zuiddrecht](https://github.com/ConductionNL/woo-website-zuiddrecht) | 0 | Zuid-Drecht instance |
| [woo-website-zuiddrecht-temp](https://github.com/ConductionNL/woo-website-zuiddrecht-temp) | 0 | Zuid-Drecht temp instance |
| [woo-website-zutphen](https://github.com/ConductionNL/woo-website-zutphen) | 0 | Zutphen v1 |
| [woo-website-zutphen-v2](https://github.com/ConductionNL/woo-website-zutphen-v2) | 0 | Zutphen v2 |

## Category 17: ARCHIVE — WordPress Plugins & Themes (12 repos)

WordPress-era plugins. All replaced by Nextcloud apps.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [formio-wordpress](https://github.com/ConductionNL/formio-wordpress) | 0 | Form.io for WordPress — replaced by Nextcloud forms/n8n |
| [waardepapieren_wordpress](https://github.com/ConductionNL/waardepapieren_wordpress) | 0 | Waardepapieren WordPress plugin — project ended |
| [waardepapieren_drupal](https://github.com/ConductionNL/waardepapieren_drupal) | 0 | Waardepapieren Drupal module — project ended |
| [waardepapieren_typo3](https://github.com/ConductionNL/waardepapieren_typo3) | 0 | Waardepapieren TYPO3 extension — project ended |
| [id-vault_wordpress](https://github.com/ConductionNL/id-vault_wordpress) | 0 | ID Vault WordPress plugin — replaced by Keycloak |
| [NL-Design_wordpress](https://github.com/ConductionNL/NL-Design_wordpress) | 0 | NL Design WordPress theme — replaced by nldesign app |
| [wordpress-docker](https://github.com/ConductionNL/wordpress-docker) | 0 | Dockerized WordPress — no longer using WordPress |
| [plugin-openpub-base](https://github.com/ConductionNL/plugin-openpub-base) | 0 | OpenPub WordPress plugin (fork) — project ended |
| [plugin-openpub-internal-data](https://github.com/ConductionNL/plugin-openpub-internal-data) | 0 | OpenPub internal data (fork) — project ended |
| [plugin-openwoo](https://github.com/ConductionNL/plugin-openwoo) | 1 | OpenWoo WordPress plugin (fork) — migrated to Nextcloud |
| [plugin-pdc-expiration-date](https://github.com/ConductionNL/plugin-pdc-expiration-date) | 0 | PDC expiration date plugin (fork) — obsolete |
| [plugin-pdc-faq](https://github.com/ConductionNL/plugin-pdc-faq) | 0 | PDC FAQ plugin (fork) — obsolete |
| [plugin-pdc-internal-products](https://github.com/ConductionNL/plugin-pdc-internal-products) | 0 | PDC internal products (fork) — obsolete |
| [plugin-pdc-leges](https://github.com/ConductionNL/plugin-pdc-leges) | 0 | PDC leges plugin (fork) — obsolete |
| [plugin-pdc-locations](https://github.com/ConductionNL/plugin-pdc-locations) | 0 | PDC locations plugin (fork) — obsolete |
| [plugin-pdc-samenwerkende-catalogi](https://github.com/ConductionNL/plugin-pdc-samenwerkende-catalogi) | 0 | PDC samenwerkende catalogi (fork) — replaced by OpenCatalogi |
| [open-government-publications](https://github.com/ConductionNL/open-government-publications) | 0 | Government publications WordPress plugin (fork) — replaced by WOO app |

## Category 18: ARCHIVE — Old Kubernetes & Infrastructure (13 repos)

Kubernetes configs from the old platform deployment. All replaced by current GitOps setup.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [commonground-kubernetes](https://github.com/ConductionNL/commonground-kubernetes) | 4 | Old CG K8s config (private) — replaced by cluster-infra |
| [conduction-website-kubernetes](https://github.com/ConductionNL/conduction-website-kubernetes) | 4 | Old website K8s (private) — replaced |
| [websites-kubernetes](https://github.com/ConductionNL/websites-kubernetes) | 0 | Old websites K8s (private) — replaced |
| [utrecht-kubernetes](https://github.com/ConductionNL/utrecht-kubernetes) | 4 | Utrecht K8s (private) — project ended |
| [utrecht-commonground-kubernetes](https://github.com/ConductionNL/utrecht-commonground-kubernetes) | 4 | Utrecht CG K8s (private) — project ended |
| [trouwen-kubernetes](https://github.com/ConductionNL/trouwen-kubernetes) | 4 | Marriage K8s (private) — project ended |
| [larping-kubernetes](https://github.com/ConductionNL/larping-kubernetes) | 4 | Old larping K8s (private) — replaced by larpingapp |
| [s-hertogenbosch-kubernetes](https://github.com/ConductionNL/s-hertogenbosch-kubernetes) | 0 | Den Bosch K8s (private) — project ended |
| [s-hertogenbosch-admin](https://github.com/ConductionNL/s-hertogenbosch-admin) | 0 | Den Bosch admin (private) — project ended |
| [s-hertogenbosch-commonground](https://github.com/ConductionNL/s-hertogenbosch-commonground) | 0 | Den Bosch CG (private) — project ended |
| [s-hertogenbosch-frontend](https://github.com/ConductionNL/s-hertogenbosch-frontend) | 0 | Den Bosch frontend (private) — project ended |
| [nextcloud-argo-bootstrap](https://github.com/ConductionNL/nextcloud-argo-bootstrap) | 0 | ArgoCD bootstrap (private) — superseded by cluster-infra |
| [nextcloud-gitops-values](https://github.com/ConductionNL/nextcloud-gitops-values) | 0 | GitOps values (private) — superseded by cluster-infra |
| [tilburg-woo-helm](https://github.com/ConductionNL/tilburg-woo-helm) | 0 | Tilburg WOO Helm chart — deployment-specific |
| [openzaak-charts](https://github.com/ConductionNL/openzaak-charts) | 0 | OpenZaak Helm charts (fork) — replaced by ExApp |
| [openstad-kubernetes](https://github.com/ConductionNL/openstad-kubernetes) | 0 | OpenStad K8s (fork) — project ended |

## Category 19: ARCHIVE — Old Forks & External Projects (17 repos)

Forks of external projects that were used for evaluation, contribution, or reference. No longer actively needed.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [OpenZaakBrug](https://github.com/ConductionNL/OpenZaakBrug) | 0 | ZDS→ZGW translator (fork) — replaced by OpenConnector |
| [signals](https://github.com/ConductionNL/signals) | 0 | Amsterdam Signalen (fork) — evaluation completed |
| [frontend](https://github.com/ConductionNL/frontend) | 0 | Signalen frontend (fork) — evaluation completed |
| [classification](https://github.com/ConductionNL/classification) | 0 | ML classification (fork) — evaluation completed |
| [sensrnet-registry-frontend](https://github.com/ConductionNL/sensrnet-registry-frontend) | 0 | SensRNet (fork) — project ended |
| [denhaag](https://github.com/ConductionNL/denhaag) | 0 | Den Haag Design System (fork) — evaluation completed |
| [themes](https://github.com/ConductionNL/themes) | 0 | NL Design themes (fork) — replaced by conduction-theme |
| [nl-design-system-with-next.js](https://github.com/ConductionNL/nl-design-system-with-next.js) | 0 | NL Design + Next.js example (fork) — obsolete |
| [nl-portal-libraries](https://github.com/ConductionNL/nl-portal-libraries) | 0 | NL Portal libs (fork) — evaluation completed |
| [schulddossier](https://github.com/ConductionNL/schulddossier) | 0 | Debt management (fork) — project ended |
| [demodam.org](https://github.com/ConductionNL/demodam.org) | 0 | Demodam placeholder (fork) — obsolete |
| [vrijBRP](https://github.com/ConductionNL/vrijBRP) | 0 | VrijBRP open platform (fork) — evaluation completed |
| [open-notificaties](https://github.com/ConductionNL/open-notificaties) | 0 | Open Notificaties (fork) — replaced by n8n |
| [open-zaak](https://github.com/ConductionNL/open-zaak) | 0 | Open Zaak (fork) — replaced by openzaak ExApp |
| [vng-api-common](https://github.com/ConductionNL/vng-api-common) | 0 | VNG API common (fork) — no longer contributing |
| [nginx-env](https://github.com/ConductionNL/nginx-env) | 0 | Nginx env vars (fork) — no longer using custom nginx |
| [recipes-contrib](https://github.com/ConductionNL/recipes-contrib) | 0 | Symfony recipes (fork) — no longer using Symfony |
| [FileSystemOperations](https://github.com/ConductionNL/FileSystemOperations) | 0 | PHP filesystem ops (fork, 2016) — obsolete |

## Category 20: ARCHIVE — Waardepapieren Ecosystem (5 repos)

Blockchain certificate components. The main `waardepapieren` repo stays in KEEP; these supporting repos can be archived.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [waardepapieren-register](https://github.com/ConductionNL/waardepapieren-register) | 4 | Certificate register — project concluded |
| [waardepapieren-service](https://github.com/ConductionNL/waardepapieren-service) | 2 | Certificate service — project concluded |
| [waardepapieren-php](https://github.com/ConductionNL/waardepapieren-php) | 0 | PHP library — project concluded |
| [docker-irma-server](https://github.com/ConductionNL/docker-irma-server) | 0 | IRMA server container — project concluded |
| [id-vault-php](https://github.com/ConductionNL/id-vault-php) | 0 | ID Vault PHP lib — replaced by Keycloak |

## Category 21: ARCHIVE — Miscellaneous Legacy (13 repos)

Repos that don't fit neatly into the above categories.

| Repository | Open Issues | Argumentation |
|---|---|---|
| [NL-Design-System](https://github.com/ConductionNL/NL-Design-System) | 1 | Old NL Design System setup — replaced by nldesign app |
| [nl-design](https://github.com/ConductionNL/nl-design) | 1 | NL Design test setup — replaced by nldesign app |
| [OpenPdc](https://github.com/ConductionNL/OpenPdc) | 0 | Open PDC stub — replaced by OpenRegister schema |
| [OpenPub](https://github.com/ConductionNL/OpenPub) | 0 | Open Pub stub — replaced by OpenCatalogi |
| [OpenWebConcept](https://github.com/ConductionNL/OpenWebConcept) | 0 | OpenWebConcept (fork) — evaluation completed |
| [nlx-training](https://github.com/ConductionNL/nlx-training) | 0 | NLX training files — training completed |
| [single-sign-on](https://github.com/ConductionNL/single-sign-on) | 1 | Mock SSO server — replaced by Keycloak |
| [AI-mail](https://github.com/ConductionNL/AI-mail) | 0 | AI mail experiment (private) — superseded by n8n workflows |
| [frinzj](https://github.com/ConductionNL/frinzj) | 4 | Frinzj application (private) — project ended |
| [bzk-mock](https://github.com/ConductionNL/bzk-mock) | 1 | BZK challenge mock — challenge ended |
| [utrecht-common-ground](https://github.com/ConductionNL/utrecht-common-ground) | 5 | Utrecht CG setup (private) — project ended |
| [larping-api](https://github.com/ConductionNL/larping-api) | 6 | Old larping API (private) — replaced by larpingapp |
| [larping-frontend](https://github.com/ConductionNL/larping-frontend) | 17 | Old larping frontend (private) — replaced by larpingapp, **high issue count worth preserving** |
| [larping-old](https://github.com/ConductionNL/larping-old) | 16 | Oldest larping version (private) — replaced by larpingapp, **high issue count worth preserving** |
| [test-component](https://github.com/ConductionNL/test-component) | 42 | CG tutorial component — used in tutorials, **high issue count from proto-component generator** |
| [recipes-contrib-2](https://github.com/ConductionNL/recipes-contrib-2) | 0 | Symfony recipes v2 — no longer using Symfony |

## Category 22: DELETE — Empty, Test, and Stub Repos (15 repos)

Repos with no meaningful content. Safe to delete permanently.

| Repository | Argumentation |
|---|---|
| [cgc](https://github.com/ConductionNL/cgc) | Description: "testje" — test repo (private) |
| [test-for-pwa](https://github.com/ConductionNL/test-for-pwa) | PWA test stub — empty template output |
| [test-pwa-2](https://github.com/ConductionNL/test-pwa-2) | PWA test stub — empty template output |
| [pwa-test-4](https://github.com/ConductionNL/pwa-test-4) | PWA test stub — empty template output |
| [pwa-pdc-kvk](https://github.com/ConductionNL/pwa-pdc-kvk) | Private, stale since 2021, unnamed |
| [gatsby-poc](https://github.com/ConductionNL/gatsby-poc) | Empty POC, no code |
| [commongroundnu](https://github.com/ConductionNL/commongroundnu) | Private, stale since 2022, no description |
| [id-vault](https://github.com/ConductionNL/id-vault) | Private, stale since 2022, ID Vault app — replaced by Keycloak |
| [Multiplayer-Game](https://github.com/ConductionNL/Multiplayer-Game) | Private, off-topic multiplayer game |
| [Workflow](https://github.com/ConductionNL/Workflow) | Fork, test workflow for unit testing — obsolete |
| [varnish-env](https://github.com/ConductionNL/varnish-env) | Varnish config — no longer using Varnish |
| [conduction-loadbalancer](https://github.com/ConductionNL/conduction-loadbalancer) | Private, stale since 2019, already archived on GitHub |
| [conductionwebsite](https://github.com/ConductionNL/conductionwebsite) | Private, already archived, old website |
| [conduction-website](https://github.com/ConductionNL/conduction-website) | Already archived, old website |
| [docker-trouwplanner](https://github.com/ConductionNL/docker-trouwplanner) | Private, already archived, old container |
| [rag-dataset](https://github.com/ConductionNL/rag-dataset) | Private, empty dataset |
| [zuid-drecht-static](https://github.com/ConductionNL/zuid-drecht-static) | Static page for fictional municipality — demo only |

## Already Archived on GitHub (8 repos)

These repos are already archived — no action needed.

| Repository | Notes |
|---|---|
| [ConductionNL.github.io](https://github.com/ConductionNL/ConductionNL.github.io) | Old GitHub Pages |
| [contactcatalogus](https://github.com/ConductionNL/contactcatalogus) | Contact catalogue |
| [conduction-website](https://github.com/ConductionNL/conduction-website) | Old website |
| [conductionwebsite](https://github.com/ConductionNL/conductionwebsite) | Old website v2 |
| [conduction-loadbalancer](https://github.com/ConductionNL/conduction-loadbalancer) | Old load balancer |
| [docker-trouwplanner](https://github.com/ConductionNL/docker-trouwplanner) | Old trouwplanner container |
| [nextcloud-gitops-deployments](https://github.com/ConductionNL/nextcloud-gitops-deployments) | Old GitOps deployments |
| [waardepapieren-website](https://github.com/ConductionNL/waardepapieren-website) | Waardepapieren website |

---

## Summary Table

| Category | Count | Action |
|---|---|---|
| 1. Active Nextcloud Apps | 13 | KEEP (assign to `developers` team) |
| 2. ExApp Wrappers | 8 | KEEP (assign to `developers` team) |
| 3. Infrastructure & Tooling | 21 | KEEP (assign to `developers` team) |
| 4. Research & Supporting | 18 | KEEP (assign to `developers` team) |
| 5. Common Ground Gateway | 5 | ARCHIVE + PRIVATE |
| 6. Symfony Bundles | 17 | ARCHIVE + PRIVATE |
| 7. CG Components | 35 | ARCHIVE + PRIVATE |
| 8. CG Services | 21 | ARCHIVE + PRIVATE |
| 9. CG Catalogues | 10 | ARCHIVE + PRIVATE |
| 10. Proto Applications | 7 | ARCHIVE + PRIVATE |
| 11. Process Engines | 4 | ARCHIVE + PRIVATE |
| 12. Publiccode Repos | 19 | ARCHIVE + PRIVATE |
| 13. Old Frontends & UIs | 26 | ARCHIVE + PRIVATE |
| 14. PWA Skeletons | 10 | ARCHIVE + PRIVATE |
| 15. Municipality Projects | 13 | ARCHIVE + PRIVATE |
| 16. WOO Municipality Websites | 45 | ARCHIVE + PRIVATE |
| 17. WordPress Plugins | 17 | ARCHIVE + PRIVATE |
| 18. Old Kubernetes | 16 | ARCHIVE + PRIVATE |
| 19. Old Forks | 18 | ARCHIVE + PRIVATE |
| 20. Waardepapieren Ecosystem | 5 | ARCHIVE + PRIVATE |
| 21. Miscellaneous Legacy | 16 | ARCHIVE + PRIVATE |
| 22. Delete Candidates | 17 | DELETE |
| Already Archived | 8 | PRIVATE (already archived) |
| **Total** | **366** | |
