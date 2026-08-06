#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-47 security-change-has-tests — a PR that changes security-sensitive
code must also touch a test.

WHY THIS WAS REWRITTEN
----------------------
The shell implementation this replaces classified a changed file by grepping
**the whole file**:

    grep -qE "(#\\[NoAdminRequired\\]|…|IUserSession|parse_url|…)" "$f"

So a file was "a security change" if the token appeared ANYWHERE in it — in a
method the PR never went near, in an import, in a comment. Two agents hit this
independently on the same day:

  * a PR whose hunks were CSS custom properties and one added chevron column
    was told to add a CSRF test, because the component file also happens to
    render something behind `IUserSession`;
  * a PR that was **provably comment-only** — all 30 changed `lib/` lines
    inside docblocks — was told to co-change tests.

Neither used the opt-out, which is the tell that matters: developers do not
reach for an opt-out when they believe the finding is wrong, they argue with
it or ignore the gate. A gate whose finding cannot be acted on truthfully is
an unclosable gate, and unclosable gates are how a suite loses its readers.

WHAT CHANGED
------------
1. **Classify on the HUNKS, not the file.** Only lines the diff actually adds
   or removes are examined. `git diff -U0` gives exactly those.

2. **A comment line counts only for an ANNOTATION.** In Nextcloud the docblock
   forms `@NoAdminRequired` / `@NoCSRFRequired` / `@PublicPage` ARE the auth
   declaration, so a changed docblock carrying one is a real security change.
   Prose that merely mentions `IUserSession` is not — it is a sentence. The
   discriminator is which token, not whether the line is a comment, because
   collapsing the two is what produced the comment-only false positive.

Path-based classification (`lib/**/Auth/**`, `lib/*Csrf*`, …) is unchanged:
a file under those paths is security code by location, and any change to it
qualifies.

WHAT STILL FIRES
----------------
A hunk that adds, removes or edits an auth annotation, a CSRF exemption, a
session lookup, a signature comparison or a URL parse — with no test file in
the same diff — is still reported, and ``test_check_security_cochange.py``
proves it for every token in the vocabulary.

Usage:
    check_security_cochange.py <base-ref> [app-dir]
    # prints one line per security-touching file with no test co-change
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

# Security code identified by LOCATION. Any change to such a file qualifies —
# there is no "incidental" edit to lib/Service/Auth/TokenVerifier.php.
_PATH_PATTERNS = (
    re.compile(r"^lib/.*Auth[^/]*\.php$"),
    re.compile(r"^lib/.*Csrf[^/]*\.php$"),
    re.compile(r"^lib/.*Session[^/]*\.php$"),
    re.compile(r"^lib/.*/(Auth|Session|Csrf|Rbac|Permission|Authorization)/.*$"),
)

# Tokens that are a security DECLARATION wherever they appear — including in a
# docblock, because in Nextcloud the docblock form IS the declaration.
_ANNOTATION_RE = re.compile(
    r"#\[NoAdminRequired\]"
    r"|#\[AuthorizedAdminSetting\("
    r"|#\[PublicPage\]"
    r"|#\[NoCSRFRequired\]"
    r"|@NoAdminRequired\b"
    r"|@NoCSRFRequired\b"
    r"|@PublicPage\b"
)

# Tokens that are security-relevant only as CODE. In prose they are the name
# of a thing being described, not a change to it.
_CODE_TOKEN_RE = re.compile(
    r"\bparse_url\s*\("
    r"|\bhash_equals\s*\("
    r"|\bpassword_verify\s*\("
    r"|\bIUserSession\b"
    r"|\bgetSecureRandom\s*\("
    r"|\brequesttoken\b"
)

_TEST_PATH_RE = re.compile(
    r"^tests?/|/tests?/|\.spec\.(js|ts|vue|php)$|\.test\.(js|ts|vue)$|Test\.php$"
)

_CANDIDATE_RE = re.compile(r"^(lib/.*\.php|src/.*\.(vue|js|ts))$")

# Comment shapes, per line, after leading whitespace.
_COMMENT_LINE_RE = re.compile(r"^\s*(?:\*|//|/\*|\#(?!\[))")


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH_RE.search(path))


def is_security_path(path: str) -> bool:
    return any(p.match(path) for p in _PATH_PATTERNS)


def line_is_security_relevant(line: str) -> bool:
    """Is this ONE changed line a security change?

    A comment line qualifies only via ``_ANNOTATION_RE``. `#[` is excluded
    from the `#` comment shape so a PHP 8 attribute is never read as a shell
    comment.
    """
    if _ANNOTATION_RE.search(line):
        return True
    if _COMMENT_LINE_RE.match(line):
        return False
    return bool(_CODE_TOKEN_RE.search(line))


def changed_lines(base_ref: str, path: str, cwd: str) -> list[str]:
    """The added/removed lines for *path*, without diff framing.

    `-U0` so no context line is mistaken for a change: context is precisely
    the code the PR did NOT touch, and treating it as touched is the defect
    this function exists to remove.
    """
    proc = subprocess.run(
        ["git", "-c", "safe.directory=*", "diff", "-U0", "--no-color",
         f"{base_ref}...HEAD", "--", path],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
    out = proc.stdout
    if not out.strip():
        proc = subprocess.run(
            ["git", "-c", "safe.directory=*", "diff", "-U0", "--no-color",
             base_ref, "--", path],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
        out = proc.stdout
    lines: list[str] = []
    for raw in out.splitlines():
        if raw.startswith(("+++", "---", "@@", "diff ", "index ",
                           "new file", "deleted file", "similarity ",
                           "rename ")):
            continue
        if raw.startswith(("+", "-")):
            lines.append(raw[1:])
    return lines


def changed_files(base_ref: str, cwd: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-c", "safe.directory=*", "diff", "--name-only",
         f"{base_ref}...HEAD"],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
    out = proc.stdout
    if not out.strip():
        proc = subprocess.run(
            ["git", "-c", "safe.directory=*", "diff", "--name-only", base_ref],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
        out = proc.stdout
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def scan(base_ref: str, cwd: str = ".") -> tuple[list[str], bool]:
    """(security-touching files, whether the diff also touches a test)."""
    files = changed_files(base_ref, cwd)
    has_test = any(is_test_path(f) for f in files)
    security: list[str] = []
    for f in files:
        if is_security_path(f):
            security.append(f)
            continue
        if not _CANDIDATE_RE.match(f):
            continue
        for line in changed_lines(base_ref, f, cwd):
            if line_is_security_relevant(line):
                security.append(f)
                break
    return security, has_test


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_security_cochange.py <base-ref> [app-dir]",
              file=sys.stderr)
        return 2
    base_ref = argv[1]
    cwd = argv[2] if len(argv) > 2 else os.getcwd()
    security, has_test = scan(base_ref, cwd)
    if security and not has_test:
        for f in security:
            print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
