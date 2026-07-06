# Writing Nextcloud Controllers

Reference for authoring Nextcloud AppFramework controllers in Conduction apps. Consolidates rules from ADR-002 (API), ADR-005 (security), ADR-050 (response envelope), ADR-051 (exception translation), and ADR-049 (config fail-mode). Read this before adding a new endpoint or modifying an existing one.

## The four invariants

Every controller method in `lib/Controller/*.php` must satisfy:

1. **Auth annotation matches the method's actual requirement** — semantic consistency, not just syntactic presence (ADR-005, gate-9 `semantic-auth`).
2. **Response envelope is flat + purpose-shaped on success, `{message, error?}` on failure** (ADR-050).
3. **Downstream `@throws` are translated to `JSONResponse` OR redeclared in the caller's docblock** (ADR-051, gate-49).
4. **Security-relevant config reads have an explicit fail-mode** (ADR-049, gate-50).

## Rule 1 — Auth annotation

Pick exactly one of:

| Annotation | Meaning | Body constraints |
|---|---|---|
| `#[PublicPage]` | Anonymous callers allowed | MUST NOT call `requireAdmin()` / `isAdmin()`. Use for OAuth callbacks, public manifests, federation gossip. |
| `#[NoAdminRequired]` | Any authenticated user allowed | MUST carry a per-object auth check (gate-7). Never trust the session alone for mutation. |
| `#[AuthorizedAdminSetting(settings: <YourAdmin>::class)]` | Admin-only, framework-enforced | Preferred for admin-surface CRUD. Lifts the admin check out of the controller body into the routing table. |
| _(none)_ | Admin-only, NC default | Prefer explicit `#[AuthorizedAdminSetting]` for clarity. |

### The admin-surface trap

A controller method that mutates *instance-wide administrative state* (federation peers, publication catalogs, register/schema definitions, app-level configuration) is admin-only — not "authenticated user allowed". `#[NoAdminRequired]` on such methods opens the whole surface to any authed user. Reference case: opencatalogi PR #79 — `ListingsController::destroy()` and `::update()` shipped with `#[NoAdminRequired]` on an admin-configuration surface. The correct annotation is `#[AuthorizedAdminSetting]`.

### The `@NoCSRFRequired` co-change rule (gate-48 `csrf-cochange`)

`@NoCSRFRequired` is a deliberate escape hatch (federation gossip endpoints, unauthenticated OAuth callbacks). When you **remove** it in a hardening PR, the endpoint immediately begins rejecting callers that lack a CSRF-satisfying signal. **Update every frontend caller in the same PR:**

- Switch to `@nextcloud/axios` (auto-injects `requesttoken`), OR
- Add `OCS-APIRequest: true` to the request headers (satisfies `Request::passesCSRFCheck()` bypass).

Failing to co-change causes silent 412s on the next fix-mode iteration.

## Rule 2 — Response envelope (ADR-050)

**Success (2xx):**

```php
return new JSONResponse($result, Http::STATUS_OK);
```

Flat payload — the resource, the operation report, the list. No `message` field on success. No `{success: true, data: $r}` envelope.

**Error (4xx / 5xx):**

```php
return new JSONResponse(
    ['message' => $this->l10n->t('Listing not found'), 'error' => 'listing-not-found'],
    Http::STATUS_NOT_FOUND,
);
```

- `message` — always present, human-readable, localised. Shown by the UI.
- `error` — optional, machine-readable slug (kebab-case) for programmatic dispatch.

No nested `data.error`. No `{status: 'failure', ...}` sub-object. **Legacy wrapped endpoints** (e.g. `{message: 'ok', data: $result}`) stay as-is until their next material change, then align.

## Rule 3 — Exception translation (ADR-051, gate-49)

Nextcloud's AppFramework does **not** auto-translate `\OCP\AppFramework\Db\DoesNotExistException` (or most domain exceptions) into 4xx responses. Only `OCSException` on `OCSController` gets translated. Any uncaught exception becomes HTTP 500 with a stack trace.

