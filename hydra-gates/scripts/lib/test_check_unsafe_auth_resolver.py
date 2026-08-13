#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Self-test for check_unsafe_auth_resolver.py (gate-8).

The bash this replaced terminated its body scan on `/^    \\}/` and its catch
scan on `/^        \\}/` — hard-coded four- and eight-space indentation. The
tab-indented fixture below is the measured false positive: a resolver that
correctly RETHROWS was reported as a fail-open because an unrelated cache method
further down returned null from its own catch.

Run: python3 scripts/lib/test_check_unsafe_auth_resolver.py   (exit 0 = green)
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_unsafe_auth_resolver import scan_file  # noqa: E402

_FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS — {name}")
    else:
        print(f"FAIL — {name}{(': ' + detail) if detail else ''}")
        _FAILED.append(name)


def run(src: str) -> list[str]:
    fd, path = tempfile.mkstemp(suffix=".php")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(src)
        return scan_file(path)
    finally:
        os.unlink(path)


# --- the decidesk#45 defect -------------------------------------------------
FAIL_OPEN = """<?php
class S {
    public function getAuthorizationService(): ?object
    {
        try {
            return $this->c->get('A');
        } catch (\\Throwable $e) {
            return null;
        }
    }
}
"""
f = run(FAIL_OPEN)
check("the decidesk#45 fail-open is reported", len(f) == 1, repr(f))
check("the finding names the method", f and "getAuthorizationService" in f[0], repr(f))

# --- the same defect, TAB indented (the old awk could not terminate) --------
FAIL_OPEN_TABS = """<?php
class S {
\tpublic function getPermissionResolver(): ?object
\t{
\t\ttry {
\t\t\treturn $this->c->get('A');
\t\t} catch (\\Throwable $e) {
\t\t\treturn null;
\t\t}
\t}
}
"""
f = run(FAIL_OPEN_TABS)
check("a TAB-indented fail-open is reported", len(f) == 1, repr(f))

# --- THE MEASURED FALSE POSITIVE -------------------------------------------
# Tab-indented file, auth method is fail-CLOSED, an unrelated later method
# legitimately returns null. The old awk ran the "body" to EOF and reported it.
TABS_FP = """<?php
class S {
\tpublic function getAuthorizationService(): object
\t{
\t\ttry {
\t\t\treturn $this->c->get('A');
\t\t} catch (\\Throwable $e) {
\t\t\tthrow new \\RuntimeException('unavailable', 0, $e);
\t\t}
\t}

\tpublic function getCachedLabel(string $k): ?string
\t{
\t\ttry {
\t\t\treturn $this->c->get('Cache')->get($k);
\t\t} catch (\\Throwable $e) {
\t\t\treturn null;
\t\t}
\t}
}
"""
f = run(TABS_FP)
check(
    "a fail-CLOSED resolver is NOT reported because a LATER method returns null",
    f == [],
    repr(f),
)

# --- procest ZgwService: catch returns a deny value, normal path returns null
FAIL_CLOSED = """<?php
class S {
    public function validateJwtAuth(): ?object
    {
        try {
            return $this->c->get('A');
        } catch (\\Throwable $e) {
            return new JSONResponse([], 403);
        }
        return null;
    }
}
"""
f = run(FAIL_CLOSED)
check("catch returns 403 while the NORMAL path returns null — NOT reported", f == [], repr(f))

EMPTY_ARRAY = """<?php
class S {
    public function getConsumerAuthorisaties(): ?array
    {
        try {
            return $this->c->get('A');
        } catch (\\Throwable $e) {
            return [];
        }
        return null;
    }
}
"""
f = run(EMPTY_ARRAY)
check("catch returns [] while the normal path returns null — NOT reported", f == [], repr(f))

# --- prose is not code (#184) ----------------------------------------------
DOCBLOCK = """<?php
class S {
    /**
     * NOT the fail-open shape:
     *     } catch (\\Throwable $e) {
     *         return null;
     *     }
     */
    public function getAuthorizationService(): object
    {
        try {
            return $this->c->get('A');
        } catch (\\Throwable $e) {
            throw new \\RuntimeException('x');
        }
    }
}
"""
f = run(DOCBLOCK)
check("a docblock DESCRIBING the anti-pattern is NOT reported", f == [], repr(f))

