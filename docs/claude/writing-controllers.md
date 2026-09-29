# Writing Nextcloud Controllers

> **Found a stale reference? Tell the user.** If something here no longer matches its source (an ADR number or title, a gate number, or a class, attribute or file that does not exist), do not quietly work around it. Tell the user which line is wrong and what the source says now, and offer to fix this file.

Reference for authoring Nextcloud AppFramework controllers in Conduction apps. Consolidates rules from ADR-002 (API), ADR-005 (security), ADR-016 (routes), ADR-050 (response envelope), ADR-054 (public surface hardening), ADR-102 (config fail-mode) and ADR-105 (exception translation). Read this before adding a new endpoint or modifying an existing one.

ADR-102 and ADR-105 were numbered ADR-049 and ADR-051 until 2026-08-26. Those numbers now belong to other ADRs (declarative widget vocabulary, semantic object handoff), so an older PR thread or code comment citing "ADR-049 config fail-mode" means ADR-102.

## The five invariants

Every controller method in `lib/Controller/*.php` must satisfy:

1. **Auth attribute matches the method's actual requirement**: semantic consistency, not just syntactic presence (ADR-005; gate-5 `route-auth`, gate-7 `no-admin-idor`, gate-9 `semantic-auth`).
2. **Response envelope is flat + purpose-shaped on success, `{message, error?}` on failure** (ADR-050).
3. **Downstream `@throws` are translated to `JSONResponse` OR redeclared in the caller's docblock** (ADR-105, gate-49).
4. **Security-relevant config reads have an explicit fail-mode** (ADR-102, gate-50).
5. **Public and token-authenticated endpoints are hardened**: rate limit, no CSRF opt-out on writes (ADR-054).

## Rule 1: Auth attribute

Pick exactly one of:

| Attribute | Who gets in | Body constraints |
|---|---|---|
| `#[PublicPage]` | Anonymous callers | MUST NOT call `requireAdmin()` / `isAdmin()` or conditionally return 401/403. Use for OAuth callbacks, public manifests, federation gossip. Also subject to Rule 5. |
| `#[NoAdminRequired]` | Any authenticated user | MUST carry a per-object auth check (gate-7): load the object, compare its stored owner/group against the session user (or admin), refuse otherwise. A "no user → 401" preamble is not that check. Never trust the session alone for mutation. |
| `#[AuthorizedAdminSetting(settings: <YourAdmin>::class)]` | Admins, plus users an admin delegated that settings section to | `<YourAdmin>` must implement `IDelegatedSettings` (NC 27+). Preferred for admin-surface CRUD. Lifts the admin check out of the controller body into a declarative attribute. |
| _(none)_ | Admins only (NC default) | Prefer explicit `#[AuthorizedAdminSetting]` for clarity. |

- **Pass the settings class, never the app ID.** The constructor takes `class-string<IDelegatedSettings>`. `#[AuthorizedAdminSetting(Application::APP_ID)]` still lets admins in, but no delegated user ever matches.
- **`#[NoCSRFRequired]` is not an auth level.** It only switches off the CSRF check; combine it with one of the rows above. gate-5 accepts it as a declared posture, so a method carrying only `#[NoCSRFRequired]` passes gate-5 and is admin-only.
- **Use PHP attributes, not docblock annotations.** Nextcloud 35 still honours `@NoCSRFRequired`, `@NoAdminRequired` and friends, but logs a deprecation for each; the gates recognise both forms.
- **App roles (chair, secretary, …) are action RBAC (ADR-023)**, declared in the app's admin settings. A hard-coded `isAdmin()` in the body locks the action to Nextcloud sysadmins.

### The admin-surface trap

A controller method that mutates *instance-wide administrative state* (federation peers, publication catalogs, register/schema definitions, app-level configuration) is admin-only, not "authenticated user allowed". `#[NoAdminRequired]` on such methods opens the whole surface to any authed user. Reference case: opencatalogi PR #79: `ListingsController::destroy()` and `::update()` shipped with `#[NoAdminRequired]` on an admin-configuration surface. The correct attribute is `#[AuthorizedAdminSetting(settings: OpenCatalogiAdmin::class)]`.

gate-7 does not catch this reliably: it only asks whether a `#[NoAdminRequired]` method has *some* per-object guard. Adding an ownership check turns gate-7 green while the surface is still open to every user. This one is a reviewer check (ADR-005).

### The `#[NoCSRFRequired]` co-change rule (gate-48 `csrf-cochange`)

`#[NoCSRFRequired]` is a deliberate escape hatch (federation gossip endpoints, unauthenticated OAuth callbacks). When you **remove** it in a hardening PR, the endpoint immediately starts rejecting callers that send no CSRF-satisfying signal with HTTP 412 (`CSRF check failed`). **Update every frontend caller in the same PR:**

- Switch to `@nextcloud/axios` (auto-injects the `requesttoken` header), OR
- Add `OCS-APIRequest: true` to the request headers (`Request::passesCSRFCheck()` accepts any non-empty value).

