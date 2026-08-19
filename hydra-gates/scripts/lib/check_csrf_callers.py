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

# 🔴 A QUOTED LITERAL IS NOT THE ONLY WAY TO SPELL A VERB — AND THE OTHER WAYS
#    WERE INVISIBLE, WHICH MEANS THEY WERE COUNTED AS SAFE.
#
# `MUTATING_METHOD` requires the verb to be a quoted literal sitting directly
# after `method:`. The fleet's create-or-update handlers do not write it that
# way; they compute it:
#
#     const method = isNew ? 'POST' : 'PUT'
#     await fetch(url, { method, headers, body })
#
#     fetch(url, { method: this.editing ? 'PUT' : 'POST', ... })
#
# Neither matches, so `verb is None`, so the call is skipped — and skipped is
# indistinguishable from protected in this helper's output. MEASURED on
# zaakafhandelapp: **15 call sites reported, 27 actually unprotected.** The
# twelve invisible ones are exactly the create-or-update handlers, which are
# the most CSRF-relevant calls in the app.
#
# THE RULE IS FAIL-CLOSED, and that is the whole design: a `method` key whose
# value this helper cannot PROVE is a safe verb counts as mutating. Proof is
# narrow on purpose — a quoted `GET`/`HEAD`/`OPTIONS`, or an identifier whose
# every assignment in the file resolves to safe verbs. Anything else (a
# ternary, a template literal, a call, a shorthand `{ method }` whose binding
# cannot be found) is treated as mutating. An unreadable value is not a pass.
METHOD_KEY_VALUE = re.compile(r"""(?<![\w$.])method\s*:\s*(?P<val>[^,}\n]+)""")
# ES6 shorthand: `{ method }` / `{ ..., method, ... }` — the value is the
# binding of the same name, resolved below.
METHOD_SHORTHAND = re.compile(r"""[{,]\s*method\s*(?=[,}])""")
SAFE_VERB_LITERAL = re.compile(r"""^\s*['"`](?:GET|HEAD|OPTIONS)['"`]\s*$""",
                               re.IGNORECASE)
MUTATING_VERB_ANYWHERE = re.compile(r"""['"`](?:POST|PUT|PATCH|DELETE)['"`]""",
                                    re.IGNORECASE)
BARE_IDENTIFIER = re.compile(r"""^\s*(?P<name>[A-Za-z_$][\w$]*)\s*$""")


def _binding_values(text: str, name: str, before: int = None) -> list:
    """Right-hand sides assigned to *name*, NEAREST PRECEDING BINDING WINS.

    ⚠️ A WHOLE-FILE SEARCH IS THE WRONG INSTRUMENT HERE, and its error is a
    FALSE POSITIVE — which in a security gate is the error that gets the gate
    ignored. A store module routinely holds

        const method = 'GET'              // in one action
        const method = isNew ? 'POST' : 'PUT'   // in another

    and answering "can `method` ever be mutating" over the whole file reports
    the GET caller too. So the resolution is positional: the last binding
    ESTABLISHED BEFORE the call site, which is what a reader resolves. When
    *before* is given and no binding precedes it, the list is empty and the
    caller fails closed.
    """
    pattern = re.compile(
        r"""(?:(?:const|let|var)\s+)?(?<![\w$.])"""
        + re.escape(name) + r"""\s*=\s*([^;\n]{1,200})""")
    hits = [m for m in pattern.finditer(text)
            if before is None or m.start() < before]
    if before is None:
        return [m.group(1) for m in hits]
    return [hits[-1].group(1)] if hits else []


