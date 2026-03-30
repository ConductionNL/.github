# Security Policy

This security policy applies to all repositories under the [ConductionNL](https://github.com/ConductionNL) organization.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

We support two reporting channels:

### 1. GitHub Private Vulnerability Reporting (preferred)

Use GitHub's built-in private reporting feature directly on the affected repository:

> **Repository → Security tab → "Report a vulnerability"**

This creates an end-to-end encrypted security advisory visible only to maintainers. It is the fastest path to coordinated disclosure and a CVE (if warranted).

### 2. Email

Send your report to **security@conduction.nl**.

For sensitive communications, request our PGP key via email.

---

## What to Include

A good vulnerability report contains:

- **Description** — what is vulnerable and why
- **Reproduction steps** — minimal steps to trigger the issue
- **Impact** — what an attacker could achieve (data access, privilege escalation, etc.)
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
| Public disclosure | After fix is released, or at **90 days** from report — whichever comes first |

We follow coordinated disclosure: we will work with you on timing and won't disclose publicly before a fix is available, unless the 90-day window expires.

---

## Severity Classification

We use [CVSSv3](https://www.first.org/cvss/calculator/3.1) to classify severity:

| Severity | CVSS Score | Response |
|---|---|---|
| **Critical** | 9.0–10.0 | Immediate — fix within 14 days |
| **High** | 7.0–8.9 | Fix within 30 days |
| **Medium** | 4.0–6.9 | Fix within 90 days |
| **Low** | 0.1–3.9 | Fixed in next scheduled release |

---

## Scope

### In scope

- All source code in repositories under [github.com/ConductionNL](https://github.com/ConductionNL)
- APIs and integrations exposed by our apps
- Authentication and authorization logic
- Data handling and privacy controls
- Dependencies with known CVEs that we have not yet patched

### Out of scope

- Vulnerabilities in Nextcloud core (report to [Nextcloud](https://nextcloud.com/security/))
- Vulnerabilities in third-party dependencies (report upstream, then inform us)
- Social engineering or phishing attacks against Conduction staff
- Physical security
- Issues requiring unlikely or unrealistic user actions
- Denial-of-service attacks against our hosted infrastructure
- Issues already publicly known

---

## Supported Versions

We provide security updates for the **latest stable release** of each app. Older versions do not receive security patches unless explicitly stated in the repository.

---

## Safe Harbor

Conduction will not pursue legal action against security researchers who:

- Report vulnerabilities through this policy in good faith
- Avoid accessing, modifying, or deleting data beyond what is necessary to demonstrate the vulnerability
- Do not disrupt production services or degrade user experience
- Do not exploit the vulnerability beyond what is needed to confirm its existence
- Give us reasonable time to address the issue before public disclosure

We consider good-faith security research a public good and will work with you rather than against you.

---

## Bug Bounty

Conduction does not currently operate a paid bug bounty program. We do recognize contributors:

- Public credit in release notes (with your permission)
- Acknowledgement in the GitHub Security Advisory

---

## Recognition

We appreciate responsible disclosure. Contributors who report valid vulnerabilities will be credited in our security advisories and release notes (with permission).

---

## Internal Incident Reporting

Conduction employees: see the [Incident Reporting](https://docs.conduction.nl/docs/ISO/incident-reporting) procedure on our internal documentation site.
