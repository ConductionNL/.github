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

## Incident Escalation

When a serious incident occurs, these rules apply:

1. **Report first, investigate later** — the team needs to know before you have all the answers
2. **Communicate more, not less** — silence creates uncertainty; share what you know, even if incomplete
3. **One person leads, the rest supports** — the dev lead or a management team member coordinates; avoid parallel decision-making
4. **Contain before you fix** — limit the damage first, then work on the root cause
5. **Log everything** — decisions, timestamps, actions taken. You will need this for the post-mortem
6. **Don't blame, learn** — the goal is to prevent recurrence, not to assign fault
7. **Escalate early** — if in doubt whether something is serious, treat it as serious. Downgrading is easier than catching up

## Classification

We distinguish three types of findings, each with their own procedure:

| Type | What is it | Examples | Procedure |
|---|---|---|---|
| **Incident** | Unexpected event with direct impact on continuity, safety, or quality | System outage, unauthorized access, data breach, broken production deployment | Register, impact analysis, resolve immediately, evaluate |
| **Deviation** (afwijking) | Non-compliance with a standard without direct impact | Development procedure not fully followed, document stored incorrectly, test step skipped | Register, analyze if structural, corrective/preventive action if needed |
| **Nonconformity** (tekortkoming) | Structural or severe deviation affecting compliance, certification, or legal obligations | Security protocol structurally not followed, audit reveals missing controls, contractual obligation breached | Register, root cause analysis, improvement plan, monitor effectiveness |

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

## Root Cause Analysis Template

The RCA memo (triggered automatically via Slack) contains the following sections:

1. **Description** — what happened, when, who discovered it
2. **Immediate measures** — containment and correction
3. **Risk assessment** — type, score, action urgency
4. **Root cause analysis** — why it happened, could it happen elsewhere
5. **Corrective actions** — tracked in Jira until closure
6. **Effectiveness review** — are the measures working
7. **Lessons learned** — shared with the team

The actual template is available on the internal ISO drive.

## Incident Trend Analysis

Incident trends are analyzed annually by the management team as part of the quality calendar. Patterns across incidents, deviations, and nonconformities are identified and lessons learned are documented and shared. This ensures structural improvements rather than just fixing individual cases.

## Internal vs External Reporting

- **Internal incidents** (quality, security) → Jira with labels, as described above. Internal SLA: 4 hours (security) / 1 business day (quality)
- **External vulnerability reports** (from security researchers) → GitHub Security tab or security@conduction.nl. External SLA: 48-hour acknowledgement, see [Security Policy](security)

_ISO 27001:2022 reference: A.6.8 — Information security event reporting_
_ISO 9001:2015 reference: §10.2 — Nonconformity and corrective action_
