#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-48 companion — which frontend call sites send NO CSRF token?

WHY THIS EXISTS
---------------
Gate-48 asks one question of a diff that removes ``@NoCSRFRequired``: *did the
same diff add a CSRF signal under* ``src/``? For a PR whose callers have
**always** sent a token there is no such signal to add, and the gate cannot be
satisfied without a waiver.

Measured on ConductionNL/larpingapp#298, which closes a live CSRF-forgery hole:
``SettingsController::create()`` and ``reimport()`` carried

    * @NoCSRFRequired removed to close the CSRF-forgery surface (closes #206).

at docblock-tag position, where Nextcloud's ``ControllerMethodReflector`` reads
it as the annotation being PRESENT — so the sentence announcing the removal was
what kept CSRF disabled. Removing it is the fix. All three frontend callers
already sent ``requesttoken``, and the shared ``CnAdminSettingsShell`` uses
``@nextcloud/axios``, which injects it. The co-change gate-48 wanted did not
exist to be made, and the cheapest way to go green would have been a cosmetic
edit containing the word ``requesttoken`` — the prose-satisfaction the gate
programme exists to stop.

THE QUESTION THIS ASKS INSTEAD
------------------------------
Not "did the diff change a caller?" but "**is any mutating caller unprotected
right now?**". That is sound in the conservative direction:

* if EVERY mutating call site already carries a CSRF-bearing mechanism, then
  whichever one reaches the endpoint whose annotation was removed is protected,
  and enforcing CSRF cannot break it;
* if ANY mutating call site lacks one, we cannot tell that it is not the
  caller of that endpoint, so the removal still blocks.

opencatalogi#79 — the defect gate-48 was built for, a delete-modal ``fetch()``
with no CSRF header — is still caught: that call site is reported here, so the
gate still fails. A fix that stopped catching it would be a gate switched off.

WHAT COUNTS AS PROTECTED
------------------------
Within the call expression itself: ``requesttoken`` / ``OCS-APIRequest`` (both
case-insensitive, HTTP header names are), or ``getRequestToken``. Or the call
goes through ``@nextcloud/axios``, imported in that file — that client attaches
the current token itself, which is the canonical Nextcloud mechanism.

Usage::

    check_csrf_callers.py <app-dir>

Prints one ``path:line — reason`` per UNPROTECTED mutating call site.
Exits 0 always; the OUTPUT is the answer (#209).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import script_mask  # noqa: E402

SRC_SUFFIXES = ('.vue', '.js', '.ts', '.mjs', '.cjs')
SKIP_DIRS = {'node_modules', 'dist', 'build', 'vendor', '.git', 'coverage'}

# `method: 'POST'` / `method: "put"` / `method:\n 'PATCH'` inside a fetch init.
MUTATING_METHOD = re.compile(
    r"""method\s*:\s*['"`](?P<verb>POST|PUT|PATCH|DELETE)['"`]""",
    re.IGNORECASE,
)
# axios.post( / axios.put( / this.$axios.delete( ...
AXIOS_MUTATING = re.compile(
    r"""\baxios\s*\.\s*(?P<verb>post|put|patch|delete)\s*\(""",
    re.IGNORECASE,
)
FETCH_CALL = re.compile(r"""\bfetch\s*\(""")
# An import of the Nextcloud axios wrapper, under any local alias.
NEXTCLOUD_AXIOS_IMPORT = re.compile(
    r"""from\s+['"]@nextcloud/axios['"]|require\(\s*['"]@nextcloud/axios['"]\s*\)"""
)
CSRF_SIGNAL = re.compile(
    r"""requesttoken|OCS-APIREQUEST|getRequestToken""",
    re.IGNORECASE,
)


def _call_text(text: str, open_paren: int) -> str:
    """Text of the call expression starting at the `(` index, paren-balanced.

    Falls back to the rest of the file when the parentheses never balance, so a
    malformed file reports the call as UNPROTECTED rather than being skipped —
    an unparseable caller is not evidence of a token.
    """
    depth = 0
    for i in range(open_paren, len(text)):
        ch = text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[open_paren:i + 1]
    return text[open_paren:]


def unprotected_call_sites(app_dir: str) -> list[str]:
    """Mutating frontend call sites carrying no CSRF-bearing mechanism."""
    findings: list[str] = []
    src_root = os.path.join(app_dir, 'src')
    if not os.path.isdir(src_root):
        return findings

    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            if not name.endswith(SRC_SUFFIXES):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding='utf-8', errors='replace') as handle:
                    text = handle.read()
            except OSError:
                continue
            rel = os.path.relpath(path, app_dir)

            # A COMMENT IS NOT A CSRF TOKEN (#415).
            # ------------------------------------
            # Every question below used to be asked of the RAW file, and this
            # helper's whole job is to make an AFFIRMATIVE claim — "every
            # mutating call site under src/ already carries a signal" — which
            # the runner then prints as a NOTE and passes on. So prose here
            # does not merely hide a finding; it manufactures a green with a
            # sentence attached saying the code is safe.
            #
            # Measured on this helper, one fixture, one variable:
            #
            #   fetch(url, { method: 'DELETE', headers: {} })
            #     -> reported UNPROTECTED, gate-48 FAIL          (correct)
            #   the same call with
            #     `// TODO: add the requesttoken header here. Not done yet.`
            #     INSIDE the init object
            #     -> reported protected, gate-48 PASS + the NOTE <- the defect
            #
            # `NEXTCLOUD_AXIOS_IMPORT` was read the same way, so a
            # COMMENTED-OUT import silenced every axios.post in the file at
            # once — one dead line, whole-file amnesty.
            #
            # STRING CONTENTS ARE KEPT, deliberately. `script_mask` blanks
            # comments and leaves literals intact, and that is required
            # rather than incidental: `'OCS-APIRequest': 'true'` is a header
            # name that IS a string, and `method: 'DELETE'` is how a mutating
            # call is recognised at all. Blanking literals here would delete
            # the evidence in both directions at once — the classic
            # over-applied fix that turns a repaired gate into a dead one.
            #
            # Offsets are preserved by the mask, so the reported line numbers
            # still address the original file.
            text = script_mask(text, path)
            uses_nc_axios = bool(NEXTCLOUD_AXIOS_IMPORT.search(text))

            # 1. axios.<verb>(...) — protected iff the file imports @nextcloud/axios.
            for m in AXIOS_MUTATING.finditer(text):
                if uses_nc_axios:
                    continue
                call = _call_text(text, m.end() - 1)
                if CSRF_SIGNAL.search(call):
                    continue
                line = text.count('\n', 0, m.start()) + 1
                findings.append(
                    f"{rel}:{line} — axios.{m.group('verb').lower()}() with no CSRF "
                    f"signal and no @nextcloud/axios import"
                )

            # 2. fetch(...) — mutating iff its init object names a mutating verb.
            for m in FETCH_CALL.finditer(text):
                call = _call_text(text, m.end() - 1)
                verb = MUTATING_METHOD.search(call)
                if verb is None:
                    continue
                if CSRF_SIGNAL.search(call):
                    continue
                line = text.count('\n', 0, m.start()) + 1
                findings.append(
                    f"{rel}:{line} — fetch() {verb.group('verb').upper()} with no "
                    f"CSRF signal"
                )
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_csrf_callers.py <app-dir>", file=sys.stderr)
        return 2
    for finding in unprotected_call_sites(argv[1]):
        print(finding)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
