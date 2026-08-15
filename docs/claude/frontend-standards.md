# Frontend Standards

Standards that apply to all Conduction Nextcloud apps. These are enforced via ESLint rules and code review.

## OpenRegister Dependency Check

All apps that depend on OpenRegister (everything except `nldesign` and `launchpad`) must show an empty state when OpenRegister is not installed, instead of a broken UI.

### Backend (SettingsController)

The settings endpoint must return `openRegisters` and `isAdmin` fields:

```php
use OCP\App\IAppManager;
use OCP\IGroupManager;
use OCP\IUserSession;

// In constructor: inject IAppManager, IGroupManager, IUserSession

// In the index() / settings GET endpoint:
$user    = $this->userSession->getUser();
$isAdmin = $user !== null && $this->groupManager->isAdmin($user->getUID());

return new JSONResponse([
    'openRegisters' => in_array(needle: 'openregister', haystack: $this->appManager->getInstalledApps()),
    'isAdmin'       => $isAdmin,
    'config'        => $this->settingsService->getSettings(),
]);
```

The controller should also have the standardized `getObjectService()` and `getConfigurationService()` methods for lazy-loading OpenRegister services (see softwarecatalog/opencatalogi for reference).

### Frontend Store (Pinia)

The settings store must expose:

- `openRegisters: false` in state
- `isAdmin: false` in state
- `hasOpenRegisters` getter
- `getIsAdmin` getter
- Read both from the API response in `fetchSettings()`

### Frontend App.vue

Three-state conditional in the template:

1. **OpenRegister missing** (`storesReady && !hasOpenRegisters`): `NcEmptyContent` inside `NcAppContent` with class `open-register-missing` — no sidebar, no navigation
2. **Normal** (`storesReady && hasOpenRegisters`): full app with menu, content, sidebar
3. **Loading** (else): centered `NcLoadingIcon`

The empty state uses:

