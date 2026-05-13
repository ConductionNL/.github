# Container Architecture

This document describes the three-container pipeline, the security constraints applied to
each container, and the audit output each container produces.

---

## Pipeline Overview

Every OpenSpec change flows through ephemeral containers in sequence:

```
Todo (<trigger-label>, default: ready-to-build)
  │
  ▼
┌─────────────────────────────────────────┐
│  Builder (hydra-builder)                │
│  Persona: Al Gorithm                    │
│  Model: opus (complex implementation)   │
│  Tools: Read Write Edit Bash Glob Grep  │
│  Max turns: 80                          │
│  Output: feature branch (pushed early), │
│          draft PR opened                │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│  Automated Quality Tests (Docker)       │
│  Script: scripts/run-quality.sh         │
│  Runs inside: Docker php:X.Y-cli        │
│  (PHP version from app-config.json)     │
│                                         │
│  Static analysis:                       │
│    lint, phpcs, phpmd, psalm, phpstan,  │
│    phpmetrics, composer audit           │
│  Frontend:                              │
│    eslint, stylelint, npm audit         │
│  Tests:                                 │
│    PHPUnit (containerized NC + SQLite)  │
│    Newman (PHP built-in server)         │
│                                         │
│  Flag: --keep-server (keep NC running   │
│        for browser tests)               │
│  Output: pass / fail with log           │
└─────────────────────────────────────────┘
  │ fail → Builder fix-quality (sonnet, max 2 retries)
  │ pass ↓
  ▼
┌─────────────────────────────────────────┐
│  Browser UI Tests (on HOST)             │
│  Script: scripts/run-browser-tests.sh   │
│  Runtime: Claude CLI + Playwright MCP   │
│           (headless Chromium)            │
│  Skill: hydra-ui-test                   │
│  Model: sonnet                          │
│                                         │
│  Tests:                                 │
│    Logs into Nextcloud, navigates to app│
│    Acceptance criteria (GIVEN/WHEN/THEN)│
│    CRUD flows, navigation, forms        │
│    Error states, console errors         │
│    Network failure detection            │
│  Output: structured verdict JSON        │
│          (CRITICAL/WARNING findings)    │
└─────────────────────────────────────────┘
  │ fail → Builder fix-browser (sonnet, max 2 retries)
  │ pass ↓
  ▼
┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────┐
│  Code Reviewer (hydra-reviewer)         │  │  Security Reviewer (hydra-security)     │
│  Persona: Juan Claude van Damme         │  │  Persona: Clyde Barcode                 │
│  Model: sonnet                          │  │  Model: sonnet                          │
│  Tools: Read Bash Grep Glob             │  │  Tools: Read Bash mcp__semgrep__*       │
│  Max turns: 30                          │  │  Max turns: 20                          │
│  Resources: 2 CPUs / 4 GB              │  │  Resources: 2 CPUs / 4 GB              │
│  Output: PR review comments + verdict   │  │  Output: Security findings + verdict    │
└─────────────────────────────────────────┘  └─────────────────────────────────────────┘
          (parallel execution — halves wall time)
  │
  │ fail → Builder fix CRITICAL+WARNING (sonnet, max 3 retries)
  │        If fix budget exhausted → needs-input label, escalate to human
  │ pass ↓
  ▼
Draft PR (ready-for-review) — human reviews and merges (auto-merge intentionally disabled)
```

Each container is destroyed after completion. No state persists between runs except what
is written to the target repository or GitHub.

---

## Model Selection

Each pipeline stage uses the most cost-effective model for its task complexity:

| Stage | Model | Rationale |
|-------|-------|-----------|
| Builder (build) | opus | Complex implementation requires deep reasoning |
| Builder (fix-quality) | sonnet | Targeted lint/test fixes are straightforward |
| Builder (fix-browser) | sonnet | Targeted UI fixes based on structured findings |
| Builder (fix review findings) | sonnet | Targeted fixes for CRITICAL+WARNING findings |
| Browser UI Tester | sonnet | Structured acceptance testing via Playwright MCP |
| Code Reviewer | sonnet | Review is analytical, not generative |
| Security Reviewer | sonnet | Pattern matching against known vulnerability classes |

Override: set `HYDRA_MODEL` environment variable to force a specific model for all stages.

---

## Security Constraints

These constraints are non-negotiable and apply to all containers in all deployment models.

