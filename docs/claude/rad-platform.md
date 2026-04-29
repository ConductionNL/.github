# Conduction RAD Platform

> One page covering the whole stack: what we ship, why it exists, and how an idea becomes a merged PR without anyone writing CRUD code by hand.

This is the orientation doc for new contributors and outside reviewers. If you've been pointed at one PR in the chain, read this first to see where it sits.

## What it is

The Conduction Rapid Application Development (RAD) platform is a **declarative app factory** for Nextcloud apps in the public-administration domain. The bet:

> Most government-app code that gets written today is structurally identical between apps — CRUD, state machines, dashboards, settings panels, notifications, integrations. The platform absorbs the shape so apps only write what's genuinely domain-specific.

The result, after a 2026-04-29 audit across decidesk + shillinq + pipelinq:

- **5,000+ lines of structurally-identical code** lifted into platform layers across three apps
- **Future apps inherit the same shape for free** — a new app's spec output collapses to schemas + a manifest + a small number of bespoke services for genuinely-custom logic
- **Specs become small** — one mechanism per spec, ≤15 tasks, parallel-mergeable

## The four-layer architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Apps (decidesk, pipelinq,               │
│                     shillinq, opencatalogi, …)             │
│   Schemas + manifest.json + a few bespoke services for      │
│   genuinely-domain logic. Most apps are 90% declarative.    │
└────────┬────────────────────────────────────────────────────┘
         │ consumes
         ▼
┌─────────────────────────────────────────────────────────────┐
│              @conduction/nextcloud-vue (lib)                 │
│   useObjectStore + manifest renderer (CnAppRoot,             │
│   CnPageRenderer, CnAppNav, CnIndexPage, CnDetailPage,       │
│   CnDashboardPage, CnFormDialog, …) +                        │
│   manifest extensions (appSettings, dashboard.layout,        │
│   pages[].config.actions).                                   │
└────────┬────────────────────────────────────────────────────┘
         │ talks to
         ▼
┌─────────────────────────────────────────────────────────────┐
│                      OpenRegister                           │
│   Schemas + objects + RBAC + audit + versioning +           │
│   archival + relations + integration providers              │
│   (Activity / Calendar / Contacts / Mail / Files /          │
│   Smart Picker / Profile) + event-driven-architecture +     │
│   webhook-payload-mapping + notificatie-engine +            │
│   four declarative annotations on the schema:               │
│     • x-openregister-lifecycle                              │
│     • x-openregister-aggregations                           │
│     • x-openregister-calculations                           │
│     • x-openregister-notifications                          │
└────────┬────────────────────────────────────────────────────┘
         │ runs in
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nextcloud (host)                         │
│   Auth, Activity, Calendar, Contacts, Mail, Talk,           │
│   Files, Notifications, system tags, IEventDispatcher,      │
│   IGroupManager, IRequest, INotificationManager.            │
└─────────────────────────────────────────────────────────────┘
```

Above this stack sits the **agentic factory**:

```
Specter (concurrentie-analyse) ──── Hydra ──── App repo
   intelligence → specs           specs → code     →     PR ready for human review
