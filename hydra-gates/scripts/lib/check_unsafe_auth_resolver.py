#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""gate-8 unsafe-auth-resolver — `catch (\\Throwable) { return null; }` in an
authorization resolver.

THE DEFECT THIS GATE EXISTS FOR
-------------------------------
decidesk#45 (2026-04-21): `DecisionApprovalService::getAuthorizationService()`
returned null on Throwable, and the caller guarded the role check with
`if ($auth !== null)`. A brief outage of the auth service therefore meant "check
skipped", not "deny" — CWE-863 / OWASP A01:2021, fail-open.

WHY THIS REPLACES THE AWK
-------------------------
The bash implementation extracted the method body with

    awk 'NR >= start { print; if (NR > start && /^    \\}/) exit }'

and the catch block with `inblk && /^        \\}/`. Both terminators are
HARD-CODED INDENTATION — four spaces for the method's closing brace, eight for
the catch's. That is not a property of PHP; it is a property of one house style.
Measured 2026-08-08 on a tab-indented file:

  * `/^    \\}/` never matches, so "the body" ran to END OF FILE and swallowed
    every later method. A file whose `getAuthorizationService()` correctly
    RETHROWS was reported as a fail-open, because an unrelated
    `getCachedLabel()` further down returned null from its own catch — a cache
    miss reported as a broken authorization gate. FALSE POSITIVE on correct
    code, which is how a security gate loses its audience (#153).
  * The apparent "detection" of tab-indented fail-opens was the same
    over-capture by luck, not a check.

Braces are the language's own block delimiter, so this walks them, over a
comment-masked copy (#184) so a docblock DESCRIBING the anti-pattern — as the
fixed decidesk code now does — is not itself a finding.

STRING CONTENTS ARE BLANKED TOO (#424)
--------------------------------------
The mask ran with `blank_strings=False`, so the docblock case was fixed and the
STRING LITERAL case was not. Measured on main:

    public function getAuthorizationService(): ?IAuth {
        $doc = 'catch (\\Throwable $e) { return null; }';   // <- prose, in quotes
        try { return $this->container->get(IAuth::class); }
        catch (\\Throwable $e) { throw new ServiceUnavailable(...); }
    }
      -> FAIL — 1 fail-open pattern(s), on a resolver that correctly RETHROWS.

Nothing this gate matches is ever a string: `function <name>(`, `catch
(\\Throwable`, `return null;` and the braces are all syntax. So there is no
evidence to lose — and blanking string contents also repairs the BRACE WALKER,
which previously counted a `{` or `}` written inside a literal as a real block
delimiter.

WHAT IS DELIBERATELY UNCHANGED
------------------------------
Still only `catch (\\Throwable ...)`, and still only a `return null` INSIDE that
catch. The two documented false positives this must keep clearing (procest
ZgwService, 2026-05-26) are methods whose catch returns a 403 / `[]` while a
NORMAL path returns null — those are fail-CLOSED and balanced extraction
excludes them by construction rather than by indentation luck.

Usage:  check_unsafe_auth_resolver.py <php-file> [<php-file>...]
Prints `path:line method=<name> rule=throwable-caught-returns-null`.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from source_scope import php_mask, read_text
except Exception:  # pragma: no cover
    php_mask = None
    read_text = None

# Methods whose NAME says they resolve authorization.
_METHOD_RX = re.compile(
    r"^[ \t]*(?:public|private|protected)(?:\s+static)?\s+function\s+"
    r"([A-Za-z0-9_]*(?:[Aa]uthori[sz]ation|[Aa]uth|[Pp]ermission|[Rr]ole|[Gg]uard)"
    r"[A-Za-z0-9_]*)\s*\(",
    re.M,
)
_CATCH_RX = re.compile(r"\bcatch\s*\(\s*\\?Throwable\b")
_RETURN_NULL_RX = re.compile(r"\breturn\s+null\s*;")


def _block_after(masked: str, i: int) -> tuple[int, int] | None:
    """Span of the `{...}` block starting at or after offset *i*."""
    n = len(masked)
    while i < n and masked[i] != "{":
        if masked[i] == ";":  # abstract / interface declaration, no body
            return None
        i += 1
    if i >= n:
        return None
    depth = 0
    j = i
    while j < n:
        if masked[j] == "{":
            depth += 1
        elif masked[j] == "}":
            depth -= 1
            if depth == 0:
                return (i, j + 1)
        j += 1
    return None


def _classify_callers(masked: str, name: str) -> str:
    """How this file's callers CONSUME a null from ``name``.

    Returns ``"open"``, ``"deny"`` or ``"unknown"``.

    THE SHAPE IS NOT THE DEFECT; THE CONSUMPTION IS.

    `catch (\\Throwable) { return null; }` is what this gate matches, but it is
    only a fail-open when the CALLER treats null as "check skipped". That was
    decidesk#45:

        $auth = $this->getAuthorizationService();
        if ($auth !== null) {          # <- null SKIPS the check
            $auth->assertMayApprove($user);
        }

    The opposite consumption is fail-CLOSED and is not a defect at all:

        if ($this->authorizeEmployee($employeeId) === null) {
            return new JSONResponse([...], Http::STATUS_NOT_FOUND);   # <- null DENIES
        }

    Measured 2026-08-19 on hrmq: 13 findings, all thirteen of the second shape,
    across AvgDsr/Comp/Document/Expense/Interview/Leave/Loonbeslag/Offer/
    Payroll/Roster controllers. Reporting those asks an app to make its
    authorization WEAKER to satisfy an authorization gate.

    Narrowing the catch is not an escape either, and that matters for why this
    lives here rather than in the apps: OpenRegister's `ObjectService::find()`
    throws a bare `Exception` when an object is missing, so for these resolvers
    the catch IS the not-found path. There is no narrower exception to name.

    `!== null` anywhere wins, because a single skip-shaped caller is the defect
    regardless of how many deny-shaped ones sit beside it. No classifiable
    caller returns ``"unknown"`` and the finding stands — a resolver whose
    consumption cannot be seen is exactly the one to keep reporting, and it
    keeps every existing fixture (which have no callers at all) reported.
    """
    call_rx = re.compile(
        r"(?:\$([A-Za-z_]\w*)\s*=\s*)?\$this\s*->\s*" + re.escape(name) + r"\s*\(",
    )
    seen_deny = False
    n = len(masked)

    for m in call_rx.finditer(masked):
        var = m.group(1)
        if var:
            # Assigned first, tested later: `$x = $this->resolve(); if ($x === null)`.
            if re.search(r"\$" + re.escape(var) + r"\s*!==\s*null", masked):
                return "open"
            if re.search(r"\$" + re.escape(var) + r"\s*===\s*null", masked):
                seen_deny = True
            continue

        # Tested inline: `if ($this->resolve(...) === null)`. Walk to the call's
        # own closing paren so a nested call cannot end the scan early.
        depth, k = 0, masked.find("(", m.end() - 1)
        while k < n:
            if masked[k] == "(":
                depth += 1
            elif masked[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        tail = masked[k + 1 : k + 60]
        if re.match(r"\s*!==\s*null", tail):
            return "open"
        if re.match(r"\s*===\s*null", tail):
            seen_deny = True

    if seen_deny:
        return "deny"
    return "unknown"


def scan_file(path: str) -> list[str]:
    try:
        src = read_text(path)
    except OSError:
        return []
    masked = php_mask(src, blank_strings=True)

    out: list[str] = []
    for m in _METHOD_RX.finditer(masked):
        name = m.group(1)
        # Step past the parameter list to the body.
        p = masked.find("(", m.end() - 1)
        depth, k = 0, p
        n = len(masked)
        while k < n:
            if masked[k] == "(":
                depth += 1
            elif masked[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        span = _block_after(masked, k + 1)
        if span is None:
            continue
        body = masked[span[0] : span[1]]
        for c in _CATCH_RX.finditer(body):
            cspan = _block_after(body, c.end())
            if cspan is None:
                continue
            if _RETURN_NULL_RX.search(body[cspan[0] : cspan[1]]):
                # The shape matches. Whether it is a DEFECT depends on how the
                # callers consume the null — see _classify_callers().
                if _classify_callers(masked, name) == "deny":
                    break
                line = masked.count("\n", 0, m.start()) + 1
                out.append(
                    f"{path}:{line} method={name} rule=throwable-caught-returns-null"
                )
                break
    return out


def main(argv: list[str]) -> int:
    if php_mask is None or read_text is None:
        print(
            "check_unsafe_auth_resolver: source_scope.py could not be imported; "
            "NOTHING was inspected",
            file=sys.stderr,
        )
        return 2
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    for path in argv[1:]:
        for finding in scan_file(path):
            print(finding)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