| Constraint | Value | Rationale |
|---|---|---|
| `--read-only` | always | Prevents the agent from modifying the container filesystem |
| `--tmpfs /tmp:size=512M` | always | Writable scratch space with size cap |
| `--tmpfs /workspace:size=2G` | always | Clone workspace with size cap |
| `--security-opt no-new-privileges` | always | Prevents privilege escalation via setuid |
| `--cap-drop ALL` | always | Removes all Linux capabilities |
| `--cap-add NET_ADMIN` | local only | Required for iptables egress rules in entrypoint.sh |
| `--cpus 4 --memory 8g` | Builder | Resource caps to prevent runaway builds |
| `--cpus 2 --memory 4g` | Reviewers | Lower resource allocation for read-only review tasks |
| `--network hydra-net` | local | Isolated Docker network |
| `--output-format stream-json` | always | JSONL output for log parsing |
| `--max-turns` | 80 / 30 / 20 | Hard turn limit prevents infinite loops (builder / reviewer / security) |
| No `--dangerously-skip-permissions` | always | Explicit allowedTools required |

**Origin of these constraints:** a prior Claude Code session inherited organisation-admin
Git rights through a developer's WSL session and bypassed peer review. These constraints
are the direct response to that threat model.

---

## SBOM & Audit Trails

### What each container produces

Every pipeline run leaves a durable, verifiable audit trail on GitHub — no separate audit
store is required.

#### Builder

| Output | Location | Contains |
|---|---|---|
| Feature branch | `hydra/<change-name>` on target repo | All code changes |
| Draft PR | Target repo PR | Structured description, spec reference, change list, test coverage |
| PR description | PR body | Summary, Spec Reference, Changes, Test Coverage sections |
| Commit messages | Git history | Task reference, what changed and why |
| RFI comment | GitHub issue (if blocked) | Blocker reason, attempted fixes, what is needed |
| Status update | `openspec/changes/<name>/design.md` | `status: pr-created` |

#### Code Reviewer

| Output | Location | Contains |
|---|---|---|
| Review comments | PR comments | Findings with CRITICAL/WARNING/SUGGESTION severity |
| Verdict comment | PR comment | `{ "pass": bool, "blocking": [...] }` |

#### Security Reviewer

| Output | Location | Contains |
|---|---|---|
| SAST findings | PR comments | Semgrep + Gitleaks + Trivy results with severity |
| Security verdict | PR comment | `{ "pass": bool, "blocking": [...] }` |

### Traceability chain

```
GitHub Issue (requirement)
  → OpenSpec change (design.md, tasks.md, specs/)
    → Builder commit history (what was implemented)
      → Draft PR (summary + spec reference)
        → Code Review verdict (correctness, style)
          → Security verdict (SAST, secrets, hardening)
            → Human approval (4-eyes rule)
              → Merge to main
```

Every step is recorded on GitHub with a timestamp and the identity of the agent or human
that took the action. This chain satisfies:

- **EU AI Act Article 12** (transparency and traceability for high-risk AI systems):
  all AI-generated code is explicitly labelled, attributed to a named agent, and reviewed
  by a human before reaching production.
- **ISO 27001 A.12.1.2** (change management): every change is traceable from requirement
  to deployment.
- **"Public money = public code"**: the full audit trail is available to any reviewer of
  the public repository.

### SBOM generation (phase 2)

In a future phase, each Builder run will additionally produce:

- A CycloneDX or SPDX SBOM for the target application's dependencies
- An attestation file (`hydra-attestation.json`) recording which model version, which spec,
  and which turn count produced the change

These will be attached to the GitHub release as assets.

---

## Configuration Layers

Agent configuration is split across two complementary layers — portable agent definitions
and Docker-specific runtime config:

### Layer 1: Agent definitions (`agents/`)

Portable, deployment-agnostic configuration managed as YAML:

```
agents/
├── base.yaml                        # Shared config (egress, MCP, env vars)
├── al-gorithm/config.yaml           # Builder overrides (tools, turns, extra env)
├── juan-claude-van-damme/config.yaml # Reviewer overrides
└── clyde-barcode/config.yaml        # Security overrides
```

`base.yaml` defines shared settings (egress allowlist, MCP servers, required env vars,
`permission_mode`). Per-agent `config.yaml` files extend it using kustomize-style merging:
scalars override, lists replace, maps deep-merge.

Key settings in `base.yaml`:
- `claude.permission_mode: acceptEdits` — allows containers to run headless without
  interactive permission prompts
- `claude.output_format: stream-json` — JSONL output for log parsing
- `egress.hosts` — allowlisted domains (api.anthropic.com, github.com, etc.)
- `mcp.github` — GitHub MCP server shared by all agents

### Layer 2: Docker image config (`images/`)

Container-specific files baked into each Docker image at build time:

```
images/{builder,reviewer,security}/
├── CLAUDE.md        # Agent identity, workflow, and constraints
├── settings.json    # Claude CLI settings (allowedTools, MCP permissions)
├── .mcp.json        # MCP server definitions (runtime format)
└── entrypoint.sh    # Container bootstrap script
```