def _method_value_is_mutating(value: str, text: str, depth: int = 0,
                              before: int = None):
    """Ternary verdict for one `method` value: True / False / None.

    ``True``  — it is, or may be, a mutating verb.
    ``False`` — proven to be a safe verb.
    ``None``  — there is no `method` key at all (the caller decides).
    """
    value = value.strip()
    if value == "":
        return True
    if SAFE_VERB_LITERAL.match(value):
        return False
    if MUTATING_VERB_ANYWHERE.search(value):
        return True
    ident = BARE_IDENTIFIER.match(value)
    if ident is not None and depth < 2:
        bindings = _binding_values(text, ident.group('name'), before)
        if not bindings:
            return True          # unresolvable binding — fail closed
        return any(
            _method_value_is_mutating(b, text, depth + 1, before) is not False
            for b in bindings
        )
    # A call, a member expression, a template literal, a computed value: this
    # helper cannot show it is safe, so it is not.
    return True


def _fetch_is_mutating(call: str, text: str, at: int = None):
    """``(is_mutating, label)`` for one `fetch(...)` call expression.

    *at* is the offset of the call inside *text*, used to resolve an identifier
    to the binding that precedes it rather than to any binding in the file.
    """
    verdict = None
    label = "method"
    for m in METHOD_KEY_VALUE.finditer(call):
        value = m.group('val')
        if _method_value_is_mutating(value, text, before=at):
            return True, value.strip()[:40]
        verdict = False
        label = value.strip()[:40]
    if verdict is None and METHOD_SHORTHAND.search(call):
        # `{ method }` — resolve the binding of that name.
        if _method_value_is_mutating("method", text, before=at):
            return True, "shorthand { method }"
        return False, "shorthand { method }"
    return (False, label) if verdict is False else (None, label)
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


# ---------------------------------------------------------------------------
# ⚠️ WHAT IS DELIBERATELY *NOT* HERE: ENDPOINT SCOPING
# ---------------------------------------------------------------------------
#
# gate-48 blocks when an annotation was removed AND any unprotected mutating
# caller exists ANYWHERE under `src/` — without relating the two. That is a
# real defect (zaakafhandelapp#371 was blocked by 15 call sites, byte-identical
# on `origin/development`, none of them targeting `api/dashboard`), and the
# obvious repair is to correlate the call site's URL with the routes of the
# controller that lost its annotation.
#
# IT WAS BUILT AND THEN WITHDRAWN, BECAUSE ITS OWN CONTROL FAILED. Measured on
# zaakafhandelapp at `d7cea2a` with routes read from `appinfo/routes.php`:
#
#     repo-wide                       27
#     scoped to DashboardController   11
#     scoped to ZakenController       11   <- IDENTICAL SET
#
# An identical count across two unrelated controllers is a property of the
# instrument, not of the diffs. The filter was dominated by the unresolvable
# residue, and among the 16 it ruled out for ZakenController was
# `src/store/modules/zaken.ts:128 — fetch() DELETE` — a zaken caller, dropped
# from the zaken scope, because the route table says `/api/zaken` while the
# store calls `/api/zrc/zaken`. A correlation that drops a true finding is
# worse than the over-blocking it replaces.
#
# `check_csrf_removal.py`'s post-image test (the deleted-vs-stripped fix)
# already clears #371 honestly on its own — measured 5 removals -> 0 — so the
# outcome this scoping was wanted for is delivered without it. Recorded here
# rather than shipped, so the next attempt starts from the measurement.
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

            # 2. fetch(...) — mutating unless its `method` is PROVEN to be a
            #    safe verb. A `method` key whose value cannot be resolved to
            #    GET/HEAD/OPTIONS counts as mutating; see the commentary above
            #    `METHOD_KEY_VALUE`. No `method` key at all is still a GET and
            #    is still skipped.
            for m in FETCH_CALL.finditer(text):
                call = _call_text(text, m.end() - 1)
                is_mutating, label = _fetch_is_mutating(call, text, m.start())
                if is_mutating is not True:
                    continue
                if CSRF_SIGNAL.search(call):
                    continue
                verb = MUTATING_METHOD.search(call)
                shown = verb.group('verb').upper() if verb else label
                line = text.count('\n', 0, m.start()) + 1
                findings.append(
                    f"{rel}:{line} — fetch() {shown} with no CSRF signal"
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
