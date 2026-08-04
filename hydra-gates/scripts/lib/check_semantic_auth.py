#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-9 semantic-auth — brace-aware PHP method body scanner.

Closes W28 from the 2026-04-24 warnings list. The previous gate
implementation in ``scripts/run-hydra-gates.sh`` used a flat
``[^}]*`` regex between ``if (...isAdmin) {`` and the
``throw STATUS_FORBIDDEN`` / ``OCSForbiddenException`` match. Any
nested ``}`` inside the if-body — closure, array literal,
match-expression, anonymous class — terminates ``[^}]*`` before the
real throw, producing a false negative.

This module:

* Reads the PHP file as text.
* Walks each ``public function …(…) :…`` declaration, slicing the
  method body using a proper brace counter that respects strings and
  comments.
* Inspects the head (everything between the previous method's close
  and this method's open) for ``#[NoAdminRequired]`` / ``@NoAdminRequired``
  vs ``#[PublicPage]`` / ``@PublicPage``.
* Inspects the body for the contradictory shapes:

    - ``$this->requireAdmin()`` or bare ``requireAdmin()``
    - ``if (... !isAdmin ...) { ... STATUS_FORBIDDEN | OCSForbidden | 403 ...}``
    - ``if (... isAdmin === false ...) { ... STATUS_FORBIDDEN | OCSForbidden | 403 ...}``
    - PublicPage + ``Http::STATUS_UNAUTHORIZED|FORBIDDEN`` in body

Prints one line per violation in the same format as the bash gate so
``run-hydra-gates.sh`` can consume it unchanged.

Usage::

    python3 scripts/lib/check_semantic_auth.py <php-file> [<php-file> ...]

Exits 0 always; the bash gate counts the printed lines.
"""
from __future__ import annotations

import re
import sys


_METHOD_RE = re.compile(
    r"\bpublic\s+function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)


def _strip_strings_and_comments(src: str) -> str:
    """Replace string literals + comments with same-length whitespace.

    Preserves byte offsets so brace positions in the cleaned string match
    the original.
    """
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        # Single-line comment // ... \n
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            if j == -1:
                j = n
            out.append(" " * (j - i))
            i = j
            continue
        # Block comment / docblock /* ... */
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            out.append(" " * (j - i))
            i = j
            continue
        # Heredoc / nowdoc — bash one-liner false positives are unlikely;
        # treat them as strings starting after `<<<` or `<<<'`.
        if c == "<" and src[i:i + 3] == "<<<":
            # Find the label, then the matching closing label on a new line.
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
        # Single / double quoted string.
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


def _find_method_bodies(src: str):
    """Yield (name, head_start, body_start, body_end_exclusive, line_no)."""
    cleaned = _strip_strings_and_comments(src)
    method_starts: list[tuple[int, str, int]] = []
    for m in _METHOD_RE.finditer(cleaned):
        method_starts.append((m.start(), m.group("name"), src.count("\n", 0, m.start()) + 1))

    for idx, (start, name, line_no) in enumerate(method_starts):
        # Find the opening { after the parameter list.
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
        prev_end = method_starts[idx - 1][0] if idx > 0 else 0
        # Walk back from prev_end to find the previous method's `}` so the
        # head-slice excludes the previous method's annotations.
        head_start = prev_end
        if idx > 0:
            # Re-derive previous body end using the same logic — cheap, methods are few.
            pj = method_starts[idx - 1][0]
            pdepth = 0
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
            pbody_start = pj
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
        yield (name, head_start, body_start, body_end, line_no)


# Anchored to PHPDoc-tag position (`* @Annotation`) or PHP-attribute position
# (`#[Annotation`) at the start of a line. Earlier flat-substring forms fired
# on prose like `(no @NoAdminRequired)` inside docblock explanations —
# observed 8/10 false positives on openregister#1419 commit 6b24be2
# (2026-05-07). Ported from the bash anchoring fix in commit 16a1bf0.
_NO_ADMIN_HEAD_RE = re.compile(
    r"^\s*\*\s*@NoAdminRequired\b|^\s*#\[NoAdminRequired\b",
    re.MULTILINE,
)
_PUBLIC_PAGE_HEAD_RE = re.compile(
    r"^\s*\*\s*@PublicPage\b|^\s*#\[PublicPage\b",
    re.MULTILINE,
)

_ADMIN_GATE_BODY_RE = re.compile(
    r"\$this->requireAdmin\s*\(|\brequireAdmin\s*\(\s*\)",
)
_FORBIDDEN_TOKEN_RE = re.compile(
    r"STATUS_FORBIDDEN|OCSForbiddenException|\b403\b",
)
# What contradicts #[PublicPage] is a SESSION/ADMIN requirement in the body:
# the annotation says "no Nextcloud login needed" while the body insists on a
# logged-in (or admin) user, so one of the two is wrong.
#
# A bare `Http::STATUS_UNAUTHORIZED|FORBIDDEN` was previously a third
# alternative here, and it was wrong: returning 401 is not evidence of a session
# requirement, it is the CORRECT response for any failed authorization —
# including the session-less kind. A #[PublicPage] endpoint authenticated by a
# per-run bearer token (CLI runner, MCP transport, webhook callback) has no NC
# session by construction and must reply 401 on a bad token, so every correctly
# built one matched. Worse, the finding's remediation text reads "remove
# #[PublicPage] or remove body auth check", and on these endpoints BOTH branches
# are harmful: dropping #[PublicPage] makes NC middleware reject the session-less
# caller (the feature breaks), and dropping the token check makes a genuinely
# unauthenticated endpoint — on hermiq's EgressAuthorizeController that is a
# public egress-permit oracle. A gate whose only green states are "broken" and
# "insecure" is worse than no gate. Observed 2026-08-04 on hermiq
# (EgressAuthorizeController::authorize, McpRunController::handle — both verify a
# per-run token first and have specs asserting exactly that).
#
# Token-authenticated public endpoints are still covered elsewhere: gate-7
# (no-admin-idor) requires a per-object guard, and the token check itself is the
# subject of those endpoints' own spec scenarios.
_PUBLIC_BODY_AUTH_RE = re.compile(
    r"\brequireAdmin\s*\(|"
    r"userSession\s*->\s*getUser\s*\(\s*\)\s*===\s*null",
)


def _has_admin_if_with_throw(body: str) -> bool:
    """True if body contains `if (...!isAdmin...) { throw/return STATUS_FORBIDDEN ... }`.

    Brace-aware: walks every `if (` whose condition tests `isAdmin` (negated
    or `=== false`), then checks the body of the if for a forbidden token at
    any depth — closures, array literals, match-expressions don't terminate
    the search prematurely.
    """
    for if_match in re.finditer(r"\bif\s*\(", body):
        if_start = if_match.start()
        # Find matching close paren.
        depth = 1
        i = if_match.end()
        while i < len(body) and depth > 0:
            if body[i] == "(":
                depth += 1
            elif body[i] == ")":
                depth -= 1
            i += 1
        if depth != 0:
            continue
        cond = body[if_match.end():i - 1]
        # Negated isAdmin or isAdmin === false. Character class must
        # include `$` (`$this->`), `>` (`->`), and word chars to span
        # `$this->isAdmin` / `$user->getUID()->isAdmin` etc.
        if not (
            re.search(r"!\s*[\w\$\->]*isAdmin\b", cond) or
            re.search(r"\bisAdmin\b[^)]*===\s*false", cond)
        ):
            continue
        # Body of the if.
        while i < len(body) and body[i] != "{":
            i += 1
        if i >= len(body):
            continue
        body_start = i
        depth = 0
        while i < len(body):
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        if_body = body[body_start:i]
        if "throw" in if_body or "return" in if_body:
            if _FORBIDDEN_TOKEN_RE.search(if_body):
                return True
    return False


def scan_file(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return 0
    violations = 0
    for name, head_start, body_start, body_end, line_no in _find_method_bodies(src):
        head = src[head_start:body_start]
        body = src[body_start:body_end]
        if _NO_ADMIN_HEAD_RE.search(head):
            if _ADMIN_GATE_BODY_RE.search(body) or _has_admin_if_with_throw(body):
                print(
                    f"{path}:{line_no} method={name} "
                    f"rule=no-admin-required-annotation-with-admin-body — "
                    f"remove @NoAdminRequired (if REST endpoint) or use "
                    f"#[AuthorizedAdminSetting(Application::APP_ID)] (if settings panel)"
                )
                violations += 1
        if _PUBLIC_PAGE_HEAD_RE.search(head):
            if _PUBLIC_BODY_AUTH_RE.search(body):
                print(
                    f"{path}:{line_no} method={name} "
                    f"rule=public-page-annotation-with-session-auth-body — "
                    f"#[PublicPage] says no login is required, but the body "
                    f"requires a logged-in/admin user. Drop #[PublicPage] if the "
                    f"endpoint really needs a session. Do NOT resolve this by "
                    f"deleting the authorization check"
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