### Shared entrypoint library (`scripts/lib/`)

Common bootstrap logic is extracted into shared scripts to reduce duplication:

- `scripts/lib/entrypoint-common.sh` — shared setup functions (git auth, egress firewall,
  directory prep) called by all three container entrypoints
- `scripts/lib/load-config.py` — YAML config parser that merges `base.yaml` with per-agent
  `config.yaml` and exposes values as environment variables
- `scripts/lib/pipeline-comment.sh` — pipeline status tracking via comments on the GitHub issue
- `scripts/run-quality.sh` — automated quality runner (all checks inside Docker php:X.Y-cli
  container: lint, phpcs, phpmd, psalm, phpstan, phpmetrics, composer audit, eslint,
  stylelint, npm audit, PHPUnit with containerized Nextcloud + SQLite, Newman API tests;
  `--keep-server` flag keeps Nextcloud running for subsequent browser tests)
- `scripts/run-browser-tests.sh` — browser UI testing on HOST via Claude CLI + Playwright
  MCP (headless Chromium); pre-extracts acceptance criteria into prompt; returns structured
  verdict JSON with CRITICAL/WARNING findings

### Why the split?

The agent definitions in `agents/` are the **source of truth for what each agent can do**
(tools, turn limits, egress, MCP servers). The Docker image config in `images/` is the
**runtime materialisation** of those definitions plus container-specific concerns
(entrypoint scripts, Claude CLI format). This separation allows the same agent definitions
to work across all three deployment models (local Docker, GitHub Actions, Kubernetes).

---

## ADR Layering

Architectural Decision Records (ADRs) guide how agents write code. They come from two
sources, applied in priority order:

### Layer 1: Conduction company-wide ADRs (baked into image)

At build time, the Builder image copies the 12 compact ADRs from this repo's
`openspec/architecture/` into `/home/claude/.claude/openspec/architecture/`. These define
baseline conventions for all Conduction projects:

| ADR | Topic |
|-----|-------|
| adr-001 | OpenRegister data layer (incl. register templates + seed data) |
| adr-002 | API conventions (NL API strategie) |
| adr-003 | Backend layering (Controller→Service→Mapper, DI, routing) |
| adr-004 | Frontend patterns (Vue 2, Pinia, @conduction/nextcloud-vue) |
| adr-005 | Security and auth |
| adr-006 | Prometheus metrics and health checks |
| adr-007 | i18n requirement (nl/en minimum, register i18n) |
| adr-008 | Mandatory test coverage |
| adr-009 | Documentation with screenshots |
| adr-010 | NL Design System (CSS vars, WCAG AA) |
| adr-011 | Schema standards (schema.org, vCard) |
| adr-012 | Deduplication check against OpenRegister core |

### Layer 2: Project-specific ADRs (from target repo at runtime)

When the Builder clones the target repository, it checks for
`openspec/architecture/` in the repo root. If present, these ADRs extend or override
the company-wide ones. Project ADRs take precedence when they conflict with Conduction ADRs.

### Resolution order

1. Read all Conduction ADRs (always present in the image)
2. Read project ADRs (if the target repo has them)
3. On conflict: project ADR wins
4. On silence: Conduction ADR applies

---

## OPSX Integration

The Builder container includes the full OPSX skill suite from this repo's
`.claude/skills/`, copied at build time. This gives the Builder access to:

- **OPSX skills** (`skills/opsx-apply`, `opsx-verify`, `opsx-archive`, etc.) — the standard
  Conduction workflow for implementing, verifying, and archiving OpenSpec changes
- **OPSX commands** (`commands/opsx/apply.md`, etc.) — slash command definitions
- **OpenSpec CLI** (`@fission-ai/openspec`) — for checking change status and getting instructions
- **Conduction schemas** — artifact templates for proposals, designs, specs, tasks, etc.

The Builder follows the OPSX apply workflow (read context → implement tasks → quality checks
→ mark complete) but runs headless without interactive prompts.

---

## Security Hooks

The Builder container inherits the PreToolUse security hook
(originally from `ConductionNL/.github/global-settings/block-write-commands.sh`). This provides defence-in-depth alongside
the container-level isolation:

- **Hard-blocks** writes to `~/.claude/` config files
- **Hard-blocks** WSL boundary escapes (not applicable in containers, but harmless)
- **Prompts for approval** on destructive operations (rm, git push, etc.)
- **Requires explicit authorization** for git push via transcript phrase matching

In headless container mode, the hook's "ask" decisions are handled by the
`permission_mode: acceptEdits` setting — the agent auto-approves non-blocked operations.
Hard-blocks still apply regardless of permission mode.
