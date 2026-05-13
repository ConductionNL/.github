# Agentic Workflow

This document describes the automated steps that agents execute within the Hydra pipeline. Each step maps to a stage on the GitHub project board.

## Pipeline Stages

### 1. Specs (Input)

**Triggered by:** Card appearing in the Specs/Todo column
**Agent role:** Builder (Al Gorithm)

The Builder reads the OpenSpec change directory (`openspec/changes/<name>/`) and prepares the implementation context:
- Reads `tasks.md` — the canonical task list authored during the spec phase
- Parses requirements (MUST, SHOULD, MAY per RFC 2119) from `design.md` and `specs/`
- Extracts acceptance criteria (GIVEN/WHEN/THEN scenarios) from task definitions
- Identifies files likely affected based on task scope
- Checks for conflicts with existing specs or in-progress changes

> **Note on tasks.md vs plan.json:** OpenSpec uses `tasks.md` as the primary authoring
> artifact. A `plan.json` can optionally be generated from `tasks.md` by running
> `/opsx-plan-to-issues`, which adds GitHub Issue links and structured metadata for
> implementation tracking. The Builder reads `tasks.md` directly — `plan.json` is not
> required for the pipeline to function.

**Output:** Implementation context ready for the Apply stage

### 2. Apply (Build)

**Triggered by:** Plan ready
**Agent role:** Builder (opus model)

The agent implements the change:
- Creates the feature branch (`hydra/{spec-name}`) and pushes early (enables quality tests)
- Scaffolds new files if needed (controllers, views, stores, tests)
- Implements the feature following project conventions
- Writes tests matching the acceptance criteria
- Commits incrementally (one commit per logical unit of work)
- Spec path is auto-detected from the issue body (or overridden via `--spec-repo` flag)

**Constraints:**
- Must follow the target app's coding standards (PHPCS, ESLint, etc.)
- Must not introduce new linting errors
- Must not break existing tests
- Each commit must have a meaningful message

**Output:** Feature branch with implementation commits

### 3. Automated Quality Tests

**Triggered by:** Apply completes (branch pushed)
**Script:** `scripts/run-quality.sh`
**Environment:** Docker `php:X.Y-cli` container (PHP version read from `app-config.json`)
**Fix agent model:** sonnet (targeted fixes)

All quality checks run inside a Docker container -- nothing runs on the host PHP. The automated quality gate covers:

- **PHP linting** — `php -l` (syntax check)
- **PHP code style** — PHPCS (PHP_CodeSniffer)
- **PHP mess detection** — PHPMD
- **PHP static analysis** — Psalm, PHPStan
- **PHP metrics** — phpmetrics (complexity, coupling, maintainability)
- **PHP dependency audit** — `composer audit`
- **Frontend linting** — ESLint, Stylelint
- **Frontend dependency audit** — `npm audit`
- **Unit tests** — PHPUnit running inside a containerized Nextcloud + SQLite environment
- **API tests** — Newman collections via PHP built-in server (when enabled)
- **Build verification** — `npm run build` / `composer install` must succeed

The `--keep-server` flag keeps the containerized Nextcloud instance running so the subsequent browser test stage can use it.

> SBOM generation, CVE scanning, and license compliance are handled by the organisation-wide quality workflow, not by this stage.

If quality tests fail:
- Builder is re-launched in **fix-quality mode** (sonnet model, max 2 retries)
- If still failing after retries, the issue is labelled `needs-input` and escalated to a human

**Output:** Clean build with passing checks

### 3a. Browser UI Tests

**Triggered by:** Quality tests pass
**Script:** `scripts/run-browser-tests.sh` (runs on HOST, not in Docker)
**Skill:** `images/builder/skills/hydra-ui-test/SKILL.md`
**Model:** sonnet
**Fix agent model:** sonnet (targeted fixes)

Browser UI tests run on the host machine using Claude CLI with Playwright MCP (headless Chromium). The script pre-extracts acceptance criteria from the spec into the prompt to avoid wasting tokens on file reading.

The browser tester:
- Logs into Nextcloud and navigates to the target app
- Tests acceptance criteria (GIVEN/WHEN/THEN scenarios from the spec)
- Tests CRUD flows, navigation, forms, and error states
- Checks for console errors and network failures
- Returns a structured verdict JSON with CRITICAL/WARNING findings

If browser tests fail:
- Builder is re-launched in **fix-browser mode** (sonnet model, max 2 retries)
- If still failing after retries, the issue is labelled `needs-input` and escalated to a human

**Output:** Structured verdict JSON confirming UI works as specified

### 4. Archive

