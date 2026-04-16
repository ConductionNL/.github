# Testing Reference

This document describes all testing commands and skills available in this workspace — when to use each, how they compare, and recommended testing workflows for common situations.

---

## Quick Comparison

| Command / Skill | Type | Focus | Agents | Output |
|-----------------|------|-------|--------|--------|
| `/test-counsel` | Skill | **Persona-based** — Would Henk/Fatima/Sem/… succeed? | 8 parallel | `{APP}/test-results/` |
| `/test-app` | Skill | **Perspective-based** — Functional, UX, accessibility, performance, security, API | 1 or 6 parallel | `{APP}/test-results/README.md` |
| `/test-functional` | Command | Feature correctness (GIVEN/WHEN/THEN) | 1 | Chat + optional evidence |
| `/test-api` | Command | REST API endpoints | 1 | Chat + API report |
| `/test-accessibility` | Command | WCAG 2.1 AA (axe-core) | 1 | Chat + a11y report |
| `/test-performance` | Command | Load times, API response | 1 | Chat |
| `/test-security` | Command | OWASP Top 10, Nextcloud roles | 1 | Chat |
| `/test-regression` | Command | Cross-feature regression | 1 | Chat |
| `/test-persona-henk` | Command | Henk's perspective only | 1 | Chat |
| `/test-persona-fatima` | Command | Fatima's perspective only | 1 | Chat |
| `/test-persona-sem` | Command | Sem's perspective only | 1 | Chat |
| `/test-persona-noor` | Command | Noor's perspective only | 1 | Chat |
| `/test-persona-annemarie` | Command | Annemarie's perspective only | 1 | Chat |
| `/test-persona-mark` | Command | Mark's perspective only | 1 | Chat |
| `/test-persona-priya` | Command | Priya's perspective only | 1 | Chat |
| `/test-persona-janwillem` | Command | Jan-Willem's perspective only | 1 | Chat |

---

## Typical Testing Workflows

### After implementing a feature (pre-PR)

The standard validation flow before raising a pull request:

```
/opsx-verify                    # Confirms implementation matches specs (reads code + artifacts, no browser)
/test-functional           # Verifies the feature behaves as specced step by step
/test-counsel                   # User acceptance from all 8 personas
/create-pr
```

For a quicker pass when you're confident in the implementation:

```
/opsx-verify
/test-app                       # Quick mode: single-agent smoke test across all perspectives
/create-pr
```

---

### Full regression sweep (before a release or major merge)

When you want comprehensive coverage — correctness, user experience, and technical quality:

```
/test-regression           # Verify no cross-feature breakage first
/test-counsel                   # All 8 persona perspectives
/test-app                       # Full mode: 6 agents (functional, UX, accessibility, performance, security, API)
```

Run `/test-regression` first — if existing flows are already broken, there's no point running the broader sweeps.

---

### Quick smoke test

When you just want to confirm the app is up and main flows work:

```
/test-app                       # Choose Quick mode when prompted (1 agent)
```

Or a single persona for a faster targeted check:

```
/test-persona-sem          # Sem (digital native) flow only — fastest meaningful check
```

---

### Focused area testing

Use single-agent commands when you need to target a specific quality dimension:

| Goal | Command |
|------|---------|
| Verify a specific feature works end-to-end | `/test-functional` |
| Validate REST API endpoints | `/test-api` |
| Audit accessibility compliance | `/test-accessibility` |
| Measure page and API speed | `/test-performance` |
| Security and role checks | `/test-security` |
| Check nothing unrelated broke | `/test-regression` |
| One persona's full journey | `/test-persona-*` |

---

### Feature design review (before implementation)

Use `/feature-counsel` to get persona feedback on specs *before* building:

```
/opsx-ff                        # Generate all spec artifacts
/feature-counsel                # 8 personas analyze specs, suggest missing features
# [review and refine specs]
/opsx-apply                     # Only then implement
```

This is the only testing-adjacent command that runs *before* implementation. It reads specs, not the live app.

---

## Skills (Multi-Agent)

### `/test-counsel` — Persona-Based Testing

**Lens:** User experience. "Would Henk, Fatima, Sem, Noor, Annemarie, Mark, Priya, or Jan-Willem succeed and be satisfied?"

**Agents:** 8 (one per persona) — run in parallel.

**Use when:** You want feedback from realistic user perspectives. Each persona represents a different role, technical level, and set of priorities (citizen, developer, municipal officer, etc.). Output includes in-character findings and verdicts per persona. Best used after `/test-functional` confirms the feature works — this answers whether *users* would succeed, not just whether the spec was met.

**Cap impact:** Very high — 8 parallel agents. Open a fresh Claude window before running. See [parallel-agents.md](parallel-agents.md).

