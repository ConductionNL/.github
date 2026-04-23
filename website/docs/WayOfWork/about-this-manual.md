---
id: about-this-manual
title: How This Manual Works
sidebar_label: About This Manual
sidebar_position: 99
description: How the employee handbook is built, where data lives, and how to contribute
---

# How This Manual Works

This employee handbook is a [Docusaurus](https://docusaurus.io/) site hosted on GitHub Pages. The source lives in the [ConductionNL/.github](https://github.com/ConductionNL/.github) repository under `website/`.

## Structure

The handbook is organized in four themes:

| Theme | What it covers |
|---|---|
| **Working at Conduction** | Onboarding, organisation, code of conduct, vacancies |
| **Building Software** | Sprints, contributing, releases |
| **Support & Safety** | Customer support, incidents, security policy |
| **About Conduction** | Mission, ISO, products |

The landing page ([Employee Handbook](/docs/intro)) gives a complete overview. Deeper pages expand on each topic.

## Languages

The site supports English (default) and Dutch. English docs live in `website/docs/`, Dutch translations in `website/i18n/nl/docusaurus-plugin-content-docs/current/`.

## Centralized data

To avoid hardcoding values that change (tool names, email addresses, schedules), we use a central data file:

**`website/src/data/site-data.json`**

This file contains:
- **`tools`** — tool lists by category (onboarding, security, development)
- **`emails`** — company email addresses (support, complaints, security, general)
- **`slack`** — Slack channel names
- **`schedule`** — standup time, report-out time, sick call deadline, sprint length
- **`links`** — URLs for external tools (Passwork, NordLayer, ESET)

Pages reference this data via React components:

```jsx
import ToolList from '@site/src/components/ToolList';
import {Val, Email} from '@site/src/components/SiteData';

// Renders: "Google Workspace, GitHub, Jira, Slack, Passwork"
<ToolList category="onboarding" />

// Renders: "10:00"
<Val path="schedule.standup" />

// Renders: a mailto link
<Email path="emails.support" />
```

**When a tool, email address, or schedule changes — update `site-data.json` once. All pages update automatically.**

## Synced files

Three files in the repo root are mirrored as docs pages:

| Repo root | Docs page |
|---|---|
| `CONTRIBUTING.md` | `docs/WayOfWork/contributing.md` |
| `SECURITY.md` | `docs/ISO/security.md` |
| `CODE_OF_CONDUCT.md` | `docs/WayOfWork/code-of-conduct.md` |

A CI workflow (`.github/workflows/docs-sync-check.yml`) checks on every PR whether these files are still in sync. If they diverge, the workflow warns.

## How to contribute

1. Create a branch from `development`
2. Edit markdown files under `website/docs/` (English) or `website/i18n/nl/` (Dutch)
3. Test locally: `cd website && npm install && npm run start`
4. Open a PR

For details, see the [Contributing guide](contributing).
