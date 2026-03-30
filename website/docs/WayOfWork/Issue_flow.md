---
id: way-of-working
title: Issue Flow and Sprint Planning
sidebar_label: Way of Working
sidebar_position: 3
description: How Conduction plans sprints, manages issues, and ships software
---

# Issue Flow and Sprint Planning Process

## Epic Creation and Sizing

1. Create Epics in Jira, linked to specific goals
   - Epics should represent complete functional features
   - Each epic should deliver independent business value
   - Epics should be linked to specific goals
2. Product Owner performs:
   - T-shirt sizing of epics
   - Priority setting
   - Deadline alignment with related goals

### T-shirt Sizing Reference Table

| Size | Hours Range | Complexity |
|------|-------------|------------|
| XS   | 1-4        | Very small, simple task |
| S    | 4-8        | Small task, straightforward |
| M    | 8-16       | Medium complexity |
| L    | 16-32      | Large, complex task |
| XL   | 32-80      | Very large, highly complex |
| XXL  | 80+        | Major undertaking, needs breakdown |

## Roadmap Planning

1. Scrum Master creates initial roadmap based on:
   - Epic T-shirt sizes
   - Deadlines
   - Team capacity
   - Epic priorities
2. Product Owner reviews and approves roadmap

## User Story Development

1. Developers create user stories for planned epics with Scrum Master guidance
2. Issue Flow:
   - Scrum Master reviews stories against issue criteria
   - If approved, status changes to "Ready for Development" (assigned to Product Owner)
   - Product Owner reviews for alignment with intended functionality
   - Product Owner either:
     - Returns with feedback
     - Sets to "Selected for Development" and unassigns himself

## Code Development

1. Developers can pick up unassigned issues in "Selected for Development"
2. After completion and code merge to `development` branch:
   - Status changes to "Review"
   - Tester can test from the beta channel (merges to `beta` trigger a beta build)
3. After successful testing, completed issues are:
   - Presented to Product Owner during sprint review (Friday)
   - Released to `main` on Monday morning following successful review (triggers a stable release)

### PR Labels for Versioning

Every pull request should be labeled with `major`, `minor`, or `patch` to control the version bump. If no label is set, it defaults to `patch`. See the [Release Process](./release-process) for full details on branching, versioning, and deployment.

## Sprint Closure

1. Scrum Master prepares sprint review proposal including:
   - List of completed issues for review
   - Overview of unfinished issues
   - Recommendation per unfinished issue (keep or return to backlog)
2. During sprint review (Friday):
   - Team reviews unfinished issues
   - Decision made per issue to either:
     - Keep in sprint (if aligned with roadmap and capacity)
     - Return to backlog
   - Decisions are made in accordance with roadmap priorities
