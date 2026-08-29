#!/usr/bin/env python3
"""Detect locale bundles that are a byte-for-byte copy of another locale.

WHY THIS EXISTS.

On 2026-06-14 a single commit titled "i18n: add 35 European locale translations
+ European parity gate" landed in five fleet apps. It added 35 locales at once,
and it populated whole language families by duplication rather than translation.
Measured 2026-08-29 across the fleet:

    decidiq, learniq, buildiq, shillinq   28 language pairs each, 100% identical
    keepiq                                the same shape at 78-89%

    be = ru = uk                          every translated value identical
    bs = cs = hr = mk = sk = sl = sr      seven languages, one text
    ca = es, da = sv, de = lb, it = rm    every translated value identical

A Czech user of decidiq is served Bosnian. A Ukrainian is served Russian. A
Swede is served Danish.

WHY NOTHING CAUGHT IT. Every existing l10n check passes on these bundles. Key
parity passes — the keys are all there. The empty-value check passes — nothing
is blank. The cognate rule passes — no value equals its English source. A bundle
that is a perfect copy of a DIFFERENT language looks, to every check we had,
exactly like a finished translation. That is the shape of a defect that survives
for months: not a failure, an absence of any question that would have found it.

WHY THE THRESHOLD IS "ALL", NOT A PERCENTAGE. Closely related languages
legitimately share a great deal — bs and hr sit around 96% in a genuinely
translated bundle, and a percentage gate would either flag that (wrong) or be
set so high it catches nothing. But two independent translations of a thousand
strings are never identical in EVERY one. Exact equality across the whole
translated set is not similarity; it is a copy. So the gate fires only when
every translated value in one locale matches another, over a floor of
MIN_VALUES so a nearly-empty bundle cannot trip it.

Compares only values that are TRANSLATED — present in both, non-empty, and
different from the English source. Values equal to English are excluded because
two locales both leaving "CSV" alone is a cognate, not a copy.

Usage:
    python3 check_locale_duplication.py <app-dir>

Exit codes:
    0  no locale is a copy of another
    1  at least one pair is a byte-for-byte copy
    4  no l10n directory, or fewer than two comparable locales (nothing to judge)
"""

import json
import os
import re
import sys

# A pair must share at least this many translated values before equality is
# evidence of anything. Below it, two small bundles can coincide honestly.
MIN_VALUES = 100

REGISTER_RE = re.compile(
    r'OC\.L10N\.register\(\s*"[^"]+"\s*,\s*(\{.*\})\s*,\s*"nplurals', re.S
)


def load_js(path):
    """Parse an OC.L10N.register bundle into {key: value}."""
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    match = REGISTER_RE.search(src)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def translated_pairs(bundle, english):
    """The subset a copy would reproduce: present, non-empty, not the source."""
    out = {}
    for key, value in bundle.items():
        if not isinstance(value, str) or not value:
            continue
        if english.get(key) == value:
            continue
        out[key] = value
    return out


def main():
    app = sys.argv[1] if len(sys.argv) > 1 else "."
    l10n = os.path.join(app, "l10n")
    if not os.path.isdir(l10n):
        print("no l10n/ directory — nothing to judge.")
        return 4

    bundles = {}
    for name in sorted(os.listdir(l10n)):
        if not name.endswith(".js"):
            continue
        loc = name[:-3]
        parsed = load_js(os.path.join(l10n, name))
        if parsed is not None:
            bundles[loc] = parsed

    english = bundles.get("en", {})
    locales = [loc for loc in bundles if loc != "en"]
    if len(locales) < 2:
        print(f"only {len(locales)} comparable locale(s) — nothing to judge.")
        return 4

    trans = {loc: translated_pairs(bundles[loc], english) for loc in locales}

    findings = []
    for i, a in enumerate(locales):
        for b in locales[i + 1:]:
            shared = [k for k in trans[a] if k in trans[b]]
            if len(shared) < MIN_VALUES:
                continue
            same = sum(1 for k in shared if trans[a][k] == trans[b][k])
            if same == len(shared):
                findings.append((a, b, same))

    print(f"checked {len(locales)} locale(s) for cross-locale duplication")

    if not findings:
        print("no locale is a byte-for-byte copy of another.")
        return 0

    print("")
    print(f"FAIL — {len(findings)} locale pair(s) are byte-for-byte copies:")
    for a, b, n in findings:
        print(f"  {a} and {b}: all {n} translated values identical")
    print("")
    print(
        "Two independent translations of this many strings are never identical in "
        "every one. A pair listed here means one locale's file was copied into the "
        "other, so users who chose one language are served the other."
    )
    print(
        "Fix by translating the copied locale, not by deleting keys: the parity gate "
        "holds every locale to key-for-key completeness and refuses empty values, so "
        "a blanked bundle fails a different check rather than telling the truth."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