- `NcEmptyContent` with `:name` and `:description` props
- `#icon` slot with the app's own icon (`imagePath('<appname>', 'app-dark.svg')`)
- `#action` slot with `NcButton` linking to app store (admin) or text hint (non-admin)
- Admin detection comes from the backend (`settingsStore.getIsAdmin`), NOT from `OC.isAdmin` (which doesn't exist)
- App store URL: `generateUrl('/settings/apps/integration/openregister')`

### Centering

The `NcAppContent` wrapper needs `.open-register-missing` class with flex centering. This goes in `src/assets/app.css` (not in a Vue `<style>` block).

## CSS Scoping

### Rule: No unscoped `<style>` in Vue files

All `<style>` blocks in `.vue` files **must** use the `scoped` attribute. Global styles go in `src/assets/app.css` and are imported in `main.js`.

**Why**: Unscoped styles leak into other components and cause hard-to-debug styling issues. The `scoped` attribute ensures styles only affect the component they belong to.

**Enforced by**: ESLint rule `vue/enforce-style-attribute`:

```js
'vue/enforce-style-attribute': ['error', { allow: ['scoped'] }]
```

### Where global styles go

- `src/assets/app.css` — app-wide overrides (e.g., library component fixes, empty state centering)
- `css/` directory — styles loaded by Nextcloud outside of webpack (e.g., dashboard widget icons)
- Import in `main.js`: `import './assets/app.css'`

## Routing History Mode

**Path-based Vue Router history (`createWebHistory`) is the fleet convention.** Hash-based (`createWebHashHistory`, `#/…` URLs) is the thing being migrated away from, not a valid alternative for new apps.

**Why path, not hash**: hash routing needs zero server-side work (everything after `#` never reaches the server) at the cost of permanently ugly URLs and broken `#`-based deep links whenever an app also wants to use the fragment for something else (e.g. anchors). Path routing gives real, shareable, refresh-safe URLs, but the trade is real: it needs a server-side catch-all, or a direct hit on a deep client route (e.g. a bookmark, a page refresh) 404s.

**A path-history app with no working catch-all is not ahead of the convention — it is broken**, and worse than staying on hash. Do not flip `createWebHashHistory` → `createWebHistory` in `main.js` without first confirming (and, ideally, live-testing a hard reload of a deep route against) one of the two sanctioned catch-all mechanisms below.

### Two sanctioned ways to get the catch-all

1. **`\OCA\OpenRegister\AppHost\Routes::standard($extra)`** — the shared route-table builder. Call it from `appinfo/routes.php` and it appends a `/{path}` catch-all (excluding `/api/*`) to whatever app-specific routes you pass as `$extra`. This is the preferred mechanism for any app that already depends on OpenRegister. Reference: `docudesk/appinfo/routes.php`.
2. **A hand-rolled catch-all route** in `appinfo/routes.php` that matches `/{path}` (or equivalent) and excludes `/api/*`, dispatching to a controller action that just renders the SPA shell (e.g. `dashboard#catchAll`, `ui#dashboard`). Reference: `openconnector/appinfo/routes.php`'s `ui#dashboard` route — pre-existing from an earlier, unfinished migration, verified working and now wired up to the frontend.

Either way, `main.js`'s `createWebHistory(...)` call needs no other change — the catch-all is purely a backend routing concern.

### Gate: `lint-router-history-mode.sh`

`.github/hydra-gates/scripts/lint-router-history-mode.sh` checks both halves of this convention per app: router mode in `src/main.js`, and (for apps already on path history) catch-all presence in `appinfo/routes.php`. A missing catch-all on a path-history app is an unconditional failure regardless of gate mode — it is a real bug, not an in-progress migration state.

```bash
# Single app, from that app's repo root:
bash ../.github/hydra-gates/scripts/lint-router-history-mode.sh

# Fleet-wide summary, from apps-extra/:
bash .github/hydra-gates/scripts/lint-router-history-mode.sh --fleet
```

As of 2026-08-15 (19 apps checked, `--fleet`): `openconnector` is on path history with a verified catch-all; `decidesk`, `docudesk`, `hermiq`, `hrmq`, `openbuild`, `portaliq`, `procest`, `scholiq`, `shillinq` were already on path history; `doriath`, `larpingapp`, `opencatalogi`, `openregister`, `pipelinq`, `softwarecatalog`, `zaakafhandelapp` remain on hash history, not yet converted. The gate runs in `WARN` mode (`HYDRA_ROUTER_HISTORY_GATE_MODE=WARN`, the default) — it reports hash-history apps without failing CI — until every remaining app has a verified catch-all and is converted; flip to `BLOCK` only after that.

## Admin Detection

Never use `OC.isAdmin` — it doesn't exist in Nextcloud's frontend JavaScript API. Instead:

- Pass `isAdmin` from the backend via the settings endpoint using `IGroupManager::isAdmin()`
- Store it in the Pinia settings store
- Access via computed property in components

## Reference Implementation

Pipelinq is the reference implementation for all these patterns:

- Backend: `pipelinq/lib/Controller/SettingsController.php`
- Store: `pipelinq/src/store/modules/settings.js`
- App.vue: `pipelinq/src/App.vue`
- CSS: `pipelinq/src/assets/app.css`
- ESLint: `pipelinq/eslint.config.js`

## Gotchas that trip mechanical gates

A few surface patterns have empirically caused review round-trips because they interact badly with either the Hydra gate regexes or the NC framework. Avoid them.

### Avoid arrow functions inside Vue attribute values

Vue templates like `<NcSelect :reduce="(o) => o">` contain a `>` character *inside* an attribute value. Some downstream tooling — including `hydra-gate-nc-input-labels` on Hydra `main` — assumes attribute values do not contain `>` and truncates the tag prematurely. A tag whose `:input-label` prop lives on a line AFTER `:reduce` will falsely trip the gate.

Two workable patterns:

```vue
<!-- Preferred: order matters — labels first, complex bindings last -->
<NcSelect
    :options="opts"
    :input-label="t('app', 'Level')"
    :reduce="(o) => o"
    :clearable="false" />

<!-- Alternative: named function, no arrow -->
<NcSelect
    :options="opts"
    :reduce="function (o) { return o }"
    :input-label="t('app', 'Level')" />
```

Reference case: opencatalogi PR #79 round-3.

### Cascade error handling — one key, not four

```js
// ❌ Cascading through 4 possible error-body shapes is a smell — the backend is drifting.
const msg = body?.data?.error || body?.error || body?.message || `HTTP ${res.status}`

// ✅ Per ADR-050, the backend returns `{message, error?}`. One fallback.
const msg = body?.message || `HTTP ${res.status}`
```

If the backend is drifting, fix the backend to align with ADR-050 rather than layering more fallbacks in the frontend.

### CSRF on raw `fetch()` calls

Raw `fetch()` to a Nextcloud AppFramework route (`/apps/{appid}/api/...`) does NOT auto-send `requesttoken`. Options, in order of preference:

1. Use `@nextcloud/axios` (auto-injects `requesttoken` via its interceptor).
2. Add `OCS-APIRequest: true` to headers — satisfies NC's CSRF bypass (`Request::passesCSRFCheck()`).
3. Manually set `requesttoken` via `getRequestToken()` from `@nextcloud/auth`.

Reference case: opencatalogi PR #79 F8 — delete-modal fetch had none of these, and the moment the backend dropped `@NoCSRFRequired` the call would have started 412ing.
