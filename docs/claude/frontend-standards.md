# Frontend Standards

Standards that apply to all Conduction Nextcloud apps. Each section says how it is checked: by a Hydra gate, by ESLint, or only by code review.

## OpenRegister Dependency Check

All apps that depend on OpenRegister (everything except `nldesign` and `launchpad`) must show an empty state when OpenRegister is not installed, instead of a broken UI.

### `CnAppRoot` does it

The app shell is `CnAppRoot` from `@conduction/nextcloud-vue`. Its `requiresApps` prop defaults to `['openregister']`. On mount it reads the Nextcloud capabilities API (`getCapabilities()` from `@nextcloud/capabilities`) once and, when any listed app is missing, renders an `NcEmptyContent` instead of the app:

- **Admins** get a button that installs/enables the missing app in place via Nextcloud's `settings/apps/enable` endpoint, with the app-store link as a fallback.
- **Non-admins** get "ask your administrator" copy.

So the default needs nothing from the app — mount `CnAppRoot` without a `requiresApps` prop:

```vue
<CnAppRoot
	:manifest="manifest"
	:registry="registry"
	appId="myapp"
	:translate="translateForApp" />
```

Rules:

- **Do not pass `:requiresApps="[]"` in an app that needs OpenRegister.** The empty array switches the guard off, and nothing else in the app replaces it. The opt-out is for apps that genuinely run without OpenRegister (OpenRegister itself, the styleguide, utility apps).
- **An app that needs a second app lists both**: `:requiresApps="['openregister', 'openconnector']"`.
- **A custom missing-app screen** goes in the `#or-missing` slot (receives `{ missingApps }`), not in a hand-rolled three-state `App.vue`.
- A failing capabilities call falls through to the app rather than blocking it; the data layer then surfaces the real error.

This replaces the older hand-built pattern (`openRegisters` / `isAdmin` in the `SettingsController` response, a Pinia `hasOpenRegisters` getter, a three-state `App.vue` with an `open-register-missing` class). Do not add that pattern to new code; leftovers of it in existing apps are dead code once the app mounts `CnAppRoot` with the guard on.

### Backend: the route table must load without OpenRegister

The empty state only renders if the app's own routes still load when OpenRegister is absent. Apps build their route table with `\OCA\OpenRegister\AppHost\Routes::standard($extra)` (see [Routing History Mode](#routing-history-mode)). Two forms are in use:

- **Guarded** (`decidesk`, `docudesk`, `larpingapp`, `procest`): `class_exists('OCA\OpenRegister\AppHost\Routes')` first, with a local copy of the canonical routes plus the SPA catch-all as the fallback. Reference: `docudesk/appinfo/routes.php`.
- **Direct** (`return \OCA\OpenRegister\AppHost\Routes::standard([...])`): relies on `Routes::standard()` being a pure array builder that is safe to require when OpenRegister is disabled.

## CSS Scoping

### Rule: No unscoped `<style>` in Vue files

All `<style>` blocks in `.vue` files **must** use the `scoped` attribute. Global styles go in `src/assets/app.css` and are imported in `main.js`.

**Why**: Unscoped styles leak into other components and cause hard-to-debug styling issues. The `scoped` attribute ensures styles only affect the component they belong to. To reach into a child or library component from a scoped block, use `:deep(...)`.

**Checked by**: code review only. The fleet's ESLint config (`@nextcloud/eslint-config` 9, see `eslint.config.mjs`) does not enable `vue/enforce-style-attribute`, and no Hydra gate checks for unscoped blocks. An app that wants it machine-enforced adds this to the app-specific block of its `eslint.config.mjs`:

```js
'vue/enforce-style-attribute': ['error', { allow: ['scoped'] }]
```

### Where global styles go

- `src/assets/app.css` — app-wide overrides that must be unscoped (e.g., library component fixes, helpers that must reach `router-view` children)
- `css/` directory — styles loaded by Nextcloud outside of webpack (e.g., dashboard widget icons)
- Import in `main.js`: `import './assets/app.css'`

## Routing History Mode

**Path-based Vue Router history (`createWebHistory`) is the fleet convention.** Hash-based (`createWebHashHistory`, `#/…` URLs) is not a valid choice for new apps.

**Why path, not hash**: hash routing needs zero server-side work (everything after `#` never reaches the server) at the cost of permanently ugly URLs and broken `#`-based deep links whenever an app also wants to use the fragment for something else (e.g. anchors). Path routing gives real, shareable, refresh-safe URLs, but the trade is real: it needs a server-side catch-all, or a direct hit on a deep client route (e.g. a bookmark, a page refresh) 404s.

**A path-history app with no working catch-all is broken.** Never ship `createWebHistory(...)` in `main.js` without one of the two sanctioned catch-all mechanisms below, and live-test a hard reload of a deep route.

