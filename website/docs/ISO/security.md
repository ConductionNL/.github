---
id: security
title: Security Policy
sidebar_label: Security Policy
sidebar_position: 5
description: How to report vulnerabilities, our response timeline, and safe harbor statement
---

# Security Policy

This security policy applies to all repositories under the [ConductionNL](https://github.com/ConductionNL) organization.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

### 1. GitHub Private Vulnerability Reporting (preferred)

Use GitHub's built-in private reporting feature directly on the affected repository:

> **Repository → Security tab → "Report a vulnerability"**

This creates an end-to-end encrypted security advisory visible only to maintainers.

### 2. Email

Send your report to **security@conduction.nl**.

---

## What to Include

- **Description** — what is vulnerable and why
- **Reproduction steps** — minimal steps to trigger the issue
- **Impact** — what an attacker could achieve
- **Affected versions** — which releases are affected
- **Suggested fix** — optional, but appreciated

---

## Response Timeline

| Milestone | Target |
|---|---|
| Acknowledgement | Within **48 hours** |
| Initial triage and severity assessment | Within **5 business days** |
| Fix for critical / high severity | Within **30 days** |
| Fix for medium severity | Within **90 days** |
| Public disclosure | After fix is released, or at **90 days** from report |

---

## Severity Classification

We use [CVSSv3](https://www.first.org/cvss/calculator/3.1) to classify severity:

| Severity | CVSS Score | Response |
|---|---|---|
| **Critical** | 9.0–10.0 | Fix within 14 days |
| **High** | 7.0–8.9 | Fix within 30 days |
| **Medium** | 4.0–6.9 | Fix within 90 days |
| **Low** | 0.1–3.9 | Fixed in next scheduled release |

---

## Scope

### In scope

- All source code under [github.com/ConductionNL](https://github.com/ConductionNL)
- APIs and integrations exposed by our apps
- Authentication and authorization logic
- Data handling and privacy controls
- Dependencies with known CVEs not yet patched

### Out of scope

- Vulnerabilities in Nextcloud core → report to [Nextcloud](https://nextcloud.com/security/)
- Vulnerabilities in third-party dependencies → report upstream first
- Social engineering or phishing attacks
- Issues requiring highly unrealistic user actions
- Denial-of-service attacks against hosted infrastructure

---

## Supported Versions

Security updates are provided for the **latest stable release** of each app only.

---

## Safe Harbor

Conduction will not pursue legal action against security researchers who:

- Report vulnerabilities through this policy in good faith
- Avoid accessing, modifying, or deleting data beyond what is necessary to demonstrate the vulnerability
- Do not disrupt production services
- Give us reasonable time to address the issue before public disclosure

We consider good-faith security research a public good.

---

## Bug Bounty

Conduction does not currently operate a paid bug bounty program. Valid reports receive:

- Public credit in release notes (with permission)
- Acknowledgement in the GitHub Security Advisory

---

## Internal Incident Reporting

Conduction employees: see the [Incident Reporting](incident-reporting) procedure for reporting security incidents and quality deviations.