**Triggered by:** Validation passes
**Agent role:** Publisher

The agent packages the change for review:
- Creates the Pull Request with structured description
- Links the PR back to the GitHub Issue / board card
- Moves the card to In Progress
- Updates the OpenSpec change status to `pr-created`

**PR description format:**
```markdown
## Summary
<!-- What this change does, in 1-3 bullets -->

## Spec Reference
<!-- Link to the OpenSpec document -->

## Changes
<!-- File-level summary of what changed -->

## Test Coverage
<!-- Which acceptance criteria are covered by tests -->
```

**Output:** Open PR ready for review

### 5. Code Review

**Triggered by:** Quality tests pass
**Agent role:** Code Reviewer (sonnet model)
**Runs in parallel with:** Security Review (stage 6)

The agent reviews the PR for:
- **Correctness** — Does the implementation match the spec?
- **Style** — Does it follow project conventions?
- **Architecture** — Are patterns used correctly? Any unnecessary complexity?
- **Edge cases** — Are error paths handled? Are inputs validated at boundaries?
- **Performance** — Any obvious N+1 queries, unnecessary re-renders, or heavy operations?

Review results are posted as PR comments. Issues are categorised:
- **CRITICAL** — Must fix before merge
- **WARNING** — Should fix, but not a blocker
- **SUGGESTION** — Nice to have, at reviewer's discretion

If CRITICAL or WARNING issues are found, the Builder is re-launched in fix mode (sonnet model, max 3 retries). If the fix budget is exhausted, the issue is labelled `needs-input` and escalated to a human. Round-based verdict pairing uses marker comments to track which review round each fix addresses.

**Output:** Review comments on the PR

### 6. Security

**Triggered by:** Quality tests pass (runs in parallel with Code Review)
**Agent role:** Security Reviewer (Clyde Barcode, sonnet model)

The agent reviews the new/changed code for security vulnerabilities:
- **OWASP Top 10** — SQL injection, XSS, command injection, LDAP injection, etc.
- **Secret detection** — No API keys, passwords, or tokens hardcoded in code
- **Unsafe patterns** — Insecure deserialization, broken auth, missing input validation
- **SAST scanning** — Semgrep with OWASP rules against the changed files

> Dependency CVE scanning, SBOM generation, and license compliance are handled by the organisation-wide quality workflow, not by this agent.

Security findings are posted as PR comments with severity ratings (CRITICAL / WARNING / INFO). WARNING-level findings also generate separate GitHub Issues labelled `finding` for tracking.

**Output:** Security code review on the PR, finding issues for WARNINGs

### 7. PR Assigned (Human Gate)

**Triggered by:** Both Code Review and Security pass
**Board column:** Review

The PR is assigned to a human reviewer. This is the single mandatory human approval point in the pipeline. The human reviews:
- Does the change make sense for the product?
- Are there concerns the agents missed?
- Is this the right time to ship this change?

The human approves, requests changes, or rejects.

### 8. Merge (Human)

**Triggered by:** Human approves the PR
**Agent role:** None — auto-merge intentionally disabled, humans must review and merge

The human merges the PR (squash or merge commit per project convention).

### 9. Archive (post-merge)

**Triggered by:** Human has merged the PR
**Script:** `scripts/run-archive.sh`

After the PR is merged, run the archive step to formalize the change:

```bash
scripts/run-archive.sh --app-path <path> --change-name <name> [--repo-path owner/repo] [--issue-number N]
```

The archive step:
1. **Sync delta specs** — copies specs from the change's `specs/` directory to the
   app's main `openspec/specs/` directory
2. **Generate test scenarios** — converts acceptance criteria from `tasks.md` into
   reusable `TS-NNN-*.md` files in `{app}/test-scenarios/`. These are auto-picked
   up by `/test-functional`, `/test-app`, and `/test-scenario-run` in future runs.
3. **Update CHANGELOG.md** — adds completed tasks under the current version
   (Keep a Changelog format)
4. **Move to archive** — moves the change to `openspec/changes/archive/YYYY-MM-DD-{name}/`
5. **Close GitHub issue** — if `--issue-number` and `--repo-path` are provided

Test scenarios accumulate over time — each archived change adds scenarios, building
a regression test library that future browser tests can execute.

**Output:** Archived change, test scenarios, updated changelog

## Traceability

Every code change is traceable to its spec through two independent paths:

**Path 1: Git history**
```
code line → git blame → commit "feat: add columns (#82)" → PR "Closes #82" → Issue #82 → spec
```

**Path 2: PHPDoc `@spec` tag**
```
code line → docblock @spec openspec/changes/kanban-mvp/tasks.md#task-1 → spec
```

