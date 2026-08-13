#!/usr/bin/env python3
"""Detect version/state gates that can never close (ADR-076 rule 3).

An app that does expensive setup — importing its OpenRegister configuration,
bootstrapping registers, seeding schemas — normally guards it with a config
key: read the stored version, compare, skip if already done.

The guard only works if something WRITES the key. A key that is only ever read
sits at its default forever, the comparison never short-circuits, and the work
it guards runs on every single call. Because these guards live in
`Application::boot()` or a service reached from it, "every call" means every
request to the whole Nextcloud instance.

Observed 2026-07-29 on docudesk: `SettingsInitializer::initialize()` read
`configuration_version` to decide whether its OpenRegister configuration was
already imported. Nothing wrote it — not the app, not OpenRegister — so
`importFromApp()` ran on every request, costing 354ms -> 255ms median once the
key was set (~28% of every request) and 14 schema lookups per object create.

This is a static fact and therefore cheap to check: a read with no matching
write, in the same app.

Exit 0 when clean, 1 when a gate cannot close.
Suppress a deliberate case with a comment that NAMES THE KEY, in quotes, on
the same line as the marker:
    // unclosable-gate exclude 'configuration_version' is written by the
    //   OpenRegister importer, not by this app

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import php_mask  # noqa: E402

# Config accessors. NC exposes both the modern IAppConfig typed getters and the
# legacy IConfig app-value pair; apps in this fleet use both.
GETTERS = ['getValueString', 'getValueBool', 'getValueInt', 'getValueFloat', 'getValueArray', 'getAppValue']
SETTERS = ['setValueString', 'setValueBool', 'setValueInt', 'setValueFloat', 'setValueArray', 'setAppValue']

# Only keys shaped like a "have we done this yet" marker. A general config key
# that is read and never written is normal — it is a setting with a default.
GATE_SHAPE = re.compile(r'(version|bootstrapped|provisioned|initialized|imported|seeded|migrated|installed_at)')

# Keys Nextcloud itself maintains; apps legitimately only read these.
NC_MANAGED = {'installed_version', 'app_version', 'core_version', 'types', 'enabled'}

# THE KEY, IN EVERY WAY PHP LETS YOU SPELL IT (.github#276).
#
# This pattern was `r"'([a-z][a-z0-9_]{3,})'"` — a SINGLE-quoted literal only.
# PHP treats `'k'` and `"k"` identically, so the gate was wrong in BOTH
# directions at once, which is #184's signature:
#
#   false GREEN     read "k" / write "k"   — neither side is seen, so the key
#                   never enters `read`, and an unclosable gate reports OK.
#   false POSITIVE  read 'k' / write "k"   — the read is seen and the write is
#                   not, so code that closes its gate correctly is reported as
#                   never closing it. Measured: the only remedy available to
#                   the app is to change its quote style.
#
# Both were reproduced against docudesk before this line changed.
KEY = re.compile(r"""['"]([a-z][a-z0-9_]{3,})['"]""")

# `private const CONFIG_KEY = 'configuration_version';` then
# `getValueString($app, self::CONFIG_KEY, '')`.
#
# A constant is the IDIOMATIC way to write a key used in two places — which is
# precisely the shape a closable gate has, since the read and the write must
# agree. Reading only quoted literals made the constant form invisible on BOTH
# sides, so the most correctly-written apps were the ones this gate could say
# nothing about. Resolving the constant to its literal keeps read and write
# symmetric: if both spell it `self::CONFIG_KEY` they cancel exactly as they
# would if both spelled it `'configuration_version'`.
CONST_DEF = re.compile(
    r"""const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['"]([a-z][a-z0-9_]{3,})['"]"""
)
CONST_REF = re.compile(r"""(?:self|static|parent|[A-Za-z_][A-Za-z0-9_\\]*)\s*::\s*([A-Z][A-Z0-9_]*)\b""")


