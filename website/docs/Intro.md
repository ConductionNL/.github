---
id: intro
title: "HowWeWork@Conduction"
sidebar_label: Employee Handbook
sidebar_position: 1
description: The Conduction employee handbook — how we work, what we expect, and where to find everything
keywords:
  - employee handbook
  - how we work
  - onboarding
  - conduction
---

import ToolList from '@site/src/components/ToolList';
import {Val, Email} from '@site/src/components/SiteData';

# HowWeWork@Conduction

The employee handbook — changes? Submit a PR on [GitHub](https://github.com/ConductionNL/.github).

## Who we are

Conduction helps bring good ideas to life. We work democratically, inclusively and transparently — not as corporate values on paper, but as a way of working. Our goal: **by 2035, every resident of the Netherlands automatically receives the government services they are entitled to.**

**Read more:** [Our mission & values](WayOfWork/way-of-work)

## Working at Conduction

**Your first days** — you get a buddy: an experienced colleague who guides you through onboarding. They help you get access (<ToolList category="onboarding" />), set up your machine, and find your way around. Don't hesitate to ask — that's what they're there for.

**Work rhythm** — we work in <Val path="schedule.sprintLength" /> sprints. Standup at <Val path="schedule.standup" />, report-out at <Val path="schedule.reportOut" /> (in Slack <Val path="slack.general" />, always with a commit link for code work). Priorities come from the Product Owner, technical questions go to the dev lead.

**Vacation & sick leave** — request vacation at least <Val path="schedule.vacationNotice" /> in advance via the HR portal and discuss in **<Val path="slack.vacation" />**. Sick? Call HR before <Val path="schedule.sickCallBefore" />. Running late? Drop a message — twice a month you treat the team to cake, the third time means a chat with HR.

**Ground rules** — treat each other with respect. Talk *with* each other, not *about* each other. Discrimination, harassment, or bullying is never accepted.

**Leaving?** — HR or your team lead walks you through offboarding: accounts, company property, payroll. See [Onboarding & offboarding](WayOfWork/onboarding).

**Read more:**
- [Onboarding & buddy system](WayOfWork/onboarding)
- [Organisation](WayOfWork/organisation) — roles, teams, structure
- [Vacancies](WayOfWork/vacancies)
- [Code of Conduct(ion)](WayOfWork/code-of-conduct)

## Building software

**What we build** — open-source components for digital government infrastructure, built on Common Ground principles. Our code lives on [GitHub](https://github.com/ConductionNL).

**How we build** — work consists of issues. Write them so a colleague can pick them up without extra explanation. Four-eyes principle on all code. Never push API keys. Tooling setup? Ask your buddy.

**Projects** — every project starts with a kick-off. Haven't had one? Ask for it — never work on assumptions.

> *Assumption is the mother of all fuckups.*

Scope, budget and planning are in the quotation. Anything outside: discuss with your supervisor first.

**Time tracking** — log hours in Tempo, always on an issue with the correct account. Don't know how? Just ask.

**Read more:**
- [Spec-driven development](WayOfWork/spec-driven-development) — OpenSpec, Claude Code, the four-stage pipeline
- [Development pipeline](WayOfWork/development-pipeline) — quality gates, security checks, automated releases
- [Way of working](WayOfWork/way-of-working) — sprints, issue flow, story points
- [Contributing guide](WayOfWork/contributing) — code standards, branching, reviews
- [Release process](WayOfWork/release-process) — branch model, versioning, deployment

## Support & safety

**Helping customers** — support goes through **<Email path="emails.support" />** (auto-creates a Jira ticket). Quick fix under 5 minutes? Just solve it. Longer? Create an issue. Complaints go to **<Email path="emails.complaints" />**.

**Helping each other** — stuck on something? Flag it as an impediment, post in Slack with a link to the issue, and raise it at standup. Your buddy is your first port of call.

:::danger Report an Incident
Spot a security or quality incident? **Act immediately.** → [Incident reporting procedure](ISO/incident-reporting)
:::

**Incidents** — talk to your supervisor immediately. Flag or create an issue with the label "security incident" or "quality incident". Write a memo with root cause analysis afterwards. Remember: **identify the risk -> assess the risk -> mitigate the risk -> review the measures.**

**Security** — access via your Conduction Google account, credentials in Passwork. Treat sensitive data like your nudes — share only with those who need it. Never send sensitive data via Slack or email. VPN for critical servers. ESET activated at all times.

**Read more:**
- [Customer support](WayOfWork/customer-support) — support flow and complaints
- [Incident reporting](ISO/incident-reporting) — procedures and templates
- [Security policy](ISO/security) — passwords, clean desk, BYOD, VPN, antivirus
- [Privacy & AVG](ISO/privacy-policy) — personal data, GDPR, data subject rights

## Want to know more?

- [Mission & values](WayOfWork/way-of-work) — who we are, what drives us, KPIs
- [ISO & Quality](ISO/iso-intro) — our certifications, audits, risk management, and PDCA cycle
- [Products & Services](Products/products-overview) — what we offer
- [How this manual works](WayOfWork/about-this-manual) — structure, data sources, and how to contribute