The Builder adds `@spec` tags at three levels:
- **File docblock**: links the file to the change that created it
- **Class docblock**: links the class to the spec requirement
- **Method docblock**: links each method to the specific task

Multiple `@spec` tags are supported (code touched by multiple changes over time).
The Code Reviewer checks for missing `@spec` tags as part of architecture compliance.

Branch naming follows: `feature/{issue-number}/{change-name}` (e.g., `feature/82/kanban-mvp`).
All commits include `(#issue-number)`. PR body starts with `Closes #N`.

## Agent Personas

Each pipeline stage is handled by a named agent persona. These personas have Conduction company profiles and contribute visibly to the repository. See [Agent Configuration](agent-configuration.md) for persona details.

## Error Handling

| Scenario | Response |
|----------|----------|
| Build fails | Agent retries up to 3 times with different approaches |
| Quality tests fail | Builder fix-quality mode (sonnet, max 2 retries); escalates with `needs-input` label |
| Browser UI tests fail | Builder fix-browser mode (sonnet, max 2 retries); escalates with `needs-input` label |
| Review finds CRITICAL/WARNING | Builder fix mode (sonnet, max 3 retries); escalates with `needs-input` label if budget exhausted |
| Security vulnerability found in code | PR blocked; Builder attempts fix based on Security Reviewer's findings |
| Spec ambiguity | Agent flags the ambiguity as a PR comment; human resolves |
| Rate limit hit | Agent backs off and retries after cooldown |
| Container crash | Pipeline retries once, then logs the failure; card stays in current column |
| OAuth token expired | Token is refreshed before each container launch |

## Concurrency

Multiple changes can be in-progress simultaneously. Each change operates on its own branch and its own board card. Concurrent pipeline isolation is achieved through issue-based temp directories (`/tmp/hydra-{issue-number}/`). Agents must:
- Use git worktrees for parallel same-repo work
- Not modify shared configuration without coordination
- Detect and flag merge conflicts early

## Implementation Status

The following stages are fully implemented in the current pipeline:

| Stage | Status | Notes |
|-------|--------|-------|
| 1. Specs (Input) | Implemented | Builder reads `tasks.md`; spec path auto-detected from issue body |
| 2. Apply (Build) | Implemented | Feature branch creation, code implementation (opus), early branch push |
| 3. Automated Quality Tests | Implemented | `scripts/run-quality.sh` — all checks inside Docker php:X.Y-cli; `--keep-server` flag |
| 3a. Fix Quality | Implemented | Builder fix-quality mode (sonnet, max 2 retries) |
| 3b. Browser UI Tests | Implemented | `scripts/run-browser-tests.sh` — Playwright MCP on host; structured verdict JSON |
| 3c. Fix Browser | Implemented | Builder fix-browser mode (sonnet, max 2 retries) |
| 4. Archive | Implemented | Draft PR creation with structured description |
| 5. Code Review | Implemented | Parallel with Security (sonnet); posts CRITICAL/WARNING/SUGGESTION |
| 6. Security | Implemented | Parallel with Code Review (sonnet); Semgrep + Gitleaks + Trivy |
| 6a. Fix Review Findings | Implemented | Builder fix mode (sonnet, max 3 retries); escalates with `needs-input` label |
| 7. PR Assigned | Implemented | Human gate — manual review required |
| 8. Merge | Manual | Auto-merge intentionally disabled -- humans must review and merge |

Additional implemented features:
- **Parallel reviewer execution** — Code Review and Security Review run simultaneously (halves wall time)
- **Browser UI testing** — Playwright MCP on host with pre-extracted acceptance criteria; structured CRITICAL/WARNING verdicts
- **Board card auto-movement** — via GitHub Projects v2 API (`docs/templates/hydra-board-sync.yml`)
- **Findings as separate issues** — WARNING-level findings create standalone `finding`-labelled issues
- **Pipeline status comment** — `scripts/lib/pipeline-comment.sh` posts progress updates on the issue
- **Retry on container crash** — 1 automatic retry before escalation
- **OAuth token refresh** — token refreshed before each container launch
- **Round-based verdict pairing** — marker comments track which review round each fix addresses
- **Structured log aggregation** — logs written to `logs/pipeline-{timestamp}/`
- **Poll mode** — `--poll` flag for continuous board monitoring
- **Multi-repo spec support** — `--spec-repo` flag for specs in a different repository
- **Concurrent pipeline isolation** — issue-based temp directories for parallel runs

## Open Questions

- Should agents be able to split a spec into multiple PRs if it's too large?
- How do we handle cross-app changes that span multiple repositories?
