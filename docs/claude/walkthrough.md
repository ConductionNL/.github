# End-to-End Walkthrough

_This is the **worked example** — see [Getting Started](./getting-started.md) for setup, and [Workflow Overview](./workflow.md) for the architecture reference._

This walkthrough follows a realistic example: adding a publication search endpoint to OpenCatalogi. We'll go through every step of the flow, showing what you type and what happens.

## The Feature

"Users of the tilburg-woo-ui frontend need to search for WOO publications by keyword. We need a search API endpoint in OpenCatalogi that returns matching publications with pagination."

## Phase 1: Spec Building

### Start the change

```
/opsx-new add-publication-search
```

Claude responds:
> Created change `add-publication-search` at `openspec/changes/add-publication-search/`

### Generate all artifacts

```
/opsx-ff
```

Claude generates four files. Let's look at each:

### proposal.md (generated)

```markdown
# Proposal: add-publication-search

## Summary
Add a search API endpoint to OpenCatalogi that allows the tilburg-woo-ui
frontend to search for WOO publications by keyword.

## Motivation
The current publication listing endpoint only supports browsing. Users need
to find specific publications by searching for keywords in titles and content.

## Affected Projects
- [x] Project: `opencatalogi` — New search controller and service
- [ ] Project: `tilburg-woo-ui` — Will consume the new endpoint (separate change)

## Scope
### In Scope
- Search API endpoint with keyword query parameter
- Search across publication titles and content
- Paginated results
- CORS support for frontend access

### Out of Scope
- Advanced filtering (by date, category, etc.) — future change
- Search suggestions / autocomplete — future change
- Frontend UI changes — separate change in tilburg-woo-ui

## Approach
Create a new SearchService that uses PostgreSQL full-text search via
OpenRegister's ObjectService. Expose it through a SearchController with
a public GET endpoint.

## Cross-Project Dependencies
- Depends on OpenRegister's ObjectService for data access
- tilburg-woo-ui will consume this endpoint (no changes needed there yet)

## Rollback Strategy
Remove the SearchController, SearchService, and route registration.
No database changes or migrations needed.

## Open Questions
None — straightforward addition.
```

### specs/search/spec.md (generated)

```markdown
# Search Specification

## Purpose
Provides keyword-based search across WOO publications for the public frontend.

## ADDED Requirements

### Requirement: Search API Endpoint
The system MUST provide a public GET endpoint at
`/index.php/apps/opencatalogi/api/search`.

#### Scenario: Search with results
- GIVEN publications exist with titles "Klimaatrapport 2024" and "Begroting 2025"
- WHEN a GET request is made to `/api/search?q=klimaat`
- THEN the response MUST be HTTP 200
- AND the response body MUST be a JSON object with a `results` array
- AND the results MUST include "Klimaatrapport 2024"
- AND the results MUST NOT include "Begroting 2025"

#### Scenario: Search with no results
- GIVEN no publications match the query
- WHEN a GET request is made to `/api/search?q=xyznonexistent`
- THEN the response MUST be HTTP 200
- AND the response body MUST contain an empty `results` array

#### Scenario: Search without query parameter
- GIVEN the search endpoint is called
- WHEN no `q` parameter is provided
- THEN the response MUST be HTTP 400
- AND the response body MUST contain `{"error": "Missing required parameter: q"}`

### Requirement: Search Pagination
The search endpoint MUST support pagination via `page` and `limit` parameters.

#### Scenario: Paginated search
- GIVEN 50 publications match the query "gemeente"
- WHEN a GET request is made to `/api/search?q=gemeente&page=2&limit=10`
- THEN the response MUST contain results 11-20
- AND the response MUST include `"total": 50`
- AND the response MUST include `"page": 2`
- AND the response MUST include `"limit": 10`

#### Scenario: Default pagination
- GIVEN more than 25 publications match
- WHEN no pagination parameters are provided
- THEN the response MUST return at most 25 results (default limit)
- AND page MUST default to 1

### Requirement: Search CORS
The search endpoint MUST be accessible from cross-origin frontends.

#### Scenario: Cross-origin request from tilburg-woo-ui
- GIVEN the tilburg-woo-ui frontend running on localhost:3000
- WHEN it makes a GET request to the search endpoint
- THEN the response MUST include `Access-Control-Allow-Origin: *`
- AND the controller method MUST use @CORS, @NoCSRFRequired, @PublicPage annotations
```

