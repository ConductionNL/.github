---
id: security
title: Security Policy
sidebar_label: Security Policy
sidebar_position: 5
description: How to report vulnerabilities, our response timeline, and safe harbor statement
---

# Security Policy

This security policy applies to all repositories under the [ConductionNL](https://github.com/ConductionNL) organization on GitHub, where all Conduction source code lives.

## We build on Nextcloud's security

We trust Nextcloud's security capabilities more than our own, and we build on them explicitly. Nextcloud's security is reviewed and attacked by a far larger community than ours. Every control we write ourselves is one more control to get wrong.

So our apps take these from Nextcloud and do not reimplement them:

| Concern | What our apps use |
| --- | --- |
| Authentication and sessions | Nextcloud login and sessions, including SSO, LDAP and two-factor authentication. No app has its own login, session, token or password storage (ADR-002, ADR-005). |
| CSRF and endpoint access | Nextcloud's CSRF protection and controller attributes: `#[NoAdminRequired]`, `#[PublicPage]`, `#[NoCSRFRequired]`, `#[AuthorizedAdminSetting]`. A gate fails any route that declares no access attribute. |
| Users, groups and sharing | Nextcloud users, groups (`IGroupManager`) and the share manager. Admin checks run on the backend. |
| Secrets and encryption | `ICrypto` for encryption and `ICredentialsManager` for stored credentials. |
| Brute-force protection | Nextcloud's brute-force protection and rate-limit attributes. Every public endpoint is throttled (ADR-082). |

What we add builds on Nextcloud identities, never on a parallel user store:

- **Register- and schema-level authorization.** OpenRegister decides per register, schema and object who may read or write, based on Nextcloud users and groups (ADR-023).
- **Organisation multitenancy.** An organisation's members are Nextcloud users and groups, and object queries are scoped to the user's organisation.
- **The audit trail.** Changes to objects are recorded with the Nextcloud user who made them, in a hash-chained trail. It is on by default.

The architecture reasoning behind this is on [One core, many registers](../strategy/one-core-many-registers.md).

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

### 1. GitHub Private Vulnerability Reporting (preferred)

Use GitHub's built-in private reporting feature directly on the affected repository:

> **Repository → Security tab → "Report a vulnerability"**

This creates an end-to-end encrypted security advisory visible only to maintainers.

### 2. Email

Send your report to **security@conduction.nl**. For sensitive communications, request our PGP key via email.

## What to Include

- **Description** — what is vulnerable and why
- **Reproduction steps** — minimal steps to trigger the issue
- **Impact** — what an attacker could achieve
- **Affected versions** — which releases are affected
- **Suggested fix** — optional, but appreciated

## Response Timeline

| Milestone                              | Target                                               |
| -------------------------------------- | ---------------------------------------------------- |
| Acknowledgement                        | Within **48 hours**                                  |
| Initial triage and severity assessment | Within **5 business days**                           |
| Fix for critical / high severity       | Within **30 days**                                   |
| Fix for medium severity                | Within **90 days**                                   |
| Public disclosure                      | After fix is released, or at **90 days** from report |

## Severity Classification

We use [CVSSv3](https://www.first.org/cvss/calculator/3.1) to classify severity:

| Severity     | CVSS Score | Response                        |
| ------------ | ---------- | ------------------------------- |
| **Critical** | 9.0–10.0   | Fix within 14 days              |
| **High**     | 7.0–8.9    | Fix within 30 days              |
| **Medium**   | 4.0–6.9    | Fix within 90 days              |
| **Low**      | 0.1–3.9    | Fixed in next scheduled release |

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
- Social engineering or phishing attacks against Conduction staff
- Physical security
- Issues requiring unlikely or unrealistic user actions
- Denial-of-service attacks against hosted infrastructure
- Issues already publicly known

## Supported Versions

We provide security updates for the **latest stable release** of each app. Older versions do not receive security patches unless explicitly stated in the repository.

## Safe Harbor

Conduction will not pursue legal action against security researchers who:

- Report vulnerabilities through this policy in good faith
- Avoid accessing, modifying, or deleting data beyond what is necessary to demonstrate the vulnerability
- Do not disrupt production services or degrade user experience
- Do not exploit the vulnerability beyond what is needed to confirm its existence
- Give us reasonable time to address the issue before public disclosure

We consider good-faith security research a public good and will work with you rather than against you.

## Bug Bounty

Conduction does not currently operate a paid bug bounty program. Valid reports receive:

- Public credit in release notes (with permission)
- Acknowledgement in the GitHub Security Advisory

## Internal Incident Reporting

Conduction employees: see the [Incident Reporting](incident-reporting.md) procedure for reporting security incidents and quality deviations.

## Employee Security Practices

The sections below apply to all Conduction employees.

### Passwords

All Conduction passwords must be at least **10 characters** and contain:

- A letter
- A number
- A special character

Store all credentials in [Passwork](https://www.passwork.me/). Never share passwords through Slack, email, or any other communication channel. When sharing credentials with a colleague or external party, use a **Passwork share-link** — these are one-time use and time-limited.

### Data Handling

- Never store personal or private data of Conduction or its clients on your local device
- Never push API keys or environment variables to GitHub
- Share files only through Google Drive or Passwork — never via USB, email, or Slack
- If you must store sensitive data locally, encrypt it with **BitLocker**
- Downloaded documents with privacy-sensitive data must be removed from your laptop within **5 days**

### Clean Desk & Clear Screen

- Always lock your device when you step away — even for coffee
- Never leave your device unattended
- Store your device in a locker at end of day, or take it with you
- Keep no notes, printouts, or peripherals lying around

### Bring Your Own Device (BYOD)

You choose your own development machine. The only requirements:

1. It can run the required local tooling
2. It conforms to the security requirements on this page (antivirus, encryption, VPN)

### VPN

Remote work — especially with sensitive data — requires a VPN connection.

- [NordLayer VPN](https://nordlayer.com/) — install and activate whenever working remotely
- If unsure whether you need it, check with your team lead

### Antivirus

ESET must be activated on all devices used for Conduction work, at all times. Request an exception from your team lead if needed.

- [ESET Business Edition — setup and downloads](https://www.eset.com/int/business/)
- Contact IT for your license key and 2FA setup

**Linux users:** ESET has limited Linux support. Install the [workstation-security](https://github.com/MWest2020/workstation-security) tooling instead. Ask your team lead for setup guidance if needed. Your security logs may be requested at any time.

### AI Tooling

Every employee receives a paid **Claude.ai** account. This account does not store conversation data. Use it for day-to-day work — never paste client credentials or personal data into any AI tool.

**Claude Code** is used for development. AI tooling inherits the permissions of the user session it runs in. The following controls are mandatory (based on documented deviation ISO-723):

- **Separate accounts** — Claude Code must use a dedicated GitHub account with standard developer permissions. Never use an admin account in the same session as Claude Code
- **Git restrictions** — `settings.json` must restrict Git operations: Claude may only push to `feature/*` branches. Direct push to `development`, `beta`, or `main` is blocked
- **Four-eyes principle applies** — all code produced by AI is subject to the same peer review requirements as human-written code. No exceptions
- **No branch protection bypass** — even if your account has admin rights, Claude must not be able to bypass branch protections

These controls are enforced via the shared [`claude-code-config`](https://github.com/ConductionNL/claude-code-config) repository (added as `.claude/` submodule in each app).

_ISO 27001:2022 reference: A.8.2 — Privileged access rights_