gate-48 only fires on a *removal* without a matching frontend change. Keeping `#[NoCSRFRequired]` where it does not belong is covered by Rule 5, not by gate-48.

## Rule 2: Response envelope (ADR-050)

**Success (2xx):**

```php
return new JSONResponse($result, Http::STATUS_OK);
```

Flat payload: the resource, the operation report, the list. No `message` field on success. No `{success: true, data: $r}` envelope.

**Error (4xx / 5xx):**

```php
return new JSONResponse(
    ['message' => $this->l10n->t('Listing not found'), 'error' => 'listing-not-found'],
    Http::STATUS_NOT_FOUND,
);
```

- `message`: always present, human-readable, localised. Shown by the UI. Static text only: **never** `$e->getMessage()`. Log the real exception server-side with `$this->logger->error('…', ['exception' => $e])` (ADR-005).
- `error`: optional, machine-readable slug (kebab-case) for programmatic dispatch.

No nested `data.error`. No `{status: 'failure', ...}` sub-object. **Legacy wrapped endpoints** (e.g. `{message: 'ok', data: $result}`) stay as-is until their next material change, then align. `OCSController` endpoints are outside this rule: the OCS spec defines their envelope.

## Rule 3: Exception translation (ADR-105, gate-49)

Nextcloud's AppFramework does **not** translate `\OCP\AppFramework\Db\DoesNotExistException` (or most domain exceptions) into 4xx responses on a regular `Controller`. Only `OCSMiddleware` translates `OCSException`, and only on an `OCSController`. Any other uncaught exception becomes an HTTP 500 instead of the documented status.

### Tracked exception classes → HTTP status