### design.md (generated)

```markdown
# Design: add-publication-search

## Architecture Overview
New SearchController + SearchService layered on top of OpenRegister's
ObjectService. No database changes needed — uses existing publication objects.

## API Design

### `GET /index.php/apps/opencatalogi/api/search`

**Query parameters:**
| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| q     | yes      | —       | Search query string |
| page  | no       | 1       | Page number |
| limit | no       | 25      | Results per page (max 100) |

**Response (200):**
```json
{
  "results": [
    {
      "id": "uuid",
      "title": "Klimaatrapport 2024",
      "summary": "...",
      "published": "2024-06-15"
    }
  ],
  "total": 50,
  "page": 2,
  "limit": 10
}
```

**Response (400):**
```json
{"error": "Missing required parameter: q"}
```

## Database Changes
None. Uses existing publication objects via ObjectService.

## Nextcloud Integration
- **Controller**: `SearchController extends ApiController`
  - `@CORS`, `@NoCSRFRequired`, `@PublicPage` annotations
- **Service**: `SearchService` injected via constructor
  - Uses ObjectService from OpenRegister for data access

## File Structure
```
lib/
  Controller/SearchController.php    (new)
  Service/SearchService.php          (new)
appinfo/
  routes.php                         (modified — add search route)
```

## Security Considerations
- Public endpoint (no authentication required)
- Input sanitization on query parameter to prevent injection
- Rate limiting not in scope (future change)
```

### tasks.md (generated)

```markdown
# Tasks: add-publication-search

## Implementation Tasks

### Task 1: Create SearchService with query method
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-api-endpoint`
- **files**: `lib/Service/SearchService.php`
- **acceptance_criteria**:
  - GIVEN publications exist WHEN SearchService::search("klimaat") is called
    THEN it returns matching publication objects
- [ ] Implement
- [ ] Test

### Task 2: Create SearchController with GET endpoint
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-api-endpoint`
- **files**: `lib/Controller/SearchController.php`, `appinfo/routes.php`
- **acceptance_criteria**:
  - GIVEN a GET request to /api/search?q=klimaat THEN returns JSON results
  - GIVEN no q parameter THEN returns HTTP 400 with error message
- [ ] Implement
- [ ] Test

### Task 3: Add pagination support
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-pagination`
- **files**: `lib/Service/SearchService.php`, `lib/Controller/SearchController.php`
- **acceptance_criteria**:
  - GIVEN 50 results WHEN page=2&limit=10 THEN returns items 11-20 with total
  - GIVEN no pagination params THEN defaults to page=1, limit=25
- [ ] Implement
- [ ] Test

### Task 4: Add CORS and public access annotations
- **spec_ref**: `openspec/specs/search/spec.md#requirement-search-cors`
- **files**: `lib/Controller/SearchController.php`, `appinfo/routes.php`
- **acceptance_criteria**:
  - GIVEN a cross-origin request THEN response includes CORS headers
  - GIVEN the controller THEN uses @CORS, @NoCSRFRequired, @PublicPage
- [ ] Implement
- [ ] Test

## Verification
- [ ] All tasks checked off
- [ ] `openspec validate` passes
- [ ] Manual testing against acceptance criteria
- [ ] Code review against spec requirements
```

### Review the artifacts

At this point, **you read through all four files** and make adjustments:

- Is the scope right?
- Are scenarios missing edge cases?
- Is the task breakdown granular enough?
- Are the spec keywords right (MUST vs SHOULD)?

Edit the files directly if needed. Once you're satisfied, move to Phase 2.

## Phase 2: Plan to GitHub Issues

```
/opsx-plan-to-issues
```

Claude responds:
> **Created GitHub Issues:**
>
> Tracking issue: https://github.com/ConductionNL/opencatalogi/issues/42
> - `[OpenSpec] add-publication-search`
>
> Task issues:
> - #43: `[add-publication-search] Create SearchService with query method`
> - #44: `[add-publication-search] Create SearchController with GET endpoint`
> - #45: `[add-publication-search] Add pagination support`
> - #46: `[add-publication-search] Add CORS and public access annotations`
>
> Saved: `openspec/changes/add-publication-search/plan.json`

Now you can see progress on GitHub! Open the tracking issue to see the full checklist. You can also add these to a GitHub Project board for kanban visualization.

## Phase 3: Implementation

```
/opsx-apply
```

### Iteration 1: SearchService

Claude reads plan.json, finds Task 1 (pending), reads the spec section, and implements:

> **Starting Task 1/4:** Create SearchService with query method
>
> Reading spec: `openspec/specs/search/spec.md#requirement-search-api-endpoint`
>
> Creating `lib/Service/SearchService.php`...
> - Added `search()` method using ObjectService
> - Query sanitization applied
>
> Acceptance check: PASS
> - SearchService::search("klimaat") returns matching objects
>
> Closing GitHub issue #43...
> Updating tracking issue #42 checklist...
>
> **Task 1 complete.** Moving to Task 2...

