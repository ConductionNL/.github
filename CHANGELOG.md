# Changelog

All notable changes to the Conduction Employee Handbook are documented in this file.

## 2026-04-13 — HWW 2.0 Review Feedback

Processed review feedback from HWW 2.0 session. Changes across EN + NL versions.

### Changed

- **ESET / Linux** (`ISO/security.md`): Added Linux alternative — workstation-security repo reference, teamlead guidance, log audit notice
- **Onboarding** (`WayOfWork/onboarding.md`): Replaced inline Code of Conduct summary with link to full `code-of-conduct` page (single source of truth)
- **Vacatures** (`WayOfWork/Vacancies.md`): Changed primary application channel from GitHub Issues to info@conduction.nl; added GitHub org link and "About Conduction" section
- **Hotfix process** (`WayOfWork/release-process.md`): Clarified that same branch protection rules (reviewer count, CI) apply to hotfixes — no exceptions to human-in-the-loop
- **Customer support** (`WayOfWork/customer-support.md`): Corrected Jira ticket creation from "auto-creates" to manual; removed vier-ogen-principe section (not relevant to support page)
- **Quality policy** (`ISO/quality-policy.md`): Removed NPS objective (not yet measured); updated communication section to reference quality sessions instead of documentation site only
- **Security policy** (`ISO/security-policy.md`): Added status.commonground.nu link to uptime monitoring objective

### Added

- **Crisis management vuistregels** (`ISO/incident-reporting.md`): Added 7 rules of thumb for crisis situations (report first, communicate more, contain before fix, etc.)

### Verified

- **Dependency checks** (point 7): All documented checks (license compliance, vulnerability scan, SBOM/CycloneDX, composer audit, npm audit) are present in the centralized `quality.yml` reusable workflow in `.github` repo. OpenRegister calls these as a reusable workflow. Documentation is accurate.
- **AI tooling** (point 13): Current documentation confirmed still accurate — no changes needed.
- **Working@ / Drive assessments** (point 3): Remains Drive-specific, no handbook changes needed per review decision.

### Verified & Resolved

- **Code of Conduct vs Working@Conduction PDF** (points 2, 10): Compared `code-of-conduct.md` against the official Working@Conduction PDF (v1.0, 1.6.2025) punkt 29. Added "Conduction Workplace Agreements" section with all Conduction-specific rules from the PDF: data security awareness, no gifts > €25, reputation clause, mutual accountability. Contributor Covenant base preserved.
