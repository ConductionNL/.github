# Writing Specs

How to write effective specifications that produce good code. Specs are the foundation of the entire workflow — bad specs lead to bad code, no matter how good the AI is.

## Spec Structure

Every spec file at `openspec/specs/{domain}/spec.md` follows this structure:

```markdown
# <Capability Name> Specification

**Status**: idea | planned | in-progress | done
**Scope**: company-wide | {app-name}
**OpenSpec changes**:
- [change-name](../../changes/change-name/)
- [archived-change](../../changes/archive/YYYY-MM-DD-archived-change/) _(archived YYYY-MM-DD)_

## Purpose
<What this capability does and why it exists (2–5 sentences). Include relevant ADR references.>

## Requirements

### REQ-{AREA}-{NNN}: <Name>
<Description using RFC 2119 keywords>

#### Scenario: <Name>
- GIVEN <precondition>
- WHEN <action>
- THEN <expected result>
- AND <additional result>

## Non-Functional Requirements

- **Performance:** <measurable performance requirement>
- **Accessibility:** <WCAG or usability requirement>
- **Internationalization:** Dutch and English MUST be supported (ADR-005)

## Acceptance Criteria

- [ ] <testable criterion>

## Notes

<Open questions, constraints, dependencies, related ADRs.>
```

### Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `**Status**` | Yes | `idea` → `planned` → `in-progress` → `done` |
| `**Scope**` | Yes | `company-wide` (in `.claude/openspec/specs/`) or app name (in `{app}/openspec/specs/`) |
| `**OpenSpec changes**` | Yes | Vertical list, one entry per line, oldest first. `_(none yet)_` until first change created. Archived entries include `_(archived YYYY-MM-DD)_`. See [Grouping rule](#openspec-changes-list-format) below. |
| `## Non-Functional Requirements` | Yes | Always present, even if minimal |
| `## Acceptance Criteria` | Yes | Placeholder OK for `idea` status; fill in before moving to `planned` |
| `## Notes` | Yes | Always present |

### Status lifecycle

```
idea ──► planned ──► in-progress ──► done
  │          │                         │
  │     ready for /opsx-ff             │ new change created
  │                                    ▼
still fuzzy, fill in             in-progress (again)
Acceptance Criteria first
```

| Status | Meaning |
|--------|---------|
| `idea` | Concept noted — Purpose defined, Requirements fuzzy |
| `planned` | Acceptance criteria fully defined — **ready for `/opsx-ff`** |
| `in-progress` | One or more OpenSpec changes have been created from this spec |
| `done` | All associated OpenSpec changes have been archived |

**Re-opening a done spec:** If a new change is created that modifies a `done` spec, set the status back to `in-progress`. The `**OpenSpec changes**` list preserves the full history (archived entries stay visible).

### OpenSpec changes list format

List entries oldest-first (top = oldest, bottom = newest). One entry per line:

```
**OpenSpec changes**:
- [change-name](../../changes/change-name/)
- [archived-change](../../changes/archive/YYYY-MM-DD-name/) _(archived YYYY-MM-DD)_
```

**When the list exceeds 15 entries**, group multiple changes per bullet by timeframe (same day → same month → same year). Oldest group first. **Never remove entries.**

```
**OpenSpec changes**:
- [change-a](link/), [change-b](link/) _(Jan 2026)_
- [change-c](link/), [change-d](link/) _(Mar 2026)_
- [newest-change](link/) _(Apr 2026)_
```

Group at the coarsest level that keeps the list under 15 bullets while preserving order. Start by grouping same-day entries, then same-month, then same-year if still too long.

## RFC 2119 Keywords

Use these keywords deliberately to communicate the importance of each requirement:

| Keyword | Meaning | Use when |
|---------|---------|----------|
| **MUST** / **SHALL** | Absolute requirement. Non-negotiable. | The feature won't work correctly without this |
| **MUST NOT** / **SHALL NOT** | Absolute prohibition | Doing this would break something or violate a constraint |
| **SHOULD** | Recommended, but exceptions may exist | Best practice that can be skipped with justification |
| **SHOULD NOT** | Discouraged, but exceptions may exist | Not ideal but acceptable in some cases |
| **MAY** | Optional | Nice to have, up to implementer |

### Examples

```markdown
# Good — clear intention
The API endpoint MUST return HTTP 404 when the resource does not exist.
The response SHOULD include a human-readable error message.
The response MAY include a machine-readable error code.

# Bad — vague, no keywords
The API should handle errors properly.
```

**Rule of thumb:** Prefer MUST/SHALL for normative requirements — if behavior is genuinely required, say so. Use SHOULD when real exceptions are acceptable. Reserve MAY for truly optional behavior; if it can be expressed as MUST or SHOULD, prefer that instead.

## Writing Scenarios

Scenarios use the Gherkin format (GIVEN/WHEN/THEN) to describe specific behaviors. They serve as both documentation and acceptance criteria for implementation.

### Good Scenarios

```markdown
#### Scenario: Successful login with valid credentials
- GIVEN a user with email "test@example.com" and a valid password
- WHEN they submit the login form
- THEN the system MUST return a JWT token
- AND the user MUST be redirected to the dashboard
- AND the session MUST be stored in the database

#### Scenario: Login fails with invalid password
- GIVEN a user with email "test@example.com"
- WHEN they submit the login form with an incorrect password
- THEN the system MUST return HTTP 401
- AND the response body MUST contain `{"error": "Invalid credentials"}`
- AND the failed attempt MUST be logged
```

### Bad Scenarios

```markdown
# Too vague
#### Scenario: Login works
- GIVEN a user
- WHEN they log in
- THEN it works

# Too implementation-specific
#### Scenario: Login
- GIVEN a POST to /api/v1/auth/login with body {"email":"x","pass":"y"}
- WHEN AuthController::login() calls UserService::authenticate()
- THEN it calls $mapper->findByEmail() and JWTService::generate()
```

### Tips for Good Scenarios

1. **Cover the happy path first**, then error cases, then edge cases
2. **Be specific about inputs and outputs** — what data, what status codes, what format
3. **Focus on behavior, not implementation** — describe what happens, not which classes/methods do it
4. **One scenario, one behavior** — don't combine multiple behaviors in one scenario
5. **Include negative scenarios** — what happens when things go wrong?

## Delta Specs

When making changes to existing functionality, use delta specs to show what's changing.

### ADDED

New requirements that didn't exist before:

```markdown
## ADDED Requirements

### Requirement: Full-Text Search
The system MUST support full-text search across publication titles and content bodies using PostgreSQL's tsvector.

#### Scenario: Search returns matching publications
- GIVEN publications with titles "Climate Report 2024" and "Budget Overview"
- WHEN a user searches for "climate"
- THEN the results MUST include "Climate Report 2024"
- AND the results MUST NOT include "Budget Overview"
- AND results MUST be ordered by relevance score
```

### MODIFIED

Changes to existing requirements. Always note what the previous behavior was:

```markdown
## MODIFIED Requirements

### Requirement: Session Duration
The system MUST expire user sessions after 15 minutes of inactivity.

(Previously: sessions expired after 30 minutes of inactivity)

#### Scenario: Session expires
- GIVEN a user who has been inactive for 16 minutes
- WHEN they make a request
- THEN the system MUST return HTTP 401
- AND the session MUST be cleared from the database
```

### REMOVED

Requirements being deprecated. Always explain why:

```markdown
## REMOVED Requirements

### Requirement: Remember Me Checkbox
(Deprecated: replaced by automatic session refresh on activity. Removing the checkbox simplifies the login form and improves security by eliminating long-lived sessions.)
```

### RENAMED

Requirements whose name is changing but whose behavior is unchanged. Always use FROM:/TO: format so reviewers can track the rename:

```markdown
## RENAMED Requirements

### Requirement: Old Requirement Name
FROM: Old Requirement Name
TO: New Requirement Name
<!-- No behavior change — rename only -->
```

## Referencing Shared Specs

When your requirement relates to a cross-project convention, reference the shared spec:

```markdown
### Requirement: Publication API Endpoint
The system MUST provide a REST endpoint at `/index.php/apps/opencatalogi/api/publications`.

See shared spec: `api-patterns/spec.md#requirement-url-structure` for URL conventions.
See shared spec: `api-patterns/spec.md#requirement-cors-support` for CORS requirements.
```

Shared specs live in `.claude/openspec/specs/` (company-wide, maintained by Conduction). Check that directory for currently available shared specs — the list evolves as new cross-app specs are added. Company-wide architectural decisions (NL Design System, API conventions, security, i18n) are captured in ADRs under `.claude/openspec/architecture/`.

## Organizing Specs

### By domain capability

```
openspec/specs/
├── auth/spec.md            # Authentication & sessions
├── publications/spec.md    # Publication CRUD
├── search/spec.md          # Search functionality
├── export/spec.md          # Data export features
└── notifications/spec.md   # User notifications
```

### Tips

- **One capability per spec file** — don't mix unrelated concerns
- **Name directories for the domain concept**, not the implementation (`search/`, not `search-controller/`)
- **Keep specs focused** — if a spec file grows past ~100 requirements, split it
- **Update specs when behavior changes** — specs must always reflect the current system behavior

## Common Mistakes

### 1. Writing specs after code

Specs written after implementation just document what exists. They don't help you think through requirements or catch issues early. **Write specs first.**

### 2. Being too vague

```markdown
# Bad
The system should handle errors.

# Good
The system MUST return HTTP 400 with a JSON body containing an `error` field
when the request body fails validation.
```

### 3. Being too implementation-specific

```markdown
# Bad — tied to specific classes
The AuthController MUST call UserMapper::findByEmail().

# Good — describes behavior
The system MUST look up users by email address during authentication.
```

### 4. Missing error scenarios

Always consider: what happens when the input is invalid? When the resource doesn't exist? When the user isn't authorized? When an external service is down?

### 5. Using MUST for everything

If everything is MUST, nothing is distinguishable. Reserve MUST for true requirements and use SHOULD/MAY for less critical behaviors.

### 6. Writing untestable requirements

```markdown
# Bad — how do you verify this?
The system MUST be fast.

# Good — measurable
The search endpoint MUST respond within 500ms for queries returning fewer than 100 results.
```

## Task Breakdown

When writing `tasks.md`, each task should:

1. **Be completable in one focused iteration** (15-30 minutes)
2. **Have a clear `spec_ref`** pointing to the specific requirement
3. **List `files`** to scope the work
4. **Include `acceptance_criteria`** extracted from spec scenarios
5. **Be ordered by dependency** — foundations first, features second, polish third

### Mandatory deliverables per feature

Every feature implemented from a spec MUST include all three layers:

1. **Backend logic** — service/controller code that implements the requirement
2. **UI** — a user-facing interface so the feature is actually usable (Vue component, page, dialog, form, etc.)
3. **Tests** — covering both backend and frontend:
   - **Unit tests** (PHPUnit) for services, mappers, and business logic
   - **Newman/Postman tests** for API endpoints (add to the app's Postman collection)
   - **Browser tests** (Playwright MCP) for the UI — verify the feature works end-to-end through the browser

After implementing each task, the agent MUST run the relevant tests to confirm everything works:
- `composer test` or `vendor/bin/phpunit` for unit tests
- `newman run` for API tests
- Browser MCP snapshot/interaction for UI verification

A task is NOT complete until its tests pass.

### Good task breakdown

```markdown
### Task 1: Create SearchService with basic query method
- **spec_ref**: `openspec/specs/search/spec.md#requirement-full-text-search`
- **files**: `lib/Service/SearchService.php`
- **acceptance_criteria**:
  - GIVEN a search query WHEN SearchService::search("test") is called THEN it returns matching objects
- [ ] Implement service logic
- [ ] Write unit test (`tests/Unit/Service/SearchServiceTest.php`)
- [ ] Run unit tests — confirm passing

### Task 2: Create SearchController with GET endpoint
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-api-endpoint`
- **files**: `lib/Controller/SearchController.php`, `appinfo/routes.php`
- **acceptance_criteria**:
  - GIVEN a GET request to /api/search?q=test THEN returns JSON array of results
- [ ] Implement controller and route
- [ ] Add Newman/Postman test to collection
- [ ] Run Newman tests — confirm passing

### Task 3: Add search UI page
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-ui`
- **files**: `src/views/SearchView.vue`, `src/router/index.js`
- **acceptance_criteria**:
  - GIVEN a user navigating to the search page WHEN they enter a query THEN results are displayed
- [ ] Implement Vue component
- [ ] Build frontend (`npm run build`)
- [ ] Browser test — navigate to page, enter query, verify results appear

### Task 4: Add pagination to search results
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-pagination`
- **files**: `lib/Service/SearchService.php`, `lib/Controller/SearchController.php`, `src/views/SearchView.vue`
- **acceptance_criteria**:
  - GIVEN 50 results WHEN requesting page=2&limit=10 THEN returns results 11-20 with total count
- [ ] Implement backend pagination
- [ ] Update UI with pagination controls
- [ ] Add Newman test for pagination params
- [ ] Run all tests — confirm passing
```

### Bad task breakdown

```markdown
### Task 1: Implement search
- [ ] Do everything

### Task 2: (also bad) Backend only, no UI or tests
- [ ] Add SearchService
- [ ] Add SearchController
# Missing: no UI (users can't use it), no tests (nothing verified)
```
