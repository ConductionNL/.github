# Available agents & skills

The Hydra pipeline is built from four **agents** (containerised personas with scoped permissions) plus a large catalogue of **skills** (reusable workflows invoked as slash-commands inside Claude Code). This page catalogs both.

> 💡 Skills live in two repos. Hydra's own `.claude/skills/` ships the pipeline-side workflow (opsx-*, hydra-gate-*, team-*, test-*, journeydoc-*, utilities). The `concurrentie-analyse` repo ships the upstream research and app-pipeline catalogue (specter-*, tender-*, ecosystem-*, app-*, swc-*).

## Pipeline agents

The four containerised personas that move a change from `ready-to-build` through code-review, security-review, and a binary apply gate to a draft PR ready for one human approval. Each agent runs in its own ephemeral container with scoped permissions and a single responsibility — see [`hydra/agents/README.md`](https://github.com/ConductionNL/hydra/tree/main/agents) for the directory layout and per-agent `purpose.md` / `behavior.md` / `constraints.md`.

| Persona | Slug | Role | Container | Model | Turns |
|---|---|---|---|---|---|
| **Al Gorithm** | `al-gorithm` | Builder — implements the change against the OpenSpec proposal, pushes a feature branch early, opens a draft PR | `hydra-builder` | opus | 200 |
| **Juan Claude van Damme** | `juan-claude-van-damme` | Code Reviewer — reviews PR, posts findings, has fix authority (ADR-013 no-loop policy) | `hydra-reviewer` | sonnet | 200 |
| **Clyde Barcode** | `clyde-barcode` | Security Reviewer — SAST analysis, posts findings, has fix authority | `hydra-security` | sonnet | 150 |
| **Axel Pliér** | `axel-plier` | Applier — binary go/no-go gate after both reviewers, no fix authority | `hydra-applier` | sonnet | 20 |

Shared config lives in [`agents/base.yaml`](https://github.com/ConductionNL/hydra/tree/main/agents/base.yaml); each agent's `config.yaml` extends it kustomize-style.

## Hydra skills (`hydra/.claude/skills/`)

### OpenSpec workflow — `opsx-*`

The day-to-day flow for spec-driven development. The canonical chain:

`/opsx-new` → `/opsx-ff` *or* `/opsx-continue` → `/opsx-plan-to-issues` → `/opsx-apply` → `/opsx-verify` → `/opsx-archive`

| Skill | Purpose |
|---|---|
| `/opsx-new` | Scaffold a new change proposal (`openspec/changes/{slug}/`) |
| `/opsx-ff` | Fast-forward — write proposal + spec delta + tasks in one pass |
| `/opsx-continue` | Resume an in-flight proposal where you left off |
| `/opsx-plan-to-issues` | Convert tasks.md into GitHub issues with proper labels |
| `/opsx-apply` | Implement one task end-to-end |
| `/opsx-apply-loop` | Loop `/opsx-apply` over remaining tasks |
| `/opsx-verify` | Validate the implementation matches the spec delta |
| `/opsx-archive` | Promote `changes/{slug}/` → `specs/` and close the proposal |
| `/opsx-onboard` | Bootstrap an existing repo into the openspec workflow |
| `/opsx-explore` | Read-only exploration of a codebase to inform a proposal |
| `/opsx-pipeline` | Run a full pipeline locally (build → review → apply) |
| `/opsx-coverage-scan` | Audit annotation coverage on an app |
| `/opsx-annotate` | Add `x-openregister-*` annotations to existing schemas |
| `/opsx-reverse-spec` | Produce a spec delta from clusters of un-annotated code |
| `/opsx-sync` | Sync spec deltas between hydra-specs and per-app `openspec/` |
| `/opsx-bulk-archive` | Archive multiple completed changes in one pass |

### Quality gates — `hydra-gate-*`

Mechanical checks that run inside the Builder/Reviewer containers before/after each pass. Used by the pipeline itself, but also runnable locally to pre-empt feedback:

`hydra-gates` (umbrella) plus individual gates:

`hydra-gate-admin-router`, `hydra-gate-composer-audit`, `hydra-gate-forbidden-patterns`, `hydra-gate-initial-state`, `hydra-gate-modal-isolation`, `hydra-gate-nc-input-labels`, `hydra-gate-no-admin-idor`, `hydra-gate-orphan-auth`, `hydra-gate-route-auth`, `hydra-gate-semantic-auth`, `hydra-gate-spdx`, `hydra-gate-stub-scan`, `hydra-gate-unsafe-auth-resolver`

### Team agents — `team-*`

Per-discipline reviewers / counsels you can invoke directly when you want a single point of view (rather than running the full pipeline).

| Skill | Role |
|---|---|
| `team-architect` | System design, ADR fit, cross-spec consistency |
| `team-backend` | PHP / API / DB review |
| `team-frontend` | Vue / nextcloud-vue / a11y |
| `team-po` | Product owner — user value, scope fit |
| `team-qa` | Test plan, edge cases, regression risk |
| `team-reviewer` | General PR reviewer counterpart to `juan-claude-van-damme` |
| `team-sm` | Scrum master — process, sprint health |

### Testing & journey docs

| Skill | Purpose |
|---|---|
| `test-accessibility` | Axe-Core + WCAG AA sweep |
| `test-api` | Newman-based API contract tests |
| `test-app` | App-scoped Playwright run |
| `test-counsel` | Orchestrates parallel test runs across multiple personas |
| `test-functional` | Functional regression sweep |
| `test-performance` | Lighthouse / load-time checks |
| `test-persona-annemarie`, `-fatima`, `-henk`, `-janwillem` | Persona-driven flows (each persona file in `hydra/personas/`) |
| `journeydoc-init` | Scaffold the journeydoc Playwright + Docusaurus capture setup |
| `journeydoc-add-story` | Add a new tutorial-page capture spec |
| `journeydoc-instrument` | Add `data-testid` instrumentation to existing components |

### Utilities

`create-pr`, `clean-env`, `feature-counsel`, `local-run`, `persistence-audit`, `report-out`, `review-pr`, `skill-creator`, `sync-docs`.

## Concurrentie-analyse skills (`concurrentie-analyse/.claude/skills/`)

The upstream research and app-pipeline side — feeds proposals back into Hydra.

| Group | Skills | Purpose |
|---|---|---|
| **App pipeline** | `app-create`, `app-design`, `app-explore`, `app-pipeline` | Scaffold and explore new apps from intelligence-DB findings |
| **Research — Specter** | `specter-analyze-docs`, `specter-competitive-alert`, `specter-concept`, `specter-harvest`, `specter-pipeline`, `specter-prepare-context`, `specter-research-app`, `specter-sync` | The Specter intelligence pipeline (tender + competitor harvest → cluster → spec) |
| **Tender** | `tender-scan`, `tender-status`, `tender-gap-report` | Operate on `intelligence.db` for tender coverage |
| **Ecosystem** | `ecosystem-investigate`, `ecosystem-propose-app` | Find ecosystem gaps and draft proposals for new apps |
| **Software catalogue** | `swc-test`, `swc-update` | Sync the public software catalogue |
| **Misc** | `intelligence-update`, `readiness-report` | DB maintenance + readiness reporting |

## User personas

Personas are non-agent — they're test subjects representing real user archetypes the testing skills drive flows against:

| File | Persona |
|---|---|
| `annemarie-de-vries.md` | Public-sector caseworker — Henk's manager's manager |
| `fatima-el-amrani.md` | Front-line municipal officer, multilingual |
| `henk-bakker.md` | Senior caseworker, sceptical of new tools |
| `janwillem-van-der-berg.md` | IT architect, evaluates platform fit |
| `mark-visser.md` | Developer onboarding the platform |
| `noor-yilmaz.md` | Citizen-side user submitting forms |
| `priya-ganpat.md` | Compliance officer, ISO / privacy lens |
| `sem-de-jong.md` | Product manager, prioritisation lens |

Full persona files live in [`hydra/personas/`](https://github.com/ConductionNL/hydra/tree/main/personas).

## Going deeper

- **Each skill is its own folder** under `.claude/skills/<name>/` with a `SKILL.md` (the instruction prompt the agent runs) plus optional `examples/`, `references/`, `templates/`, `assets/`. See [Writing skills](./writing-skills.md) and the [Skill checklist](./skill-checklist.md).
- **Skill maturity levels (L1–L7)** describe how much evaluation backs each skill. The [Skill evaluation](./skill-evals.md) page documents the L5+ workflow with `evals.json` baselines.
- **Skills are invokable** via `Skill: <name>` inside Claude Code or as `/<name>` slash-commands. The harness also publishes them to sub-agents through the `Agent` tool.
