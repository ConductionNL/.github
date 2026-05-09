---
title: Hydra
sidebar_label: Hydra
sidebar_position: 1
description: Conduction's agentic spec-driven CI/CD pipeline — what it is, how it works, and how to put it to work on your PR.
---

# Hydra

**Hydra is Conduction's agentic spec-driven CI/CD pipeline.** It takes an OpenSpec change proposal and runs it through a multi-stage AI pipeline — Builder, automated quality tests, parallel Code and Security Review — and produces a draft pull request ready for a single human approval. No code reaches `main` without a human in the loop.

It is the factory, not the product. The applications Hydra builds live under [ConductionNL](https://github.com/ConductionNL); Hydra itself lives at [ConductionNL/hydra](https://github.com/ConductionNL/hydra).

## How it works

```
Todo (ready-to-build)
  │
  ▼
Builder                     — implements the change, pushes branch early,
  │                           opens draft PR
  │
  ▼
Quality tests               — lint, phpcs, phpmd, psalm, phpstan,
  │                           phpmetrics, composer audit, eslint,
  │                           stylelint, npm audit, PHPUnit, Newman
  │  fail → Builder fix-quality (max 2 retries)
  │
  ▼
Browser UI tests            — Playwright MCP runs the GIVEN/WHEN/THEN
  │                           acceptance criteria against a live NC
  │  fail → Builder fix-browser (max 2 retries)
  │
  ├── Code Reviewer        ─┐
  └── Security Reviewer    ─┘ parallel — halves wall time
  │
  │  fail → Builder fix CRITICAL+WARNING (max 3 retries)
  │         If fix budget exhausted → needs-input label
  ▼
Draft PR (ready-for-review) — human reviews and merges
  │  with full-auto label: pipeline approves and merges automatically
  │
  ▼ (after human merge)
Archive — sync specs, generate test scenarios, update changelog
```

**Traceability.** Every line of code traces to its spec via two paths: a `@spec` PHPDoc tag pointing at `openspec/changes/{name}/tasks.md#task-N`, and `git blame` → commit `(#N)` → PR `Closes #N` → issue → spec. Branch naming is `feature/{issue-number}/{change-name}` and every commit includes `(#N)`.

**Model selection.** Builder uses Opus for implementation and Sonnet for fix modes. Reviewers and the Browser UI Tester use Sonnet.

## How to use Hydra on your PR

You don't run Hydra yourself — you trigger it with labels.

1. **Open an issue** in the target repo with a clear acceptance description and add the `ready-to-build` label. Hydra picks it up.
2. **Or, on an existing PR**, request review from Hydra by adding a label:
   - `code-review:queued` — queue a code review.
   - `security-review:queued` — queue a security review.

   Reviews are **sequential** by design (the security review consumes the code review's git state). Setting both queued labels at once is not supported and will produce conflicts. Trigger them one at a time.
3. **Crashes escalate to `needs-input`** rather than auto-retrying. If a Hydra container fails, you'll see a `needs-input` label so a human can investigate the root cause instead of looping.
4. **PRs that only touch Markdown auto-merge.** Documentation-only changes don't need the full review cycle.

## Where to learn more

The deep technical detail stays in the [hydra repo](https://github.com/ConductionNL/hydra):

- [hydra/README.md](https://github.com/ConductionNL/hydra/blob/main/README.md) — quickstart and full pipeline overview.
- [hydra/docs/](https://github.com/ConductionNL/hydra/tree/main/docs) — pipeline-overview, agentic-workflow, container-architecture, github-workflow, deployment-models, agent-configuration.
- [hydra/openspec/architecture/](https://github.com/ConductionNL/hydra/tree/main/openspec/architecture) — 20+ ADRs covering data layer, API, backend, frontend, security, metrics, i18n, testing, docs, NL Design, schema standards, deduplication, container pool, licensing, common patterns, routes, component composition, widget header actions, integration registry, gate scope.
- [hydra/.claude/skills/](https://github.com/ConductionNL/hydra/tree/main/.claude/skills) — every gate (`hydra-gate-*`), every opsx command (`opsx-*`), and the Hydra-specific tooling.

For how Hydra fits into the broader Claude-driven development workflow, see [Claude workflow](/claude/).
