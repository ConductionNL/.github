# ConductionNL OpenSpec — Organization-Wide Specifications

This directory contains organization-wide OpenSpec specifications that apply across all ConductionNL repositories. These are shared standards and quality baselines that every app must follow.

## What is OpenSpec?

OpenSpec is a spec-driven development workflow where changes are defined as structured artifacts (proposal, specs, design, tasks) before implementation begins. Specs live alongside code and persist across sessions, ensuring continuity and traceability.

## Planned Specifications

The following org-wide specs are planned or in progress:

### Test Coverage (75% minimum)

- **Target**: All apps must achieve at least 75% code coverage
- **Scope**: Unit tests (PHPUnit / Vitest), integration tests, API tests
- **Enforcement**: CI pipeline blocks merge below threshold
- **Status**: Planned

### NL Design System Compliance

- **Target**: All apps must render correctly with the nldesign Nextcloud app enabled
- **Scope**: No hardcoded colors, use CSS variables, WCAG AA contrast, Rijkshuisstijl compatibility
- **Token sets**: Rijkshuisstijl, Utrecht, Amsterdam, Den Haag, Rotterdam
- **Enforcement**: Visual regression tests with each token set
- **Status**: Planned

### API Patterns

- **Target**: Consistent REST API design across all apps
- **Scope**: URL conventions, CORS handling, error response format, pagination, filtering
- **Standards**: JSON:API-inspired, Nextcloud OCS conventions, OpenAPI documentation
- **Enforcement**: OpenAPI schema validation in CI
- **Status**: Planned

### Internationalization (i18n) — Dutch and English

- **Target**: All apps must support at minimum Dutch (nl) and English (en)
- **Scope**: All UI strings, error messages, API responses, documentation
- **Enforcement**: Missing translation detection in CI, Transifex integration
- **Status**: Planned

## Directory Structure

Once specs are formalized, they will follow this structure:

```
openspec/
  specs/
    test-coverage/
      spec.md          # Full specification
      scenarios.md     # GIVEN/WHEN/THEN acceptance criteria
    nl-design/
      spec.md
      scenarios.md
    api-patterns/
      spec.md
      scenarios.md
    i18n/
      spec.md
      scenarios.md
  changes/             # Active changes being worked on
  archive/             # Completed and archived changes
```

## How Specs Are Used

1. **Per-app specs** live in `{app}/openspec/` within each repository
2. **Org-wide specs** (this directory) define shared baselines
3. Apps reference org-wide specs and may extend them with app-specific requirements
4. The OpenSpec workflow (`/opsx:new`, `/opsx:ff`, `/opsx:apply`, `/opsx:verify`, `/opsx:archive`) manages the lifecycle

## Contributing

To propose a new org-wide spec:

1. Open an issue in this repository describing the standard
2. Draft a `spec.md` following the OpenSpec format
3. Submit a PR for team review
4. Once merged, all apps are expected to adopt the spec within a reasonable timeline