| Exception | Status |
|---|---|
| `\OCP\AppFramework\Db\DoesNotExistException` | `404 not-found` |
| `\OCP\AppFramework\Db\MultipleObjectsReturnedException` | `500`: a data-integrity fault, not a client error. Log it; don't translate it to a 4xx |
| `\OCP\Files\NotFoundException` | `404` |
| `\OCA\OpenRegister\Exception\RegisterNotFoundException` | `404` |
| `\OCA\OpenRegister\Exception\SchemaNotFoundException` | `404` |
| `\OCA\OpenRegister\Exception\SchemaNotInRegisterException` | `404` |
| `\OCA\OpenRegister\Exception\NotAuthorizedException` | `403 forbidden` (or `404` where a 403 would reveal that another tenant's id exists) |
| `\OCA\OpenRegister\Exception\ValidationException` | `422 unprocessable-entity` |
| `\OCA\OpenRegister\Exception\CustomValidationException` | `422` |
| `\OCA\OpenRegister\Exception\ObjectExistsException` | `409 conflict` |
| `\OCA\OpenRegister\Exception\LockedException` | `423 locked` |
| `\OCA\OpenRegister\Exception\AppendOnlyException` | `405 method-not-allowed` |
| `\OCA\OpenRegister\Exception\ArchivalImmutableException` | `405` |

App-specific exceptions under the app's own `lib/Exception/` get a mapping from the app's maintainer.

### Canonical shape

```php
try {
    $result = $this->getObjectService()->deleteObject(
        uuid: (string) $id,
        register: $registerScope,
        schema: $schemaScope,
    );
} catch (\OCP\AppFramework\Db\DoesNotExistException $e) {
    return new JSONResponse(
        ['message' => $this->l10n->t('Listing not found'), 'error' => 'listing-not-found'],
        Http::STATUS_NOT_FOUND,
    );
}
```

Alternative (rarely correct): declare `@throws DoesNotExistException` on the caller's own docblock, signalling intentional propagation.

**A catch-all is never a substitute for the specific catches.** `catch (\Throwable $e)` alone turns the documented 404 into a 500. After the specific catches, a last-resort `catch (\Throwable $e)` is fine if it logs the exception and returns a static message (ADR-015). A catch-all that neither logs nor rethrows swallows bugs.

gate-49 is a heuristic: it flags calls to service methods named like `deleteObject`, `find`, `saveObject`, `updateObject`, `getObject`, … and accepts any `catch` of a class ending in `Exception`. A green gate-49 does not prove the right exception maps to the right status.

## Rule 4: Security config fail-mode (ADR-102, gate-50)

Reads of security-relevant config keys must have an explicit fail-mode within 10 lines. A key is security-relevant when its name matches any of:

- Scope IDs: `*register*`, `*schema*`, `*_scope`, `*_id_scope`
- Allow/block lists: `*allowed_*`, `*allow_list*`, `*whitelist*`, `*blocklist*`
- Auth/permission: `*csrf*`, `*rbac*`, `*permission*`, `*auth*`
- Secrets: `*_secret*`, `*_key*`, `*_token*`
- Federation/trust: `instance_aliases`, `trusted_domains`, `trusted_proxies`

The rule covers `IAppConfig::getValueString/Bool/Int` and `IConfig::getAppValue*`. gate-50 only detects the `IAppConfig` form; `getAppValue*` reads are a reviewer check. Pick one fail-mode, in this order of preference:

**Fail closed** (preferred for admin-triggered endpoints). `$this->config` is `IAppConfig`:

```php
$listingRegister = $this->config->getValueString($this->appName, 'listing_register', '');
if ($listingRegister === '') {
    return new JSONResponse(
        ['message' => $this->l10n->t('Listings feature is not configured'), 'error' => 'not-configured'],
        Http::STATUS_SERVICE_UNAVAILABLE,
    );
}
```

`503` says "temporarily unavailable": send `Retry-After` with it, and expect clients and proxies to retry. When the config is absent permanently (feature never set up), `412` or `501` is more precise (ADR-102).

**Log-warn** (for background jobs / non-admin cron):

```php
if ($listingRegister === '' || $listingSchema === '') {
    $this->logger->warning('WOO-515 scope defense inactive: listing_register or listing_schema is empty');
}
```

**Explicit non-empty guard** (for downstream sites where null is a valid input; combine with log-warn for the tightest posture):

```php
$registerScope = null;
if ($listingRegister !== '') {
    $registerScope = $listingRegister;
}
// downstream MUST handle null explicitly
```

## Rule 5: Routes and public surface (ADR-002, ADR-016, ADR-054)

- **Routes live in `appinfo/routes.php` only**, each naming `controller#method` explicitly. No routes registered at runtime (ADR-016). The auth gates scan `routes.php`, so an endpoint registered elsewhere is never checked.
- **Rate-limit every `#[PublicPage]` endpoint** and every endpoint authenticated by a bearer or link token instead of the NC session: `#[AnonRateLimit(limit: …, period: …)]`, or `#[UserRateLimit(…)]` where a session exists (ADR-054 Rule 1).
- **No `#[NoCSRFRequired]` on POST/PUT/PATCH/DELETE routes.** The one exemption ADR-054 recognises is a GET that returns a file download, with a reason comment. An inbound webhook that cannot send a token is `#[PublicPage]` and verifies a signature that fails closed when its secret is unset (ADR-054 Rules 2–3).
- **Metrics and health-detail endpoints stay admin-only**: no `#[PublicPage]` or `#[NoAdminRequired]`. A bare liveness ping may be public if it returns no version or config data (ADR-054 Rule 5).
- **Cross-origin public endpoints** also register a CORS `OPTIONS` route (ADR-002).

ADR-054's own gates (`public-endpoint-rate-limit`, `csrf-on-writes`, `metrics-auth`) are not implemented yet, so this rule is a reviewer check.

## Docblock template

```php
/**
 * Delete a listing by ID.
 *
 * @param string|int $id The listing's identifier.
 * @return JSONResponse The deletion report, or {message, error} on failure.
 *
 * @spec openspec/specs/directory/spec.md#requirement-listing-crud
 */
#[AuthorizedAdminSetting(settings: OpenCatalogiAdmin::class)]
public function destroy(string | int $id): JSONResponse
```

The body translates `DoesNotExistException` as in [Rule 3](#rule-3-exception-translation-adr-105-gate-49). Add `@throws X` only when the method deliberately propagates `X`.

## Common mistakes (see also: opencatalogi #79 / #86 / #85 review threads)

- ❌ `#[NoAdminRequired]` on an admin-surface CRUD endpoint → the whole surface opens to every user. gate-7 only flags it while the method has no guard at all.
- ❌ `#[AuthorizedAdminSetting(Application::APP_ID)]` → admins only; delegation never matches.
- ❌ `#[NoCSRFRequired]` removed without updating frontend callers → gate-48 red, HTTP 412 for every caller that sends neither `requesttoken` nor `OCS-APIRequest`.
- ❌ `#[NoCSRFRequired]` kept on a state-changing route → ADR-054 Rule 2.
- ❌ `deleteObject()` called without try/catch → gate-49 red, HTTP 500 on the defended path.
- ❌ `getValueString('...schema...', '')` used directly without empty-check → gate-50 red, silent defense-off state.
- ❌ `$e->getMessage()` in a response body → leaks internals (ADR-005).
- ❌ Response returns `{success: true, data: $r}` on a new endpoint → drift from ADR-050.

## Related

- [ADR-002 API](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-002-api.md)
- [ADR-005 security](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-005-security.md)
- [ADR-015 common patterns](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-015-common-patterns.md)
- [ADR-016 routes](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-016-routes.md)
- [ADR-023 action authorization](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-023-action-authorization.md)
- [ADR-050 response envelope](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-050-response-envelope.md)
- [ADR-054 public surface hardening](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-054-public-surface-hardening.md)
- [ADR-102 config fail-mode](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-102-config-fail-mode.md)
- [ADR-105 controller exception translation](https://github.com/ConductionNL/hydra/blob/development/openspec/architecture/adr-105-controller-exception-translation.md)
- [security-review-checklist.md](./security-review-checklist.md): the pre-flight checklist for security-sensitive PRs