**See:** [.claude/skills/test-counsel/SKILL.md](https://github.com/ConductionNL/hydra/blob/main/.claude/skills/test-counsel/SKILL.md)

---

### `/test-app` — Perspective-Based Testing

**Lens:** Technical quality. "Does everything work from functional, UX, accessibility, performance, security, and API angles?"

**Agents:** 1 (Quick mode) or 6 (Full mode) — one per perspective.

**Use when:** You want a structured technical sweep. Each perspective has a specific checklist. Quick mode is low-cost and fine to run regularly. Full mode is for thorough pre-release validation.

**Output:** `{APP}/test-results/README.md` — summary with PASS/PARTIAL/FAIL/CANNOT_TEST per perspective.

**Cap impact:** Low (Quick) to Very high (Full). See [parallel-agents.md](parallel-agents.md).

**See:** [.claude/skills/test-app/SKILL.md](https://github.com/ConductionNL/hydra/blob/main/.claude/skills/test-app/SKILL.md)

---

## `/test-counsel` vs `/test-app`

| Aspect | `/test-counsel` | `/test-app` |
|--------|-----------------|--------------------|
| **Lens** | Persona — user goals and experience | Perspective — technical correctness |
| **Question** | "Would Henk/Fatima/Priya/… complete their tasks?" | "Do features work, perform, and meet standards?" |
| **Agents** | 8 (one per persona) | 1 or 6 (Quick or Full mode) |
| **Output style** | In-character findings, persona verdicts | PASS/PARTIAL/FAIL, technical notes |
| **Best for** | User acceptance, UX feedback | Quality gates, regression, coverage |

Both cover the full app. Use both for thorough validation: `/test-counsel` for user perspective, `/test-app` for technical perspective.

---

## Commands (Single-Agent)

### `/test-functional`

Feature correctness via browser. Executes GIVEN/WHEN/THEN scenarios from specs or acceptance criteria against the live app.

**Use when:** You've implemented something specific and want to confirm it behaves exactly as specced, step by step. More targeted than `/test-counsel` — it follows the spec, not a persona narrative. Good as the first test after implementation before running broader sweeps.

---

### `/test-api`

REST API testing. Checks endpoints, authentication, pagination, and error responses for Nextcloud app APIs.

**Use when:** You've added or changed API behaviour — new endpoints, modified responses, or changed data structures. Also useful when Priya's or Annemarie's persona test surfaces API concerns worth investigating further.

---

### `/test-accessibility`

WCAG 2.1 AA compliance using axe-core. Injects axe, runs automated checks, reports violations. Adds manual verification for keyboard navigation and focus management.

**Use when:** You've added or changed UI components, forms, or navigation. Should be run before archiving any change that touches the frontend. `/test-app` Full mode includes an accessibility perspective, but this command goes deeper.

---

### `/test-performance`

Load times, API response times, network requests. Uses browser timing APIs and sequential API calls to measure real-world performance.

**Use when:** You've added new pages, heavy queries, or API-heavy features. Also use when `/test-app` Full mode flags a performance concern that needs more detail.

---

### `/test-security`

OWASP Top 10, Nextcloud roles, authorization. Checks XSS, CSRF, sensitive data exposure, and role-based access control.

**Use when:** You've changed authentication, permission logic, or added any form or user input handler. Also use before archiving changes that touch admin interfaces or user data.

---

### `/test-regression`

Cross-feature regression. Tests unrelated flows to verify a change hasn't broken anything outside its scope. Broader than `/test-functional`.

**Use when:** You've made structural changes — database schema, core service updates, shared utilities — where side-effects are plausible. Run this *before* the persona sweeps in a full regression cycle; if something is already broken it'll surface here first.

---

### `/test-persona-*`

Single-persona deep dive. Use when you want one persona's full assessment without launching all eight:

| Command | Persona | Role |
|---------|---------|------|
| `/test-persona-henk` | **Henk Bakker** | Elderly citizen — low digital literacy |
| `/test-persona-fatima` | **Fatima El-Amrani** | Low-literate migrant citizen |
| `/test-persona-sem` | **Sem de Jong** | Young digital native |
| `/test-persona-noor` | **Noor Yilmaz** | Municipal CISO / functional admin |
| `/test-persona-annemarie` | **Annemarie de Vries** | VNG standards architect |
| `/test-persona-mark` | **Mark Visser** | MKB software vendor |
| `/test-persona-priya` | **Priya Ganpat** | ZZP developer / integrator |
| `/test-persona-janwillem` | **Jan-Willem van der Berg** | Small business owner |

**Use when:** You know which persona is most affected by the change, or when you've already run `/test-counsel` and want a deeper single-perspective follow-up. One agent instead of eight — lower cap cost than `/test-counsel`.

---

## Test Scenarios

Test scenarios (`{APP}/test-scenarios/TS-NNN-slug.md`) are reusable, Gherkin-style flows that the test commands pick up automatically. When scenarios exist, the following commands ask whether to include them before launching agents:

| Command | Behaviour |
|---------|-----------|
| `/test-app` | Offers to include all active scenarios before launching agents. Agents execute scenario steps before free exploration. |
| `/test-counsel` | Offers to include scenarios, grouped by persona. Each persona agent receives only the scenarios tagged with their slug. |
| `/test-persona-*` | Scans for scenarios matching that persona's slug. Asks to run them before free exploration. |
| `/test-scenario-run` | Runs scenarios directly (by ID, tag, persona, or all) |

### `/test-scenario-create`

Guided wizard for creating a well-structured test scenario for a Nextcloud app.

**Usage:**
```
/test-scenario-create
/test-scenario-create openregister
```

**What it does:**
1. Determines the next ID (`TS-NNN`) by scanning existing scenarios
2. Asks for title, goal, category (functional/api/security/accessibility/performance/ux/integration), and priority
3. Shows relevant personas and asks which this scenario targets
4. Suggests which test commands should automatically include it
5. Auto-suggests tags based on category and title
6. Guides through Gherkin steps (Given/When/Then), test data, and acceptance criteria
7. Generates persona-specific notes for each linked persona
8. Saves to `{APP}/test-scenarios/TS-NNN-slug.md`

**Scenario categories and suggested personas:**

| Category | Suggested personas |
|---|---|
| functional | Mark Visser, Sem de Jong |
| api | Priya Ganpat, Annemarie de Vries |
| security | Noor Yilmaz |
| accessibility | Henk Bakker, Fatima El-Amrani |
| ux | Henk Bakker, Jan-Willem, Mark Visser |
| performance | Sem de Jong, Priya Ganpat |
| integration | Priya Ganpat, Annemarie de Vries |

---

### `/test-scenario-run`

Execute one or more test scenarios against the live Nextcloud environment using a browser agent.

**Usage:**
```
/test-scenario-run                        # list and choose
/test-scenario-run TS-001                 # run specific scenario
/test-scenario-run openregister TS-001    # run from specific app
/test-scenario-run --tag smoke            # run all smoke-tagged scenarios
/test-scenario-run --all openregister     # run all scenarios for an app
/test-scenario-run --persona priya-ganpat # run all Priya's scenarios
```

**What it does:**
1. Discovers scenario files in `{APP}/test-scenarios/`
2. Filters by tag, persona, or ID as specified
3. Asks which environment to test against (local or custom URL)
4. Asks whether to use Haiku (default, cost-efficient) or Sonnet (for complex flows)
5. Launches a browser agent per scenario (parallelised up to 5 for multiple)
6. Agent verifies preconditions, follows Given-When-Then steps, checks each acceptance criterion
7. Writes results to `{APP}/test-results/scenarios/`
8. Synthesises a summary report for multiple runs

**Model:** Asked at run time. **Haiku** (default) — fast, cost-efficient. **Sonnet** — for complex multi-step flows or ambiguous UI states where Haiku may misread the interface. Cap cost scales with the number of scenarios run in parallel.

**Cap impact:** Low for single scenario; medium for multiple. See [parallel-agents.md](parallel-agents.md).

**Result statuses**: PASS / FAIL / PARTIAL / BLOCKED

---

### `/test-scenario-edit`

Edit an existing test scenario — update any field (metadata or content) interactively.

**Usage:**
```
/test-scenario-edit                      # list all scenarios, pick one
/test-scenario-edit TS-001               # open specific scenario
/test-scenario-edit openregister TS-001  # open from specific app
```

**What it does:**
1. Locates the scenario file
2. Shows a summary of current values (status, priority, category, personas, tags, spec refs)
3. Asks what scope to edit: metadata only / content only / both / status only / tags only
4. Walks through each field in scope, showing the current value and asking for the new one
5. Supports `+tag` / `-tag` syntax for incremental tag changes, same for personas
6. Regenerates persona notes if the personas list changed
7. Optionally renames the file if the title changed
8. Writes the updated file and shows a diff-style summary

---

### How existing test commands use scenarios

| Command | Behaviour when scenarios exist |
|---|---|
| `/test-app` | Asks to include active scenarios before launching agents. Agents execute scenario steps before free exploration. |
| `/test-counsel` | Asks to include scenarios, grouped by persona. Each persona agent receives only the scenarios tagged with their slug. |
| `/test-persona-*` | Scans for scenarios matching that persona's slug. Asks to run them before free exploration in Step 2. |

---

## Environment

All testing uses:
- **Base URL:** `http://localhost:8080` (local env) or `http://localhost:3000` (dev)
- **Credentials:** `admin` / `admin` (local env)
- **Browser:** Playwright MCP — see browser usage below

Ensure Docker is running and Nextcloud is accessible before testing. See [docker.md](docker.md) for environment setup.

---

## Browser Usage

| Context | Browser | When |
|---------|---------|------|
| **Single-agent commands** | `browser-1` | `/test-functional`, `/test-persona-*`, `/test-*` — one agent at a time |
| **test-counsel (8 parallel)** | `browser-2`–`browser-5`, `browser-7` + overflow | One browser per persona |
| **test-counsel (1 persona)** | `browser-1` | When testing a single persona only |
| **test-app Quick** | `browser-1` | Single agent smoke test |
| **test-app Full (6 parallel)** | `browser-2`–`browser-5`, `browser-7` + 1 | Each perspective gets a distinct browser |
| **User observation** | `browser-6` | Headed browser for watching tests live |

**Rule:** Single agent = `browser-1`. Parallel agents = each gets a distinct browser (`browser-2`, `browser-3`, `browser-4`, …) to avoid session conflicts.