### Tracked exception classes → HTTP status

| Exception | Status |
|---|---|
| `\OCP\AppFramework\Db\DoesNotExistException` | `404 not-found` |
| `\OCP\AppFramework\Db\MultipleObjectsReturnedException` | `409 conflict` |
| `\OCP\AppFramework\Exception\NotFoundException` | `404` |
| `\OCA\OpenRegister\Exception\PermissionException` | `403 forbidden` |
| `\OCA\OpenRegister\Exception\ValidationException` | `422 unprocessable-entity` |
| `\OCA\OpenRegister\Exception\ForbiddenException` | `403` |
| `\OCA\OpenRegister\Exception\CustomValidationException` | `422` |
| `\OCA\OpenRegister\Exception\AppendOnlyException` | `405 method-not-allowed` |
| `\OCA\OpenRegister\Exception\ArchivalImmutableException` | `405` |

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

**Do not** catch `\Throwable` or `\Exception` as a catch-all. That swallows bugs. Catch specific documented shapes; let anything else propagate to the framework's 500 with a proper log entry.

## Rule 4 — Security config fail-mode (ADR-049, gate-50)

Reads of security-relevant config keys (register/schema scope, allow_list, csrf, rbac, permission, auth, *_secret, instance_aliases, trusted_domains) must have an explicit fail-mode within 10 lines. Pick one:

**Fail closed** (preferred for admin-triggered endpoints):

```php
$listingRegister = $this->config->getValueString($this->appName, 'listing_register', '');
if ($listingRegister === '') {
    return new JSONResponse(
        ['message' => $this->l10n->t('Listings feature is not configured'), 'error' => 'not-configured'],
        Http::STATUS_SERVICE_UNAVAILABLE,
    );
}
```

**Log-warn** (for background jobs / non-admin cron):

```php
if ($listingRegister === '' || $listingSchema === '') {
    $this->logger->warning('WOO-515 scope defense inactive: listing_register or listing_schema is empty');
}
```

**Explicit non-empty guard** (for downstream sites where null is a valid input):

```php
$registerScope = null;
if ($listingRegister !== '') {
    $registerScope = $listingRegister;
}
// downstream MUST handle null explicitly
```

## Docblock template

```php
/**
 * Delete a listing by ID.
 *
 * @param string|int $id The listing's identifier.
 * @return JSONResponse
 *
 * @throws \OCP\AppFramework\Db\DoesNotExistException when the scoped object is not found (declared → propagation is intentional)
 *
 * @spec openspec/specs/directory/spec.md#requirement-listing-crud
 */
#[AuthorizedAdminSetting(settings: OpenCatalogiAdmin::class)]
public function destroy(string | int $id): JSONResponse
```

## Common mistakes (see also: opencatalogi #79 / #86 / #85 review threads)

- ❌ `#[NoAdminRequired]` on an admin-surface CRUD endpoint → gate-7 red, real IDOR vulnerability.
- ❌ `@NoCSRFRequired` retained after admin guard tightened → gate-48 red, silent 412 on next iteration.
- ❌ `deleteObject()` called without try/catch → gate-49 red, HTTP 500 on the defended path.
- ❌ `getValueString('...schema...', '')` used directly without empty-check → gate-50 red, silent defense-off state.
- ❌ Response returns `{success: true, data: $r}` on a new endpoint → drift from ADR-050.

## Related

- [ADR-002 API](https://codeberg.org/Conduction/hydra/src/branch/main/openspec/architecture/adr-002-api.md)
- [ADR-005 security](https://codeberg.org/Conduction/hydra/src/branch/main/openspec/architecture/adr-005-security.md)
- [ADR-050 response envelope](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-050-response-envelope.md)
- [ADR-051 controller exception translation](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-051-controller-exception-translation.md)
- [ADR-049 config fail-mode](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-049-config-fail-mode.md)
- [security-review-checklist.md](./security-review-checklist.md) — the pre-flight checklist for security-sensitive PRs