### Two sanctioned ways to get the catch-all

1. **`\OCA\OpenRegister\AppHost\Routes::standard($extra)`** — the shared route-table builder. Call it from `appinfo/routes.php` and it appends a `/{path}` catch-all (excluding `/api/*`) after whatever app-specific routes you pass as `$extra`. This is the preferred mechanism for any app that depends on OpenRegister. Reference: `docudesk/appinfo/routes.php`.
2. **A hand-rolled catch-all route** in `appinfo/routes.php` that matches `/{path}` (or equivalent) and excludes `/api/*`, dispatching to a controller action that just renders the SPA shell. Reference: `openconnector/appinfo/routes.php`'s `ui#dashboard` route (`'requirements' => ['path' => '(?!api(/|$)).*']`).

Either way, `main.js`'s `createWebHistory(...)` call needs no other change — the catch-all is purely a backend routing concern.

### Links from the hash era

Links built under hash routing (`/apps/<app>/#/…`) may still be in the wild — in emails, bookmarks, links handed to people outside the app. Under path routing the fragment is never read, so those links land on the app root. Where old links matter, rewrite them in place before the router is created (`history.replaceState`, no reload). Reference: `keepiq/src/bootstrap/hash-route-handoff.js`, which also shows how to keep a secret that lived in the fragment out of the query string.

### Gate: `lint-router-history-mode.sh`

`.github/hydra-gates/scripts/lint-router-history-mode.sh` checks both halves of this convention per app: router mode in `src/main.js`, and (for apps on path history) catch-all presence in `appinfo/routes.php`. A missing catch-all on a path-history app is an unconditional failure regardless of gate mode.

```bash
# Single app, from that app's repo root:
bash ../.github/hydra-gates/scripts/lint-router-history-mode.sh

# Fleet-wide summary, from apps-extra/:
bash .github/hydra-gates/scripts/lint-router-history-mode.sh --fleet
```

As of 2026-09-30 (`--fleet` against each app's `development` branch, 21 apps with a `src/main.js`): every app is on path history with a catch-all present — 0 still on hash, 0 broken. A hash-history app is reported as a warning only while the gate runs in `WARN` mode (`HYDRA_ROUTER_HISTORY_GATE_MODE=WARN`, the default).

## Admin Detection

Never use the `OC.isAdmin` / `OC.isUserAdmin()` globals. In the frontend, read `getCurrentUser()?.isAdmin` from `@nextcloud/auth` — this is what `CnAppRoot` does, and it passes the result down (e.g. to `CnAppNav` to show the Admin-settings link).

The frontend flag is **presentation only**. The access boundary is always the backend: `IGroupManager::isAdmin()` in the controller, or Nextcloud's settings framework, which refuses admin pages server-side for non-admins.

## Reference Implementation

- **App shell**: `docudesk/src/App.vue` — `CnAppRoot` with the default OpenRegister guard.
- **Route table**: `docudesk/appinfo/routes.php` — guarded `Routes::standard($extra)` with a local fallback.
- **ESLint**: `pipelinq/eslint.config.mjs` — the fleet's canonical shape (eslint 10 + `@nextcloud/eslint-config` 9). Copy it verbatim; only the last two blocks (app-specific globals and file-scoped exemptions) differ per app.
- **Global CSS**: `pipelinq/src/assets/app.css`, imported in `pipelinq/src/main.js`.

## Gotchas that trip review or the framework

### Cascade error handling — one key, not four

```js
// ❌ Cascading through 4 possible error-body shapes is a smell — the backend is drifting.
const msg = body?.data?.error || body?.error || body?.message || `HTTP ${res.status}`

// ✅ Per ADR-050, the backend returns `{message, error?}`. One fallback.
const msg = body?.message || `HTTP ${res.status}`
```

If the backend is drifting, fix the backend to align with ADR-050 rather than layering more fallbacks in the frontend.

### CSRF on raw `fetch()` calls

Raw `fetch()` to a Nextcloud AppFramework route (`/apps/{appid}/api/...`) does NOT auto-send `requesttoken`. Nextcloud core does wrap `window.fetch`, but for Nextcloud URLs it only adds `X-Requested-With` — not the token. Options, in order of preference:

1. Use `@nextcloud/axios` (auto-injects `requesttoken` via its interceptor).
2. Add `OCS-APIRequest: true` to headers — satisfies NC's CSRF bypass (`Request::passesCSRFCheck()`).
3. Manually set `requesttoken` via `getRequestToken()` from `@nextcloud/auth`.

A route marked `#[NoCSRFRequired]` works without any of these, which is why a missing token often goes unnoticed until someone removes that attribute. Reference case: opencatalogi PR #79 F8 — delete-modal fetch had none of these, and the moment the backend dropped `@NoCSRFRequired` the call would have started 412ing.