### Iteration 2: SearchController

> **Starting Task 2/4:** Create SearchController with GET endpoint
>
> Reading spec: `openspec/specs/search/spec.md#requirement-search-api-endpoint`
>
> Creating `lib/Controller/SearchController.php`...
> Adding route to `appinfo/routes.php`...
>
> Acceptance check: PASS
> - GET /api/search?q=klimaat returns JSON results
> - GET /api/search (no q param) returns HTTP 400
>
> Closing GitHub issue #44...
>
> **Task 2 complete.** Moving to Task 3...

### Iteration 3: Pagination

> **Starting Task 3/4:** Add pagination support
>
> Reading spec: `openspec/specs/search/spec.md#requirement-search-pagination`
>
> Modifying `SearchService::search()` to accept page/limit params...
> Modifying `SearchController::search()` to read query params...
>
> Acceptance check: PASS
> - 50 results, page=2, limit=10 returns items 11-20 with total=50
> - No params defaults to page=1, limit=25
>
> Closing GitHub issue #45...
>
> **Task 3 complete.** Moving to Task 4...

### Iteration 4: CORS

> **Starting Task 4/4:** Add CORS and public access annotations
>
> Reading spec: `openspec/specs/search/spec.md#requirement-search-cors`
>
> Adding annotations to SearchController::search()...
> Adding OPTIONS route to routes.php...
>
> Acceptance check: PASS
> - Cross-origin request includes CORS headers
> - @CORS, @NoCSRFRequired, @PublicPage annotations present
>
> Closing GitHub issue #46...
>
> **All 4 tasks complete!** Run `/opsx-verify` to verify against specs.

## Phase 4: Review

```
/opsx-verify
```

Claude loads ALL the specs and checks every requirement:

> **Review: add-publication-search**
>
> Tasks completed: 4/4
> GitHub issues closed: 4/4
>
> **Spec Compliance Check:**
>
> Requirement: Search API Endpoint
> - Scenario: Search with results — PASS
> - Scenario: Search with no results — PASS
> - Scenario: Search without query parameter — PASS
>
> Requirement: Search Pagination
> - Scenario: Paginated search — PASS
> - Scenario: Default pagination — PASS
>
> Requirement: Search CORS
> - Scenario: Cross-origin request — PASS
>
> **Shared Spec Check:**
> - nextcloud-app: Route ordering — PASS (search route before wildcards)
> - api-patterns: URL structure — PASS
> - api-patterns: Error responses — WARNING (missing `details` field in 400 response)
> - nl-design: N/A (no frontend changes)
>
> **Findings:**
> - 0 CRITICAL
> - 1 WARNING: Error response missing optional `details` field
> - 0 SUGGESTIONS
>
> **Recommendation: APPROVE**
>
> Review saved: `openspec/changes/add-publication-search/review.md`

## Phase 5: Archive

```
/opsx-archive
```

> Archiving `add-publication-search`...
> - Syncing delta specs → main specs
> - Moving to `openspec/changes/archive/2026-02-15-add-publication-search/`
> - All artifacts preserved
>
> Done! The search spec is now part of the main specs at
> `openspec/specs/search/spec.md`.

## Result

After this flow, you have:

1. **Working code** — SearchController and SearchService implemented
2. **Spec documentation** — `openspec/specs/search/spec.md` describes the current behavior
3. **Audit trail** — The full change preserved in `openspec/changes/archive/`
4. **GitHub history** — Tracking issue #42 with all sub-issues closed
5. **Review report** — `review.md` confirming spec compliance

The next time someone needs to modify search behavior, they'll find the spec, understand the current requirements, and write delta specs for their changes.
