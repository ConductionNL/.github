# GIBIT ICT Quality Norms Compliance

**Status:** Proposal
**Scope:** Org-wide (all Conduction apps)
**Created:** 2026-03-23

## Problem

GIBIT (Gemeentelijke ICT-kwaliteitsnormen en Beveiligingsnormen voor ICT) defines quality norms for government ICT procurement and operations. Analysis of tender sources shows 49 tenders requiring GIBIT compliance, making it one of the most frequently demanded standards in Dutch government procurement.

Our Conduction apps currently do not explicitly document or verify GIBIT compliance. This creates risk in tender responses -- we cannot demonstrate compliance systematically, and individual apps may have gaps in meeting specific GIBIT norms. Related standards compound the demand: BIO (170 tender sources), AVG/GDPR (149), and ISO 27001 (53).

## Solution

Create a GIBIT compliance framework that applies to all Conduction Nextcloud apps. This includes a compliance matrix, automated verification where possible, and per-app documentation of compliance status.

## Features

### GIBIT Compliance Matrix
- Central document mapping all GIBIT norms to their applicability per Conduction app
- Current compliance status per norm per app (compliant / partially compliant / non-compliant / not applicable)
- Gap analysis with remediation roadmap

### Security Norms
- Password policy enforcement (delegated to Nextcloud, documented)
- Session management (timeout, invalidation, concurrent session handling)
- Encryption at rest (database, file storage) and in transit (TLS, API security)
- Input validation and output encoding across all apps

### Availability Norms
- Uptime SLA documentation per deployment model (self-hosted vs managed)
- Backup frequency and retention requirements
- Disaster recovery plan template
- Health check endpoints per app

### Data Quality Norms
- Data validation rules documented per schema/entity
- Integrity checks (referential integrity, constraint enforcement)
- Audit logging of all data mutations (who, what, when)

### Privacy Norms (AVG/GDPR)
- Data minimization: document which personal data is collected and why
- Right to be forgotten: deletion/anonymization capabilities
- Data processing agreements: template and documentation
- Privacy by design: architectural decisions documented

### Interoperability Norms
- Open standards usage (StUF, ZGW, CMIS, OpenAPI)
- API documentation completeness (OpenAPI specs for all endpoints)
- Data portability (export/import in open formats)
- Standard protocol support (REST, GraphQL where applicable)

### Automated CI Checks
- Security header verification (CSP, HSTS, X-Frame-Options)
- Dependency vulnerability scanning (Composer audit, npm audit)
- Code quality gates (existing PHPCS/PHPMD/Psalm/PHPStan checks)
- License compliance scanning
- OWASP dependency check integration

### Per-App Compliance Badge
- Compliance status badge in each app's README
- Automated status update from CI pipeline
- Link to detailed compliance report

## Standards

| Standard | Description | Tender Demand |
|----------|-------------|---------------|
| GIBIT 2020 | Gemeentelijke ICT-kwaliteitsnormen en Beveiligingsnormen | 49 sources |
| BIO | Baseline Informatiebeveiliging Overheid | 170 sources |
| AVG/GDPR | Algemene Verordening Gegevensbescherming | 149 sources |
| ISO 27001 | Information Security Management | 53 sources |

## Scope

All 11 Conduction Nextcloud apps:
- OpenRegister
- OpenCatalogi
- OpenConnector
- Docudesk
- NL Design
- MyDash
- SoftwareCatalog
- LarpingApp
- ZaakAfhandelApp
- Procest
- Pipelinq

## Risks

- GIBIT norms are broad; not all norms apply to application-level software (some are infrastructure/organizational)
- Compliance is partly inherited from Nextcloud platform -- need clear delineation of responsibilities
- Maintaining compliance documentation requires ongoing effort as apps evolve
- Some norms may require infrastructure-level changes outside app scope (hosting provider responsibility)

## Open Questions

1. Which GIBIT norms are application-level vs infrastructure-level vs organizational?
2. How do we handle compliance inheritance from the Nextcloud platform?
3. Should compliance checks block CI pipelines or only report?
4. What is the minimum viable compliance set for tender responses?
