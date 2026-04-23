---
id: spec-driven-development
title: Spec-Driven Development
sidebar_label: Spec-Driven Development
sidebar_position: 2
description: How Conduction uses OpenSpec and Claude Code to go from idea to implementation
---

# Spec-Driven Development

At Conduction, we don't start coding before we know what we're building. We use a **spec-driven workflow** where every change is defined as structured artifacts before implementation begins. Specs live alongside code and persist across sessions, ensuring continuity and traceability.

## The Pipeline

All development follows four stages:

| Stage | What happens | Output |
|---|---|---|
| **1. Obtain** | Discover requirements — from issues, tenders, app research, documentation | Understanding of what to build |
| **2. Specify** | Write structured specs that define the change | proposal.md → specs.md → design.md → tasks.md → GitHub Issues |
| **3. Build** | Implement by assembling components, schemas, and workflows | Working software |
| **4. Validate** | Verify quality, run tests, check against specs | Confidence to ship |

## OpenSpec

OpenSpec is our specification format. Every change produces a chain of artifacts:

```
proposal.md ──► specs.md ──► design.md ──► tasks.md ──► GitHub Issues
```

- **Proposal** — what and why (problem statement, scope, stakeholders)
- **Specs** — detailed requirements with GIVEN/WHEN/THEN acceptance criteria
- **Design** — technical approach, component selection, data model
- **Tasks** — breakdown into implementable units
- **Issues** — tasks become trackable GitHub Issues with an epic

Org-wide specs (test coverage baselines, API patterns, NL Design System compliance, i18n requirements) live in the [`openspec/`](https://github.com/ConductionNL/.github/tree/main/openspec) directory of this repository. Individual apps extend these with app-specific specs.

## Claude Code

We use [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as our development orchestrator. Claude acts as an **architect and assembler** — it defines, configures, and validates, but delegates actual implementation to the platform's building blocks:

| Layer | Tool | What Claude does |
|---|---|---|
| **Frontend** | `@conduction/nextcloud-vue` | Select and configure components, define views and routing |
| **Backend data** | OpenRegister | Define schemas, registers, object structures, validation rules |
| **Backend logic** | n8n workflows | Design workflow logic, configure triggers, map data |

A shared configuration repository ([`claude-code-config`](https://github.com/ConductionNL/claude-code-config)) provides all commands, skills, and workflow instructions. It's added as a git submodule at `.claude/` in each app repository.

## Key Commands

| Command | Stage | Purpose |
|---|---|---|
| `/opsx-explore` | Obtain | Investigate a topic or problem |
| `/opsx-new` | Specify | Start a new change with a proposal |
| `/opsx-ff` | Specify | Generate all spec artifacts in one go |
| `/opsx-plan-to-issues` | Specify | Convert tasks to GitHub Issues |
| `/opsx-apply` | Build | Implement tasks from the specs |
| `/opsx-verify` | Validate | Check implementation against specs |
| `/opsx-archive` | Done | Archive completed change |
