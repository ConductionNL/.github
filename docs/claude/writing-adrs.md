# Writing ADRs for AI Agents

Guidelines for writing Architectural Decision Records (ADRs) that are consumed by
AI coding agents (Claude Code, Hydra pipeline, etc.).

## Core Principle

**Every line in an ADR competes for attention with the actual work.**

ADRs are injected into every agent session as context. Bloated ADRs cause agents to
ignore rules — the same way humans skip long documents. An ADR with 50 crisp rules
outperforms one with 200 verbose rules.

## What Goes In an ADR

**ONLY rules that require JUDGMENT to apply.**

A rule belongs in an ADR if:
- A tool cannot enforce it automatically
- The agent needs to understand WHEN and WHY, not just WHAT
- Applying the rule requires understanding the codebase context

Examples of JUDGMENT rules:
- "Controllers MUST be thin — routing + validation + response only" (judgment: what is "business logic"?)
- "Use schema.org vocabulary where equivalent exists" (judgment: does an equivalent exist?)
- "Multi-tenant isolation at API/service level" (judgment: how to scope data access)

## What Does NOT Go In an ADR

**Rules that can be enforced by tools.**

| Rule | Enforced By | NOT an ADR |
|------|-------------|------------|
| "Lines must not exceed 150 chars" | PHPCS | Script handles it |
| "No var_dump() calls" | PHPCS | Script handles it |
| "Scoped styles required" | ESLint/Stylelint | Script handles it |
| "Named arguments in PHP" | PHPCS custom sniff | Script handles it |
| "SPDX license headers" | `reuse lint` | Script handles it |
| "No hardcoded colors" | Stylelint | Script handles it |
| "publiccode.yml required" | CI check | Script handles it |

**Also not ADRs:** Workflow/process rules about HOW to use the pipeline (these belong
in skill definitions or pipeline docs, not in architecture context).

## Format

Use this compact format — no headers, no essays, no "context" or "alternatives" sections:

```markdown
## Topic Name (ADR-NNN references)

- RULE in imperative form. Brief explanation if needed.
- Another RULE. Example: `code example` if it clarifies.
- Exception: when X, then Y instead.
```

### Do

```markdown
## Backend Layering

- Controller → Service → Mapper (strict 3-layer). Controllers NEVER call mappers directly.
- Controllers: thin (<10 lines/method). Routing + validation + response only.
- Entity setters: POSITIONAL args only. `$e->setName('val')` — NEVER named args.
```

### Don't

```markdown
## ADR-099: Backend Layering — Controller, Service, and Mapper Separation

### Context

In our Nextcloud applications, we've observed that some developers put business
logic directly in controllers, which leads to fat controllers that are hard to test...

### Decision

We have decided to enforce a strict three-layer architecture where controllers
handle only HTTP concerns, services contain all business logic, and mappers
handle database operations...

### Consequences

This means that all new code must follow this pattern. Existing code should be
refactored when touched...
```

The "Don't" version is 3x longer and says the same thing. The agent doesn't need
to know WHY the rule exists — it needs to know WHAT to do.

## Size Budget

| Scope | Target | Max |
|-------|--------|-----|
| Single ADR topic | 5-15 lines | 20 lines |
| All ADRs combined | 80-120 lines | 200 lines |
| Estimated tokens | 1,000-2,000 | 3,000 |

At 200 lines / 3,000 tokens, the ADRs consume ~1.5% of a 200K context window.
Above that, you're paying diminishing returns.

## Token Efficiency Tips

1. **Use bullet points, not paragraphs.** Bullets are ~40% shorter than prose.
2. **Use code examples instead of descriptions.** `$e->setName('val')` is clearer
   than "use positional arguments when calling entity setter methods."
3. **Combine related rules.** "Controller → Service → Mapper (strict 3-layer)"
   replaces three separate rules.
4. **State the rule, not the reason.** "NEVER `\OC::$server`" vs "Because the
   Nextcloud DI container should be used instead of the legacy static service
   locator pattern, you must never use `\OC::$server`."
5. **Use exceptions sparingly.** If a rule has more exceptions than applications,
   reconsider whether it's a rule.

## Deduplication

Each rule should appear ONCE. If a rule applies to multiple topics, put it in the
most specific topic and reference it:

```markdown
## Security
- Entity setters: positional args only (see Backend Layering).
```

NOT:
```markdown
## Backend Layering
- Entity setters: POSITIONAL args only.

## Security  
- Entity setters: POSITIONAL args only. This is important for security.

## Code Quality
- Entity setters: POSITIONAL args only. This prevents bugs.
```

## Compounding Improvements

