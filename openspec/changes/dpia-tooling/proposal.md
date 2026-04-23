# DPIA (Privacy Impact Assessment) Tooling

**Status:** Proposal
**Scope:** Org-wide (all Conduction apps)
**Created:** 2026-03-23

## Problem

Data Protection Impact Assessments (DPIAs) are legally required under AVG/GDPR Article 35 for processing that poses high risk to data subjects. Analysis of tender sources shows 25 tenders explicitly demanding DPIA documentation or tooling, with 149 tender sources requiring broader AVG/GDPR compliance.

Our Conduction apps process personal data -- cases contain citizen information (Procest), contacts store personal details (Pipelinq), and documents may contain sensitive content (Docudesk). Despite this, there is no structured DPIA support: no templates, no tooling to identify what personal data is processed, and no automated support for data subject rights (access, deletion, portability).

Organizations deploying our apps must perform DPIAs manually, without guidance from the software itself on what data is processed and how.

## Solution

Create DPIA templates and tooling that help organizations perform privacy impact assessments for each Conduction app. Add privacy-by-design features to the apps themselves, including a privacy dashboard, data subject rights tooling, and automated data processing register generation.

## Features

### DPIA Template per App
- Standardized DPIA document template following Dutch AP (Autoriteit Persoonsgegevens) guidance
- Pre-filled per app: what personal data is processed, legal basis options, identified risks, standard mitigations
- Exportable as PDF for inclusion in tender responses and compliance dossiers

### Pre-filled DPIA from Data Model
- Automated analysis of OpenRegister schemas to identify personal data fields
- Classification of data sensitivity (regular personal data, special categories, BSN)
- Mapping of data flows: where data enters, is stored, shared, and deleted
- Retention period documentation per data type

### Privacy Dashboard (Nextcloud Admin)
- Overview of all personal data stored across all Conduction apps
- Data volume metrics: how many records, how many data subjects
- Retention status: objects past retention date flagged
- Data sharing overview: which external systems receive personal data (via OpenConnector)

### Data Subject Access Request (DSAR) Tooling
- Search across all OpenRegister schemas for a specific person (by BSN, name, email)
- Export all data for a data subject in machine-readable format (JSON, CSV)
- Audit trail of who accessed the export
- Configurable per organization: which fields to search, which schemas to include

### Right to Be Forgotten
- Delete or anonymize all data for a specific person across OpenRegister
- Configurable anonymization rules per schema (which fields to blank, hash, or delete)
- Cascading deletion across related objects
- Audit log entry documenting the deletion (without revealing deleted data)
- Legal hold override: prevent deletion when legal retention applies

### Data Processing Register (Verwerkingsregister)
- Auto-generated from app configurations and OpenRegister schema metadata
- Documents: purpose, legal basis, categories of data subjects, categories of personal data, recipients, transfers to third countries, retention periods, security measures
- Exportable in standard format for submission to AP
- Version history to track changes over time

### Retention Policy Enforcement
- Define retention periods per schema/object type in OpenRegister
- Automated flagging of objects past retention date
- Optional automated deletion/anonymization with approval workflow
- Dashboard widget showing retention status

### Privacy-by-Design CI Checklist
- PR template checklist for privacy considerations
- Automated check: new database fields/schema properties flagged for privacy review
- Warning when personal data fields lack retention metadata
- Documentation requirement for any new data processing activity

## Standards

| Standard | Article | Description | Tender Demand |
|----------|---------|-------------|---------------|
| AVG/GDPR | Art. 35 | Data Protection Impact Assessment | 25 sources |
| AVG/GDPR | Art. 30 | Records of processing activities (verwerkingsregister) | included in 149 |
| AVG/GDPR | Art. 15 | Right of access by the data subject | included in 149 |
| AVG/GDPR | Art. 17 | Right to erasure (right to be forgotten) | included in 149 |
| AVG/GDPR | Art. 20 | Right to data portability | included in 149 |
| BIO | - | Baseline Informatiebeveiliging Overheid (privacy controls) | 170 sources |

## Scope

All Conduction apps, with priority on apps that handle personal data:

**High priority (direct personal data processing):**
- Procest (case management with citizen data)
- Pipelinq (contact and workflow management)
- Docudesk (document management, potentially sensitive content)
- ZaakAfhandelApp (case handling with personal data)

**Medium priority (indirect personal data):**
- OpenRegister (foundation -- stores all structured data)
- OpenConnector (data sharing with external systems)
- OpenCatalogi (catalog may reference personal data schemas)

**Lower priority (minimal personal data):**
- NL Design (theming, no personal data)
- MyDash (dashboard, displays data from other apps)
- SoftwareCatalog (software metadata)
- LarpingApp (hobby app, limited personal data)

## Risks

- Schema analysis for personal data detection requires metadata that may not exist yet in all schemas
- DSAR across large datasets could be performance-intensive
- Right to be forgotten conflicts with legal retention obligations (need clear precedence rules)
- Auto-generated verwerkingsregister may not capture all processing activities (especially those outside OpenRegister)
- Privacy dashboard requires cross-app data access that may need architectural changes

## Open Questions

1. Should the privacy dashboard be a standalone app or integrated into an existing app (MyDash)?
2. How to handle BSN (Burger Service Nummer) -- special legal requirements for storage and access?
3. What level of automation is appropriate for retention enforcement (flag only vs auto-delete)?
4. How to detect personal data in unstructured documents (Docudesk)?
5. Should DPIA templates be maintained in the app or as separate downloadable documents?
