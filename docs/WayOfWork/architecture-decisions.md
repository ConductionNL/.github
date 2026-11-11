---
id: architecture-decisions
title: Architecture decisions
sidebar_label: Architecture decisions
sidebar_position: 3
description: The company-wide architecture decision records (ADRs) every Conduction app follows, by number, title and a one-line summary.
---

# Architecture decisions

Company-wide architecture decision records (ADRs) apply to every Conduction app. This page lists them by number, so a product page can cite "ADR-083" and a reader can look it up here.

The ADR files live in our internal Hydra repository, under `openspec/architecture/`. That repository is private, so this page is the public index. How ADRs relate to specs is on [Spec-driven development](spec-driven-development.md#where-specs-and-decisions-live).

## How to read the status column

- **Core rule.** ADR-001 to ADR-016, except ADR-007 and ADR-013. These are the compact base rules every agent session loads. They carry no status field because they are the standing baseline.
- **Accepted.** The decision is in force.
- **Proposed.** The decision is written and under review. Many proposed ADRs already have a gate or a test that enforces them; the status is what the file says, not a measure of adoption.

Numbers 027, 028 and 116 to 121 are not in use. A number is never reused.

## Data, API and backend

| ADR | Title | Summary | Status |
| --- | --- | --- | --- |
| 001 | Data layer | All domain data lives in OpenRegister objects; app config lives in `IAppConfig`. | Core rule |
| 002 | API | One URL pattern, standard HTTP methods, `_page`/`_limit` pagination, Nextcloud auth only. | Core rule |
| 003 | Backend | Controller, service, mapper in strict layers; constructor injection; no static locators. | Core rule |
| 005 | Security | Nextcloud authentication only, admin checks on the backend, per-object authorization on every mutation. | Core rule |
| 006 | Metrics | Every app exposes a Prometheus metrics endpoint and a public health endpoint. | Core rule |
| 011 | Schema standards | schema.org as the primary vocabulary, relations through OpenRegister, breaking changes migrate. | Core rule |
| 012 | Deduplication | Search OpenRegister and the shared library before building a new capability. | Core rule |
| 014 | Licensing | Code is EUPL-1.2; `info.xml` says `agpl` because the App Store does not know EUPL. | Core rule |
| 015 | Common patterns | Patterns found in three or more reviews, fixed across all files in one pass. | Core rule |
| 016 | Routes | `appinfo/routes.php` is the only place routes are registered. | Core rule |
| 019 | Integration registry pattern | Things linked to an OpenRegister object are declared in a two-sided registry. | Accepted |
| 022 | Apps consume OpenRegister abstractions | When OpenRegister offers a capability, apps use it instead of building their own. | Accepted |
| 023 | Action-level authorization | OpenRegister decides who may read or write which objects; apps trust its filtering. | Accepted |
| 031 | Schema-declarative business logic | Behaviour that a schema extension can express is declared in the schema, not coded. | Proposed |
| 041 | Cross-app commands via events | One app asks another to act through typed Nextcloud events, not HTTP calls. | Proposed |
| 045 | OpenRegister owns the MDM surface | Data quality and deduplication are schema-scoped OpenRegister features. | Proposed |
| 047 | OpenRegister owns the AVG/DSAR workflow | Data subject requests are one OpenRegister capability, not rebuilt per app. | Proposed |
| 048 | Cross-app semantic references | References between apps resolve by semantic type, not by app id or schema slug. | Proposed |
| 050 | Response envelope | Endpoints return flat, purpose-shaped payloads without a wrapper envelope. | Accepted |
| 051 | Semantic object handoff | Cross-app workflows hand objects over by semantic type. | Proposed |
| 052 | URL canonicalization | Every URL comparison uses one shared canonicalizer. | Accepted |
| 058 | Bounded object queries | Object queries get a default limit when the caller sets none. | Proposed |
| 065 | One flow engine and one canvas | The flow engine lives in OpenRegister; the flow canvas lives in the shared Vue library. | Accepted |
| 066 | Cross-app leaf registration | Sibling apps may add read-only leaf providers through a typed collect event. | Accepted |
| 069 | Background jobs, repair steps and listeners | One directory and one set of conventions for jobs, repair steps and listeners. | Proposed |
| 070 | OpenRegister-backed persistence is the default | New apps store data in registers; own database tables need an exception ADR. | Proposed |
| 078 | Object event work placement | Listener work that cannot change the write runs asynchronously. | Proposed |
| 083 | OpenRegister dependency shape | OpenRegister is constructor-injected and guarded at runtime. | Proposed |
| 084 | OpenRegister published contract | OpenRegister publishes interfaces; consumers type-hint the interface, never the class. | Proposed |
| 091 | External API surface belongs to OpenConnector | Endpoints authenticated by anything other than a Nextcloud session live in OpenConnector. | Proposed |
| 092 | Retire the classic OpenConnector dialect | Old ingestion entities give way to OpenRegister's flow engine. | Proposed |
| 098 | Fleet workflow convergence | Every workflow runs on the OpenRegister engine; a node can be a person, group or agent. | Proposed |
| 099 | Acting on behalf of a user | Acting as a user is a granted, run-scoped identity with one implementation. | Accepted |
| 100 | A well-formed app | App id, directory name and `lib/` vocabulary are one consistent fact. | Proposed |
| 103 | Virtual schemas for Nextcloud entities | Nextcloud entities appear as virtual schemas with semantic providers. | Proposed |
| 105 | Controller exception translation | Controllers translate service exceptions into JSON responses or declare them. | Accepted |
| 106 | Request lifecycle work placement | Setup work runs at install, upgrade or cron, never during a request. | Proposed |
| 107 | Money and effort ownership | Each kind of money and effort has one owning app. | Proposed |

## Security and integrations

| ADR | Title | Summary | Status |
| --- | --- | --- | --- |
| 054 | Public surface hardening | Public endpoints get rate limits, CSRF on writes, webhook secrets and signed tokens. | Proposed |
| 055 | Authorization gate extensions | Checks for actor parameters, write symmetry, tenant scope and RBAC bypass flags. | Proposed |
| 060 | Test reality and phantom green | Privileged actions reachable by non-admins need a test that can actually fail. | Proposed |
| 064 | Credential custody | Apps store a credential reference; the secret lives in the credential broker. | Proposed |
| 067 | Shared egress plane | Outbound calls to shared third-party APIs go through one adapter and one egress guard. | Proposed |
| 082 | Public endpoint throttling | Every public endpoint is throttled, and the attribute alone is not enough. | Proposed |
| 095 | Tool grants are a structure | An agent's tool grants are app, subject, action and tool, not loose strings. | Accepted |
| 102 | Config fail-mode | Every security-relevant config read states what happens when the value is empty. | Accepted |

## Frontend and user interface

| ADR | Title | Summary | Status |
| --- | --- | --- | --- |
| 004 | Frontend | Pinia stores, Nextcloud axios, translated strings, shared components. | Core rule |
| 007 | Internationalization | Every app supports Dutch and English. | Accepted |
| 010 | NL Design System | Design tokens instead of hard-coded styling, scoped styles, WCAG AA. | Core rule |
| 017 | Component composition | Self-contained components are not wrapped in extra layout containers. | Accepted |
| 018 | Features and roadmap menu | Every app links to its features and roadmap from the navigation settings. | Proposed |
| 024 | App manifest | Every app describes its pages and menus in a validated `manifest.json`. | Accepted |
| 025 | i18n source of truth | One source of truth for translations and API language negotiation. | Proposed |
| 026 | Store migration patterns | Apps load OpenRegister data through the shared object store. | Accepted |
| 033 | Collaborative editing | Rules for showing and editing an OpenRegister object on a detail page. | Proposed |
| 034 | AI chat companion | One shared chat companion component family for every app. | Proposed |
| 036 | Universal widget manifest | Every page type uses one `widgets[]` array on a grid. | Proposed |
| 042 | First-time setup wizard | A shared setup wizard, declared in the manifest. | Proposed |
| 043 | Product walkthrough engine | A shared walkthrough engine, declared in the manifest. | Proposed |
| 044 | Menu architecture | Apps build their menu through one shared manifest pipeline. | Proposed |
| 049 | Declarative widget vocabulary | Built-in widget types come before custom widgets. | Proposed |
| 053 | Semantic color tokens | Widget colours are semantic tokens, not colour values. | Proposed |
| 057 | i18n locale parity and key hygiene | A check fails when a locale misses a key the English file has. | Proposed |
| 059 | Keyboard operability of custom controls | Anything that responds to a pointer also works with a keyboard. | Proposed |
| 061 | Frontend bundle and boot hygiene | The shared library is tree-shakeable and apps boot lean. | Proposed |
| 062 | Detail page grid discipline | A detail-page widget fills its grid cell and never overflows it. | Proposed |
| 071 | Shared frontend runtime | The frontend runtime lives in `@conduction/nextcloud-vue`. | Proposed |
| 072 | Component absorption | A component hand-rolled in two apps moves into the shared library. | Proposed |
| 073 | Vue 3 library target | Every app targets the Vue 3 line of the shared library. | Proposed |
| 077 | Semantic icon vocabulary | One icon per concept across the fleet. | Proposed |
| 079 | Settings surface placement | Admin settings live in Nextcloud's settings; the gear is per user. | Proposed |
| 080 | Store plane | OpenRegister owns discovery; each app owns its own install. | Proposed |
| 081 | Vue 3 migration | The shared library moves to Vue 3 before any app does. | Accepted |
| 085 | Forms and journeys | Forms and journeys are OpenRegister data, rendered by one runtime. | Proposed |
| 087 | Office suite abstraction | File conversion goes through Nextcloud's conversion manager. | Proposed |
| 089 | Communal core loads once | The shared library is made smaller before several apps share it on one page. | Proposed |
| 096 | Dashboard, index and detail | An app opens on a dashboard; collections are index pages leading to detail pages. | Accepted |
| 097 | Navigation budget | Four main menu domains, six at most. | Proposed |
| 101 | Universal in-app editing | One edit shell that appears in every app. | Proposed |
| 109 | Public portal shared runtime | The public portal runs the same manifest runtime as the apps. | Proposed |
| 110 | App navigation contract | Links to other apps sit in an Integrations section, not the main menu. | Proposed |
| 111 | Demo data and setup walkthrough | Every app ships demo data and offers it first in its setup walkthrough. | Proposed |
| 112 | Reports are one page | An app's reports are one page of cards. | Proposed |
| 113 | Cross-app widgets declare their app | A widget that needs another app says so and shows a set-up state when it is absent. | Proposed |
| 114 | App chrome is seven items | The fixed app chrome has seven items, checked by one gate. | Proposed |

## Platform and products

| ADR | Title | Summary | Status |
| --- | --- | --- | --- |
| 030 | Journeydoc | User documentation is produced from captured screenshots of the running app. | Accepted |
| 035 | MCP per-app coverage | Every app with user actions exposes them as MCP tools. | Proposed |
| 037 | Modular config fragments | Each change adds its own register or manifest fragment file. | Accepted |
| 039 | Root configuration consolidation | Root config files follow one shared template. | Accepted |
| 040 | AppHost | OpenRegister's AppHost takes over observability and boilerplate from apps. | Proposed |
| 046 | Portal contribution contract | Apps contribute to the portal through one declared class. | Accepted |
| 063 | MCP as a platform abstraction | Schemas declare MCP tools; OpenRegister derives them. | Proposed |
| 075 | Document generation has one channel | One app owns document and PDF generation for the fleet. | Proposed |
| 076 | AppHost settings plane | The app scaffold and settings are AppHost services. | Proposed |
| 086 | Portaliq headless CMS | Portaliq is the fleet's content system; its API is the product. | Proposed |
| 094 | Automation targets the OpenRegister flow engine | New automation uses OpenRegister's flow engine, not n8n. | Accepted |
| 104 | Spectr market intelligence app | Market intelligence is rebuilt as a configured app. | Proposed |
| 108 | Public surface placement | Citizen-facing object access belongs to Portaliq. | Proposed |

## Engineering process

| ADR | Title | Summary | Status |
| --- | --- | --- | --- |
| 008 | Testing | Every service, component, endpoint and spec scenario gets a test. | Core rule |
| 009 | Documentation | Every user-facing feature is documented with screenshots. | Core rule |
| 013 | Unified container pool | All pipeline containers share one slot pool. | Accepted |
| 020 | Gates scoped to the PR diff | Mechanical gates judge the lines a pull request changed. | Accepted |
| 021 | Bounded fix scope by shape | A reviewer may fix only changes of a defined shape. | Accepted |
| 029 | Route reachability gate | Every controller method that returns a response has a route, and every route a method. | Accepted |
| 032 | Spec sizing and chaining | A proposal declares its kind, which sets its route and budget. | Proposed |
| 038 | Canonical requirement heading | One heading form for requirements, with an optional id suffix. | Proposed |
| 056 | Spec canonical home and status truth | A spec exists when it is on the default branch; status claims need an anchor. | Proposed |
| 068 | Skill maturity and self-learning | One seven-level maturity model for skills. | Proposed |
| 074 | E2E surface coverage baseline | Every UI surface has a Playwright test that can fail. | Proposed |
| 088 | Agent-authored artefacts are marked | Anything an agent writes carries a durable mark. | Proposed |
| 090 | Dependency integrity gates | A build does not start from a tree that disagrees with its lockfile. | Proposed |
| 093 | Composer dependency cooldown | New composer releases wait a cooldown period before Dependabot proposes them. | Proposed |
| 115 | A green instrument is not a present feature | A check that judged nothing says so, and nobody counts it as a pass. | Proposed |

## Adding or changing an ADR

Read [Writing ADRs](../claude/writing-adrs.md) for the format and for when a decision belongs in an app's own `openspec/architecture/` instead. When a new company-wide ADR lands, add its row here in the same pull request.