# --- name scoping: non-auth methods are out of scope ------------------------
NON_AUTH = """<?php
class S {
    public function getCache(): ?object
    {
        try {
            return $this->c->get('Cache');
        } catch (\\Throwable $e) {
            return null;
        }
    }
}
"""
f = run(NON_AUTH)
check("a non-auth method name is out of scope", f == [], repr(f))

# --- nesting depth is irrelevant -------------------------------------------
NESTED = """<?php
class S {
    public function getPermissionChecker(string $t): ?object
    {
        if ($t !== '') {
            try {
                return $this->c->get('P');
            } catch (\\Throwable $e) {
                return null;
            }
        }

        return null;
    }
}
"""
f = run(NESTED)
check("a fail-open NESTED inside an if is reported", len(f) == 1, repr(f))

# --- #424: a STRING LITERAL is not code either ------------------------------
# The comment axis was fixed in #184 and the literal axis was not, so the same
# false positive survived one quote character away.
#
# Mutation-checked by pointing scan_file's mask back at `php_mask(src)`:
#   EVIDENCE (red under the mutation)
#     "a quoted DESCRIPTION of the anti-pattern is not the anti-pattern"
#     "an unbalanced brace inside a literal does not move a method boundary"
#   CONTROL (green both ways — it proves the fix did not simply stop the gate)
#     "the REAL fail-open beside that prose is still reported"
QUOTED_ANTIPATTERN = """<?php
class DemoService {
    /** A resolver that correctly RETHROWS. */
    public function getAuthorizationService(): ?IAuth {
        $doc = 'catch (\\Throwable $e) { return null; }';
        try {
            return $this->container->get(IAuth::class);
        } catch (\\Throwable $e) {
            throw new ServiceUnavailable($e->getMessage());
        }
    }
}
"""
f = run(QUOTED_ANTIPATTERN)
check("a quoted DESCRIPTION of the anti-pattern is not the anti-pattern",
      len(f) == 0, repr(f))

# The paired true positive, in the same file as the prose, so a fix that
# blanked the whole method would be caught here rather than looking green.
QUOTED_PLUS_REAL = """<?php
class DemoService {
    public function getAuthorizationService(): ?IAuth {
        $doc = 'catch (\\Throwable $e) { return null; }';
        try {
            return $this->container->get(IAuth::class);
        } catch (\\Throwable $e) {
            return null;
        }
    }
}
"""
f = run(QUOTED_PLUS_REAL)
check("the REAL fail-open beside that prose is still reported",
      len(f) == 1, repr(f))

# A `{` or `}` inside a literal is not a block delimiter. Before #424 the brace
# walker counted them, so an unbalanced brace in prose shifted every method
# boundary after it.
UNBALANCED_BRACE_IN_STRING = """<?php
class DemoService {
    public function getRoleGuard(): ?IAuth {
        $sql = 'SELECT json_extract(x, \\'$.a{\\') FROM t';
        return $this->guard;
    }
    public function getCachedLabel(): ?string {
        try { return $this->cache->get('k'); }
        catch (\\Throwable $e) { return null; }
    }
}
"""
f = run(UNBALANCED_BRACE_IN_STRING)
check("an unbalanced brace inside a literal does not move a method boundary",
      len(f) == 0, repr(f))

# --- MUTATION CHECK ---------------------------------------------------------
_SRC = open(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "check_unsafe_auth_resolver.py"
    )
).read()
check("extraction is brace-based, not indentation-based", "_block_after" in _SRC)
check("comments are masked", "php_mask" in _SRC)

# The runner must DELEGATE, not carry a second copy of the old awk. (The
# docstring above quotes `/^    \}/` when explaining the defect, so grepping
# this file for it proves nothing — the runner is the honest place to look.)
_RUNNER = open(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "run-hydra-gates.sh"
    )
).read()
check(
    "the runner delegates gate-8 to this helper",
    "check_unsafe_auth_resolver.py" in _RUNNER,
)
check(
    "the superseded indentation-terminated awk is gone from the runner",
    "inblk && /^        \\}/ { exit }" not in _RUNNER,
)
check(
    "gate-8 reports `na` on an empty scope rather than PASS",
    '_skip 8 "unsafe-auth-resolver" na' in _RUNNER,
)

print()
if _FAILED:
    print(f"FAILED: {len(_FAILED)} — {_FAILED}")
    sys.exit(1)
print("ALL check_unsafe_auth_resolver assertions passed")