When an agent makes a mistake that an ADR should have prevented:
1. Check if the rule already exists — maybe it's too wordy and got ignored
2. If missing, add a 1-line rule to the relevant topic
3. If existing but ignored, make it shorter and more prominent

Never add a new ADR file for a single rule. Add it to the existing topic.

## Review Checklist

Before merging an ADR change:
- [ ] Every rule requires judgment (can't be a script)
- [ ] No rule is duplicated across topics
- [ ] No paragraphs — bullets only
- [ ] Total ADR file is under 200 lines
- [ ] Added rules have been tested by running the agent and verifying it follows them

---

## ADRs in practice — where they live

Every Conduction app repo follows a clean split:

| Location | Scope | Who writes |
|---|---|---|
| [`hydra/openspec/architecture/`](https://github.com/ConductionNL/hydra/tree/main/openspec/architecture) | **Org-wide ADRs** — apply to every Conduction app | Humans (architecture-level decisions) |
| `<app>/openspec/architecture/` | **Repo-specific ADRs** — apply only to that app (data model choices, domain standards, storage decisions) | Authored by Specter during research; evolved by humans |

App repos do **NOT** carry copies of the org-wide ADRs. Earlier they had stale duplicates that drifted (e.g. a copy saying `fetch()` while hydra's master said `axios`) — those copies were removed across every app repo that had them.

**How agents see org-wide ADRs:**
- Reviewer + builder containers copy the relevant ADRs from the hydra repo at image-build time.
- Agents operating in an app repo outside a container (IDE humans, manual `/opsx-ff` runs) read them from hydra's `main` branch directly.
- `specter-prepare-context` surfaces the applicable org-wide ADRs in `context-brief.md` for each spec so the builder sees them pre-loaded.

**Rule of thumb for where a new ADR belongs:**
- Applies to ≥2 Conduction apps → org-wide, in `hydra/openspec/architecture/`.
- Applies only to one app's domain/storage/auth choice → app-specific, in `<app>/openspec/architecture/`.

## The org-wide ADRs

| ADR | Topic |
|---|---|
| [001](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-001-data-layer.md) | Data layer (OpenRegister, entities, mappers) |
| [002](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-002-api.md) | API design (REST, Common Ground, NL API) |
| [003](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-003-backend.md) | Backend (PHP, Nextcloud, services, spec traceability) |
| [004](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-004-frontend.md) | Frontend (Vue, components, settings) |
| [005](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-005-security.md) | Security (auth, CORS, input validation) |
| [006](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-006-metrics.md) | Metrics & observability |
| [007](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-007-i18n.md) | i18n (English primary, Dutch required) |
| [008](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-008-testing.md) | Testing (PHPUnit, Newman, Playwright) |
| [009](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-009-docs.md) | Documentation |
| [010](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-010-nl-design.md) | NL Design System (government theming) |
| [011](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-011-schema-standards.md) | Schema standards (schema.org, DCAT) |
| [012](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-012-deduplication.md) | Deduplication |
| [013](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-013-container-pool.md) | Container pool (model selection, turns, no-loop policy) |
| [014](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-014-licensing.md) | Licensing (EUPL-1.2) |
| [015](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-015-common-patterns.md) | Common patterns (rate-limit retry, dep enforcement) |
| [016](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-016-routes.md) | Routes (`appinfo/routes.php` is the only registration path) |
| [017](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-017-component-composition.md) | Component composition |
| [018](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-018-widget-header-actions.md) | Widget header actions |
| [019](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-019-integration-registry.md) | Integration registry |
| [020](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-020-gate-scope-to-pr-diff.md) | Gate scope is the PR diff, not the whole repo |
| [021](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-021-bounded-fix-scope-by-shape.md) | Reviewer bounded-fix scope is defined by change shape, not line count |
| [022](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-022-apps-consume-or-abstractions.md) | Apps consume OpenRegister abstractions (RBAC, audit trail, archival, relations) |
| [023](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-023-action-authorization.md) | Action-level authorization via admin-configured action/group mappings |
| [024](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-024-app-manifest.md) | App manifest (fleet-wide adoption) |
| [025](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-025-i18n-source-of-truth.md) | i18n source-of-truth |
| [029](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-029-route-reachability-gate.md) | Route reachability gate |
| [030](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-030-journeydoc-pattern.md) | Journeydoc — capture-driven user documentation |
| [031](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-031-schema-declarative-business-logic.md) | Schema-declarative business logic over service classes |
| [032](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-032-spec-sizing-and-chaining.md) | Spec sizing taxonomy and chained-spec routing |

ADRs 026–028 are reserved for in-flight numbering.
