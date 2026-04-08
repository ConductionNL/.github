---
id: incident-reporting
title: Incident Reporting
sidebar_label: Incident Reporting
sidebar_position: 4
description: How to report security incidents and quality deviations at Conduction
---

# Incident Reporting

Conduction has a duty to detect, report, and learn from incidents — both security incidents (ISO 27001:2022 A.6.8) and quality deviations (ISO 9001:2015 §10.2).

**If you suspect something is wrong, report it immediately. There is no penalty for reporting in good faith.**

## What to Report

### Security Incidents (ISO 27001:2022 A.6.8)

Report any suspected or confirmed:

- Unauthorised access to systems, accounts, or data
- Data breach or data loss (customer data, employee data, credentials)
- Malware, phishing, or social engineering attempts
- Exposure of secrets, API keys, or credentials (e.g. accidentally committed to Git)
- Loss or theft of a device with access to company systems
- Unusual or suspicious activity on any company account or system

### Quality Deviations / Near-Misses (ISO 9001:2015 §10.2)

Report any:

- Delivered software that did not meet agreed requirements
- Process failure that could have led to customer impact
- Near-miss: something that could have gone wrong but didn't

## How to Report

**Create or flag an issue in Jira** and label it **`security-incident`** or **`quality-incident`**. This is the only correct way to report an incident.

Not sure how? Ask a team member, your supervisor, or someone from management — they'll help you create the issue.

Labeling an issue as an incident automatically triggers a Slack flow that requests a **root cause analysis template** to be filled in.

**Response time expectation:**
- Security incidents: acknowledged within **4 business hours**
- Quality deviations: acknowledged within **1 business day**

## What Happens After You Report

1. The Quality & Safety Lead acknowledges the report
2. Severity is assessed (critical / high / medium / low)
3. Containment actions are taken if needed
4. Root cause is investigated
5. Corrective action is documented and tracked to closure
6. Lessons learned are shared with the team

## Your Responsibilities

- Report incidents **as soon as you discover them** — delay increases impact
- Do not attempt to investigate or resolve a security incident on your own before reporting
- Preserve evidence (logs, screenshots) if possible
- Cooperate with the investigation

_ISO 27001:2022 reference: A.6.8 — Information security event reporting_
_ISO 9001:2015 reference: §10.2 — Nonconformity and corrective action_
