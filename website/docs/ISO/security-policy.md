---
id: security-policy
title: Information Security Policy
sidebar_label: Security Policy
sidebar_position: 3
draft: true
description: Conduction information security policy — ISO 27001:2022 §5.2
---

# Information Security Policy

:::warning Ter managementbeoordeling / Pending management review

Dit document is een werkversie en dient te worden goedgekeurd door het managementteam voordat het als officieel beleid geldt.

_This document is a working draft and must be approved by the management team before it takes effect as official policy._

:::

## Purpose

Conduction is committed to protecting the confidentiality, integrity, and availability of information it handles — including customer data, internal systems, and the open-source software it develops and operates.

This policy establishes the framework for Conduction's Information Security Management System (ISMS) in accordance with ISO 27001:2022.

## Scope

This policy applies to:
- All information assets owned or processed by Conduction
- All employees, contractors, and third parties with access to Conduction systems
- All systems, services, and software developed and operated by Conduction

## Security Objectives

Conduction pursues the following information security objectives (ISO 27001:2022 §6.2):

- Prevent unauthorised access to systems and data
- Ensure availability of critical systems in line with agreed service levels
- Protect customer and employee data in compliance with applicable regulations (including AVG/GDPR)
- Detect, respond to, and learn from security incidents
- Continuously improve security controls based on risk assessments and audits

## Roles and Responsibilities

| Role | Responsibility |
|---|---|
| Management | Approve and resource the ISMS; review annually |
| Quality & Safety Lead | Own and maintain the ISMS; coordinate audits and reviews |
| All employees | Follow security procedures; report incidents and suspected incidents promptly |
| Development Lead | Ensure secure development practices are applied in all software delivery |

See [organisation](../WayOfWork/organisation) for full role descriptions.

## Key Controls

The following controls are in effect (ISO 27001:2022 Annex A):

- **Access control** (A.5.15): Access to systems is role-based and granted on a need-to-know basis
- **Acceptable use** (A.5.10): Company systems and data are used only for authorised purposes
- **Cryptography** (A.8.24): Sensitive data in transit and at rest is encrypted
- **Supplier relationships** (A.5.19): Third-party suppliers with access to data are assessed and contractually bound
- **Incident management** (A.6.8): All suspected incidents must be reported — see [Incident Reporting](incident-reporting)
- **Business continuity** (A.5.29): Critical services have documented recovery procedures

## Communication to Employees

This policy is communicated to all employees via this documentation site and during onboarding. Employees are required to acknowledge this policy. Questions or concerns can be directed to the Quality & Safety Lead or raised via a [GitHub Issue](https://github.com/ConductionNL/.github/issues).

_ISO 27001:2022 reference: §5.2 — Information Security Policy; Annex A.5.1_
_Last review: pending_
_Next review: annual management review cycle_
