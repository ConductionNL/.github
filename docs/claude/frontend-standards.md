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
