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

<cn-arch-flow>
  <span>Todo</span>
  <span accent>Builder</span>
  <span>Quality tests</span>
  <span>Browser tests</span>
</cn-arch-flow>
<cn-arch-flow arrow="down">
  <span>Code review</span>
  <span hex>Security review</span>
  <span>Draft PR</span>
  <span>Archive</span>
</cn-arch-flow>

- **Builder** — implements the change, pushes the branch early, opens a draft PR. The accent of the build phase.
- **Quality tests** — lint, phpcs, phpmd, psalm, phpstan, phpmetrics, composer audit, eslint, stylelint, npm audit, PHPUnit, Newman. A failure loops back to the Builder for a bounded `fix-quality` round.
- **Browser tests** — Playwright MCP runs the GIVEN/WHEN/THEN acceptance criteria against a live Nextcloud. Failures loop back to the Builder for a bounded `fix-browser` round.
- **Code review** — reads diff + ADRs, applies bounded in-scope fixes directly to the PR branch. A `fail` verdict escalates to `needs-input` — no retry loop ([ADR-013](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-013-container-pool.md)).
- **Security review** — runs after the code reviewer hands off (sequential — reviewers share git state), same bounded fix authority. The orange-hex accent is here because security is the last gate before human approval.
- **Draft PR** — a human reviews and merges. With the `yolo` label, the pipeline approves and merges automatically.
- **Archive** — after merge, sync specs to Specter, generate test scenarios, update changelog.

**Traceability.** Every line of code traces to its spec via two paths: a `@spec` PHPDoc tag pointing at `openspec/changes/{name}/tasks.md#task-N`, and `git blame` → commit `(#N)` → PR `Closes #N` → issue → spec. Branch naming is `feature/{issue-number}/{change-name}` and every commit includes `(#N)`.

**Model selection.** Default model for every persona is Sonnet. When the weekly Sonnet quota runs out, the Builder falls back to **Haiku** (cheaper, still good at pattern-following from `tasks.md`/`design.md`); the Reviewers and the Applier fall back to **Opus** (deeper, since judgment work is the last line of defense before human approval). Authoritative configuration lives in each persona's `agents/<persona>/config.yaml` in the hydra repo; runtime overrides via `HYDRA_BUILDER_MODEL`, `HYDRA_REVIEWER_MODEL`, `HYDRA_APPLIER_MODEL`, and their `*_FALLBACK_MODEL` counterparts.

## How to use Hydra on your PR

You don't run Hydra yourself — you trigger it with labels.

1. **Open an issue** in the target repo with a clear acceptance description and add the `ready-to-build` label. Hydra picks it up.
2. **Or, on an existing PR**, request review from Hydra by adding a label:
   - `code-review:queued` — queue a code review.
   - `security-review:queued` — queue a security review.

   Reviews are **sequential** by design (the security review consumes the code review's git state). Setting both queued labels at once is not supported and will produce conflicts. Trigger them one at a time.
3. **Crashes escalate to `needs-input`** rather than auto-retrying. If a Hydra container fails, or either reviewer emits a fail verdict, you'll see a `needs-input` label so a human can investigate. There is no retry loop ([ADR-013](https://github.com/ConductionNL/hydra/blob/main/openspec/architecture/adr-013-container-pool.md)) — recovery is explicit via the `retry:queued` (fix the flagged findings) or `rebuild:queued` (start over) labels.
4. **The `yolo` label means auto-merge after the pipeline passes.** All phases still run; `yolo` only removes the human approval gate at the end.

## Where to learn more

The deep technical detail stays in the [hydra repo](https://github.com/ConductionNL/hydra):

- [hydra/README.md](https://github.com/ConductionNL/hydra/blob/main/README.md) — quickstart and full pipeline overview.
- [hydra/docs/](https://github.com/ConductionNL/hydra/tree/main/docs) — pipeline-overview, agentic-workflow, container-architecture, github-workflow, deployment-models, agent-configuration.
- [hydra/openspec/architecture/](https://github.com/ConductionNL/hydra/tree/main/openspec/architecture) — the org-wide ADRs (data layer, API, backend, frontend, security, container pool, and more). GitHub renders the directory as a browsable index; the directory itself is the authoritative list.
- [hydra/.claude/skills/](https://github.com/ConductionNL/hydra/tree/main/.claude/skills) — every gate (`hydra-gate-*`), every opsx command (`opsx-*`), and the Hydra-specific tooling.

For how Hydra fits into the broader Claude-driven development workflow, see [Claude workflow](/claude/).
