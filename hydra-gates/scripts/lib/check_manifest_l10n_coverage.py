#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""
Gate 99 — manifest-l10n-coverage.

Every user-visible string the manifest declares must have a key in the app's
Dutch catalogue, or a Dutch user reads English.

WHY THIS IS NOT ALREADY COVERED.

An app's l10n extractor scans .vue/.js/.ts for `t('<app>', '...')` calls. The
manifest is not source it reads; it is DATA THE RENDERER WALKS. CnAppNav
translates `menu[].label`, CnPageHeader a page's `title` and `description`,
CnWalkthrough a step's `title` / `body` / `task` — each through the app's own
translate function, each looking up a key the extractor never saw. A missing
key falls back to the English source, so the page renders English and nothing
reports a problem.

`check:l10n-js` does NOT catch this and cannot. That check compares
l10n/<locale>.json against the generated l10n/<locale>.js, and a string absent
from BOTH is perfectly in sync. Measured on buildiq 2026-08-27: nl.json and
nl.js at 1,045 keys each, both missing `Flow`, check green.

WHAT IT COST, MEASURED.

A fleet sweep translated ~3,900 manifest strings across 17 apps and left every
one at zero missing. Within hours, two apps had regressed the ordinary way —
not old debt, just the next PR that added a manifest string:

    keepiq  #448  "Registered by", "Requested"
    buildiq #485  "Flow"

Both merged green. Only humaniq ran a check that would have failed, and only
because someone had written a bespoke one for that app.

WHAT IS CHECKED.

Every string in src/manifest.json and src/manifest.d/*.json under the fields a
reader actually sees:

    title, body, task, label, description,
    emptyText, placeholder, subtitle, helpText

must appear as a key in l10n/nl.json. The fragments matter: they are merged
into the manifest at runtime via require.context, so reading only
src/manifest.json is blind to them. shillinq has 87.

WHAT IS NOT CHECKED.

Interpolation placeholders (`{{title}}`) are skipped — they are substituted at
render time and translating them breaks the template. Underscore-prefixed
blocks are skipped: `_meta` is per-fragment provenance (spdx, change, adr),
never rendered.

Only nl is asserted. Dutch is the language this fleet ships to, and demanding
every European locale would make the gate unpassable rather than useful.

FULL-TREE, not diff-scoped: the string is either covered or it is not, and a
diff-scoped version would report clean on every PR that does not happen to
touch the manifest.
"""

import json
import os
import sys

VISIBLE_FIELDS = (
    "title",
    "body",
    "task",
    "label",
    "description",
    "emptyText",
    "placeholder",
    "subtitle",
    "helpText",
)


def _walk(node, hits, counter):
    """
    Collect user-visible manifest strings.

    :param node: current dict / list / scalar.
    :param hits: accumulator of strings.
    :param counter: single-element list used as a mutable count.
    :return: None
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_"):
                continue
            if key in VISIBLE_FIELDS and isinstance(value, str) and value.strip():
                # `{{name}}` is substituted by the renderer, not read by a human.
                if value.startswith("{{"):
                    continue
                counter[0] += 1
                hits.add(value)
            else:
                _walk(value, hits, counter)
    elif isinstance(node, list):
        for value in node:
            _walk(value, hits, counter)


def _manifest_files(root):
    """
    The manifest and every runtime-merged fragment.

    :param root: repository root.
    :return: list of paths in load order.
    """
    found = []
    main = os.path.join(root, "src", "manifest.json")
    if os.path.isfile(main):
        found.append(main)
    frag_dir = os.path.join(root, "src", "manifest.d")
    if os.path.isdir(frag_dir):
        for name in sorted(os.listdir(frag_dir)):
            if name.endswith(".json"):
                found.append(os.path.join(frag_dir, name))
    return found


def main(argv):
    """
    Entry point.

    :param argv: argv, where argv[1] is the repository root (default ".").
    :return: 0 covered, 1 uncovered strings, 4 nothing to check.
    """
    root = argv[1] if len(argv) > 1 else "."
    files = _manifest_files(root)
    catalogue = os.path.join(root, "l10n", "nl.json")

    if not files or not os.path.isfile(catalogue):
        print("checked 0 manifest string(s)")
        return 4

    try:
        with open(catalogue, "r", encoding="utf-8") as handle:
            keys = set((json.load(handle).get("translations") or {}).keys())
    except (OSError, ValueError) as exc:
        # An unreadable catalogue is not a coverage verdict. Say so.
        print("SKIP l10n/nl.json: unreadable (%s)" % exc)
        print("checked 0 manifest string(s)")
        return 4

    strings = set()
    counter = [0]
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            # A manifest that will not parse is gate-manifest-validation's
            # finding, not this gate's.
            print("SKIP %s: unreadable (%s)" % (os.path.relpath(path, root), exc))
            continue
        _walk(data, strings, counter)

    uncovered = sorted(s for s in strings if s not in keys)
    for value in uncovered:
        excerpt = value if len(value) <= 120 else value[:117] + "..."
        print("FAIL no nl.json key: %s" % excerpt)

    if uncovered:
        print("")
        print("A manifest string with no catalogue key renders its ENGLISH source")
        print("to a Dutch user, and nothing else reports it: check:l10n-js compares")
        print("nl.json to nl.js, and a string absent from both is in sync.")
        print("Add the key to l10n/nl.json, then run `npm run l10n:build`.")

    print("checked %d manifest string(s)" % counter[0])
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