def call_args(blob: str, anchor: str, fname: str):
    """Yield the argument text of every `fname(...)` CALL SITE.

    TWO SOURCES, ONE COORDINATE SYSTEM (#424)
    -----------------------------------------
    This gate's evidence IS a string literal — the config key — so the mask
    cannot blank string contents. But the CALL is not a string, and scanning
    the same text for both questions meant a sentence closed the gate:

        $hint = "call setValueString('fixapp','configuration_version','3') next";

    read as a write of `configuration_version`. A gate whose entire subject is
    "this guard never closes" was closed by a comment saying someone would
    close it later — the same shape as the commented-out setter this gate
    already masks for, one quote character away.

    So: the call site is located in *anchor* (`php_mask(..., blank_strings=
    True)`, where that sentence is blank and its parentheses cannot be walked)
    and the argument text is read from *blob* (string contents intact) at the
    SAME offsets, which both masks preserve. This is the anchoring contract
    `source_scope.js_exec_mask` documents.
    """
    for m in re.finditer(re.escape(fname) + r'\s*\(', anchor):
        depth = 0
        i = m.end() - 1
        while i < len(anchor):
            if anchor[i] == '(':
                depth += 1
            elif anchor[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield blob[m.end():i]


def suppressed(src: str, key: str) -> bool:
    """True when a suppression comment names this key's gate.

    Reads RAW source on purpose — the marker is a comment, which is exactly
    what the mask in scan_app() removes.

    THE KEY MUST BE QUOTED ON THE MARKER'S OWN LINE (.github#276), in either
    quote style.

    It used to be looked for in a FOUR-LINE WINDOW around the marker — and the
    read this suppression is attached to lives inside that window, carrying its
    own key literal. So a suppression naming `'some_other_version'` matched
    `'configuration_version'` two lines below it: the marker suppressed
    whatever happened to be near it rather than what it named. That is the
    same shape as gate-64's `SUPPRESS` bug, where `\\s` let a bare annotation
    swallow the next line of source as its "reason".

    Nothing in the fleet uses this marker yet (measured: 0 files), so tightening
    it costs nothing and closes the hole before the first user arrives.
    """
    for line in src.split('\n'):
        if 'unclosable-gate exclude' not in line:
            continue
        if f"'{key}'" in line or f'"{key}"' in line:
            return True
    return False


def keys_in(arg: str, constants: dict) -> set:
    """Every config key named by *arg*, literal or via a resolved constant."""
    found = set(KEY.findall(arg))
    for name in CONST_REF.findall(arg):
        value = constants.get(name)
        if value is not None:
            found.add(value)
    return found


def scan_app(app_dir: str):
    """Return [(key, read_count)] for gates in app_dir that can never close."""
    sources = {}
    for root, _dirs, files in os.walk(os.path.join(app_dir, 'lib')):
        for name in files:
            if not name.endswith('.php'):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding='utf-8', errors='replace') as handle:
                    sources[path] = handle.read()
            except OSError:
                continue

    if not sources:
        return []

    raw = '\n'.join(sources.values())

    # A COMMENT IS NOT A WRITE (.github#276, the #184 shape).
    #
    # This scan ran on raw source, so a commented-out or not-yet-written setter
    #
    #     // TODO: $this->cfg->setValueString('app', 'configuration_version', $v);
    #
    # put the key into `written` and CLOSED the finding. That is the false
    # GREEN — and it is the single most likely comment to sit beside a key
    # nobody writes, because it is what someone types when they notice the gap
    # and defer it. A gate whose whole subject is "this guard never closes" was
    # itself closed by a comment saying the guard would be closed later.
    #
    # `php_mask` blanks comment REGIONS and preserves offsets and newlines;
    # string CONTENTS are kept, because the key literal is the evidence.
    #
    # The SUPPRESSION is the one thing that must keep reading raw text — it is
    # authored as a comment, which is exactly what this mask removes.
    blob = php_mask(raw)
    # The CALL-SITE scope: same text, same offsets, string CONTENTS blanked.
    # See call_args() for why there have to be two of these.
    anchor = php_mask(raw, blank_strings=True)

    # A `const` written inside a string is not a declaration either, and the
    # `const` keyword surviving in the anchor is the cheap proof that this one
    # is real code.
    constants = {
        m.group(1): m.group(2)
        for m in CONST_DEF.finditer(blob)
        if anchor.startswith('const', m.start())
    }

    read, written = set(), set()
    for fname in GETTERS:
        for arg in call_args(blob, anchor, fname):
            read |= keys_in(arg, constants)
    for fname in SETTERS:
        for arg in call_args(blob, anchor, fname):
            written |= keys_in(arg, constants)

    out = []
    for key in sorted(read - written):
        if key in NC_MANAGED or not GATE_SHAPE.search(key):
            continue
        if suppressed(raw, key):
            continue
        out.append((key, sum(1 for _ in re.finditer(re.escape(key), blob))))
    return out


def main() -> int:
    targets = sys.argv[1:] or ['.']
    failures = 0
    for target in targets:
        app = os.path.basename(os.path.abspath(target))
        for key, refs in scan_app(target):
            print(
                f"{app}: config key '{key}' is READ but never WRITTEN "
                f"({refs} reference(s)) — the setup it guards runs on every call. "
                f"Persist it next to the work it guards (ADR-076 rule 3), or add "
                f"'unclosable-gate exclude <reason>'."
            )
            failures += 1

    if failures:
        print(f"\n{failures} unclosable gate(s).")
        return 1

    print('unclosable-gate: OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