```

- **Specter** gathers market intelligence (75K tenders, ~7K canonical features, 100 competitors), classifies each feature into a platform mechanism, and emits one OpenSpec change per (feature, mechanism) pair.
- **Hydra** picks up `*:queued` issues and runs the build → quality → code review → security review → applier loop with four container personas (Al Gorithm builder on Haiku, Juan Claude reviewer on Sonnet, Clyde Barcode security on Sonnet, Axel Pliér applier on Sonnet).

## What each platform layer provides

A working knowledge of the catalog is the difference between writing 200 lines of dead code and writing 0. The **single source of truth** is [`openregister/openspec/platform-capabilities.md`](https://github.com/ConductionNL/openregister/blob/development/openspec/platform-capabilities.md). Five buckets:

### 1. Schema annotations — declarative, no code

| Annotation | Replaces |
|---|---|
| `x-openregister-relations` | Hand-coded link tables |
| `x-openregister-archival` | Hand-coded retention metadata |
| `x-openregister-seeds` | Hand-coded seeders |
| `x-openregister-lifecycle` | `<Resource>Service::transition()` + `<Resource>Controller::lifecycle` + `TRANSITIONS` const + `POST /api/<resource>/{id}/lifecycle` route |
| `x-openregister-aggregations` | `<Resource>AnalyticsService::get*()` + `<Resource>AnalyticsController` + `/api/analytics/...` routes |
| `x-openregister-calculations` | Hand-written PHP/Vue computed fields, virtual properties, derived display values |
| `x-openregister-notifications` | `<Resource>NotificationService::notify*()` + per-channel dispatch boilerplate |

### 2. NC-app integration providers — surface objects in NC apps

| Provider | What it integrates |
|---|---|
| `activity-provider` | NC Activity feed, dashboard widget, email digest |
| `calendar-provider` | NC Calendar — object date fields surface as read-only events |
| `contacts-actions` | NC Contacts — ContactsMenu provider matching by email/name/org |
| `mail-sidebar` | NC Mail — viewing an email shows linked OpenRegister objects |
| `mail-smart-picker` | NC Mail / Talk / Text / Collectives — Smart Picker reference provider |
| `file-actions` | NC Files — rename / copy / move / version on object-attached files |
| `profile-actions` | NC user profile — GDPR export, password, API tokens |
| `object-interactions` | Notes / tasks / files / tags / audit on every object (wraps NC's CalDAV + ICommentsManager + IRootFolder + tag manager) |

### 3. Object interactions — free with every object

Notes, tasks, files, tags, audit trail (immutable, hash-chained), versioning, deep links — all wired through `object-interactions` against NC's native subsystems. No per-app code.

### 4. Infrastructure — apps consume but never write

`event-driven-architecture` (39+ typed events + `IEventDispatcher`), `webhook-payload-mapping` (Twig template payloads, retry/HMAC/dead-letter), `notificatie-engine` (INotificationManager + channel adapters + user prefs), `authorization-rbac-enhancement` (per-object ACLs), `saas-multi-tenant`, `zoeken-filteren` (search + facet + pagination over Postgres / Solr / ES backends), `mappings`, `geo-metadata-kaart`, `mcp-discovery`, `graphql-api` + `realtime-updates`, `openapi-generation`, `data-import-export`.

### 5. Frontend abstractions — `@conduction/nextcloud-vue`

`useObjectStore` (canonical Pinia store), manifest renderer (`CnAppRoot`, `CnPageRenderer`, `CnAppNav`, `CnIndexPage`, `CnDetailPage`, `CnDashboardPage`), schema-driven dialogs (`CnFormDialog` / `CnAdvancedFormDialog` / `CnSchemaFormDialog`), `appSettings.fields[]` / `dashboard.layout[]` / `pages[].config.actions[]` declarative manifest extensions.

## What an app actually writes

After walking the catalog top-down, app code is justified for:

- **LLM / orchestration / template generation** — decidesk's minutes-draft generation, action-item extraction.
- **External system clients / bidirectional sync** — pipelinq's CardDAV ↔ CRM bridging, KvK enrichment, ICP scoring.
- **Bespoke UI** the manifest can't express — DAG editors, real-time WebSocket boards, visual form builders.
- **Workflow orchestration** with parallel branches / joins / conditional cascades — pipelinq's automation engine.

Everything else lands in:
- The schema (with annotations)
- The manifest (with declarative shells, dashboards, settings, page actions)
- A handful of small classes for guard implementations + side-effect listeners + LLM template files

A typical Tier 4 app has **zero per-schema CRUD controllers**, **zero per-schema Pinia stores** (one canonical store wraps everything), and **zero `Settings.vue` / `Dashboard.vue`** (the manifest renders both).

## How a feature becomes code

```
        Tender / competitor / standard / GitHub issue
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│ Specter (concurrentie-analyse)                            │
│  Phase 5  — Classify into 9 buckets:                      │
│             ADR / CRUD / lifecycle / aggregation /        │
│             manifest-shell / notification /               │
│             NC-integration / shared-business-logic /      │
│             app-specific.                                 │
│             Sets `platform_mechanism` per feature.        │
│  Phase 5b — Split features whose description maps to     │
│             multiple mechanisms into N sub-features.      │
│             One sub-feature → one spec.                   │
│  Phase 6  — App design (ARCHITECTURE.md, FEATURES.md)    │
│             references the catalog rows.                  │
│  Phase 7  — App create (boostraps the repo).              │
│  Phase 7b — Run two linters before queueing for hydra:    │
│             • lint-spec-for-redundant-crud.py             │
│               (catches bespoke wrappers per ADRs 022 +    │
│               024–027)                                    │
│             • check-spec-size.py                          │
│               (catches bundles per ADR-028)               │
│  Output   — One OpenSpec change directory per spec, with  │
│             a GitHub issue tagged ready-to-build.         │
└────────────────────────────┬──────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────┐
│ Hydra (hydra)                                              │
│  Supervisor picks up *:queued.                             │
│  Builder (Al Gorithm, Haiku) reads:                        │
│    • the spec's tasks.md + design.md                       │
│    • implementation-brief.md (ADRs + catalog rows from     │
│      Specter Phase 6 baked into /pr-context/)              │
│    • Step 0 in team-backend / team-frontend SKILL.md       │
│      — read platform-capabilities.md before anything       │
│      else                                                  │
│  Mechanical gates run before push (10 gates incl.          │
│    redundant-controller).                                  │
│  Code reviewer (Juan Claude, Sonnet) + security reviewer  │
│    (Clyde Barcode, Sonnet).                                │
│  Applier (Axel, read-only Sonnet) on post-fix diff.        │
│  Output  — PR on the app repo's feature branch, ready      │
│            for human review (or auto-merge if `yolo`).     │
└───────────────────────────────────────────────────────────┘
```

## The 4-layer defence against bespoke reinvention

Every spec passes through four enforcement points before code reaches the app repo:

| # | Layer | Where | What it catches |
|---|---|---|---|
| 1 | **Specter classifier** | `app-pipeline` SKILL.md Phase 5 | Routes the feature to the right `platform_mechanism` so the spec output uses the catalog path |
| 2 | **Specter splitter + spec-time linters** | `app-pipeline` Phase 5b + Phase 7b | Splits multi-mechanism features into N specs; runs `lint-spec-for-redundant-crud.py` + `check-spec-size.py` before queueing |
| 3 | **Hydra mechanical gates** | `scripts/run-hydra-gates.sh` (10 gates) | After the builder writes code: catches pass-through controllers, redundant CRUD, missing auth, IDOR, semantic-auth mismatch, stub code, missing SPDX, etc. |
| 4 | **Reviewer + applier judgment** | Sonnet/Opus container personas | Catches anything the mechanical layers missed; fix-applier verdict is binary go/no-go on the post-fix diff |

A bespoke wrapper has to slip past all four. Each layer is independently effective; combined they're decisive.

## ADRs that pin the contract

| ADR | What it codifies |
|---|---|
| ADR-019 | Integration registry — the pluggable surface for NC-app integrations |
| ADR-022 | Apps consume OR abstractions over local duplication |
| ADR-024 | Declarative state machines via `x-openregister-lifecycle` |
| ADR-025 | Declarative aggregations (+ calculations) via `x-openregister-aggregations` / `x-openregister-calculations` |
| ADR-026 | Declarative app shell — `appSettings`, `dashboard`, `pages[].config.actions` in `manifest.json` |
| ADR-027 | Declarative notifications via `x-openregister-notifications` |
| ADR-028 | Small, single-capability specs (one mechanism per spec, ≤15 tasks, explicit `depends_on`) |

The ADRs live in `hydra/openspec/architecture/` and are copied into builder / reviewer containers at image-build time. The platform-capabilities catalog lives in `openregister/openspec/platform-capabilities.md` and is copied alongside.

## Spec shape (per ADR-028)

A spec covers exactly one of these shapes:

| Shape | Slug pattern | Example |
|---|---|---|
| Schema-introduction | `<schema>-schema` | `meeting-schema` |
| Annotation extension | `<schema>-<annotation>` | `meeting-lifecycle`, `action-item-aggregations` |
| Manifest extension | `<app>-<section>` or `<schema>-<page-section>` | `decidesk-app-settings`, `meeting-detail-actions` |
| Integration registration | `<schema>-<provider>` | `meeting-calendar-integration`, `decision-activity-feed` |
| Bespoke domain capability | `<app>-<domain>` | `minutes-llm-extraction`, `pipelinq-prospect-scoring` |
| Cross-cutting infra | `<app>-<concern>` | `decidesk-eslint-flat-config` |

Hard limits, mechanically enforced by `hydra/scripts/lib/check-spec-size.py`:

- ≤ 15 tasks per spec
- Exactly 1 platform mechanism in `tasks.md`
- ≤ 1 schema modified
- ≤ 10 files-likely-affected (advisory)

Specs that need more become multiple specs with explicit `depends_on` chains. The supervisor enforces `depends_on` at dispatch time per `hydra.json` v2 — a sub-spec only goes to `build:queued` when its prerequisites are merged.

## Naming conventions

| Thing | Pattern | Example |
|---|---|---|
| Spec slug | `<target>-<mechanism>`, lowercase, hyphens | `meeting-lifecycle` |
| Annotation | `x-openregister-<noun>` | `x-openregister-aggregations` |
| Integration provider | `<noun>-provider` or `<noun>-actions` or `<noun>-sidebar` | `calendar-provider`, `contacts-actions` |
| Repo branch | `feature/<short-description>` | `feature/declarative-engines-adr024-027` |
| ADR | `adr-NNN-<short-name>.md` | `adr-024-declarative-state-machines.md` |

## How to extend the platform

When you build a new platform mechanism:

1. **ADR first.** A new annotation / provider / mechanism gets a 1-page ADR in `hydra/openspec/architecture/` explaining the principle, the contract, and the migration recipe.
2. **Implementation spec second.** The change directory in `openregister/openspec/changes/` (or `nextcloud-vue/openspec/changes/`) holds proposal + design + tasks + the spec delta against an existing implemented spec. The implementation rides on existing infrastructure (event-driven-architecture, webhook-payload-mapping, etc.) rather than introducing a parallel subsystem.
3. **Catalog third.** Add a row to `openregister/openspec/platform-capabilities.md` with status, spec link, and one-line description. Specter and Hydra read this — your new mechanism becomes visible to both.
4. **Skills update fourth.** team-backend / team-frontend / team-architect SKILL.md may need a row added so builders know to use the mechanism. The Step 0 block already points at the catalog, so explicit per-mechanism updates are usually optional.

## How to extend Specter's classifier

When a new feature shape emerges that the existing buckets don't catch:

1. Add a new bucket to Phase 5 in `concurrentie-analyse/.claude/skills/app-pipeline/SKILL.md` with: name, mechanism, keyword heuristic, rescue list.
2. If the bucket has multiple sub-mechanisms (like NC-integration providers), add an `INTEGRATION_PROVIDERS`-style map.
3. The platform_mechanism column on `canonical_features` carries the result; Phase 6 (App Design) and Phase 7 (App Create) read it to emit the right spec.

## Glossary

| Term | Meaning |
|---|---|
| **Annotation** | A `x-openregister-*` key on a JSON Schema declaring a platform-managed behavior |
| **Mechanism** | One unit of platform capability — an annotation, a manifest section, an integration provider, a canonical store, or a bespoke service |
| **Bundle (anti-pattern)** | A spec that mixes multiple mechanisms; rejected by `check-spec-size.py` |
| **Wrapper (anti-pattern)** | A controller/service that just pass-throughs to OpenRegister; rejected by `lint-spec-for-redundant-crud.py` and `hydra-gate-redundant-controller` |
| **Tier** | Adoption level for the manifest renderer. Tier 0 = no manifest; Tier 4 = full manifest-driven shell. |
| **Catalog** | `openregister/openspec/platform-capabilities.md` — the single source of truth for what the platform provides |
| **Brief** | The context bundle Specter generates per spec, mounted at `/pr-context/` in builder containers |
| **Persona** | One of Hydra's four container roles — Al Gorithm (builder), Juan Claude (reviewer), Clyde Barcode (security), Axel Pliér (applier) |

## Where to look

| For | Look at |
|---|---|
| The platform's full capability list | [`openregister/openspec/platform-capabilities.md`](https://github.com/ConductionNL/openregister/blob/development/openspec/platform-capabilities.md) |
| ADRs that pin the architecture | [`hydra/openspec/architecture/`](https://github.com/ConductionNL/hydra/tree/development/openspec/architecture) |
| How a feature becomes a spec | [`concurrentie-analyse/.claude/skills/app-pipeline/SKILL.md`](https://github.com/ConductionNL/market-intelligence/blob/development/.claude/skills/app-pipeline/SKILL.md) |
| How a spec becomes code | [`hydra/CLAUDE.md`](https://github.com/ConductionNL/hydra/blob/development/CLAUDE.md) |
| The mechanical gates that catch wrappers | [`hydra/scripts/lib/`](https://github.com/ConductionNL/hydra/tree/development/scripts/lib) — `detect-redundant-controllers.py`, `lint-spec-for-redundant-crud.py`, `check-spec-size.py` |
| The team skills that brief builders | [`hydra/.claude/skills/team-{backend,frontend,architect,reviewer}/SKILL.md`](https://github.com/ConductionNL/hydra/tree/development/.claude/skills) |
| A reference Tier-4 app | [`decidesk`](https://github.com/ConductionNL/decidesk) (manifest at `src/manifest.json`) |
