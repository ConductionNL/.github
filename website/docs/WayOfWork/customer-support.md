---
id: customer-support
title: Customer Support
sidebar_label: Customer Support
sidebar_position: 7
description: How Conduction handles customer support tickets and complaints
---

# Customer Support

## Quick Fixes

If a customer issue takes **less than 5 minutes** to resolve and doesn't require looking up internals or environment settings — just fix it. No need to create an issue.

If it takes longer than 5 minutes, create an issue. Minimum time logged: **1 hour**.

## Support Flow

1. **Email** — customers send queries to **support@conduction.nl**, which auto-creates a Jira ticket
2. **Slack** — right-click a customer message and select "create issue from" to generate a Jira ticket
3. **Assign** — review the ticket and assign it to the right person
4. **Update** — keep the customer informed about progress, even if there's no significant update
5. **Follow up** — after resolution, confirm with the customer that the issue is resolved

## Customer Complaints

Complaints go to **klachten@conduction.nl**. Examples: billing errors, inappropriate employee behavior, quality issues.

## Four-Eyes Principle

All code changes require peer review. **Core bundles** and **payment-related code** require a **six-eyes principle** — two reviewers. No code may be merged into protected branches without the required review.
