#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-7 no-admin-idor — brace-aware PHP controller method scanner.

Every ``public function`` in a controller file that is annotated with
``#[NoAdminRequired]`` / ``@NoAdminRequired`` must contain an
authorisation guard in its body, or qualify for one of the documented
exemptions below.

Recognised guard patterns (body must contain at least one):
  - ``OCSForbiddenException`` thrown
  - ``isAdmin(`` check
  - ``->authorize*(`` / ``->require*(`` / ``->ensure*(`` service call
  - ``#[PublicPage]`` or ``@PublicPage`` annotation on the same method
  - ``Http::STATUS_UNAUTHORIZED`` or ``Http::STATUS_FORBIDDEN``
  - ``TemplateResponse`` return — SPA renderers; NC middleware already
    guarantees an authenticated session so there is no object access to gate

Two additional *delegated*-guard patterns are recognised so the gate stops
emitting whole-repo false positives on codebases that centralise their
authorisation one call-hop away from the routed method:

  Pattern 1 — private guard-helper delegation (app-agnostic).
    A routed method that invokes a same-class helper which itself performs
    the authorisation (throws / returns a 401/403/404 Response / checks
    ``isAdmin`` / ``getUser() === null`` / is a ``is*Admin`` / ``can*Access`` /
    ``assert*`` / ``guard*`` / ``require*`` / ``ensure*`` / ``authorize*``
    predicate) is considered guarded.  A light two-pass first collects the
    class's guard-bearing helpers, then clears any public method that calls
    one of them *before its first data mutation*.  Conservative: the helper
    must actually exist in the class and be invoked — a bare method name is
    never assumed to guard.

  Pattern 2 — OpenRegister data-layer RBAC delegation (ADR-022).
    Inside the OpenRegister app itself (``namespace OCA\\OpenRegister``), a
    ``@NoAdminRequired`` method whose data access goes through
    ``ObjectService`` / ``$this->objectService->`` / a ``*Mapper`` is treated
    as having per-object authorisation delegated to OR's register RBAC +
    multitenancy layer, which is enforced on every fetch/save.  This pattern
    is deliberately scoped to the ``OCA\\OpenRegister`` namespace: consumer
    apps (decidesk, pipelinq, …) that merely *call* ObjectService still need
    an explicit controller-level guard (or a Pattern-1 helper), so a real
    IDOR in a leaf app is never masked.  See "Pattern 2 boundary" below.

Exemptions (method skipped entirely):
  1. ``__construct`` — not a routed action, the 20-line look-back window can
     accidentally catch it when a constructor follows an annotated method.
  2. Methods whose name starts with ``preflightedCors`` (case-insensitive
     prefix ``preflightedcors``) — Nextcloud OCS/CORS preflight handlers.
     OPTIONS pre-flight requests are sent by browsers *without credentials*
     before the real credentialed request; an auth guard would break CORS.
     The fleet convention names these ``preflightedCors`` (exact match used
     in opencatalogi, openconnector, etc.) or ``preflightedCorsItem`` /
     ``preflightedCorsNested`` (variant suffixes). Any method whose
     lower-cased name begins with ``preflightedcors`` is considered a CORS
     preflight handler and is never an IDOR vector.
  3. Methods whose body *only* sets ``Access-Control-*`` headers
     (or calls ``applyCorsHeaders``) without any object/data access —
     catches oddly-named CORS-only handlers. Real endpoints that also
     emit CORS headers while fetching objects are **not** exempted.
  4. Methods whose docblock carries ``@no-admin-idor-exempt <reason>`` —
     deliberately app-wide endpoints (read-only proxies, availability
     probes) that take no caller-supplied object id. The reason text is
     REQUIRED; a bare tag does not exempt. Mirrors the reason-bearing
     exclude conventions of gate-16 (``@spec exclude``) and gate-19
     (``@e2e exclude``); reviewers verify the stated reason.

Prints one ``<file>:<line> method=<name> rule=no-auth-guard-in-body`` line
per violation — the same format the bash gate consumes — and exits 0 always
(the caller counts lines).

Usage::

    python3 scripts/lib/check_no_admin_idor.py lib/Controller/FooController.php …

"""
from __future__ import annotations

import re
import sys

# ---------------------------------------------------------------------------
# PHP source text helpers (shared pattern with check_semantic_auth.py)
# ---------------------------------------------------------------------------

_METHOD_RE = re.compile(
    r"\bpublic\s+function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)

# Every function declaration (any visibility) — used by the Pattern-1 pass to
# collect same-class helper methods that may carry an authorisation guard.
_ANY_FUNC_RE = re.compile(
    r"\bfunction\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)


def _strip_strings_and_comments(src: str) -> str:
    """Replace string literals and comments with same-length whitespace.

    Preserves byte offsets so brace positions in the cleaned string match
    those in the original source.
    """
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        # Single-line comment // …
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            if j == -1:
                j = n
            out.append(" " * (j - i))
            i = j
            continue
        # Block comment / docblock /* … */
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            out.append(" " * (j - i))
            i = j
            continue
        # Heredoc / nowdoc
        if c == "<" and src[i:i + 3] == "<<<":
            m = re.match(r"<<<['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*\n", src[i:])
            if m:
                label = m.group(1)
                end_pat = re.compile(rf"^\s*{re.escape(label)}\s*;?\s*$", re.MULTILINE)
                tail = src[i + m.end():]
                em = end_pat.search(tail)
                stop = i + m.end() + (em.end() if em else len(tail))
                out.append(" " * (stop - i))
                i = stop
                continue
        # Single / double quoted string
        if c in ("'", '"'):
            quote = c
            j = i + 1
            while j < n:
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if src[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(" " * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _body_span(cleaned: str, start: int):
    """Return ``(body_start, body_end)`` for the function whose declaration
    begins at *start* in *cleaned*, or ``None`` for a bodyless declaration
    (abstract/interface method ending in ``;``).

    Offsets are valid in the original source too — ``cleaned`` preserves byte
    offsets — so callers may slice the raw ``src`` with them.
    """
    n = len(cleaned)
    paren_depth = 0
    j = start
    while j < n:
        c = cleaned[j]
        if c == "(":
            paren_depth += 1
        elif c == ")":
            paren_depth -= 1
        elif c == "{" and paren_depth == 0:
            break
        elif c == ";" and paren_depth == 0:
            return None
        j += 1
    if j >= n or cleaned[j] != "{":
        return None
    body_start = j
    depth = 0
    k = j
    while k < n:
        ck = cleaned[k]
        if ck == "{":
            depth += 1
        elif ck == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    if depth != 0:
        return None
    return body_start, k + 1


def _all_method_spans(cleaned: str):
    """Yield ``(name, body_start, body_end)`` for *every* function in *cleaned*.

    Unlike :func:`_find_method_bodies` this includes private/protected helpers
    — the Pattern-1 pass needs them to find guard-bearing helper methods.
    """
    for m in _ANY_FUNC_RE.finditer(cleaned):
        span = _body_span(cleaned, m.start())
        if span is not None:
            yield m.group("name"), span[0], span[1]


def _find_method_bodies(src: str):
    """Yield ``(name, head_start, sig_start, body_start, body_end, line_no)``
    for every ``public function`` in *src*.

    *head_start* points to the character immediately after the previous
    method's closing brace (or 0 for the first method).  This slice is the
    docblock / attribute region from which annotations are read.

    *sig_start* points to the ``public function`` keyword so that the function
    signature (including the return-type hint, e.g. ``: TemplateResponse``) can
    be included in guard checks.  This mirrors the bash gate's behaviour of
    starting ``_body`` at the function declaration line.
    """
    cleaned = _strip_strings_and_comments(src)
    method_starts: list[tuple[int, str, int]] = []
    for m in _METHOD_RE.finditer(cleaned):
        method_starts.append(
            (m.start(), m.group("name"), src.count("\n", 0, m.start()) + 1)
        )

    for idx, (start, name, line_no) in enumerate(method_starts):
        # Advance past the parameter list to find the opening `{`.
        paren_depth = 0
        j = start
        while j < len(cleaned):
            c = cleaned[j]
            if c == "(":
                paren_depth += 1
            elif c == ")":
                paren_depth -= 1
            elif c == "{" and paren_depth == 0:
                break
            j += 1
        if j >= len(cleaned) or cleaned[j] != "{":
            continue
        body_start = j
        depth = 0
        k = j
        while k < len(cleaned):
            ck = cleaned[k]
            if ck == "{":
                depth += 1
            elif ck == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth != 0:
            continue
        body_end = k + 1

        # Head = text after the previous method's `}` up to this method's `{`.
        head_start = 0
        if idx > 0:
            pj = method_starts[idx - 1][0]
            paren_d = 0
            while pj < len(cleaned):
                cj = cleaned[pj]
                if cj == "(":
                    paren_d += 1
                elif cj == ")":
                    paren_d -= 1
                elif cj == "{" and paren_d == 0:
                    break
                pj += 1
            pdepth = 0
            pk = pj
            while pk < len(cleaned):
                ck = cleaned[pk]
                if ck == "{":
                    pdepth += 1
                elif ck == "}":
                    pdepth -= 1
                    if pdepth == 0:
                        break
                pk += 1
            head_start = pk + 1

        yield (name, head_start, start, body_start, body_end, line_no)


# ---------------------------------------------------------------------------
# Annotation and guard patterns
# ---------------------------------------------------------------------------

# Look-back annotation patterns: anchored so prose inside a docblock
# like "(no @NoAdminRequired)" does not fire.
_NO_ADMIN_RE = re.compile(
    r"^\s*\*\s*@NoAdminRequired\b|^\s*#\[NoAdminRequired\b",
    re.MULTILINE,
)
_PUBLIC_PAGE_ANNOTATION_RE = re.compile(
    r"^\s*\*\s*@PublicPage\b|^\s*#\[PublicPage\b",
    re.MULTILINE,
)
# Reason-bearing explicit exemption: `@no-admin-idor-exempt <reason>` in the
# method docblock. The reason text is mandatory — a bare tag stays flagged.
_IDOR_EXEMPT_RE = re.compile(
    r"^\s*\*\s*@no-admin-idor-exempt[ \t]+\S",
    re.MULTILINE,
)

# Guard patterns that satisfy gate-7 when found in the method body.
#
# The numeric ``401`` / ``403`` alternatives are a *parity* fix: many
# controllers return ``new JSONResponse(..., statusCode: 403)`` /
# ``new JSONResponse($e, 403)`` rather than the ``Http::STATUS_FORBIDDEN``
# constant.  The gate already accepts the constant form as a guard, so the
# numeric literal — matched only in response-construction position
# (``statusCode: 40x`` or ``, 40x)``) to avoid catching unrelated magic
# numbers — is recognised identically.  This does not widen what counts as a
# guard shape, only the spelling of an already-accepted one.
#
# The ``::forbidden(`` / ``->unauthorized(`` alternatives are the same kind of
# *spelling* parity fix as the numeric ones: many controllers centralise their
# deny-responses in a small helper (``ResponseHelper::forbidden(...)``,
# ``$this->responses->unauthorized()``) instead of constructing a JSONResponse
# with ``Http::STATUS_FORBIDDEN`` inline.  A method literally named
# ``forbidden`` / ``unauthorized`` / ``accessDenied`` called in response
# position *is* the deny path — recognising it does not widen what counts as a
# guard shape, only how that already-accepted shape may be written.
_GUARD_BODY_RE = re.compile(
    r"OCSForbiddenException"
    r"|isAdmin\s*\("
    r"|->\s*(?:authorize|require|ensure)[A-Z][A-Za-z0-9_]*\s*\("
    r"|Http::STATUS_(?:UNAUTHORIZED|FORBIDDEN)"
    r"|(?:statusCode:\s*|,\s*)(?:401|403)\b"
    r"|(?:::|->)\s*(?:forbidden|unauthorized|accessDenied)\s*\("
    r"|TemplateResponse",
)

# Patterns that indicate a CORS-headers-only body (exemption 3).
_CORS_HEADER_RE = re.compile(r"Access-Control-Allow|applyCorsHeaders")
# Patterns that indicate data access (disqualifies exemption 3).
_DATA_ACCESS_RE = re.compile(
    r"findObject|findAll|ObjectService|Mapper"
    r"|->\s*(?:save|delete|update|create|insert)\s*\("
)

# ---------------------------------------------------------------------------
# Pattern 1 — private guard-helper delegation
# ---------------------------------------------------------------------------

# A same-class helper counts as guard-bearing if its NAME reads like an
# authorisation predicate.  Anchored so only the classic guard shapes match —
# ``canRender`` / ``hasChanges`` (no auth suffix) deliberately do NOT.
_GUARD_HELPER_NAME_RE = re.compile(
    r"^(?:is|has|can|may)[A-Z][A-Za-z0-9_]*"
    r"(?:Admin|Access|Permission|Permitted|Owner|Allowed|Authori[sz]ed)$"
    r"|^(?:assert|guard|deny|verify|authori[sz]e)[A-Za-z0-9_]*$"
    r"|^(?:require|ensure|check)[A-Z][A-Za-z0-9_]*$"
    r"|^isAdmin$"
)

# A same-class helper also counts as guard-bearing if its BODY performs a
# recognised authorisation action (throws, returns a 401/403/404, checks
# admin membership, denies an anonymous session, …).
_HELPER_GUARD_BODY_RE = re.compile(
    r"OCSForbiddenException"
    r"|NotPermittedException"
    r"|ForbiddenException"
    r"|\bthrow\b"
    r"|isAdmin\s*\("
    r"|isCurrentUserAdmin\s*\("
    r"|->\s*(?:authorize|require|ensure|check|assert|guard)[A-Z][A-Za-z0-9_]*\s*\("
    r"|Http::STATUS_(?:UNAUTHORIZED|FORBIDDEN|NOT_FOUND)"
    r"|(?:statusCode:\s*|,\s*)(?:401|403|404)\b"
    r"|getUser\s*\(\s*\)\s*===\s*null"
)

# First data-mutation in a method body — used to enforce "guard before write".
_MUTATION_RE = re.compile(
    r"->\s*(?:save|delete|update|create|insert|remove|persist|store|patch)"
    r"[A-Za-z0-9_]*\s*\(",
)

# ---------------------------------------------------------------------------
# Pattern 2 — OpenRegister data-layer RBAC delegation (ADR-022)
# ---------------------------------------------------------------------------

# Scoped strictly to the OpenRegister app: only there does data-layer access
# equate to per-object authorisation.  Consumer apps keep the explicit-guard
# requirement so a real IDOR in a leaf app is never masked.
_OR_NAMESPACE_RE = re.compile(r"\bnamespace\s+OCA\\OpenRegister\b")

# Data access routed through OR's RBAC-enforcing layer: the ObjectService
# facade or any ``*Mapper``.  Every fetch/save on these enforces register
# RBAC + multitenancy, so per-object authz is delegated by design.
_OR_RBAC_ACCESS_RE = re.compile(
    r"->\s*objectService\s*->"
    r"|\$objectService\s*->"
    r"|\bObjectService\b"
    r"|->\s*[A-Za-z0-9_]*[Mm]apper\s*->"
    r"|\$[A-Za-z0-9_]*[Mm]apper\s*->"
    r"|->\s*mapper\s*->"
)


# ---------------------------------------------------------------------------
# Pattern 3 — session-scoped endpoint with no caller-supplied object reference
# ---------------------------------------------------------------------------
#
# IDOR requires a *direct object reference the caller controls*. A routed
# method that accepts no parameters at all AND reads nothing from the request
# has no such reference to manipulate — the only identity in play is the one
# the session supplies. ``GET /api/acknowledgements/pending`` is the canonical
# shape: it returns the current user's own pending items and there is no id an
# attacker could substitute.
#
# Deriving identity from the session instead of from a parameter is the
# *correct* way to write these endpoints — strictly safer than accepting an id
# and then checking it. Before this pattern the gate flagged them anyway,
# because it looked for the presence of a guard *call* and these have nothing
# to guard. That trains reviewers to wave through gate-7 output, which is worse
# than the false positive itself.
#
# All three conditions must hold, so the clear stays narrow:
#   1. zero declared parameters — nothing bound from the route path;
#   2. no request reads (``getParam``/``$_GET``/raw body/uploads) — nothing
#      bound from the query string or request body either;
#   3. the body references a session-derived identity — positive evidence the
#      method is scoped to the caller rather than reading globally.
#
# Scope note: this clears *IDOR* only, which is what gate-7 is named for. A
# zero-input method that returns instance-wide data is a different defect class
# (broken access control / information disclosure) and is out of this gate's
# contract — condition 3 is what keeps such a method from being cleared here.

# Anything that pulls caller-controlled input in through the request object.
# Presence of ANY of these disqualifies the pattern: the method then has an
# attacker-influenceable value, which is exactly what IDOR manipulates.
_REQUEST_INPUT_RE = re.compile(
    r"->\s*getParams?\s*\("
    r"|->\s*getQueryParam"
    r"|->\s*getUploadedFile\s*\("
    r"|->\s*getBody\s*\("
    r"|\$_(?:GET|POST|REQUEST|COOKIE|FILES)\b"
    r"|php://input"
)

# Positive evidence that the method is scoped to the *session* user.
_SESSION_IDENTITY_RE = re.compile(
    r"\$this\s*->\s*userId\b"
    r"|\$this\s*->\s*userSession\b"
    r"|->\s*getUID\s*\(\s*\)"
    r"|->\s*getUser\s*\(\s*\)"
    r"|getCurrentUserId\s*\("
)


def _parameter_list(cleaned: str, sig_start: int):
    """Return the raw parameter-list text of the function declared at *sig_start*.

    Brace-aware so default values containing parentheses (e.g.
    ``int $x = foo(1)``) do not truncate the span. Returns ``None`` when no
    parameter list can be located.
    """
    i = cleaned.find("(", sig_start)
    if i == -1:
        return None
    depth = 0
    j = i
    n = len(cleaned)
    while j < n:
        c = cleaned[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return cleaned[i + 1:j]
        j += 1
    return None


def _is_session_scoped_no_reference(params, body: str) -> bool:
    """True when the method has no caller-supplied object reference (Pattern 3).

    See the Pattern 3 commentary above for why all three conditions are
    required. *params* is the raw parameter-list text (``None`` when it could
    not be parsed — treated as "not clearable", fail-closed).
    """
    if params is None:
        return False
    if params.strip() != "":
        return False
    if _REQUEST_INPUT_RE.search(body):
        return False
    return bool(_SESSION_IDENTITY_RE.search(body))


# ---------------------------------------------------------------------------
# Exemption helpers
# ---------------------------------------------------------------------------

def _is_preflight_cors_method(name: str) -> bool:
    """True when *name* matches the Nextcloud CORS preflight handler convention.

    The fleet uses ``preflightedCors`` as the canonical name, with optional
    suffixes for sub-resource variants (``preflightedCorsItem``, etc.).
    The check is case-insensitive so ``PreflightedCors`` variants are also
    caught.  A plain ``preflight`` prefix is intentionally *not* exempted
    here — use the broader body-CORS check (exemption 3) for those.

    Nextcloud's OCS framework sends OPTIONS pre-flight requests without
    credentials; adding an auth guard to these handlers would reject all
    cross-origin requests before they start.  They are never IDOR vectors.
    """
    return name.lower().startswith("preflightedcors")


def _collect_guard_helpers(cleaned: str, src: str, is_or_repo: bool) -> set:
    """Return the set of same-class method names that carry an auth guard.

    A method is guard-bearing when its name reads like an authorisation
    predicate (``_GUARD_HELPER_NAME_RE``) OR its body performs a recognised
    authorisation action (``_HELPER_GUARD_BODY_RE``).  These are the helpers a
    routed method may delegate its guard to (Pattern 1).

    Inside the OpenRegister app (*is_or_repo*), a helper whose body fetches or
    saves through OR's RBAC-enforcing data layer (``_OR_RBAC_ACCESS_RE`` —
    ObjectService / a ``*Mapper``) also counts: it resolves the object under
    register RBAC + multitenancy, so a routed method that loads its object via
    such a helper (e.g. ``validateObject()``) has per-object authz delegated
    exactly as Pattern 2 intends — just one call-hop away.  Still OR-scoped,
    so leaf-app helpers are never assumed to guard.
    """
    helpers: set = set()
    for name, body_start, body_end in _all_method_spans(cleaned):
        if _GUARD_HELPER_NAME_RE.match(name):
            helpers.add(name)
            continue
        body = src[body_start:body_end]
        if _HELPER_GUARD_BODY_RE.search(body):
            helpers.add(name)
            continue
        if is_or_repo and _OR_RBAC_ACCESS_RE.search(body):
            helpers.add(name)
    return helpers


def _calls_guard_helper_before_mutation(body: str, helpers: set) -> bool:
    """True when *body* invokes a guard-bearing helper before its first write.

    The helper must be called on ``$this`` / ``self`` / ``static`` / ``parent``
    and appear *before* the first data mutation in the body (a read-only method
    with no mutation qualifies on invocation alone).  This keeps the clear
    conservative: a guard that runs only *after* the object has been mutated
    does not protect the write.
    """
    if not helpers:
        return False
    mutation = _MUTATION_RE.search(body)
    mutation_pos = mutation.start() if mutation is not None else None
    for h in helpers:
        call_re = re.compile(
            r"(?:\$this|self|static|parent)\s*(?:->|::)\s*" + re.escape(h) + r"\s*\("
        )
        for m in call_re.finditer(body):
            if mutation_pos is None or m.start() < mutation_pos:
                return True
    return False


def _is_cors_only_body(body: str) -> bool:
    """True when *body* only sets CORS headers and does not access objects.

    Catches oddly-named CORS-only handlers that are not covered by the
    ``preflightedCors*`` name exemption.  Real endpoints that also emit
    ``Access-Control-*`` headers while fetching or mutating data are *not*
    considered CORS-only and must still carry a guard.
    """
    return bool(_CORS_HEADER_RE.search(body)) and not bool(_DATA_ACCESS_RE.search(body))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_file(path: str) -> int:
    """Scan *path* for gate-7 violations; print each one and return the count."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return 0

    # One-time, per-file context for the two delegated-guard patterns.
    cleaned = _strip_strings_and_comments(src)
    is_or_repo = bool(_OR_NAMESPACE_RE.search(cleaned))
    guard_helpers = _collect_guard_helpers(cleaned, src, is_or_repo)

    violations = 0
    for name, head_start, sig_start, body_start, body_end, line_no in _find_method_bodies(src):
        head = src[head_start:body_start]
        # ``sig`` is the function declaration line (return type, parameter
        # types etc.) — included in guard checks so that ``TemplateResponse``
        # in the return-type hint is recognised (mirrors the bash gate's
        # behaviour of starting _body at the function declaration line).
        sig = src[sig_start:body_start]
        body = src[body_start:body_end]

        # ---- Exemption 1: constructor -----------------------------------
        if name == "__construct":
            continue

        # ---- Exemption 2: CORS preflight handler by name ----------------
        # Nextcloud convention: preflightedCors / preflightedCorsItem / etc.
        # These are OPTIONS handlers that MUST be unauthenticated — the
        # browser sends them without credentials. Adding an auth guard here
        # would break all cross-origin preflight requests.
        if _is_preflight_cors_method(name):
            continue

        # Only methods carrying @NoAdminRequired / #[NoAdminRequired] are in scope.
        if not _NO_ADMIN_RE.search(head):
            continue

        # ---- Exemption 3: CORS-headers-only body ------------------------
        # Catches oddly-named preflight handlers not covered by exemption 2.
        if _is_cors_only_body(body):
            continue

        # @PublicPage on the *same* method satisfies the gate — the method
        # is intentionally open to unauthenticated callers.
        if _PUBLIC_PAGE_ANNOTATION_RE.search(head):
            continue

        # ---- Exemption 4: reason-bearing explicit exempt tag -------------
        # `@no-admin-idor-exempt <reason>` in the method docblock marks a
        # deliberately app-wide endpoint (read-only proxy, availability
        # probe, …) that takes no caller-supplied object id. The reason is
        # REQUIRED — a bare tag does not exempt (mirrors gate-16/19 exclude
        # conventions) — and reviewers treat the reason as a claim to verify.
        if _IDOR_EXEMPT_RE.search(head):
            continue

        # At least one authorisation guard must appear in the body OR the
        # function signature (e.g. TemplateResponse in the return type hint).
        if _GUARD_BODY_RE.search(sig + body):
            continue

        # ---- Pattern 1: private guard-helper delegation -----------------
        # The routed method calls a same-class helper that performs the auth
        # (throws / returns 401/403/404 / is an is*Admin/assert*/guard*/
        # require*/ensure*/authorize* predicate) before its first mutation.
        if _calls_guard_helper_before_mutation(body, guard_helpers):
            continue

        # ---- Pattern 2: OpenRegister data-layer RBAC delegation ---------
        # Inside the OpenRegister app, data access through ObjectService or a
        # *Mapper delegates per-object authz to OR's register RBAC +
        # multitenancy (ADR-022). Scoped to OCA\OpenRegister so leaf-app
        # IDORs are never masked.
        if is_or_repo and _OR_RBAC_ACCESS_RE.search(body):
            continue

        # ---- Pattern 3: session-scoped, no caller-supplied reference ----
        # Zero parameters + no request reads + a session-derived identity =
        # there is no direct object reference for an attacker to substitute,
        # so IDOR is not structurally possible. See the Pattern 3 commentary
        # for why all three conditions are required.
        if _is_session_scoped_no_reference(_parameter_list(cleaned, sig_start), body):
            continue

        print(
            f"{path}:{line_no} method={name} rule=no-auth-guard-in-body"
        )
        violations += 1

    return violations


def main(argv: list[str]) -> int:
    total = 0
    for path in argv[1:]:
        total += scan_file(path)
    return 0  # exit 0 always — caller counts printed lines


if __name__ == "__main__":
    sys.exit(main(sys.argv))
