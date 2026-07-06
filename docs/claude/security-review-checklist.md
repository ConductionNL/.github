# Security Review Checklist

Pre-flight for any PR that touches security-sensitive code in a Conduction app. Referenced by [writing-controllers.md](./writing-controllers.md); intended to be referenced by the review-pr skill's Step 4b (persistence-audit offer) — follow-up wiring in a separate PR against hydra's `review-pr` skill.

## When this checklist fires

Your PR touches at least one of:

- `.php` under `lib/Auth*`, `lib/Session*`, `lib/Csrf*`, `lib/*/Rbac/*`, `lib/*/Permission/*`, `lib/*/Authorization/*`
- Any file containing `#[NoAdminRequired]`, `#[AuthorizedAdminSetting]`, `#[PublicPage]`, `@NoAdminRequired`, `@NoCSRFRequired`
- URL parsing (`parse_url`, `parse_str`), hash comparison (`hash_equals`), password checks (`password_verify`), CSPRNG (`random_bytes`, `getSecureRandom`)
- User identity: `IUserSession`, `->getUID()`, `->getUser()`
- CSRF: `requesttoken`, `OCS-APIRequest`, `csrf`

If any of the above shows up in `git diff --name-only $BASE...HEAD`, the checklist applies.

## The 7-point pre-flight

Run through this list before opening the PR — the reviewer will run through it again, so getting there first saves a round.

### 1. Admin-surface CRUD uses `#[AuthorizedAdminSetting]` (ADR-005)

Every mutating endpoint on an admin surface (federation peers, catalogs, register/schema config, app-config) carries `#[AuthorizedAdminSetting(settings: <AppAdmin>::class)]` — NOT `#[NoAdminRequired]`. Framework-enforced. Reference case: opencatalogi PR #79 F1/F2.

### 2. `@NoCSRFRequired` co-change (ADR-005, gate-48)

Are you REMOVING `@NoCSRFRequired` from any controller method in this PR? If yes:

- [ ] Every frontend caller of the endpoint in `src/**/*.{vue,js,ts}` is also updated in this PR.
- [ ] Update either uses `@nextcloud/axios` (auto-injects `requesttoken`) OR adds `OCS-APIRequest: true` to headers.

Reference case: opencatalogi PR #79 F8 — @NoCSRFRequired retained on `destroy()` while the delete-modal fetch still sent no CSRF header. Silent 412 waiting to happen.

### 3. Downstream `@throws` are translated (ADR-051, gate-49)

For every controller method that calls a service method documenting `@throws X`, verify:

- [ ] `X` is caught in a try/catch translating to `JSONResponse` with the correct HTTP status, OR
- [ ] `X` is declared in the caller's own docblock (intentional propagation).

Tracked exception classes are listed in [writing-controllers.md § Rule 3](./writing-controllers.md). Reference case: opencatalogi PR #86 — `destroy()` called `deleteObject()` without a try/catch → HTTP 500 on the defended path.

### 4. Security-relevant config reads have a fail-mode (ADR-049, gate-50)

For every `$this->config->getValueString/Bool/Int('appid', 'key', '')` in changed files where the key matches a security predicate (register/schema scope, allow_list, csrf, rbac, permission, auth, *_secret, instance_aliases, trusted_domains):

- [ ] Empty default is handled within 10 lines: fail-closed early return, log-warn, or explicit non-empty guard.

Reference case: opencatalogi PR #86 — silent unscoped fallback when either `listing_register` or `listing_schema` was empty. The WOO-515 defense silently turned off.

### 5. URL comparisons use the canonicalizer (ADR-052)

Any URL comparison in changed files (self-detection, allowlist match, callback validation, dedup):

- [ ] Uses `UrlCanonicalizer::sameHostPort()` (or the equivalent app-local utility) rather than inline `parse_url()` + manual comparison.

Reference case: opencatalogi PR #85 — inline `parse_url()` failed on default ports (`example.com` vs `example.com:443`), IPv6 aliases (`explode(':')` broke `[::1]:8080`), and case sensitivity. The WOO-516 scenario the PR was written to fix still didn't work under the delivered implementation.

### 6. Response envelope is flat (ADR-050)

- [ ] Success returns `$result` directly, not `{message, data: $result}`.
- [ ] Errors return `{message, error?}` with `message` localised and `error` a kebab-case slug.
- [ ] No nested `data.error` on 4xx / 5xx.

Reference case: opencatalogi PR #81 — sibling controllers `DirectoryController::synchronize()` and `ListingsController::add()` returned different envelopes; the frontend had to ship `response.data.data ?? response.data`.

### 7. Tests are touched in the same PR (gate-47)

If any of the above check-boxes touches a security-sensitive site, the PR MUST also touch at least one file under `tests/`.

- [ ] A test file was added or modified in this PR.

Reference case: opencatalogi PR #85 (WOO-516) and PR #86 (WOO-515) — both security-adjacent, both shipped with zero test changes, both had blockers surface only via manual code review.

**Opt-out** (deliberate, ≥ 20 chars reason): add `[hydra-gate-security-change-has-tests exclude] <reason>` to the PR body or head commit message. Reviewers will read the reason.

## Related

- [writing-controllers.md](./writing-controllers.md) — full authoring guide.
- [ADR-005 security](https://codeberg.org/Conduction/hydra/src/branch/main/openspec/architecture/adr-005-security.md)
- [ADR-051 controller exception translation](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-051-controller-exception-translation.md)
- [ADR-049 config fail-mode](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-049-config-fail-mode.md)
- [ADR-052 URL canonicalization](https://codeberg.org/Conduction/hydra/src/branch/development/openspec/architecture/adr-052-url-canonicalization.md)
- Companion mechanical gates: [gate-47 security-change-has-tests](https://codeberg.org/Conduction/hydra/src/branch/development/.claude/skills/hydra-gate-security-change-has-tests/SKILL.md), [gate-48 csrf-cochange](https://codeberg.org/Conduction/hydra/src/branch/development/.claude/skills/hydra-gate-csrf-cochange/SKILL.md), [gate-49 controller-exception-translation](https://codeberg.org/Conduction/hydra/src/branch/development/.claude/skills/hydra-gate-controller-exception-translation/SKILL.md), [gate-50 security-config-fail-mode](https://codeberg.org/Conduction/hydra/src/branch/development/.claude/skills/hydra-gate-security-config-fail-mode/SKILL.md).
