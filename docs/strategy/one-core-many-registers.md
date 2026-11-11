---
id: one-core-many-registers
title: One core, many registers
sidebar_label: One core, many registers
sidebar_position: 2
description: Why Conduction builds one abstract application on a communal core and Nextcloud, instead of one application per register, and how we judge the size of what we build.
---

# One core, many registers

Government runs on registers: cases, permits, publications, contacts, assets. The usual answer is one application per register, each with its own login, its own permissions, its own notifications and its own database. We build the other way round.

## One abstract application, many configurations

We build one abstract application from a communal core, and we configure it per register.

- **OpenRegister holds the data.** Every app stores its domain data as OpenRegister objects in registers and schemas (ADR-001, ADR-070).
- **The shared Vue library renders it.** Pages, menus and widgets are configuration in the app's manifest, rendered by `@conduction/nextcloud-vue` (ADR-024, ADR-071).
- **Behaviour is declared where it can be.** Validation, workflow and notifications are schema configuration and OpenRegister flows, not code per app (ADR-031, ADR-065).

So a new government register is configuration on top of OpenRegister: a register definition, its schemas and a manifest. It is not a new application with its own stack.

When two apps need the same thing, it moves into the core instead of being built twice (ADR-012, ADR-022, ADR-072).

## Nextcloud is the framework

We do not build what Nextcloud already provides. Our apps use Nextcloud for:

- users, groups, login, sessions and two-factor authentication;
- sharing, files and the activity stream;
- notifications;
- background jobs, app configuration and the settings pages.

So there is no separate authorisation service, notification service or user store next to our apps. What we add on top, such as register-level authorization and organisation tenancy, builds on Nextcloud identities. How that works for security is on [Security policy](../iso/security.md#we-build-on-nextclouds-security).

## Sidecars are always optional

An app must work on a plain Nextcloud. A search engine such as Elasticsearch or Solr, or any other extra service, may make something faster or richer. It may never be required.

OpenRegister searches the Nextcloud database. It needs no external search engine at all.

## Count the lines of the whole stack

Every line we write is a line we maintain. The smallest footprint is the one with the fewest lines to keep working.

That count only means something across the whole stack a product replaces. One app per register looks small per app. Add up each app's own login, permissions, notifications, storage and frontend, and the total is many times larger. Our individual components can look large, because the core carries what every app would otherwise repeat. Judge the total, not the component.

## Next step

Planning a new app or register? Start with [Spec-driven development](../WayOfWork/spec-driven-development.md), and check [Architecture decisions](../WayOfWork/architecture-decisions.md) for what the core already does.
