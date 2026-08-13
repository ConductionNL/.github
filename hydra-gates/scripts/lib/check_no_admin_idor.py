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
  - ``#[PublicPage]`` / ``@PublicPage`` — but only when no caller-supplied
    identifier reaches a lookup the caller can steer.  "May be called
    without a session" is not "every object it can reach is public"; see
    the Pattern 8 commentary.
  - ``Http::STATUS_UNAUTHORIZED`` or ``Http::STATUS_FORBIDDEN``
  - ``TemplateResponse`` return — SPA renderers; NC middleware already
    guarantees an authenticated session so there is no object access to gate

WHAT IS *NOT* A GUARD, AND IS THE MOST IMPORTANT LINE IN THIS FILE
(``ConductionNL/.github#365``): an AUTHENTICATION check.

    $user = $this->userSession->getUser();
    if ($user === null) { return new JSONResponse([], Http::STATUS_UNAUTHORIZED); }

answers "is anyone logged in?". This gate exists to answer "may THIS caller
touch THIS object?". Under ``#[NoAdminRequired]`` the framework has already
settled the first question before the method runs, so the clause cannot even
fail — and it was clearing the gate. Measured: gate-7 reported **0 in all
eighteen fleet apps** while **453 of 791** controller files carried that
preamble. An ``if`` whose condition tests only whether a caller identity is
ABSENT, and whose consequent refuses, is therefore blanked out of the text
every guard pattern here reads — WHATEVER STATUS IT ANSWERS WITH, because
authentication-ness is a property of the condition, not of the status code.
See the ``#365`` commentary further down for the three controls that keep that
blanking from eating a real guard.

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

  Pattern 4 — delegated guard reached through a chain and/or a collaborator.
    Patterns 1–3 all require the guard to be *one* call-hop away and on
    ``$this``.  Real controllers routinely centralise authorisation in an
    injected responder/guard collaborator, and route several thin public
    actions through private helpers before reaching it.  Measured on decidesk
    2026-08-04, that shape produced 11 findings and **every one was guarded**:
    8 reached ``$this->responder->staffAction()`` → ``requireStaff()`` (which
    checks ``currentUid() !== null`` AND ``isStaff()``), 3 reached
    ``citizenAction()`` (401 for an anonymous caller), and ``validateProposal``
    took three hops (``validateProposal`` → ``approveProposal`` /
    ``rejectProposal`` → ``applyProposalDecision`` → ``staffAction``).

    Pattern 4 therefore does two things, both evidence-based:

      a. *Cross-class resolution.* The controller's typed constructor-promoted
         properties and property declarations give ``$prop -> ClassName``.  The
         class is resolved to a real file under the app's ``lib/`` tree (PSR-4
         basename, confirmed by an actual ``class <Name>`` declaration) and
         **that file is parsed**.  A call ``$this->prop->method(`` clears the
         routed method only when ``method`` is demonstrably guard-bearing in
         the collaborator's own source.  Nothing is assumed from the name of
         the property or of the class — an unresolvable class clears nothing.

      b. *Transitive closure.* A same-class method that reaches a guard (by
         (a) or by a strict in-body signal) before its first data mutation is
         itself guard-bearing, and the closure is iterated to a fixpoint, so an
         arbitrarily long intra-class delegation chain is followed.

    Propagation deliberately uses a **stricter** signal than the one-hop
    Pattern 1 (``_STRICT_GUARD_BODY_RE``): a bare ``throw`` or a 404 does not
    seed a chain, because a method that throws ``NotFoundException`` is not an
    authorisation guard and chaining would let that leak arbitrarily far.  Only
    an explicit deny (401/403, ``OCSForbiddenException``, ``isAdmin``, an
    ``authorize*``/``require*``/``ensure*``/``assert*``/``guard*`` call, or an
    anonymous-session rejection) starts or continues a chain.  Every hop must
    also occur before the caller's first data mutation, so a guard that runs
    only after the write still fails the gate.

  Pattern 6 — session-identity hand-off (``.github#365``).
    Every call that receives a caller-supplied value ALSO receives a
    session-derived identity, so the object reference is resolved under a
    scope the caller cannot forge (``findOwned(entryId: $id, userId: $uid)``).

  Pattern 7 — in-body ownership comparison (``.github#365``).
    A refusing ``if`` that compares a session-derived identity against object
    data is an authorisation guard whatever status it answers with — including
    the 404 chosen deliberately so a 403 cannot become an existence oracle.

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

import os
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
#
# ⚠️ THE ATTRIBUTE MAY BE WRITTEN FULLY QUALIFIED (2026-08-08). `#[NoAdminRequired`
# only matches the imported short form. PHP equally permits
#
#     #[\OCP\AppFramework\Http\Attribute\NoAdminRequired]
#
# and with that spelling the method fell out of scope entirely — an unguarded
# endpoint reported PASS. Measured by planting a textbook IDOR (caller-supplied
# `$id`, no ownership check) with the FQ attribute: gate-7 reported PASS; the
# byte-identical body under `#[NoAdminRequired]` reported FAIL. No fleet file
# uses the FQ form today, so this closes a hole before it is stepped in rather
# than after — a false NEGATIVE on a security gate leaves no log to notice.
_FQ = r"(?:\\?(?:OCP\\+AppFramework\\+Http\\+Attribute\\+))?"
_NO_ADMIN_RE = re.compile(
    r"^\s*\*\s*@NoAdminRequired\b|^\s*#\[\s*" + _FQ + r"NoAdminRequired\b",
    re.MULTILINE,
)
_PUBLIC_PAGE_ANNOTATION_RE = re.compile(
    r"^\s*\*\s*@PublicPage\b|^\s*#\[\s*" + _FQ + r"PublicPage\b",
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

# The same set WITHOUT the ``TemplateResponse`` alternative, for `@PublicPage`
# methods. See the note at its use in ``scan_file``.
_PUBLIC_TEMPLATE_STRIPPED_RE = re.compile(
    _GUARD_BODY_RE.pattern.replace(r"|TemplateResponse", ""),
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
# authorisation predicate.  An auth token (``Admin``/``Access``/``Permission``/
# ``Permitted``/``Owner``/``Allowed``/``Authorised``) is REQUIRED; it may sit
# anywhere after the ``is``/``has``/``can``/``may`` prefix as a complete
# CamelCase segment, not only at the end.  That admits the very common
# verb-object spelling where the object noun trails the auth token —
# ``canUserAccessAgent()``, ``canUserModifyAgent()``,
# ``hasOwnerPermissionForRun()`` — which are genuine authorisation predicates.
# ``canRender`` / ``hasChanges`` still deliberately do NOT match: they carry no
# auth token at all, in any position.
#
# Evidence for relaxing the position: ConductionNL/hermiq @ development
# (cd23f547), full-scope run 31490144919 / job 93776678440 — gate-7 reported
# FAIL with 3 methods, and all three were false positives caused by this
# anchoring: AgentsController::index (filters every result through
# ``canUserAccessAgent()`` in-body) and AgentVersionController::index / ::diff
# (both delegate to ``loadAccessibleAgent()``, which calls
# ``canUserAccessAgent()`` and returns null, on which the caller returns
# ``Http::STATUS_NOT_FOUND`` — the 404-style tenancy refusal this gate's own
# FAIL message endorses).  Gate-7 was confirmed NOT blind on that repo first:
# a textbook IDOR planted into the tracked AgentVersionController took the
# count 3 → 4.
#
# ``.github#360`` — THE TOKEN MAY ALSO COME FIRST.  ``#353`` relaxed where the
# auth token may sit, but left the segment before it MANDATORY
# (``[A-Z][A-Za-z0-9_]*`` with no ``?``), so the token could never be the first
# segment after the prefix.  ``hasPermission()`` and ``canAccess()`` — about as
# conventional as a per-object guard name gets — were therefore still reported
# as unguarded IDOR, before AND after ``#353``.  Making that segment repeatable
# and optional (``(?:[A-Z][a-z0-9_]*)*?``) admits the token in ANY position,
# first included.  Measured, old regex vs new:
#
#     hasPermission canAccess isOwner isAllowed mayAccess hasAccess   ✗ → ✓
#     canUserAccessAgent hasOwnerPermissionForRun isAdmin
#     canEditPermission canViewOwner hasACLAccess assertOwner         ✓ → ✓
#     canRender hasChanges canUserModifyAgent hasPendingRevision
#     isVisible canDelete hasItems                                    ✗ → ✗
#
# AN AUTH TOKEN IS STILL REQUIRED, and the token SET is unchanged: the newly
# admitted names are exactly ``{is,has,can,may}`` + token + optional object
# noun.  ``canRender``/``hasChanges`` remain non-guards, which is the abuse
# control — widening this to "any is/has/can/may method" would let gate-7 clear
# real IDORs.  ``canUserModifyAgent`` also stays unmatched, correctly: "Modify"
# is not an auth token, and an earlier note listing it beside
# ``canUserAccessAgent`` as fixed by ``#353`` was wrong.
#
# Also corrected for the record: the ``#353`` commit message says ``canAccess``
# matched.  Measured against BOTH the pre- and post-``#353`` regexes, it never
# did.  ``#353`` was still a clean widening — nothing it used to match was lost
# — but its message overstated the scope, and this comment is where that stops
# being repeated.
_GUARD_HELPER_NAME_RE = re.compile(
    r"^(?:is|has|can|may)(?:[A-Z][a-z0-9_]*)*?"
    r"(?:Admin|Access|Permission|Permitted|Owner|Allowed|Authori[sz]ed)"
    r"(?:[A-Z][A-Za-z0-9_]*)?$"
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
    r"|\bthrow\b[^;\n]{0,120}?"
    r"(?:Forbidden|Unauthori[sz]ed|NotPermitted|NotAllowed|AccessDenied"
    r"|Permission|NotAuthenticated|Authori[sz]ation|Tenan|Owner)"
    r"|isAdmin\s*\("
    r"|isCurrentUserAdmin\s*\("
    r"|->\s*(?:authorize|require|ensure|check|assert|guard)[A-Z][A-Za-z0-9_]*\s*\("
    r"|Http::STATUS_(?:UNAUTHORIZED|FORBIDDEN|NOT_FOUND)"
    r"|(?:statusCode:\s*|,\s*)(?:401|403|404)\b"
)
# `.github#365` removed a `getUser() === null` alternative from the line above.
# It named an AUTHENTICATION test as a guard, which is the whole defect; and in
# the only shape that matters — inside a refusing `if` — the clause is now
# blanked before this pattern ever runs, so the alternative was simultaneously
# dead and a re-entry point. Outside a refusing `if` it never described a guard
# at all (`$anon = $this->userSession->getUser() === null;` computes a flag).

# First data-mutation in a method body — used to enforce "guard before write".
_MUTATION_RE = re.compile(
    r"->\s*(?:save|delete|update|create|insert|remove|persist|store|patch)"
    r"[A-Za-z0-9_]*\s*\(",
)

# ---------------------------------------------------------------------------
# Pattern 4 — delegation chains and collaborator-hosted guards
# ---------------------------------------------------------------------------

# The signal that may START or CONTINUE a delegation chain.
#
# Deliberately STRICTER than _HELPER_GUARD_BODY_RE, which is kept as-is for the
# one-hop Pattern-1 clear.  Two alternatives are dropped here on purpose:
#
#   - a bare `throw`. A method that throws NotFoundException is not an
#     authorisation guard; accepting it at one hop is already generous, and
#     propagating it transitively would let "this function can fail" stand in
#     for "this function checks who you are" arbitrarily far up the call chain.
#   - `404` / STATUS_NOT_FOUND. Same reason: not-found is not access-denied.
#
# What remains is an explicit deny decision: a 401/403, a forbidden exception,
# an admin-membership test, a call to an authorize*/require*/ensure*/assert*/
# guard* predicate, or the rejection of an anonymous session.
_STRICT_GUARD_BODY_RE = re.compile(
    r"OCSForbiddenException"
    r"|NotPermittedException"
    r"|ForbiddenException"
    r"|isAdmin\s*\("
    r"|isCurrentUserAdmin\s*\("
    r"|->\s*(?:authorize|authorise|require|ensure|assert|guard)[A-Z][A-Za-z0-9_]*\s*\("
    r"|Http::STATUS_(?:UNAUTHORIZED|FORBIDDEN)"
    r"|(?:statusCode:\s*|,\s*)(?:401|403)\b"
)
# `.github#365` removed the `(?:getUser|getUID|currentUid|getCurrentUserId)()
# === null` alternative from the line above — the "anonymous-session rejection"
# the Pattern-4 commentary lists as a legitimate chain seed. It is not one: an
# anonymous-session rejection is AUTHENTICATION, and seeding a delegation chain
# with it let a `citizenAction()`-style wrapper clear every action routed
# through it. decidesk's three `citizenAction()` callers were cleared exactly
# this way and become findings again with this change; that is the intended
# direction, not a regression.

# ---------------------------------------------------------------------------
# AUTHENTICATION IS NOT AUTHORISATION (ConductionNL/.github#365)
# ---------------------------------------------------------------------------
#
# THE DEFECT. Every guard regex above accepts `Http::STATUS_UNAUTHORIZED`, the
# numeric `401`, `->unauthorized(` and `getUser() === null` as a guard. Those
# tokens spell the house-style preamble
#
#     $user = $this->userSession->getUser();
#     if ($user === null) {
#         return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
#     }
#
# which answers "is anyone logged in?" — AUTHENTICATION. Gate-7 exists to ask
# "may THIS caller touch THIS object?" — AUTHORISATION. The preamble cannot
# answer that question, and under `#[NoAdminRequired]` it cannot even fail:
# Nextcloud's own middleware has already rejected the anonymous caller before
# the method runs, so the clause is dead defensive code that nonetheless
# silenced the gate.
#
# Measured with a three-arm committed-plant control (same file, same commit,
# same run, byte-identical data-access bodies):
#
#     bare unguarded method                          -> 1 finding
#     + a `no user -> 401` preamble, nothing else    -> 0 findings
#     + a real per-object ownership check            -> 0 findings  (correct)
#
# Fleet scale at the time of the fix: gate-7 reported 0 in ALL EIGHTEEN apps
# while 453 of 791 controller files carried that preamble.
#
# WHY THIS IS NOT "DROP 401 FROM THE REGEX". Two shapes make the token-level
# repair both too narrow and too wide, and both were measured:
#
#   TOO WIDE — a REAL per-object decision that answers with the wrong status:
#
#       if ($account['ownerId'] !== $user->getUID()) {
#           return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
#       }
#
#     That is a genuine authorisation guard written with a 401. Deleting the
#     token turns it into a false POSITIVE — and false positives are exactly
#     how gate-7 lost its credibility (`#353`, `#360`), which is why its
#     silences were believed long enough for this defect to survive.
#
#   TOO NARROW — the same authentication clause answering 403:
#
#       if ($user === null) {
#           return new JSONResponse([], Http::STATUS_FORBIDDEN);
#       }
#
#     Still authentication. If only `401` were dropped, one character of
#     edit would buy the silence straight back — a gate made green by
#     weakening the code it inspects.
#
# So AUTHENTICATION-NESS IS A PROPERTY OF THE CONDITION, NOT OF THE STATUS
# CODE. What is neutralised below is an `if` statement whose condition tests
# only whether a caller identity is ABSENT and whose consequent refuses. The
# whole statement — condition and consequent — is blanked to same-length
# whitespace before any guard regex runs, so byte offsets, line numbers and
# every other pattern in this file are untouched. A method left with no other
# guard is then reported; a method that also carries a real check still clears
# on that check.
#
# THREE CONTROLS KEEP THE BLANKING NARROW, each one closing a way this could
# have eaten a real guard:
#
#   1. POLARITY. Only an ABSENCE test is blanked (`=== null`, `=== false`,
#      `empty()`, `!$user`, `!$user instanceof IUser`). A PRESENCE test is
#      not: `if ($user !== null) { ...whole method body... }` is a wrapper,
#      and blanking it would erase every guard inside it.
#   2. ZERO-ARGUMENT OPERANDS ONLY. The tested expression may contain no call
#      arguments and no array subscript, so `$this->access->canAccess($id,
#      $user)` and `$account['ownerId']` are never mistaken for an identity —
#      the first is a guard, the second is object data.
#   3. THE CONSEQUENT MUST REFUSE (`return` / `throw` / `exit` / `die`).
#      A conditional that merely computes something is not a guard clause and
#      is left alone.
#
# The identity test is deliberately spelling-AGNOSTIC. `#365`'s own re-audit
# built the opposite mistake into its triage tool — it enumerated three
# spellings of "who is the caller" (`getUID(`, `->uid(`, `getCurrentUserId(`),
# and doriath's `sessionUserId()` matched none, producing 19 false positives
# from one unrecognised name. A regex that enumerates spellings of a concept
# reports the spellings it does not know as ABSENCE, and on a security
# detector absence is the alarming answer. So identity is recognised by TOKEN
# (`user` / `uid` / `session` / `actor` / `caller` / `principal` / `login`)
# anywhere in a call-argument-free expression, plus a one-hop alias lookup for
# `$u = $this->userSession->getUser();`.

# Tokens that make an expression read as "the caller's identity". Deliberately
# excludes `account`, `owner`, `member` and similar: those name the OBJECT in
# the fleet's controllers (`$accountId`, `$ownerId`) and treating them as
# identity would blank real ownership comparisons.
_IDENTITY_TOKEN_RE = re.compile(
    r"user|uid|session|actor|caller|principal|logged_?in|login",
    re.IGNORECASE,
)

# ...but an AUTHORISATION token anywhere in the expression vetoes it, whatever
# else it spells. Caught by this suite's own `test_predicate_named_helper_
# clears_caller`, which the first draft of this fix broke:
#
#     if ($this->isCurrentUserAdmin() === false) { return new JSONResponse([], 403); }
#
# is an argument-free call containing `User`, compared against a falsy literal
# — structurally identical to an identity-absence test, and a REAL admin guard.
# Blanking it produced exactly the false positive that made gate-7 untrusted in
# the first place. The veto is what keeps this fix from re-entering that.
_AUTHORISATION_TOKEN_RE = re.compile(
    r"admin|access|permission|permitted|owner|allow|authori[sz]|grant|revoke"
    r"|role|scope|tenant|organisation|organization|entitle",
    re.IGNORECASE,
)

# The right-hand side of an absence comparison.
_NULLISH_LITERAL_RE = re.compile(r"^(?:null|false|''|\"\"|\[\s*\])$", re.IGNORECASE)

# A consequent that does not refuse is not a guard clause.
_REFUSAL_RE = re.compile(r"\b(?:return|throw|exit|die)\b")


def _matching_close(text: str, open_pos: int) -> int:
    """Index of the bracket closing the one at *open_pos*, or ``-1``."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    opener = text[open_pos]
    closer = pairs.get(opener)
    if closer is None:
        return -1
    depth = 0
    for i in range(open_pos, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    return -1


def _top_level_split(text: str, sep: str) -> list:
    """Split *text* on *sep* at bracket depth 0."""
    parts: list = []
    depth = 0
    start = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and text.startswith(sep, i):
            parts.append(text[start:i])
            i += len(sep)
            start = i
            continue
        i += 1
    parts.append(text[start:])
    return [p.strip() for p in parts]


def _is_identity_expression(expr: str, context: str = "") -> bool:
    """True when *expr* reads as "the caller's identity" and nothing else.

    Control 2 of the three listed above: the expression may carry no call
    ARGUMENTS and no array subscript, so a guard call (``canAccess($id, $uid)``)
    and object data (``$account['ownerId']``) can never be read as an identity
    however their names are spelled.
    """
    expr = expr.strip()
    if expr == "":
        return False
    if expr[0] in ("'", '"'):
        # A string literal is never an identity. Without this, a status
        # constant like `'user_draft'` would read as one wherever a comparison
        # is classified.
        return False
    if re.search(r"\(\s*[^)\s]", expr):  # any call with arguments
        return False
    if "[" in expr:
        return False
    if _AUTHORISATION_TOKEN_RE.search(expr):
        return False
    if _IDENTITY_TOKEN_RE.search(expr):
        return True
    # One-hop alias: `$u = $this->userSession->getUser();` earlier in scope.
    m = re.fullmatch(r"\$([A-Za-z_][A-Za-z0-9_]*)", expr)
    if m is not None and context:
        assigns = re.findall(
            r"\$" + re.escape(m.group(1)) + r"\s*=\s*([^;\n]{1,200});", context
        )
        if assigns and _IDENTITY_TOKEN_RE.search(assigns[-1]):
            return True
    return False


def _is_identity_absence_atom(atom: str, context: str = "") -> bool:
    """True when *atom* asserts that a caller identity is ABSENT.

    Control 1: polarity is tracked through ``!``, so ``$user === null`` and
    ``!$user`` qualify while ``$user !== null`` — the wrapper shape — does not.
    """
    atom = atom.strip()
    negated = False
    while True:
        if atom.startswith("!"):
            negated = not negated
            atom = atom[1:].strip()
            continue
        if (
            atom.startswith("(")
            and atom.endswith(")")
            and _matching_close(atom, 0) == len(atom) - 1
        ):
            atom = atom[1:-1].strip()
            continue
        break
    if atom == "":
        return False

    m = re.fullmatch(r"(?:empty|is_null)\s*\((.*)\)", atom, re.S)
    if m is not None:
        # empty($user) / is_null($user) assert absence; negated, presence.
        return not negated and _is_identity_expression(m.group(1), context)
    m = re.fullmatch(r"isset\s*\((.*)\)", atom, re.S)
    if m is not None:
        return negated and _is_identity_expression(m.group(1), context)

    parts = _top_level_split(atom, " instanceof ")
    if len(parts) == 2:
        # `$user instanceof IUser` asserts presence; `!$user instanceof IUser`
        # asserts absence (instanceof binds tighter than `!` in PHP).
        return negated and _is_identity_expression(parts[0], context)

    op = None
    for candidate in ("===", "!==", "==", "!="):
        if candidate in atom:
            op = candidate
            break
    if op is not None:
        parts = _top_level_split(atom, op)
        if len(parts) != 2:
            return False
        lhs, rhs = parts
        if _NULLISH_LITERAL_RE.match(rhs):
            expr = lhs
        elif _NULLISH_LITERAL_RE.match(lhs):
            expr = rhs
        else:
            # Two substantive operands — this is a COMPARISON, the shape a real
            # per-object check takes. Never an authentication test.
            return False
        equality = op in ("===", "==")
        # `$user === null` is absence; `$user !== null` is presence; a leading
        # `!` flips whichever it was.
        return (equality is not negated) and _is_identity_expression(expr, context)

    # A relational operator means this is a magnitude test, not a presence
    # test. `->` and `=>` are stripped first: their `>` is not an operator, and
    # reading it as one made `!$this->userId` — one of the commonest spellings
    # of the whole defect — fall through unrecognised. Caught by the
    # spelling-agnosticism test rather than by review.
    if re.search(r"[<>]", atom.replace("->", "").replace("=>", "")):
        return False
    # Bare truthiness: `!$user` is absence, `$user` is presence.
    return negated and _is_identity_expression(atom, context)


def _is_authentication_only_condition(cond: str, context: str = "") -> bool:
    """True when *cond* tests ONLY whether a caller identity is absent."""
    cond = cond.strip()
    if cond == "":
        return False
    if re.search(r"\?(?!\?|->)", cond):  # a ternary is too complex to classify
        return False
    if re.search(r"\b(?:and|or|xor)\b", cond, re.IGNORECASE):
        return False
    atoms: list = []
    for chunk in _top_level_split(cond, "&&"):
        atoms.extend(_top_level_split(chunk, "||"))
    atoms = [a for a in atoms if a != ""]
    if not atoms:
        return False
    return all(_is_identity_absence_atom(a, context) for a in atoms)


def _consequent_end(cleaned: str, i: int) -> int:
    """End offset of the statement/block starting at *i*, or ``-1``."""
    n = len(cleaned)
    while i < n and cleaned[i].isspace():
        i += 1
    if i >= n:
        return -1
    if cleaned[i] == "{":
        close = _matching_close(cleaned, i)
        return -1 if close == -1 else close + 1
    if cleaned[i] == ":":
        # Alternative `if (): ... endif;` syntax — not classified.
        return -1
    depth = 0
    while i < n:
        c = cleaned[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            return i + 1
        i += 1
    return -1


def _authentication_only_guard_spans(cleaned: str, src: str) -> list:
    """``(start, end)`` spans of every authentication-only guard clause.

    *cleaned* (strings and comments blanked, byte offsets preserved) is used to
    find structure; *src* is used to classify text, because
    ``_strip_strings_and_comments`` would have erased the ``''`` in
    ``$userId === ''``.
    """
    spans: list = []
    for m in re.finditer(r"\bif\s*\(", cleaned):
        open_paren = cleaned.find("(", m.start())
        close = _matching_close(cleaned, open_paren)
        if close == -1:
            continue
        end = _consequent_end(cleaned, close + 1)
        if end == -1:
            continue
        # Control 3: a clause that does not refuse is not a guard clause.
        if not _REFUSAL_RE.search(cleaned[close + 1:end]):
            continue
        context = src[max(0, m.start() - 1500):m.start()]
        if not _is_authentication_only_condition(src[open_paren + 1:close], context):
            continue
        spans.append((m.start(), end))
    return spans


def _blank_authentication_only_guards(cleaned: str, src: str) -> str:
    """*src* with every authentication-only guard clause blanked out.

    Length-preserving and newline-preserving, so every offset, span and line
    number computed elsewhere in this module stays valid.
    """
    spans = _authentication_only_guard_spans(cleaned, src)
    if not spans:
        return src
    out = list(src)
    for start, end in spans:
        for i in range(start, min(end, len(out))):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def _guard_source(src: str, cleaned: str = None) -> str:
    """The text guard patterns are matched against: *src* minus authentication."""
    if cleaned is None:
        cleaned = _strip_strings_and_comments(src)
    return _blank_authentication_only_guards(cleaned, src)


# ---------------------------------------------------------------------------
# Pattern 6 — the SESSION-IDENTITY HAND-OFF (the other half of `.github#365`)
# ---------------------------------------------------------------------------
#
# WHY THIS SHIPS IN THE SAME CHANGE AS THE #365 FIX, AND MUST.
#
# Blanking the authentication preamble takes away a clear that ~453 of 791
# fleet controller files were relying on. Most of those files deserve the
# finding. Some do not, and they fail in one specific, RECOGNISABLE shape —
# doriath writes almost every endpoint this way:
#
#     $userId = $this->sessionUserId();
#     if ($userId === null) { return ... 401 ... }          <- authentication
#     $this->attachmentService->delete(attachmentId: $id, userId: $userId);
#
# and `AttachmentService::loadOwnedSecret()` two frames down does
#
#     if ($secret->getOwnerId() !== $userId) { throw ... 'Not authorized' }
#
# The caller supplies `$id`; the SCOPE it is resolved under is an identity the
# caller cannot forge. That is not an IDOR — it is the correct way to write the
# endpoint. doriath's whole gate-7 exposure was hand-read as ZERO for exactly
# this reason, and shipping the #365 fix without this pattern would have
# reported 45 findings in that one app, all false.
#
# THE FALSE-POSITIVE HISTORY IS WHY THIS IS NOT OPTIONAL. gate-7's #365 defect
# survived because its known failure mode was false POSITIVES (`#353`, `#360` —
# verb-object predicates, `hasPermission`, `canAccess`), so reviewers were
# trained to distrust its findings and therefore to trust its silences. Fixing a
# false negative by manufacturing 45 false positives would restart that cycle
# with the same gate.
#
# THE RULE, and it is deliberately an ALL-quantifier rather than an ANY:
#
#   EVERY method call that receives a CALLER-SUPPLIED PARAMETER must ALSO
#   receive a SESSION-DERIVED IDENTITY.
#
# `any` would be far too generous — a method that reads one object unscoped and
# then calls `$this->audit->logForUser($userId)` would clear itself with the log
# line. `all` says: wherever the caller's own value reaches a call, the caller's
# identity is alongside it. One unqualified data call and the method reports.
#
# SESSION-DERIVED is load-bearing and is checked, not assumed:
#   * a local assigned in this body from an argument-free identity expression
#     (`$this->sessionUserId()`, `$this->userSession->getUser()?->getUID()`) —
#     the same argument-free / no-subscript / no-authorisation-token test the
#     blanking uses, so it stays spelling-agnostic; or
#   * an argument-free identity expression written inline (`$this->userId`).
#   * NEVER a declared parameter. `find($id, $userId)` where `$userId` came off
#     the route proves nothing at all, and that exclusion is what stops this
#     pattern from being a blanket.
#
# WHAT THIS DELIBERATELY DOES NOT CATCH, stated because it is a real residual:
# a callee that ACCEPTS the identity and ignores it. pipelinq's `NotesService`
# resolves `$currentUserId` and uses it only to compute an `isOwn` display flag.
# Gate-7 sees one method body by contract — its own FAIL message says the guard
# may live two frames down — so this residual is symmetrical with the guidance
# already printed to reviewers, and it is the price of not re-poisoning the
# gate's credibility. It is narrowed, not eliminated, by the ALL-quantifier.

# A method call: `->name(` or `::name(`. Used to locate argument lists.
_METHOD_CALL_RE = re.compile(r"(?:->|::)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _declared_parameter_names(params: str) -> set:
    """Variable names declared in a raw parameter-list text."""
    if not params:
        return set()
    return set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", params))


def _session_identity_names(body: str, declared: set) -> set:
    """Locals in *body* assigned from an argument-free identity expression."""
    out: set = set()
    for m in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]{1,200});", body):
        name, rhs = m.group(1), m.group(2)
        if name in declared:
            # A reassigned parameter is still a name the caller chose the first
            # value of. Refuse it rather than reason about flow.
            continue
        if _is_identity_expression(rhs):
            out.add(name)
    return out


def _split_arguments(arg_text: str) -> list:
    """Split a raw argument list on top-level commas."""
    return [a.strip() for a in _top_level_split(arg_text, ",") if a.strip() != ""]


def _argument_is_session_identity(arg: str, declared: set, session: set) -> bool:
    """True when one argument carries the caller's session-derived identity."""
    arg = arg.strip()
    # Named-argument syntax: `userId: $userId`.
    named = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:\s*(?!:)(.*)$", arg, re.S)
    if named is not None:
        arg = named.group(1).strip()
    m = re.fullmatch(r"\$([A-Za-z_][A-Za-z0-9_]*)", arg)
    if m is not None:
        if m.group(1) in session:
            return True
        if m.group(1) in declared:
            return False  # caller-supplied: proves nothing
        return False
    return _is_identity_expression(arg)


# Locals bound from the request are caller-supplied exactly as parameters are.
_REQUEST_BOUND_ASSIGN_RE = re.compile(
    r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^;\n]*"
    r"(?:->\s*getParams?\s*\(|->\s*getQueryParam|->\s*getBody\s*\("
    r"|->\s*getUploadedFile\s*\(|\$_(?:GET|POST|REQUEST|COOKIE|FILES)\b)"
)

# ---------------------------------------------------------------------------
# Pattern 6, clause 2: which calls can actually RESOLVE AN OBJECT
# (`ConductionNL/.github#398`)
# ---------------------------------------------------------------------------
#
# Clause 2 vetoes when "a caller-controlled value reaches an unscoped call".
# It used to treat EVERY method call as such a call, so a method that was
# already correctly scoped was flipped to a finding by a line that touches no
# store at all. Isolated in both directions on one body:
#
#     $safeKey = $this->sanitizeKey($key);       <- ADDING this line: 0 -> 1
#     return $this->store->find($key, $uid);     <- unchanged, still scoped
#
# and adding a session identity to the SANITISER's own argument list cleared it
# again — which is the tell that the veto, not the data access, was deciding.
#
# ⚠️ ADDING AN AUTHORISATION GUARD IS THE WRONG REPAIR for that shape. The
# method is already scoped; a guard would be dead code written to satisfy a
# misreading, and gate-7's whole credibility problem is that the fleet learned
# to trust its silences.
#
# THE FIX IS IN TWO HALVES AND *BOTH* ARE REQUIRED. The second one alone is a
# recall regression, which is the trap this class is laid over:
#
#   (A) TAINT PROPAGATION. A local assigned from an expression mentioning a
#       caller-supplied value IS caller-supplied. Before this, `$safeKey` was
#       invisible to clause 2 — so
#
#           $safeKey = $this->sanitizeKey($key);
#           return $this->store->find($safeKey);      // REAL IDOR
#
#       was reported ONLY BY ACCIDENT, via the same veto that produced the
#       false positive above. Exempting the sanitiser without (A) would have
#       silently cleared that method. (A) is a recall INCREASE and lands first.
#
#   (B) A same-class `$this->helper(...)` that demonstrably resolves nothing
#       does not, by itself, veto. The helper is looked up in this class's own
#       source and ITS BODY IS READ — nothing is inferred from its name, for
#       the same reason Pattern 4 refuses to infer anything from a property
#       name. A body that performs any data access, any mutation or any
#       request read is NOT clearable, and an unresolvable callee is NOT
#       clearable. Fail-closed in every direction.
#
# With both, the sanitiser case clears and the IDOR case above still reports —
# proven by the `SanitiserHelperFalsePositiveTest` near-miss arms.
_TAINT_ASSIGN_RE = re.compile(
    r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]{1,400});")
_TAINT_FOREACH_RE = re.compile(
    r"\bforeach\s*\(\s*([^)]{1,200}?)\s+as\s+(?:\$[A-Za-z_][A-Za-z0-9_]*\s*=>\s*)?"
    r"\$([A-Za-z_][A-Za-z0-9_]*)")

# PSR-3 logging is the other call shape that cannot resolve an object. The
# interface is fixed, every method returns void, and a controller that puts a
# caller-supplied id into its error message is doing diagnostics, not a
# lookup. Measured while hand-reading the sample: openbuild's
# `AppOverrideController::getUser` is correctly scoped
# (`getUserDelta(appId: $appId, uid: $user->getUID())`) and would STILL have
# been reported after (B), purely because of
# `$this->logger->error('... appId '.$appId, ...)`.
# Exempting it can only suppress a finding whose sole unscoped call was a log
# line — i.e. one where nothing was resolved at all. The
# `test_logger_exempt_does_not_hide_a_real_lookup` arm pins that.
_PSR3_LOG_RECEIVER_RE = re.compile(
    r"\$this\s*->\s*(?:logger|log|psrLogger)\s*$")
_PSR3_LOG_LEVELS = frozenset(
    ("debug", "info", "notice", "warning", "warn", "error",
     "critical", "alert", "emergency", "log"))

# A helper body containing any data-access, mutation or request-input token is
# treated as capable of resolving or changing an object, so it keeps its veto.
# `_is_non_resolving_helper` reads `_DATA_ACCESS_RE` / `_MUTATION_CALL_RE` /
# `_REQUEST_INPUT_RE` by NAME at call time — they are defined further down this
# module. That indirection is deliberate: this rule must stay the UNION of the
# gate's existing vocabularies, and re-spelling them here would let the two
# copies drift, which is how a checker quietly stops checking.
#
# ⚠️ NOTE FOR A FUTURE READER: `_DATA_ACCESS_RE` is defined TWICE in this file
# (once around the Pattern-3 block, once in the Pattern-3b block). Python keeps
# the LAST one, which is the object-access spelling — the one wanted here. The
# earlier definition is dead. Left as found rather than fixed blind; recorded
# so nobody "tidies" the surviving one away.


def _class_method_bodies(cleaned: str, src: str) -> dict:
    """name -> body text for EVERY method declared in this file.

    Private helpers included: Pattern 6's clause 2 has to reason about the
    helper a routed method delegates to, and those are private by design.
    """
    out: dict = {}
    for name, start, end in _all_method_spans(cleaned):
        out.setdefault(name, src[start:end])
    return out


def _is_non_resolving_helper(name: str, bodies: dict, _seen=None,
                             _depth: int = 0) -> bool:
    """True when same-class helper *name* provably resolves/changes nothing.

    Fail-closed: an unknown callee, a recursion, a body past the depth limit,
    or any data-access / mutation / request-read token all return False.
    """
    if _depth > 3:
        return False
    if name not in bodies:
        return False  # not a same-class method — nothing was read, clear nothing
    _seen = set() if _seen is None else _seen
    if name in _seen:
        # A cycle. Purity here is a GREATEST fixpoint, so assuming it on the
        # back-edge is sound rather than lax: every body in the cycle has
        # already run the three impure-token checks below — those happen
        # BEFORE this function recurses — so a data access anywhere in the
        # cycle has already returned False. Refusing instead was measured
        # wrong on openregister's `SecurityService::sanitizeInput`, which
        # recurses through `array_map` to sanitise array members and is
        # otherwise pure string handling.
        return True
    _seen = _seen | {name}
    body = bodies[name]
    for rx in (_DATA_ACCESS_RE, _MUTATION_CALL_RE, _REQUEST_INPUT_RE):
        if rx.search(body):
            return False
    # EVERY outbound call must be accounted for. Only two shapes are:
    #   * a plain PHP function (`trim`, `preg_replace`, `array_map`, …) — no
    #     `->` / `::` receiver, so it reaches no collaborator; and
    #   * a same-class `$this->helper(` that is itself non-resolving.
    # ANYTHING ELSE — `$this->prop->method(`, `Foo::bar(`, `$var->method(` —
    # returns False.
    #
    # ⚠️ THIS LOOP USED TO ONLY FOLLOW `$this->name(`, AND THAT WAS FAIL-OPEN.
    # Caught by hand-reading the cleared set rather than by any arm I had
    # written: procest's `ZaakdossierDownloadController::downloadZip` calls
    # `$this->zipExporter->collectDocuments(caseId: $caseId)` with NO session
    # identity, and `collectDocuments` resolves the dossier via
    # `$this->dossierService->getDossierForCase(caseId: $caseId)`. That call
    # matches none of the three vocabularies above — `getDossierForCase` is
    # not `getObject`/`getBy`/`find`/`load` — and the old loop did not follow
    # a `$this->prop->` hop at all, so the helper was declared "pure" and a
    # REAL unguarded case download was SILENTLY CLEARED. Pinned by
    # `test_helper_delegating_to_a_collaborator_is_not_pure`.
    for m in _METHOD_CALL_RE.finditer(body):
        receiver = body[max(0, m.start() - 60):m.start()]
        if re.search(r"\$this\s*$", receiver):
            if _is_non_resolving_helper(m.group(1), bodies, _seen, _depth + 1):
                continue
        return False
    return True


def _taint_closure(body: str, seeds: set, session: set) -> set:
    """Names carrying a caller-supplied value, closed to a fixpoint.

    A local assigned from — or a `foreach` variable iterated over — an
    expression mentioning a tainted name is itself tainted. Without this,
    laundering a parameter through ANY expression made it invisible to
    clause 2 (see the commentary above); this is the half of `#398` that
    ADDS findings.

    ⚠️ TAINT STOPS AT A SCOPED RESULT, and leaving that out is a false-RED
    generator. Measured on the fleet before this clause existed: **6 new
    findings, and all six were false** —

        $result   = $this->userService->revokeApiToken($currentUser, $id);
        $response = new JSONResponse(data: $result);
        return $this->securityService->addSecurityHeaders(response: $response);

    `revokeApiToken` is correctly scoped (it takes the session user), but the
    taint flowed out of it into `$result`, then into `$response`, and the
    header decorator — which resolves nothing whatsoever — became "a
    caller-controlled value reaching an unscoped call".

    The rule that fixes it is the same one Pattern 6 is built on: a value
    produced by a call that ALSO received the caller's own identity was
    resolved under a scope the caller cannot forge, so it is data, not a
    steerable reference. Propagation stops there. A call that did NOT receive
    the identity keeps tainting its result — and that call has already vetoed
    on its own account anyway.
    """
    tainted = set(seeds)
    scoped_re = re.compile(
        "|".join([r"\$" + re.escape(s) + r"\b" for s in sorted(session)])
    ) if session else None

    def _is_scoped_rhs(expr: str) -> bool:
        if _SESSION_IDENTITY_RE.search(expr):
            return True
        return scoped_re is not None and scoped_re.search(expr) is not None

    for _ in range(8):  # fixpoint; bodies are far shallower than this
        grew = False
        for rx, src_grp, dst_grp in (
                (_TAINT_ASSIGN_RE, 2, 1), (_TAINT_FOREACH_RE, 1, 2)):
            for m in rx.finditer(body):
                dst, expr = m.group(dst_grp), m.group(src_grp)
                if dst in tainted or dst in session:
                    continue
                if _is_scoped_rhs(expr):
                    continue
                if any(re.search(r"\$" + re.escape(t) + r"\b", expr)
                       for t in tainted):
                    tainted.add(dst)
                    grew = True
        if not grew:
            break
    return tainted


def _has_session_identity_handoff(body: str, params, helper_bodies=None,
                                  collaborator_bodies=None) -> bool:
    """Pattern 6 — see the commentary above.

    Three clauses, and all three are required:

      1. a session-derived identity exists in this body;
      2. EVERY method call that receives a caller-supplied value (a declared
         parameter, or a local bound from the request) ALSO receives that
         identity;
      3. at least ONE method call receives the identity — the positive
         evidence that the data access is actually scoped, without which
         clause 2 is vacuously true over a method that never uses its input.

    `#398`: clause 2 now applies only to calls that could RESOLVE something —
    see the commentary above `_TAINT_ASSIGN_RE`. *helper_bodies* is this
    class's `name -> body` map; when it is None no helper is clearable, so a
    caller that cannot supply it keeps the old, stricter behaviour.
    """
    if params is None:
        return False
    declared = _declared_parameter_names(params)
    declared |= set(_REQUEST_BOUND_ASSIGN_RE.findall(body))
    # `session` is computed from the UNTAINTED seed set, exactly as before, so
    # this change cannot move which names count as a session identity.
    session = _session_identity_names(body, declared) - declared
    if not session and not _IDENTITY_TOKEN_RE.search(body):
        return False
    # `#398` half (A): follow the caller's value through the locals it is
    # laundered into, so half (B) below cannot silently drop a real IDOR.
    declared = _taint_closure(body, declared, session)

    saw_scoped_call = False
    for m in _METHOD_CALL_RE.finditer(body):
        open_paren = body.find("(", m.start())
        close = _matching_close(body, open_paren)
        if close == -1:
            continue
        args = _split_arguments(body[open_paren + 1:close])
        if not args:
            continue
        identity_here = any(
            _argument_is_session_identity(a, declared, session) for a in args
        )
        caller_value_here = any(
            re.search(r"\$" + re.escape(p) + r"\b", a) for a in args for p in declared
        )
        if caller_value_here and not identity_here:
            # `#398` half (B): a call that provably resolves NOTHING is not
            # evidence of an unscoped lookup. Two shapes, both fail-closed —
            # anything not positively cleared here still vetoes.
            receiver = body[max(0, m.start() - 60):m.start()]
            callee = m.group(1)
            if (_PSR3_LOG_RECEIVER_RE.search(receiver)
                    and callee.lower() in _PSR3_LOG_LEVELS):
                continue  # PSR-3 diagnostics: returns void, resolves nothing
            if (helper_bodies is not None
                    and re.search(r"\$this\s*$", receiver)
                    and _is_non_resolving_helper(callee, helper_bodies)):
                continue  # same-class helper, body READ, resolves nothing
            if collaborator_bodies:
                pm = re.search(
                    r"\$this\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", receiver)
                if (pm is not None
                        and pm.group(1) in collaborator_bodies
                        and _is_non_resolving_helper(
                            callee, collaborator_bodies[pm.group(1)])):
                    continue  # collaborator method, body READ, resolves nothing
            return False  # a caller-controlled value reaching an unscoped call
        if identity_here:
            saw_scoped_call = True
    return saw_scoped_call


# ---------------------------------------------------------------------------
# Pattern 7 — an in-body OWNERSHIP comparison, whatever status it answers with
# ---------------------------------------------------------------------------
#
# The dual of the `#365` rule. If authentication-ness is a property of the
# CONDITION rather than of the status code, so is authorisation-ness — and
# `_GUARD_BODY_RE` recognises a guard only by the code it returns. It
# deliberately excludes 404, because not-found is not access-denied. But the
# fleet's most careful controllers answer an ownership mismatch with 404 ON
# PURPOSE, so that a 403 cannot become an existence oracle for another user's
# ids — which is the reasoning gate-7's OWN FAIL message prints to reviewers:
#
#     "a deliberate 404-style tenancy refusal IS a guard, chosen so a 403
#      cannot become an existence oracle for another tenant's ids."
#
# Until now that sentence was advice to a human, not something the checker
# could act on, and Pattern 5 only implemented it for ORGANISATION-level
# tenancy (`belongsTo`, `activeOrganisation`). Per-USER ownership was left out,
# so doriath's
#
#     if ($secret->getOwnerType() !== 'user' || $secret->getOwnerId() !== $userId) {
#         return new JSONResponse(['message' => 'Not found'], Http::STATUS_NOT_FOUND);
#     }
#
# — a textbook correct guard — was invisible. It did not MATTER before `#365`,
# because the 401 preamble above it cleared the method anyway. Removing that
# clear is what exposes it, so it belongs in this change rather than after it.
#
# The rule: a refusing `if` whose condition COMPARES a session-derived identity
# against a substantive non-identity operand is an authorisation guard. Both
# halves are required, and the nullish-literal case is excluded — that is the
# authentication shape this same change just finished demoting.


# A consequent that DENIES, as opposed to one that merely returns.
#
# `_REFUSAL_RE` accepts any `return`, which is right inside a routed method —
# there is nothing to return but the answer. It is WRONG inside a predicate
# HELPER, where `return true` is a GRANT written in the same shape. The
# package's own abuse control caught this: `canRenderAgent()` doing
# `if ($agent->getOwner() === $userId) { return true; }` is a tokenless
# predicate the fleet has decided must NOT clear the gate (`#353`/`#360`
# coordinator note: "Modify"/"Render" are not auth tokens), and reading it as
# an ownership guard silently reversed that decision.
_DENIAL_CONSEQUENT_RE = re.compile(
    r"\bthrow\b"
    r"|return\s+null\b"
    r"|return\s*;"
    r"|return\s+(?:false|\[\s*\])\s*;"
    r"|Http::STATUS_"
    r"|(?:statusCode:\s*|,\s*)(?:401|403|404)\b"
    r"|Response\s*\(",
)


def _has_ownership_comparison_guard(cleaned: str, src: str, start: int, end: int,
                                    require_denial: bool = False) -> bool:
    """True when the body compares a caller identity against object data and refuses.

    *require_denial* tightens ``refuses`` from "any return" to an actual
    denial — used when the body being read is a HELPER rather than a routed
    method. See ``_DENIAL_CONSEQUENT_RE``.
    """
    for m in re.finditer(r"\bif\s*\(", cleaned[start:end]):
        at = start + m.start()
        open_paren = cleaned.find("(", at)
        close = _matching_close(cleaned, open_paren)
        if close == -1 or close >= end:
            continue
        stop = _consequent_end(cleaned, close + 1)
        if stop == -1 or stop > end:
            continue
        consequent = cleaned[close + 1:stop]
        if not _REFUSAL_RE.search(consequent):
            continue
        if require_denial and not _DENIAL_CONSEQUENT_RE.search(consequent):
            continue
        cond = src[open_paren + 1:close]
        atoms: list = []
        for chunk in _top_level_split(cond, "&&"):
            atoms.extend(_top_level_split(chunk, "||"))
        for atom in atoms:
            op = None
            for candidate in ("===", "!==", "==", "!="):
                if candidate in atom:
                    op = candidate
                    break
            if op is None:
                continue
            parts = _top_level_split(atom, op)
            if len(parts) != 2:
                continue
            lhs, rhs = parts
            if _NULLISH_LITERAL_RE.match(lhs) or _NULLISH_LITERAL_RE.match(rhs):
                continue  # an absence test — authentication, already demoted
            if _is_identity_expression(lhs) or _is_identity_expression(rhs):
                return True
    return False


# ---------------------------------------------------------------------------
# Pattern 5 — the TENANCY guard (ConductionNL/.github#160)
#
# `_STRICT_GUARD_BODY_RE` above deliberately excludes a bare `throw` and a
# 404, on the reasoning that "NotFoundException is not an authorisation
# guard". For a MULTI-TENANT codebase that reasoning inverts, and gate-7
# ended up ANTI-CORRELATED with the property it checks.
#
# OpenRegister's FlowService says why, in its own comment:
#
#     A flow the caller may not see raises the SAME exception as a flow that
#     does not exist. Distinguishing them would turn every read into an
#     oracle for enumerating other tenants' flow ids.
#
#     public function find(string $uuid): Flow {
#         $flow = $this->mapper->findByUuid($uuid);
#         if ($flow->belongsTo($this->activeOrganisation()) === false) {
#             throw new DoesNotExistException('No such flow');
#         }
#         return $flow;
#     }
#
# THAT IS THE GUARD. It is indistinguishable from a 404 on purpose, because
# a 403 here leaks the existence of another tenant's object. So gate-7
# flagged exactly the code that got tenancy right — and would have gone
# GREEN if the 404 were replaced with a 403, i.e. if the code were made to
# leak. `FlowController::state()` WAS a real IDOR, was fixed by routing
# through `FlowService::find()`, and gate-7 reported it identically before
# and after. A verdict that does not move when the defect does is not
# measuring the defect.
#
# The signal below is evidence-based in the same way Pattern 4a is: the
# collaborator's SOURCE is parsed, and what clears it is a comparison
# against a SESSION-DERIVED scope followed by a refusal. Both halves are
# required. A body that merely mentions `belongsTo` and never refuses is
# not a guard; a body that throws with no tenancy comparison is not seeded
# by THIS rule (it may still be seeded by the strict one, which is correct).
_TENANCY_SCOPE_RE = re.compile(
    r"->\s*belongsTo[A-Za-z0-9_]*\s*\("
    r"|->\s*(?:getActiveOrganisation|activeOrganisation|getActiveTenant"
    r"|activeTenant|currentOrganisation|currentTenant)\s*\("
    r"|->\s*apply(?:Organisation|Organization|Tenant)Filter\s*\("
    r"|\bMultiTenancyTrait\b"
)

# The refusal half. A tenancy comparison that leads to nothing is not a
# guard — it is a computed value nobody acted on.
_TENANCY_REFUSAL_RE = re.compile(
    r"\bthrow\b"
    r"|DoesNotExistException"
    r"|NotFoundException"
    r"|return\s*\[\s*\]"
    r"|return\s+null\b"
)


def _has_tenancy_guard(body: str) -> bool:
    """True when *body* compares against a session-derived tenant scope AND
    refuses on mismatch. Both halves required — see Pattern 5 above."""
    return bool(_TENANCY_SCOPE_RE.search(body) and _TENANCY_REFUSAL_RE.search(body))


# Typed property declarations and constructor-promoted properties:
#   private readonly ParticipationResponder $responder,
#   protected ?FooGuard $guard;
# Captures (ClassName, propertyName). Scalar/builtin types are filtered out by
# _COLLABORATOR_SKIP_TYPES so `private string $key` never becomes a lookup.
_PROPERTY_DECL_RE = re.compile(
    r"\b(?:private|protected|public)\s+(?:readonly\s+)?\??"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\\[A-Za-z_][A-Za-z0-9_]*)*)\s+"
    r"\$([A-Za-z_][A-Za-z0-9_]*)"
)

_COLLABORATOR_SKIP_TYPES = frozenset(
    {
        "array", "bool", "boolean", "callable", "float", "int", "integer",
        "iterable", "mixed", "object", "string", "self", "static", "null",
        "readonly", "false", "true", "void",
    }
)

_CLASS_DECL_TEMPLATE = r"\b(?:abstract\s+|final\s+|readonly\s+)*class\s+%s\b"

# Per-repo index of `ClassName -> [path, ...]` under the app's lib/ tree, built
# lazily and cached. Bounded to lib/ so a scan never walks node_modules/vendor.
_CLASS_INDEX_CACHE: dict = {}
# Per-file cache of the strict guard-bearing method set of a collaborator class.
_COLLABORATOR_GUARD_CACHE: dict = {}


def _app_root_for(path: str):
    """Return the app root for *path* — the parent of its ``lib/`` directory.

    Gate-7 is only ever handed ``lib/Controller/*.php``, so the root is the
    directory containing the ``lib`` segment.  Returns ``None`` when there is
    no such segment (the caller then resolves no collaborators at all, which
    fails closed: unresolved means unguarded means flagged).
    """
    parts = os.path.abspath(path).split(os.sep)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "lib":
            return os.sep.join(parts[:i]) or os.sep
    return None


def _class_index(root: str) -> dict:
    """Map ``ClassName -> [file, ...]`` for every PHP file under ``root/lib``.

    PSR-4 basename indexing: the fleet's apps all name the file after the
    class.  Candidates are *verified* by the caller against an actual ``class
    <Name>`` declaration, so a basename collision cannot silently resolve to
    the wrong file.
    """
    cached = _CLASS_INDEX_CACHE.get(root)
    if cached is not None:
        return cached
    index: dict = {}
    lib_dir = os.path.join(root, "lib")
    for dirpath, dirnames, filenames in os.walk(lib_dir):
        dirnames[:] = [
            d for d in dirnames if d not in ("vendor", "node_modules", ".git")
        ]
        for fn in filenames:
            if fn.endswith(".php"):
                index.setdefault(fn[:-4], []).append(os.path.join(dirpath, fn))
    _CLASS_INDEX_CACHE[root] = index
    return index


def _strict_guard_methods(cleaned: str, src: str) -> set:
    """Names of methods in one class that reach a strict guard, transitively.

    Seeded with methods whose name is an authorisation predicate
    (``_GUARD_HELPER_NAME_RE``) or whose body carries a strict deny signal
    (``_STRICT_GUARD_BODY_RE``), then closed over same-class calls: a method
    that invokes a known guard-bearing method *before its first data mutation*
    becomes guard-bearing itself.  Iterated to a fixpoint, so a chain of any
    length is followed.
    """
    spans = list(_all_method_spans(cleaned))
    known: set = set()
    for name, body_start, body_end in spans:
        if _GUARD_HELPER_NAME_RE.match(name):
            known.add(name)
        elif _STRICT_GUARD_BODY_RE.search(src[body_start:body_end]):
            known.add(name)
        elif _has_tenancy_guard(src[body_start:body_end]):
            known.add(name)
    changed = True
    while changed:
        changed = False
        for name, body_start, body_end in spans:
            if name in known:
                continue
            if _calls_guard_helper_before_mutation(src[body_start:body_end], known):
                known.add(name)
                changed = True
    return known


def _collaborator_guard_methods(class_file: str) -> set:
    """Strict guard-bearing method names declared by the class in *class_file*."""
    cached = _COLLABORATOR_GUARD_CACHE.get(class_file)
    if cached is not None:
        return cached
    try:
        with open(class_file, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        _COLLABORATOR_GUARD_CACHE[class_file] = set()
        return set()
    cleaned = _strip_strings_and_comments(src)
    # `.github#365`: a collaborator whose only "guard" is a `no user -> 401`
    # preamble (decidesk's `citizenAction()` is the measured example) must not
    # seed a delegation chain either — the defect is the same one call-hop away.
    result = _strict_guard_methods(cleaned, _guard_source(src, cleaned))
    _COLLABORATOR_GUARD_CACHE[class_file] = result
    return result


def _collaborator_guard_map(cleaned: str, path: str) -> dict:
    """Map ``propertyName -> {guard method names}`` for this class's collaborators.

    Reads the typed constructor-promoted properties and property declarations,
    resolves each type to a real file under the app's ``lib/`` tree, confirms
    the file actually declares that class, and parses it for guard-bearing
    methods.  A type that cannot be resolved contributes nothing — the routed
    method then stays flagged, which is the fail-closed direction.
    """
    root = _app_root_for(path)
    if root is None:
        return {}
    index = _class_index(root)
    out: dict = {}
    for type_name, prop in _PROPERTY_DECL_RE.findall(cleaned):
        short = type_name.rsplit("\\", 1)[-1]
        if short.lower() in _COLLABORATOR_SKIP_TYPES:
            continue
        guards: set = set()
        decl_re = re.compile(_CLASS_DECL_TEMPLATE % re.escape(short))
        for candidate in index.get(short, []):
            if os.path.abspath(candidate) == os.path.abspath(path):
                continue
            try:
                with open(candidate, encoding="utf-8") as fh:
                    csrc = fh.read()
            except OSError:
                continue
            if not decl_re.search(_strip_strings_and_comments(csrc)):
                continue
            guards |= _collaborator_guard_methods(candidate)
        if guards:
            out.setdefault(prop, set()).update(guards)
    return out


def _collaborator_method_bodies(cleaned: str, path: str) -> dict:
    """Map ``propertyName -> {methodName: body}`` for this class's collaborators.

    The read-only twin of :func:`_collaborator_guard_map`, resolving types the
    same way and for the same reason: `#398`'s clause-2 exemption must READ the
    callee, never infer it from a name. An unresolvable type contributes
    nothing, so the routed method keeps its veto — the fail-closed direction.

    Needed because the sanitiser false positive also occurs ONE HOP OUT.
    Measured on openregister `UserController::updateMe`, which is correctly
    scoped (`updateUserProperties(user: $currentUser, data: $sanitizedData)`)
    yet was vetoed by `$this->securityService->sanitizeInput(input: $value)`.
    Restricting the exemption to same-class `$this->helper()` would have left
    that one — and it was a false positive this change itself created, by
    tainting the `foreach` variable that reaches the sanitiser.
    """
    root = _app_root_for(path)
    if root is None:
        return {}
    index = _class_index(root)
    out: dict = {}
    for type_name, prop in _PROPERTY_DECL_RE.findall(cleaned):
        short = type_name.rsplit("\\", 1)[-1]
        if short.lower() in _COLLABORATOR_SKIP_TYPES:
            continue
        decl_re = re.compile(_CLASS_DECL_TEMPLATE % re.escape(short))
        for candidate in index.get(short, []):
            if os.path.abspath(candidate) == os.path.abspath(path):
                continue
            try:
                with open(candidate, encoding="utf-8") as fh:
                    csrc = fh.read()
            except OSError:
                continue
            ccleaned = _strip_strings_and_comments(csrc)
            if not decl_re.search(ccleaned):
                continue
            bodies = _class_method_bodies(ccleaned, csrc)
            if bodies:
                out.setdefault(prop, {}).update(bodies)
    return out


def _calls_collaborator_guard_before_mutation(body: str, guard_map: dict) -> bool:
    """True when *body* calls ``$this-><prop>-><guard>(`` before its first write.

    *guard_map* comes from :func:`_collaborator_guard_map`, so every method
    named here was read out of the collaborator's own source — this is a
    resolved delegation, not a naming convention.
    """
    if not guard_map:
        return False
    mutation = _MUTATION_RE.search(body)
    mutation_pos = mutation.start() if mutation is not None else None
    for prop, methods in guard_map.items():
        for method in methods:
            call_re = re.compile(
                r"\$this\s*->\s*" + re.escape(prop) + r"\s*->\s*"
                + re.escape(method) + r"\s*\("
            )
            for m in call_re.finditer(body):
                if mutation_pos is None or m.start() < mutation_pos:
                    return True
    return False


def _delegated_guard_methods(cleaned: str, src: str, guard_map: dict) -> set:
    """Same-class methods that reach a guard through *any* resolved route.

    Seed = strict in-body guards (``_strict_guard_methods``) plus methods that
    delegate straight to a resolved collaborator guard; then closed over
    same-class calls to a fixpoint.  This is what clears decidesk's
    ``validateProposal`` → ``approveProposal`` → ``applyProposalDecision`` →
    ``$this->responder->staffAction()`` three-hop chain.
    """
    spans = list(_all_method_spans(cleaned))
    known = _strict_guard_methods(cleaned, src)
    for name, body_start, body_end in spans:
        if name in known:
            continue
        if _calls_collaborator_guard_before_mutation(src[body_start:body_end], guard_map):
            known.add(name)
    changed = True
    while changed:
        changed = False
        for name, body_start, body_end in spans:
            if name in known:
                continue
            if _calls_guard_helper_before_mutation(src[body_start:body_end], known):
                known.add(name)
                changed = True
    return known


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
#
# ---------------------------------------------------------------------------
# Pattern 3b — zero-input READ, without the session-identity requirement
# ---------------------------------------------------------------------------
#
# .github#297. Condition 3 above is positive evidence of caller-scoping, and it
# is the right requirement for an endpoint that returns the caller's OWN data.
# But it also withheld the clear from a method that reads nothing caller-
# specific at all — a static catalogue, a published public key, a feature flag
# — and for those the scope note's own reasoning cuts the other way: the
# finding is filed under `no-admin-idor`, and IDOR is *structurally impossible*
# when the caller controls no value whatsoever. Every authenticated user
# receives a byte-identical response; there is no reference to substitute.
#
# THIS DELIBERATELY MOVES THE LINE THE SCOPE NOTE ABOVE DREW, so it is bounded
# by measurement rather than by argument. All six fleet findings that satisfy
# it were read individually; every one is a single delegation to a
# ZERO-ARGUMENT service call:
#
#   nldesign      CatalogController::tokenSets        -> getPublicCatalogue()
#   openregister  FederatedConfigController::types    -> types()
#   openregister  FederatedConfigController::publicKey-> publicKey()   (public by design)
#   openregister  FlowController::eventCatalog        -> getCatalog()  (static triggers)
#   doriath       SettingsController::getPolicy       -> getPolicy()
#   procest       AssistantController::availability    -> isAvailable()
#
# None takes an argument, so no caller-controlled value can reach storage.
#
# THE ABUSE CONTROL is that this clears READS ONLY. A zero-input method that
# MUTATES (`->save*`, `->delete*`, `->reset*`, `->purge*`, …) is still
# reported: "the caller names no object" is not a reason to let an unguarded
# side effect through, and a zero-parameter `purgeAll()` is precisely the shape
# that argument would otherwise wave past. See
# `ZeroInputReadOnlyEndpoints` in test_check_no_admin_idor.py, where each arm
# ships with the true positive it must not swallow.
#
# What is NOT cleared, and stays out of contract as before: a zero-input method
# that returns instance-wide data is still not an IDOR, but if it also writes,
# or if it reads the request at all, this pattern does not apply.

# Anything that pulls caller-controlled input in through the request object.
# Presence of ANY of these disqualifies the pattern: the method then has an
# attacker-influenceable value, which is exactly what IDOR manipulates.
#
# ⚠️ `IRequest::getContent()` WAS MISSING, and it is the same read as
# `php://input` — which this list has always carried (`#413`). Without it, a
# parameterless `#[PublicPage]` handler that reads its envelope with
# `$this->request->getContent()` was cleared by Pattern 3b as a "zero-input
# READ", one branch AFTER Pattern 8b had correctly put it in scope. Two clauses
# disagreeing about whether the same line is caller input is how a widening
# quietly buys nothing. The alternative is anchored on the REQUEST receiver so
# that `$file->getContent()` and `$response->getContent()` — neither of which
# is caller input — are untouched.
_REQUEST_INPUT_RE = re.compile(
    r"->\s*getParams?\s*\("
    r"|->\s*getQueryParam"
    r"|->\s*getUploadedFile\s*\("
    r"|->\s*getBody\s*\("
    r"|(?:\$this\s*->\s*request|\$request)\s*->\s*getContent\s*\("
    r"|\$_(?:GET|POST|REQUEST|COOKIE|FILES)\b"
    r"|php://input"
)

# OBJECT ACCESS. Pattern 3b's second condition, and the one that keeps it from
# becoming a blanket.
#
# The first draft of Pattern 3b cleared any zero-input READ, and that was too
# wide — it swallowed
#
#     public function listEverything() { return $this->svc->findAll(); }
#     public function index() { $data = $this->mapper->findAll(); ... }
#
# which are unscoped instance-wide enumerations, and which this suite already
# pinned as findings (`test_zero_params_without_session_identity_still_flagged`,
# `test_cors_plus_data_access_not_exempted`). Six existing tests failed on that
# draft, which is exactly what they are for.
#
# So Pattern 3b also requires #297's own second condition: the body performs no
# OBJECT ACCESS. What remains clearable is the shape actually measured in the
# fleet — a single delegation to a zero-argument catalogue/config/status call
# (`getPublicCatalogue()`, `publicKey()`, `getCatalog()`, `isAvailable()`) —
# while anything that reaches the store still reports.
_DATA_ACCESS_RE = re.compile(
    r"->\s*(?:find|load|fetch|query|search|list|count)[A-Za-z0-9_]*\s*\("
    r"|->\s*getObjects?\s*\("
    r"|->\s*getBy[A-Za-z0-9_]*\s*\("
    r"|->\s*mapper\b"
    r"|->\s*objectService\b"
    r"|\bObjectService\b"
    r"|\bQueryBuilder\b"
    r"|->\s*getQueryBuilder\s*\(",
    re.IGNORECASE)

# A side effect. Pattern 3b clears READS ONLY: "the caller names no object" is
# not a reason to let an unguarded mutation through, and a zero-parameter
# `purgeAll()` / `resetSettings()` is exactly the shape that argument would
# otherwise wave past.
_MUTATION_CALL_RE = re.compile(
    r"->\s*(?:save|store|insert|update|delete|remove|create|persist|destroy"
    r"|purge|reset|truncate|drop|flush|clear|revoke|grant|enable|disable"
    r"|write|import|migrate|rebuild|regenerate|rotate|sync)[A-Za-z0-9_]*\s*\(",
    re.IGNORECASE)

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


def _is_zero_input_read_only(params, body: str) -> bool:
    """True when the caller controls NO value and the method only reads.

    Pattern 3b (.github#297). With no parameters and no request reads there is
    no direct object reference to substitute, so IDOR is structurally
    impossible. Two further conditions keep the clear narrow:

      * no MUTATION — "the caller names no object" is not a reason to let an
        unguarded `purgeAll()` through;
      * no OBJECT ACCESS — a zero-input `findAll()` is an unscoped instance-wide
        enumeration, which this gate has always reported and still must.

    What is left is the shape actually measured in the fleet: one delegation to
    a zero-argument catalogue / config / status call.
    """
    if params is None:
        return False
    if params.strip() != "":
        return False
    if _REQUEST_INPUT_RE.search(body):
        return False
    if _MUTATION_CALL_RE.search(body):
        return False
    if _DATA_ACCESS_RE.search(body):
        return False
    return True


# ---------------------------------------------------------------------------
# Pattern 8 — a `#[PublicPage]` handler must resolve a caller-supplied
# identifier inside a DECLARED-PUBLIC SCOPE
# ---------------------------------------------------------------------------
#
# THE SECOND BLINDING EXEMPTION, and the larger of the two.
#
# Until now this file skipped every `#[PublicPage]` method unconditionally,
# commented "intentionally open to unauthenticated callers". That conflates
# "may be called WITHOUT A SESSION" with "every object it can reach is
# PUBLIC". The second does not follow from the first, and the exemption
# carried no stated reason, so there was nothing to audit.
#
# It is not safe by construction. opencatalogi#856, merged as `963f832a`,
# was exactly this shape: `GET /api/themes/{id}` was `@PublicPage` and its
# `find()` carried no register and no schema, so it fell through to
# OpenRegister's `findAcrossAllMagicTables()` path and served an anonymous
# caller — no session at all — a municipal `zaak` status record out of an
# unrelated register. That commit's own message records the second half of
# the lesson: "`_rbac: true` was never sufficient on its own: OpenRegister
# grants read by default on a schema that declares no authorization block".
#
# MEASURED, at package `57bcb2b`, on a nine-arm rig in one file/commit/run:
# a byte-identical IDOR plant carrying `#[PublicPage]` — including an
# UNAUTHENTICATED WRITE to an arbitrary `$id` — reported PASS.
#
# 🔑 AND THE EXEMPTION IS NOT WHERE THE BLINDING MOSTLY LIVES. Deleting it
# and changing nothing else moves ONLY the arm that carries BOTH attributes.
# A `#[PublicPage]`-only method never reaches the exemption at all: it is
# dropped one branch earlier by the `_NO_ADMIN_RE` scope filter. Across the
# fleet's `lib/Controller` trees that is 267 of 357 public methods — 75% —
# invisible to any edit of the exemption. Hence this pattern widens the
# SCOPE FILTER as well, and a `#[PublicPage]` method is now judged.
#
# THE PREDICATE, and why it is not the `#[NoAdminRequired]` one. There is no
# "current user" to compare an owner against, so ownership guards do not
# transfer. What a correct public endpoint does instead — measured on the
# fix opencatalogi shipped, and on doriath's machine-credential endpoints —
# is CONSTRAIN THE LOOKUP TO A SCOPE IT DECLARES PUBLIC rather than resolve
# the caller's identifier globally. So:
#
#   in scope   a caller-supplied SCALAR value reaches a selection call
#              (`array $data` is a payload, not a selector; a `$token` /
#              `$secret` IS the authorisation — Nextcloud's own public-share
#              convention — and neither is a selector).
#
#   cleared    every such value reaches at least one selection that is
#              CONSTRAINED, by any of five measured spellings:
#                a. an argument the caller did not supply and that carries a
#                   value (`$themeConfig['register']`). A bare literal does
#                   NOT constrain — `_rbac: true` is the counter-example the
#                   opencatalogi fix names by name;
#                b. a callee whose name declares publicness as a COMPLETE
#                   CamelCase segment (`findPublished`), so that
#                   `getPublicationById` is not read as one;
#                c. a receiver already carrying the scope as STATE —
#                   `$svc->setRegister(...); $svc->setSchema(...); $svc->find($id)`
#                   is how OpenRegister's ObjectService is scoped fleet-wide;
#                d. a CONTAINER RESOLUTION: this call's own result constrains
#                   a later selection AND an unresolvable container is
#                   refused. That is opencatalogi's own fix shape — resolve
#                   the catalog, refuse if it does not exist, then look the
#                   id up inside it;
#                e. one resolved delegation hop — `publicationDownload($id)`
#                   handing straight to `PublicationService::download()`,
#                   which opens with `isObjectInCatalogScope($id) === false
#                   -> 404`. Read out of the collaborator's own file, never
#                   assumed from a name.
#              plus a whole-body clear: a refusing `if` whose CONDITION tests
#              a publication / visibility / enablement predicate. That is the
#              dual of Pattern 7 — the decision was made just after the read
#              rather than inside it.
#
# PER SELECTOR, NOT PER CALL. Once a value has been resolved inside a scope,
# later uses of that same value are "verify in scope, then act" — the
# commonest correct public shape in the fleet (opencatalogi's `attachments()`
# proves the object is in the catalog, refuses 404 if not, and only then
# fetches by id). Judging each call in isolation reports the second half of
# a correct method.
#
# ⚠️ THE FAILURE MODE BEING REPAIRED HERE IS DISTRUST. gate-7's KNOWN defect
# was false POSITIVES (`#353`, `#360`), which is exactly why the fleet came
# to trust its silences. A public-page rule that lights up the apps getting
# it right would restart that cycle, so clears a–e were each derived from a
# shape that was READ in a fleet app, and the two-directional control is
# `ThemesController::show` before and after `963f832a`: FLAGGED at
# `f6e86ab`, SILENT at `963f832`, same file, same method, same checker.

# A capability identifier: the value IS the authorisation, so substituting
# another one is not an authorisation bypass but a guess at a secret. This is
# Nextcloud's own public-share convention and doriath's link-share,
# ephemeral-send and secret-request-fill routes.
_PUBLIC_CAPABILITY_RE = re.compile(
    r"(?:^|_)(?:token|secret|hash|signature|nonce|otp|key)s?$"
    r"|[a-z](?:Token|Secret|Hash|Signature|Nonce|Otp|Key)s?$",
)

# Publicness declared as a COMPLETE CamelCase segment or snake word. The
# segment requirement is the same device `_GUARD_HELPER_NAME_RE` uses, and it
# is what stops `getPublicationById` — a plain object read — being mistaken
# for a publicness constraint because its name happens to start with "public".
_PUBLICNESS_SEGMENT_RE = re.compile(
    r"(?:^|_)(?:public|published|publicly|publishable|anonymous|guest|visible"
    r"|listable|unauthenticated)(?![a-z])"
    r"|(?<=[a-z0-9])(?:Public|Published|Publicly|Publishable|Anonymous"
    r"|Guest|Visible|Listable|Unauthenticated)(?![a-z])",
)

# The same, widened for the whole-body REFUSAL test only: a public endpoint
# that refuses when the resource is not switched on for public consumption has
# made the publication decision, whatever noun it uses for it.
_PUBLICNESS_REFUSAL_RE = re.compile(
    _PUBLICNESS_SEGMENT_RE.pattern
    + r"|(?:^|_|(?<=[a-z0-9]))(?:Enabled|Disabled|Harvestable|Exposed|Listed)"
      r"(?![a-z])"
    + r"|(?:^|_)(?:enabled|disabled|harvestable|exposed|listed)(?![a-z])",
)

_PUBLIC_CALL_RE = re.compile(r"(?:->|::)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")

# A call that RESOLVES an identifier: reads that select a record, and writes
# that target one. A bare `create`/`submit` selects nothing, which is why a
# public form submission — portaliq's entire reason for existing — is not in
# scope here.
_PUBLIC_SELECTION_RE = re.compile(
    r"^(?:find|load|fetch|get|query|search|read|show|render|resolve|lookup"
    r"|save|store|update|patch|delete|remove|destroy|revoke|publish|depublish"
    r"|unpublish|download|serve|stream|attach|detach|assign|handle|process)",
    re.IGNORECASE)

# `array $data` is a request BODY, not a selector.
_PUBLIC_PAYLOAD_TYPE_RE = re.compile(r"\b(?:array|object|iterable)\b")

# A non-caller argument only CONSTRAINS if it carries a value.
_PUBLIC_SUBSTANTIVE_RE = re.compile(r"\$[A-Za-z_]|::|->|\bself\b|\bstatic\b")

_PUBLIC_RECEIVER_CALL_RE = re.compile(
    r"(\$[A-Za-z_]\w*(?:\s*->\s*\w+)*?)\s*->\s*([A-Za-z_]\w*)\s*\(")
_PUBLIC_SCOPE_SETTER_RE = re.compile(
    r"^(?:set|with|scope|restrict|constrain|limit)[A-Z]")

_PUBLIC_ASSIGN_RE = re.compile(
    r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]{1,400});")
_PUBLIC_FOREACH_RE = re.compile(
    r"foreach\s*\(([^)]{1,200}?)\s+as\s+"
    r"(?:\$[A-Za-z_]\w*\s*=>\s*)?\$([A-Za-z_]\w*)\s*\)")
_PUBLIC_THIS_PROP_CALL_TEMPLATE = (
    r"\$this\s*->\s*%s\s*->\s*([A-Za-z_]\w*)\s*\(")


def _public_declared_names(params, body: str) -> set:
    """EVERY caller-supplied name, payload and capability ones included.

    Used to disqualify an argument from CONSTRAINING: `save($id, $data)` is
    not scoped by its own payload.
    """
    out = set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", params or ""))
    out |= set(_REQUEST_BOUND_ASSIGN_RE.findall(body))
    return out


def _public_tainted_names(params, body: str) -> set:
    """Caller-supplied values that could SELECT an object.

    Taint propagates through casts, concatenation and array indexing, but NOT
    through a `->method()` call: the caller chose WHICH record, and the values
    inside the record the server handed back are the server's. Every
    laundering hop through a selection call is itself judged by this pattern,
    so nothing is lost by stopping taint there.
    """
    tainted = set()
    for chunk in _top_level_split(params or "", ","):
        m = re.search(r"\$([A-Za-z_][A-Za-z0-9_]*)", chunk)
        if m is None:
            continue
        if _PUBLIC_PAYLOAD_TYPE_RE.search(chunk[:m.start()]):
            continue
        if _PUBLIC_CAPABILITY_RE.search(m.group(1)):
            continue
        tainted.add(m.group(1))
    for name in _REQUEST_BOUND_ASSIGN_RE.findall(body):
        if not _PUBLIC_CAPABILITY_RE.search(name):
            tainted.add(name)

    for _ in range(4):  # bounded fixpoint
        grew = False
        for m in _PUBLIC_ASSIGN_RE.finditer(body):
            name, rhs = m.group(1), m.group(2)
            if name in tainted:
                continue
            if _PUBLIC_CALL_RE.search(rhs):
                continue
            if re.search(r"::\s*[A-Za-z_]\w*\s*\[", rhs):
                # Read out of a CLASS CONSTANT — `self::RESOURCE_MAP[$resource]`.
                # The caller picked the key; the VALUE is one the app wrote
                # down, so it is not a caller-supplied selector.
                continue
            if any(re.search(r"\$" + re.escape(t) + r"\b", rhs) for t in tainted):
                tainted.add(name)
                grew = True
        if not grew:
            break
    return tainted


def _public_derivation(body: str) -> dict:
    """``name -> names it was derived from`` (assignments and foreach binds)."""
    out: dict = {}
    for m in _PUBLIC_ASSIGN_RE.finditer(body):
        out.setdefault(m.group(1), set()).update(
            re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", m.group(2)))
    for m in _PUBLIC_FOREACH_RE.finditer(body):
        out.setdefault(m.group(2), set()).update(
            re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", m.group(1)))
    return out


def _public_origins(name: str, deriv: dict, depth: int = 6) -> set:
    """Transitive closure of what *name* was derived from."""
    seen: set = set()
    frontier = {name}
    for _ in range(depth):
        nxt: set = set()
        for n in frontier:
            for src in deriv.get(n, ()):  # noqa: SIM118
                if src not in seen:
                    seen.add(src)
                    nxt.add(src)
        if not nxt:
            break
        frontier = nxt
    return seen


def _public_refused_on(var: str, body: str) -> bool:
    """True when a refusing ``if`` tests *var* — the container-resolution gate."""
    for m in re.finditer(r"\bif\s*\(", body):
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        if not re.search(r"\$" + re.escape(var) + r"\b", body[op + 1:cl]):
            continue
        end = _consequent_end(body, cl + 1)
        if end > cl and _REFUSAL_RE.search(body[cl:end]):
            return True
    return False


def _public_refuses_on_publicness(body: str) -> bool:
    """A refusing ``if`` whose CONDITION tests a publication predicate."""
    for m in re.finditer(r"\bif\s*\(", body):
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        if not _PUBLICNESS_REFUSAL_RE.search(body[op + 1:cl]):
            continue
        end = _consequent_end(body, cl + 1)
        if end > cl and _REFUSAL_RE.search(body[cl:end]):
            return True
    return False


def _public_refuses_on_scope_predicate(body: str) -> bool:
    """A refusing ``if`` whose CONDITION calls an authorisation/scope predicate.

    opencatalogi's `PublicationService::download()` opens with

        if ($this->isObjectInCatalogScope(objectId: $id) === false) {
            return new JSONResponse(['error' => 'Not Found'], 404);
        }

    — a real per-object scope decision, deliberately answered 404 so a 403
    cannot become an existence oracle for an anonymous caller. `_GUARD_BODY_RE`
    cannot see it (no 401/403, no `authorize*`/`require*` prefix) and Pattern 7
    cannot either (no identity to compare — there is no session here). Same
    reasoning as Pattern 7 and as `#365` itself: recognise the DECISION by its
    CONDITION, not by the status code it answers with.
    """
    for m in re.finditer(r"\bif\s*\(", body):
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        cond = body[op + 1:cl]
        if "(" not in cond:
            continue  # a predicate CALL, not a bare field comparison
        if not _AUTHORISATION_TOKEN_RE.search(cond):
            continue
        end = _consequent_end(body, cl + 1)
        if end > cl and _REFUSAL_RE.search(body[cl:end]):
            return True
    return False


def _public_state_scoped_receivers(body: str, declared: set) -> dict:
    """Receivers handed a scope as STATE before the lookup runs."""
    out: dict = {}
    for m in _PUBLIC_RECEIVER_CALL_RE.finditer(body):
        recv, callee = m.group(1).strip(), m.group(2)
        if not _PUBLIC_SCOPE_SETTER_RE.match(callee):
            continue
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        args = _split_arguments(body[op + 1:cl])
        if not args:
            continue
        if any(re.search(r"\$" + re.escape(d) + r"\b", a)
               for a in args for d in declared):
            continue  # a scope the CALLER chose is not a scope
        if not any(_PUBLIC_SUBSTANTIVE_RE.search(a) for a in args):
            continue
        out.setdefault(recv, cl)
    return out


def _public_collaborator_files(cleaned: str, path: str) -> dict:
    """``propertyName -> [class file]`` for this class's typed collaborators.

    Same resolution rule as Pattern 4: PSR-4 basename, confirmed by an actual
    ``class <Name>`` declaration. A type that does not resolve contributes
    nothing, which is the fail-closed direction.
    """
    root = _app_root_for(path)
    if root is None:
        return {}
    index = _class_index(root)
    out: dict = {}
    for type_name, prop in _PROPERTY_DECL_RE.findall(cleaned):
        short = type_name.rsplit("\\", 1)[-1]
        if short.lower() in _COLLABORATOR_SKIP_TYPES:
            continue
        decl_re = re.compile(_CLASS_DECL_TEMPLATE % re.escape(short))
        for candidate in index.get(short, []):
            if os.path.abspath(candidate) == os.path.abspath(path):
                continue
            try:
                with open(candidate, encoding="utf-8") as fh:
                    csrc = fh.read()
            except OSError:
                continue
            if decl_re.search(_strip_strings_and_comments(csrc)):
                out.setdefault(prop, []).append(candidate)
    return out


def _public_delegate_scopes(prop: str, method: str, files) -> bool:
    """One resolved hop: does ``<prop>-><method>()`` scope its own lookups?

    The callee's body is READ out of the collaborator's file and put through
    the same predicate, with every one of its own parameters treated as
    caller-supplied. No recursion: a second hop is not resolved, so an
    unscoped delegate two frames down still reports.

    ⚠️ POSITIVE EVIDENCE IS REQUIRED, and the first draft of this hop did not
    demand it. "The callee has no unscoped selector" is VACUOUSLY TRUE of a
    leaf data-access method — `ThemeService::find($id) { return $row; }` has
    no selection call of its own — so the probe cleared every delegation to
    the data layer, which is precisely the shape being hunted. Caught by the
    rig: all three plants went silent. The callee must now SHOW a guard, a
    declared-publicness refusal, or a lookup it scoped itself.
    """
    for class_file in files or ():
        try:
            with open(class_file, encoding="utf-8") as fh:
                csrc = fh.read()
        except OSError:
            continue
        ccleaned = _strip_strings_and_comments(csrc)
        cguard = _blank_authentication_only_guards(ccleaned, csrc)
        for (cname, _chead, csig, cbstart, cbend, _cline) in _find_method_bodies(csrc):
            if cname != method:
                continue
            cparams = _parameter_list(ccleaned, csig)
            cbody = cguard[cbstart:cbend]
            if _GUARD_BODY_RE.search(csrc[csig:cbstart] + cbody):
                return True
            if _public_refuses_on_publicness(cbody):
                return True
            if _public_refuses_on_scope_predicate(cbody):
                return True
            selects, validated = _public_selection_scope(cbody, cparams, None)
            if selects and not (selects - validated):
                return True
    return False


def _public_unscoped_selectors(body: str, params, delegate_probe=None) -> list:
    """Caller-supplied selectors that NEVER reach a scoped lookup.

    Empty list = nothing to report: either the method takes no selector, no
    selector reaches a selection call, or every one of them was resolved
    inside a declared scope. *delegate_probe* is an optional
    ``(prop, method) -> bool`` used for the one-hop collaborator clear.
    """
    if params is None:
        return []
    if _public_refuses_on_publicness(body):
        return []
    if _public_refuses_on_scope_predicate(body):
        return []
    selects, validated = _public_selection_scope(body, params, delegate_probe)
    return sorted(selects - validated)


def _public_selection_scope(body: str, params, delegate_probe=None):
    """``(selectors that reach a lookup, those that reach a SCOPED one)``."""
    if params is None:
        return (set(), set())
    tainted = _public_tainted_names(params, body)
    if not tainted:
        return (set(), set())

    declared = _public_declared_names(params, body)
    capability = {d for d in declared if _PUBLIC_CAPABILITY_RE.search(d)}
    state_scoped = _public_state_scoped_receivers(body, declared)
    deriv = _public_derivation(body)

    # ALLOW-LIST VALIDATION. A caller value used as a subscript into a class
    # constant, with a refusal when it does not resolve, can only ever name a
    # member of a closed set the app wrote down. decidesk's `OriController`
    # does exactly this — `self::RESOURCE_MAP[$resource] ?? null`, unknown =>
    # 404 — and there is no object to steer afterwards.
    for t in list(tainted):
        for am in re.finditer(
                r"\$([A-Za-z_]\w*)\s*=\s*[^;\n]{0,80}?"
                r"(?:self|static|parent|[A-Za-z_]\w*)::[A-Za-z_]\w*\s*\[\s*\$"
                + re.escape(t) + r"\b", body):
            if _public_refused_on(am.group(1), body):
                tainted.discard(t)
                break

    # Everything that constrains SOME selection, and everything those values
    # were derived from. A call whose RESULT lands in here resolved a
    # container rather than an object.
    constraint_origins: set = set()
    for m in _PUBLIC_CALL_RE.finditer(body):
        if not _PUBLIC_SELECTION_RE.match(m.group(1)):
            continue
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        for arg in _split_arguments(body[op + 1:cl]):
            if any(re.search(r"\$" + re.escape(d) + r"\b", arg) for d in declared):
                continue
            for var in re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", arg):
                constraint_origins.add(var)
                constraint_origins |= _public_origins(var, deriv)

    selects: set = set()
    validated: set = set()

    # CAPABILITY VALIDATION. A caller value checked ALONGSIDE an unguessable
    # capability, with a refusal on the result, has been authorised by the
    # secret. shillinq's `lookupByToken` does
    #
    #     $result = $this->tokens->validate($appointmentId, $token);
    #     if ($result['ok'] === false) { return ...; }
    #     $appointment = $this->loadAppointment(appointmentId: $appointmentId);
    #
    # — the later load carries no token, but by then the pair has been proven.
    if capability:
        for m in _PUBLIC_CALL_RE.finditer(body):
            op = body.find("(", m.start())
            cl = _matching_close(body, op)
            if cl == -1:
                continue
            args = _split_arguments(body[op + 1:cl])
            if not any(re.search(r"\$" + re.escape(c) + r"\b", a)
                       for a in args for c in capability):
                continue
            paired = {t for t in tainted
                      if any(re.search(r"\$" + re.escape(t) + r"\b", a) for a in args)}
            if not paired:
                continue
            lhs = re.search(r"\$([A-Za-z_]\w*)\s*=\s*[^;\n]{0,200}$", body[:m.start()])
            if lhs is not None and _public_refused_on(lhs.group(1), body):
                validated |= paired
    for m in _PUBLIC_CALL_RE.finditer(body):
        callee = m.group(1)
        if not _PUBLIC_SELECTION_RE.match(callee):
            continue
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        args = _split_arguments(body[op + 1:cl])
        if not args:
            continue
        here = set()
        for t in tainted:
            if any(re.search(r"\$" + re.escape(t) + r"\b", a) for a in args):
                here.add(t)
        if not here:
            continue
        selects |= here

        scoped = False
        if _PUBLICNESS_SEGMENT_RE.search(callee):
            scoped = True
        # A CAPABILITY alongside the identifier constrains it: shillinq's
        # `lookupByToken` resolves the appointment by an unguessable token and
        # merely NARROWS with `appointmentId`. The secret is the scope.
        if not scoped and any(
                re.search(r"\$" + re.escape(c) + r"\b", a)
                for a in args for c in capability):
            scoped = True
        if not scoped:
            for arg in args:
                if any(re.search(r"\$" + re.escape(d) + r"\b", arg)
                       for d in declared):
                    continue
                if (_PUBLICNESS_SEGMENT_RE.search(arg)
                        or _PUBLIC_SUBSTANTIVE_RE.search(arg)):
                    scoped = True
                    break
        if not scoped:
            before = body[:m.start()].rstrip()
            for recv, setpos in state_scoped.items():
                if setpos < m.start() and before.endswith(recv):
                    scoped = True
                    break
        if not scoped:
            lhs = re.search(
                r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^;\n]{0,200}$",
                body[:m.start()])
            if (lhs is not None and lhs.group(1) in constraint_origins
                    and _public_refused_on(lhs.group(1), body)):
                scoped = True
        if not scoped and delegate_probe is not None:
            prop = re.search(
                r"\$this\s*->\s*([A-Za-z_]\w*)\s*->\s*$", body[:m.start() + 2])
            if prop is None:
                prop = re.search(
                    r"\$this\s*->\s*([A-Za-z_]\w*)\s*$", body[:m.start()])
            if prop is not None and delegate_probe(prop.group(1), callee):
                scoped = True
        if scoped:
            validated |= here

    return (selects, validated)


# ---------------------------------------------------------------------------
# Pattern 8b — the RAW REQUEST BODY (`ConductionNL/.github#413`)
# ---------------------------------------------------------------------------
#
# 🔴 PATTERN 8 IS KEYED ON THE METHOD SIGNATURE, SO A SOAP ENDPOINT IS
# STRUCTURALLY INVISIBLE TO IT.
#
# Everything above decides scope by asking whether a caller-supplied SCALAR
# reaches a selection call, and every source of such a scalar it knows about is
# either a declared parameter or a `->getParam()`-family read. That is right for
# REST and it has no opinion at all about the shape where the method takes NO
# PARAMETERS and the selector arrives inside the request body.
#
# MEASURED, three arms in one file varying only the selector's SOURCE:
#
#     armVisible(string $id)  -> $this->dispatcher->find($id)        1 finding
#     armRawBody()            -> $this->dispatcher->dispatch(
#                                    rawBody: file_get_contents('php://input'))
#                                                                    0 findings
#     armRawBodyVerified()    -> ->dispatchVerified(rawBody: …)      0 findings
#
# The middle arm is the defect: the same delegate, the same unscoped
# resolution, and the gate cannot see it. The live instance is procest's
# `StufController::zaken()` / `::personen()` — `#[PublicPage]` +
# `#[NoCSRFRequired]`, reaching a responder that dispatches `zakLk01` (case
# create/update), `zakLv01` (case query), `npsLv01` (PERSON QUERY BY BSN) and
# `edcLk01` (document create/update) with no authentication of any kind.
# gate-7 reported ZERO findings on that app's 79 public methods.
#
# 🔑 THE SILENCE WAS RIGHT 77 TIMES AND WRONG TWICE, which is precisely the
# ratio that makes a silence persuasive — the failure mode Pattern 8's own
# commentary warns about, one level up.
#
# THE PREDICATE.
#
#   in scope   a `#[PublicPage]` method reads the RAW REQUEST BODY and hands a
#              value derived from it to a `->` / `::` method call. The raw body
#              is not `array $data`: a payload is bound by the route to one
#              resource, whereas an envelope handed to a collaborator names its
#              own OPERATION as well as its subject, so the caller chose both.
#              A raw body that is only decoded, measured or logged reaches no
#              collaborator and is not in scope — PSR-3 diagnostics are
#              excluded by the same receiver/level test Pattern 6 uses.
#
#   cleared    NOTHING NEW. This clause widens the SCOPE ONLY; every clear that
#              already exists then applies unchanged — the whole-body publicness
#              and scope-predicate refusals here, and after this returns, the
#              401/403 body guard, Pattern 7's ownership comparison, Pattern 1's
#              same-class guard helper and Pattern 4's RESOLVED collaborator
#              guard in scan_file. That is deliberate: inventing a second
#              vocabulary for "this webhook authenticated its sender" is how a
#              gate acquires a clear nobody can audit. All five fleet apps that
#              get this right are cleared by machinery that was already here —
#              `checkSignature()` and `verifyWsse()` by Pattern 1/4's name
#              rules, `validateSignature()` by the inline 401 it answers with,
#              and procest's repaired `dispatch()` by Pattern 4 reading
#              `authenticateSender()`'s `STATUS_UNAUTHORIZED` out of the
#              collaborator's own file.

_PUBLIC_RAW_BODY_RE = re.compile(
    r"php://input"
    r"|(?:\$this\s*->\s*request|\$request)\s*->\s*getContent\s*\(",
)


def _public_raw_body_names(body: str) -> set:
    """Locals carrying a value derived from the raw request body.

    Propagation stops at a `->method()` call for the same reason
    `_public_tainted_names` stops there — past that hop the value is the
    server's answer, and that hop is itself judged. Plain FUNCTION calls
    (`json_decode`, `simplexml_load_string`, `trim`) are not method calls and
    do propagate: decoding a body does not make it the server's.
    """
    names: set = set()
    for _ in range(4):  # bounded fixpoint
        grew = False
        for m in _PUBLIC_ASSIGN_RE.finditer(body):
            name, rhs = m.group(1), m.group(2)
            if name in names:
                continue
            if _PUBLIC_RAW_BODY_RE.search(rhs):
                names.add(name)
                grew = True
                continue
            if _PUBLIC_CALL_RE.search(rhs):
                continue
            if any(re.search(r"\$" + re.escape(t) + r"\b", rhs) for t in names):
                names.add(name)
                grew = True
        if not grew:
            break
    return names


def _public_argument_is_capability(arg: str) -> bool:
    """True when *arg* carries an unguessable credential.

    Both spellings count, because both were MEASURED. `handle($rawBody,
    $signature)` names it in the VARIABLE (pipelinq's
    `BrpController::mutationWebhook`) and `handleWebhook(rawBody: $rawBody,
    signature: $signatureArg)` names it in the NAMED-ARGUMENT LABEL
    (`CtiController::webhook`) — the same idiom, and reading only one of them
    would report one of those two while clearing the other.
    """
    named = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?!:)", arg)
    if named is not None and _PUBLIC_CAPABILITY_RE.search(named.group(1)):
        return True
    return any(_PUBLIC_CAPABILITY_RE.search(v)
               for v in re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", arg))


def _public_raw_body_reaches_collaborator(body: str) -> bool:
    """True when the raw body — or a value derived from it — is handed on
    WITHOUT the sender's credential travelling with it.

    ⚠️ THE CREDENTIAL CLEAR IS NOT A NEW IDEA, it is Pattern 8's own. The
    scalar-selector half already holds that "a `$token` / `$secret` IS the
    authorisation — Nextcloud's own public-share convention", and clears a
    lookup that carries one. A webhook signature is the same object: an
    unguessable value the caller cannot forge, collected from the request and
    handed to the verifier alongside the bytes it authenticates.

    MEASURED before this clear existed: the widening produced exactly two new
    findings across the eighteen core apps, and BOTH were this shape —
    pipelinq's BRP and CTI webhooks, each reading an `X-…-Signature` header and
    forwarding it. Neither was reachable by the existing clears (the CTI one
    refuses on `$result['valid'] === false`, a bare field comparison that
    `_public_refuses_on_scope_predicate` deliberately does not read), so both
    would have been false positives whose only remedy was an exempt tag.

    The residual risk is stated rather than hidden: an app that collects a
    signature and never verifies it clears here. That is precisely the risk
    Pattern 8 already accepts for `$token`, and it is a smaller one than the
    raw-body blindness this pattern exists to close.
    """
    names = _public_raw_body_names(body)
    for m in _PUBLIC_CALL_RE.finditer(body):
        op = body.find("(", m.start())
        cl = _matching_close(body, op)
        if cl == -1:
            continue
        args = _split_arguments(body[op + 1:cl])
        if not args:
            continue
        carries = any(_PUBLIC_RAW_BODY_RE.search(a) for a in args) or any(
            re.search(r"\$" + re.escape(n) + r"\b", a) for a in args for n in names)
        if not carries:
            continue
        receiver = body[max(0, m.start() - 60):m.start()]
        if (_PSR3_LOG_RECEIVER_RE.search(receiver)
                and m.group(1).lower() in _PSR3_LOG_LEVELS):
            continue  # diagnostics: returns void, resolves nothing
        if any(_public_argument_is_capability(a) for a in args):
            continue  # the sender's proof travels with the envelope
        return True
    return False


def _public_raw_body_is_unjudged(body: str) -> bool:
    """Pattern 8b entry point — see the commentary above."""
    if not _PUBLIC_RAW_BODY_RE.search(body):
        return False
    if _public_refuses_on_publicness(body):
        return False
    if _public_refuses_on_scope_predicate(body):
        return False
    return _public_raw_body_reaches_collaborator(body)


def _public_page_lookup_is_unscoped(cleaned: str, path: str, sig_start: int,
                                    body: str) -> bool:
    """Pattern 8 entry point — see the commentary above."""
    params = _parameter_list(cleaned, sig_start)
    if params is None:
        return False  # unparsed signature judges nothing
    files = None

    def probe(prop, method):
        nonlocal files
        if files is None:
            files = _public_collaborator_files(cleaned, path)
        return _public_delegate_scopes(prop, method, files.get(prop))

    if _public_unscoped_selectors(body, params, probe):
        return True
    # `#413`: the selector that never appears in a signature.
    return _public_raw_body_is_unjudged(body)


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
    # 🔴 THE BODY TEST READS COMMENT-FREE TEXT, and it did not used to.
    #
    # `src` here is the AUTH-BLANKED SOURCE, which still contains every
    # comment — so `_HELPER_GUARD_BODY_RE` was matching prose. MEASURED on
    # hermiq `AgentWebhookController::loadOwnedAgent`, whose body contains no
    # `throw` statement at all; the word appears only in a code comment
    # explaining why the helper CATCHES one:
    #
    #     // caller invokes this helper OUTSIDE its own try block — so the throw
    #     // would escape as a framework 500 …
    #
    # That comment made the helper guard-bearing, and Pattern 1 then cleared
    # all four routed methods that call it. A gate that can be silenced by a
    # sentence in a comment is not measuring the code. `_blank_…(cleaned,
    # cleaned)` keeps the `#365` blanking while dropping comments and string
    # literals, so an authentication-only helper still does not qualify.
    guard_text = _blank_authentication_only_guards(cleaned, cleaned)
    helpers: set = set()
    for name, body_start, body_end in _all_method_spans(cleaned):
        if _GUARD_HELPER_NAME_RE.match(name):
            helpers.add(name)
            continue
        body = guard_text[body_start:body_end]
        if _HELPER_GUARD_BODY_RE.search(body):
            helpers.add(name)
            continue
        # An OWNERSHIP COMPARISON is a guard wherever it is written, including
        # in a helper that answers with `null` rather than a status code —
        # hermiq's `loadOwnedAgent()` is exactly that, and it is the reason the
        # narrowed `throw` alternative above costs no true clear. Same rule as
        # Pattern 7: recognise the decision by its CONDITION.
        if _has_ownership_comparison_guard(cleaned, src, body_start, body_end,
                                           require_denial=True):
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
    # `.github#365`: every guard lookup below runs against `gsrc`, which is
    # `src` with authentication-only guard clauses blanked to same-length
    # whitespace. Offsets, spans and line numbers are unchanged — only the text
    # the guard patterns get to see is. `src` itself is still what gets
    # reported, so findings name real lines.
    gsrc = _blank_authentication_only_guards(cleaned, src)
    is_or_repo = bool(_OR_NAMESPACE_RE.search(cleaned))
    guard_helpers = _collect_guard_helpers(cleaned, gsrc, is_or_repo)
    # Pattern 4 context: resolve this class's typed collaborators to real files
    # and read their guard-bearing methods out of their own source, then close
    # the same-class delegation graph over that. Both are lazy/cached; a file
    # with no @NoAdminRequired method never pays for them.
    collaborator_guards = _collaborator_guard_map(cleaned, path)
    delegated_guards = _delegated_guard_methods(cleaned, gsrc, collaborator_guards)
    # `#398` Pattern 6 context: this class's own method bodies, so clause 2 can
    # READ a `$this->helper()` it is about to veto on instead of assuming.
    helper_bodies = _class_method_bodies(cleaned, gsrc)
    collaborator_bodies = _collaborator_method_bodies(cleaned, path)

    violations = 0
    for name, head_start, sig_start, body_start, body_end, line_no in _find_method_bodies(src):
        head = src[head_start:body_start]
        # ``sig`` is the function declaration line (return type, parameter
        # types etc.) — included in guard checks so that ``TemplateResponse``
        # in the return-type hint is recognised (mirrors the bash gate's
        # behaviour of starting _body at the function declaration line).
        sig = src[sig_start:body_start]
        # `.github#365`: guard lookups read the de-authenticated body. Only the
        # authentication-only clauses differ from `src[body_start:body_end]`,
        # and those carry no data access, so the CORS and zero-input patterns
        # below are unaffected by reading it too.
        body = gsrc[body_start:body_end]

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

        # Methods carrying @NoAdminRequired / #[NoAdminRequired] are in scope,
        # and so — since Pattern 8 — are @PublicPage ones. Before that, a
        # PublicPage method with no NoAdminRequired was dropped HERE, one
        # branch before the exemption that was blamed for the blindness: 267
        # of the fleet's 357 public controller methods never reached it. See
        # the Pattern 8 commentary.
        is_public_page = bool(_PUBLIC_PAGE_ANNOTATION_RE.search(head))
        if not _NO_ADMIN_RE.search(head) and not is_public_page:
            continue

        # ---- Exemption 3: CORS-headers-only body ------------------------
        # Catches oddly-named preflight handlers not covered by exemption 2.
        if _is_cors_only_body(body):
            continue

        # ---- Exemption 3b: @PublicPage that resolves nothing global -------
        # WAS: `@PublicPage` on the same method exempted it unconditionally,
        # "intentionally open to unauthenticated callers". That is a claim
        # about the CALLER, and the gate's question is about the OBJECT.
        # A public page still exempts — but only once Pattern 8 has read the
        # body and found that no caller-supplied identifier reaches a lookup
        # it can steer. Everything else in this loop still applies, so a
        # public method that carries a real guard, a resolved delegation or a
        # reason-bearing exempt tag clears exactly as it would have.
        if is_public_page and not _public_page_lookup_is_unscoped(
                cleaned, path, sig_start, body):
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
        #
        # ⚠️ The TemplateResponse alternative is withheld from a `@PublicPage`
        # method. Its stated reason — "NC middleware already guarantees an
        # authenticated session so there is no object access to gate" — is
        # true under `@NoAdminRequired` and FALSE under `@PublicPage`, which
        # is the annotation that turns the session guarantee off. A public
        # renderer that resolves a caller-supplied id into its template
        # parameters is the same exposure as a JSON one. An exemption's
        # reason is a testable claim; this one does not survive the move.
        if (_PUBLIC_TEMPLATE_STRIPPED_RE if is_public_page
                else _GUARD_BODY_RE).search(sig + body):
            continue

        # ---- Pattern 7: in-body ownership comparison --------------------
        # An ownership mismatch answered with 404 rather than 403 is the
        # deliberate anti-oracle choice this gate's own FAIL message endorses.
        # Recognised by the CONDITION, for the same reason authentication is
        # demoted by the condition rather than by the status code.
        if _has_ownership_comparison_guard(cleaned, gsrc, body_start, body_end):
            continue

        # ---- Pattern 1: private guard-helper delegation -----------------
        # The routed method calls a same-class helper that performs the auth
        # (throws / returns 401/403/404 / is an is*Admin/assert*/guard*/
        # require*/ensure*/authorize* predicate) before its first mutation.
        if _calls_guard_helper_before_mutation(body, guard_helpers):
            continue

        # ---- Pattern 4: resolved delegation chain / collaborator guard ---
        # Either the routed method hands straight to a collaborator method
        # that was READ and found guard-bearing in its own file
        # ($this->responder->staffAction()), or it reaches one through a chain
        # of same-class helpers. Every hop is required to occur before the
        # first data mutation, and an unresolvable collaborator clears nothing.
        if _calls_collaborator_guard_before_mutation(body, collaborator_guards):
            continue
        if _calls_guard_helper_before_mutation(body, delegated_guards):
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
        _params = _parameter_list(cleaned, sig_start)
        if _is_session_scoped_no_reference(_params, body):
            continue

        # ---- Pattern 3b: zero-input READ, no session identity needed ----
        # The caller controls no value at all, so there is no direct object
        # reference to substitute and IDOR is structurally impossible. Reads
        # only — a zero-input mutation still reports. See .github#297 and the
        # Pattern 3b commentary.
        if _is_zero_input_read_only(_params, body):
            continue

        # ---- Pattern 6: session-identity hand-off ------------------------
        # Every call that receives a caller-supplied parameter also receives a
        # session-derived identity, so the object reference is resolved under a
        # scope the caller cannot forge. This is the shape `.github#365`'s
        # blanking would otherwise have turned into 45 false positives in
        # doriath alone. See the Pattern 6 commentary.
        if _has_session_identity_handoff(body, _params, helper_bodies,
                                         collaborator_bodies):
            continue

        # NOTE (.github#315): the guidance that goes with this finding — that
        # the guard may live in a service or mapper two frames down — is
        # printed ONCE by the runner's gate-7 FAIL message, not appended here.
        # `filter_preexisting_methods.py` parses this line with
        # `rule=(?P<rule>.+)$`, so anything added after `rule=` becomes part of
        # the rule NAME and would silently break pre-existing filtering.
        # A `@PublicPage` finding gets its OWN rule name. The remedy differs:
        # there is no session identity to compare an owner against, so the
        # fix is to constrain the lookup to a scope the endpoint declares
        # public — not to add an ownership check. A distinct name also lets
        # triage separate the two populations without re-reading every hit.
        rule = ("publicpage-unscoped-object-lookup" if is_public_page
                else "no-auth-guard-in-body")
        print(f"{path}:{line_no} method={name} rule={rule}")
        violations += 1

    return violations


def main(argv: list[str]) -> int:
    total = 0
    for path in argv[1:]:
        total += scan_file(path)
    return 0  # exit 0 always — caller counts printed lines


if __name__ == "__main__":
    sys.exit(main(sys.argv))
