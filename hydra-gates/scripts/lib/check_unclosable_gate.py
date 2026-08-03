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
Suppress a deliberate case with a comment containing:
    unclosable-gate exclude <reason>
on the reading line or the line above it.

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""

import os
import re
import sys

# Config accessors. NC exposes both the modern IAppConfig typed getters and the
# legacy IConfig app-value pair; apps in this fleet use both.
GETTERS = ['getValueString', 'getValueBool', 'getValueInt', 'getValueFloat', 'getValueArray', 'getAppValue']
SETTERS = ['setValueString', 'setValueBool', 'setValueInt', 'setValueFloat', 'setValueArray', 'setAppValue']

# Only keys shaped like a "have we done this yet" marker. A general config key
# that is read and never written is normal — it is a setting with a default.
GATE_SHAPE = re.compile(r'(version|bootstrapped|provisioned|initialized|imported|seeded|migrated|installed_at)')

# Keys Nextcloud itself maintains; apps legitimately only read these.
NC_MANAGED = {'installed_version', 'app_version', 'core_version', 'types', 'enabled'}

KEY = re.compile(r"'([a-z][a-z0-9_]{3,})'")


def call_args(src: str, fname: str):
    """Yield the argument text of every `fname(...)` call in src."""
    for m in re.finditer(re.escape(fname) + r'\s*\(', src):
        depth = 0
        i = m.end() - 1
        while i < len(src):
            if src[i] == '(':
                depth += 1
            elif src[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield src[m.end():i]


def suppressed(src: str, key: str) -> bool:
    """True when a suppression comment names this key's gate."""
    for line_no, line in enumerate(src.split('\n')):
        if 'unclosable-gate exclude' in line:
            window = '\n'.join(src.split('\n')[max(0, line_no - 1):line_no + 3])
            if f"'{key}'" in window:
                return True
    return False


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

    blob = '\n'.join(sources.values())
    read, written = set(), set()
    for fname in GETTERS:
        for arg in call_args(blob, fname):
            read |= set(KEY.findall(arg))
    for fname in SETTERS:
        for arg in call_args(blob, fname):
            written |= set(KEY.findall(arg))

    out = []
    for key in sorted(read - written):
        if key in NC_MANAGED or not GATE_SHAPE.search(key):
            continue
        if suppressed(blob, key):
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
