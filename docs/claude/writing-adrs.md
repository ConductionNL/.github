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
## ADR-008: Backend Layering — Controller, Service, and Mapper Separation

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
