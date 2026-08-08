#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
r"""Gate-44 autocomplete-attr — an `<input>` whose name/id/model says it
collects a well-known personal detail must declare `autocomplete=`, so browser
autofill and password managers can fill it. WCAG 2.2 AA SC 1.3.5 (Identify
Input Purpose).

WHY THIS IS A FILE AND NOT A HEREDOC
------------------------------------
gate-44 ran an inline `python3 - "$vue" <<'PYAC' >> log 2>/dev/null` once per
file and never read the exit status. Measured 2026-08-08 on opencatalogi with
a `python3` that exits 1 on every invocation, gates 40, 42 and 44 all reported
PASS — gate-40 over the 13 real findings it had reported one run earlier —
while every a11y gate whose checker lived in a file reported SKIPPED (wiring).
An empty log is not a clean sheet (ConductionNL/.github#147 / #249). Moving
the logic here buys the return-code guard the runner already applies
everywhere else in the family.

A SINGLE-QUOTED ATTRIBUTE IS THE SAME ATTRIBUTE
-----------------------------------------------
The previous regex read values out of DOUBLE QUOTES ONLY:

    re.search(r'(^|\s)(?:name|id|:name|:id|v-model)\s*=\s*"([^"]+)"', attrs)

so `<input id='b44-tel' type='text' name='telephone'>` — identical rendered
DOM, identical defect — was invisible. Proven by control fixture: the
double-quoted form fired in both a .vue app and a PHP-template app, the
single-quoted form reported PASS in both. Zero occurrences in the fleet
today, which is exactly why it could sit there indefinitely.

`[^>]*` went for the same reason it went from gate-39: a `>` inside an
attribute value is not the end of the tag (#259, #198, #236).

WHAT IS NOT FLAGGED
-------------------
  * `type=` in hidden/submit/button/reset/image/file/checkbox/radio/color/range
    — nothing to autofill
  * anything already carrying `autocomplete=`, literal or bound
  * markup inside comments or `<script>`/`<style>` blocks — an `<input>` in a
    JS string is not a control. The heredoc this replaces scanned the raw
    file, so a commented-out example counted; that is the gate-64 defect
    (#184) and the one gate-38 (#247) and gate-41 (#266) each shipped a fix
    for.

Usage:
    check_autocomplete.py <file>...     # findings on stdout, exit 0
"""
from __future__ import annotations

import re
import sys

COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
BLOCK = re.compile(r'<(script|style)\b[^>]*>.*?</\1\s*>', re.DOTALL | re.IGNORECASE)

# Quote-aware attribute run: whole quoted values are consumed, so a `>` inside
# one cannot terminate the tag early.
INPUT = re.compile(r'<input\b((?:"[^"]*"|\'[^\']*\'|[^>"\'])*?)/?>',
                   re.IGNORECASE | re.DOTALL)

SKIP_TYPE = re.compile(
    r'(?:^|\s)type\s*=\s*["\']'
    r'(?:hidden|submit|button|reset|image|file|checkbox|radio|color|range)["\']',
    re.IGNORECASE)
HAS_AUTOCOMPLETE = re.compile(r'(?:^|\s)(?::|v-bind:)?autocomplete\s*=')
# Both quote styles. The name is captured so the finding can name it.
NAME_LIKE = re.compile(
    r'(?:^|\s)(?::|v-bind:)?(?:name|id|v-model)\s*=\s*'
    r'(?:"([^"]+)"|\'([^\']+)\')')
SEMANTIC = re.compile(
    r'(email|tel(?:ephone)?|phone|firstname|lastname|fullname|address|street'
    r'|city|postal|postcode|zip|country|password|username|organization'
    r'|birthday|dob)', re.IGNORECASE)


def scan_source(fname: str, src: str) -> list[str]:
    txt = BLOCK.sub(' ', COMMENT.sub(' ', src)).replace('\n', ' ')
    findings: list[str] = []
    for m in INPUT.finditer(txt):
        attrs = m.group(1) or ''
        if SKIP_TYPE.search(attrs):
            continue
        if HAS_AUTOCOMPLETE.search(attrs):
            continue
        # EVERY name-like attribute, not just the first one found. The regex
        # this replaces used `re.search`, so the FIRST of name/id/v-model
        # decided the verdict alone:
        #
        #     <input id="e" type="text" name="email">
        #
        # matched `id="e"`, found no semantic noun in `e`, and stopped — while
        # `name="email"` sat one attribute to the right. Caught by
        # test_a_semantic_input_without_autocomplete, which is the plainest
        # textbook case this gate has.
        for name_m in NAME_LIKE.finditer(attrs):
            val = name_m.group(1) if name_m.group(1) is not None else name_m.group(2)
            if SEMANTIC.search(val):
                findings.append(
                    f'{fname}: <input name/id="{val}" ...> '
                    f'rule=semantic-input-without-autocomplete')
                break
    return findings


def scan_files(files: list[str]) -> list[str]:
    out: list[str] = []
    for fname in files:
        try:
            with open(fname, encoding='utf-8', errors='replace') as f:
                src = f.read()
        except OSError:
            continue
        out.extend(scan_source(fname, src))
    return out


def main(argv: list[str]) -> int:
    for line in scan_files(argv[1:]):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
