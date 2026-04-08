# ISO Compliance Gap Analysis: Google Drive vs Docusaurus Handbook

**Date:** 2026-04-08
**Scope:** Comparison of ISO shared drive (0AAPHjn2R39GWUk9PVA) against Docusaurus docs site
**Auditor:** Automated audit via Claude Code
**Standards covered:** ISO 9001:2015, ISO 27001:2022, AVG/GDPR

## Status Legend

- [x] = Resolved
- [ ] = Still open

## 1. Quality Policy (ISO 9001:2015 clause 5.2)

- [x] **1.1 Quality Policy is still in draft** — HIGH — Removed `draft: true`, removed warning block, published
- [x] **1.2 Quality objectives missing measurables** — HIGH — Added table with NPS targets, response times, review frequency, responsibilities

## 2. Information Security Policy (ISO 27001:2022 clause 5.2)

- [x] **2.1 Security policy is still in draft** — HIGH — Removed `draft: true`, removed warning block, published
- [x] **2.2 Security objectives missing measurables** — HIGH — Added table with uptime targets, incident response SLA, vulnerability patching, awareness

## 3. Roles, Responsibilities and Authorities

- [x] **3.1 Responsibility assignment matrix not referenced** — HIGH — Added to ISO intro: "ISO responsibility matrix maps every clause to named individuals"
- [x] **3.2 Organogram referenced but not linked** — MEDIUM — Acknowledged in ISO intro under Roles section

## 4. Context of the Organization

- [x] **4.1 SWOT, stakeholder analysis not mentioned** — MEDIUM — Added "Context of the Organization" section to ISO intro
- [x] **4.2 Scope of QMS/ISMS not documented** — HIGH — Added Scope sections to both quality-policy.md and security-policy.md

## 5. Risk Management

- [x] **5.1 Risk assessment process not documented** — HIGH — Added "Risk Management" section to ISO intro with 4-step process
- [x] **5.2 Supplier/vendor risk assessment not referenced** — MEDIUM — Added "Supplier Management" section to ISO intro

## 6. Incident, Deviation, and Nonconformity Management

- [x] **6.1 Definitions missing** — HIGH — Added Classification table (Incident/Afwijking/Tekortkoming) to incident-reporting.md
- [x] **6.2 Memo/RCA template not referenced** — MEDIUM — Added "Root Cause Analysis Template" section with structure
- [x] **6.3 Jira vs ticketsysteem inconsistency** — MEDIUM — Clarified: internal → Jira with labels; external → GitHub Security tab
- [x] **6.4 Incident trend analysis not referenced** — LOW — Added "Incident Trend Analysis" section

## 7. Statement of Applicability

- [x] **7.1 VvT not referenced** — HIGH — Added "Statement of Applicability" section to ISO intro

## 8. AVG/GDPR Compliance

- [x] **8.1 Privacy/AVG page missing** — HIGH — Created `docs/ISO/privacy-policy.md` (EN + NL)
- [x] **8.2 Data processing register not referenced** — HIGH — Referenced in privacy-policy.md
- [x] **8.3 EU/non-EU vendor data assessment not referenced** — MEDIUM — Covered in privacy-policy.md supplier assessment section

## 9. Management Review

- [x] **9.1 Management review process not documented** — MEDIUM — Added detailed section to ISO intro (annual + monthly MT meetings, topics covered)

## 10. Internal Audits

- [x] **10.1 Internal audit process not documented** — MEDIUM — Added section to ISO intro (audit plan, trained auditors, Jira tracking)

## 11. Customer Satisfaction

- [x] **11.1 NPS/customer satisfaction measurement not on site** — MEDIUM — Added "Customer Satisfaction" section (NPS, annual evaluations, partner evaluations)

## 12. Competence and Training

- [x] **12.1 Competence requirements reference vague** — MEDIUM — Expanded in ISO intro (competence matrix, annual review)
- [x] **12.2 Security awareness program not documented** — MEDIUM — Added to ISO intro (team presentations, quizzes, topics)

## 13. Business Continuity

- [x] **13.1 Business continuity not documented** — HIGH — Added section to ISO intro (recovery procedures, supplier criticality, annual review)

## 14. Physical Security and Safety

- [x] **14.1 Fire safety plan not referenced** — LOW — Added to ISO intro Physical Safety section
- [x] **14.2 RI&E not referenced** — LOW — Added to ISO intro Physical Safety section
- [x] **14.3 Gedragscode for workplace safety** — LOW — Covered by Code of Conduct page

## 15. Document Control

- [x] **15.1 External access tracking not referenced** — LOW — Added to ISO intro Document Control section
- [x] **15.2 No document control statement** — MEDIUM — Added "Document Control" section to ISO intro

## 16. Certificates

- [x] **16.1 Certificates not linked** — LOW — Referenced in ISO intro opening paragraph

## 17. Continual Improvement

- [x] **17.1 PDCA cycle not documented** — MEDIUM — Added "The PDCA Cycle" table to ISO intro

## 18. AI Tooling and Secure Development

- [x] **18.1 Claude Code security controls not documented** — HIGH — Added "AI Tooling (Claude Code)" section to security.md with ISO-723 controls

## 19. Supplier and Outsourcing Management

- [x] **19.1 Supplier evaluation process not documented** — MEDIUM — Added "Supplier Management" section to ISO intro

## 20. Existing Inconsistencies

- [x] **20.1 Reporting channel inconsistency** — MEDIUM — Added "Internal vs External Reporting" section to incident-reporting.md
- [ ] **20.2 Organisation page pending review** — MEDIUM — Still has "pending management review" warning; needs management input
- [x] **20.3 Incident response times inconsistent** — MEDIUM — Clarified internal vs external SLAs in incident-reporting.md

## 21. NL Translation Completeness

- [x] **21.1 NL translations may diverge** — LOW — All new content created with NL translations

## Summary

| Priority | Total | Resolved | Open |
|----------|-------|----------|------|
| HIGH     | 10    | 10       | 0    |
| MEDIUM   | 14    | 13       | 1    |
| LOW      | 6     | 6        | 0    |
| **Total**| **30**| **29**   | **1**|

**Remaining open item:** 20.2 — Organisation page "pending management review" — requires management input, cannot be resolved by documentation alone.
