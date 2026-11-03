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

Data-binding blocks are skipped: under `source` and `bind` a widget is told
WHERE its rows come from and WHICH field to read or write, so `label`, `title`
or `description` there name a field path ("label": "title" means "show each
row's title field"), not copy. Reading them as copy made the toggle-table on
shillinq's required-fields admin tab fail on a string "title" that no user
ever sees.

Pure field templates are skipped: a string made only of `{path}` tokens
(`{accountName}`, `{amount|currency} · {dueDate|date}`) is filled from the row
by nextcloud-vue's fillTemplate after translation, and has no word for a
translator to change. A template with words in it ("Invoice date
{invoiceDate|date}") is still copy and still needs its key.

Some keys that collide with a visible field are not copy, and each skip is
narrow: the value must also have the shape of the thing it is.

- Width keys (`columnWidths` and its entries, `width`, `minWidth`,
  `maxWidth`, `paneWidth`) hold CSS lengths. `"columnWidths": {"title":
  "275px"}` sizes the title column. A value under them is skipped only when it
  is a CSS length (`275px`, `40%`, `1.5rem`, `auto`).
- Value maps (`colorMap`, `variantMap`, `iconMap`, `typeMap`) map the app's
  data values to tokens: in `"colorMap": {"task": "purple"}` the key `task` is
  a record type and `purple` a badge variant.
- Field-path blocks name the row field to show: a board `card`, `cardLayout`,
  `expandableRows`, a field-list `row`, and a fields entry with an
  `initialsPath`. A value there is skipped only when it is a field path
  (`title`, `owner.name`); a worded string in the same place is still copy.
- A binding token (`@object.title`, `@me`) is resolved by the renderer. A
  string starting with `@` that has a space in it is still copy.

Only nl is asserted. Dutch is the language this fleet ships to, and demanding
every European locale would make the gate unpassable rather than useful.

FULL-TREE, not diff-scoped: the string is either covered or it is not, and a
diff-scoped version would report clean on every PR that does not happen to
touch the manifest.
"""

import json
import os
import re
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

DATA_BINDING_KEYS = (
    "source",
    "bind",
)

# Keys whose value, or whose entries' values, size a layout box.
WIDTH_KEYS = (
    "columnWidths",
    "width",
    "minWidth",
    "maxWidth",
    "paneWidth",
)

CSS_LENGTH = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)(?:px|%|rem|em|fr|vw|ch)|auto")

# Blocks whose keys are data values and whose values are tokens, never copy.
VALUE_MAP_KEYS = (
    "colorMap",
    "variantMap",
    "iconMap",
    "typeMap",
)

# Blocks in which these visible-looking keys name a row field.
FIELD_PATH_BLOCKS = {
    "cardLayout": ("title", "description", "subtitle"),
    "expandableRows": ("title", "description"),
    "row": ("title", "titleFallback"),
}

# A board's `card` is a field-path block; `nav.card` carries real copy.
BOARD_CARD_PARENTS = ("board",)

FIELD_PATH = re.compile(r"[a-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*")

# The `@` token grammar: `@me`, `@objectId`, `@object.title`, `@today+7d`, `@resolve:x`.
BINDING_TOKEN = re.compile(r"@[A-Za-z][A-Za-z0-9_.:+-]*\??")

# nextcloud-vue's fillTemplate token: `{path}`, `{path|format}`, `{path|format:arg}`.
FIELD_TOKEN = re.compile(r"\{[^{}\s|]+(?:\|[a-z]+(?::[^{}\s]+)?)?\}")


def _is_pure_field_template(value):
    """
    Whether a string is only field tokens plus punctuation and whitespace.

    :param value: the manifest string.
    :return: True when at least one token is present and no letter remains.
    """
    rest, count = FIELD_TOKEN.subn("", value)
    return count > 0 and not any(ch.isalpha() for ch in rest)


def _field_path_keys(node, parent_key, grand_key):
    """
    The keys of a dict that name a row field rather than carry copy.

    :param node: the dict.
    :param parent_key: the key the dict sits under, or None.
    :param grand_key: the key the parent sits under, or None.
    :return: tuple of key names.
    """
    keys = FIELD_PATH_BLOCKS.get(parent_key, ())
    if parent_key == "card" and grand_key in BOARD_CARD_PARENTS:
        keys = keys + ("title",)
    if "initialsPath" in node:
        keys = keys + ("title", "subtitle")
    return keys


def _is_not_copy(value, in_width, is_path_key):
    """
    Whether a visible-field string is a layout value, field path or binding.

    :param value: the string.
    :param in_width: True when it sits under a width key.
    :param is_path_key: True when its key names a row field in this block.
    :return: True to skip the string.
    """
    if value.startswith("{{") or _is_pure_field_template(value):
        return True
    if in_width and CSS_LENGTH.fullmatch(value.strip()):
        return True
    if is_path_key and FIELD_PATH.fullmatch(value):
        return True
    return BINDING_TOKEN.fullmatch(value) is not None


def _walk(node, hits, counter, keys=(None, None)):
    """
    Collect user-visible manifest strings.

    :param node: current dict / list / scalar.
    :param hits: accumulator of strings.
    :param counter: single-element list used as a mutable count.
    :param keys: the key `node` sits under and the one above it.
    :return: None
    """
    if isinstance(node, list):
        for value in node:
            _walk(value, hits, counter, keys)
        return
    if not isinstance(node, dict):
        return
    parent_key, grand_key = keys
    path_keys = _field_path_keys(node, parent_key, grand_key)
    in_width = parent_key in WIDTH_KEYS
    for key, value in node.items():
        if key.startswith("_"):
            continue
        if key in DATA_BINDING_KEYS + VALUE_MAP_KEYS and isinstance(value, dict):
            continue
        if key in VISIBLE_FIELDS and isinstance(value, str) and value.strip():
            if _is_not_copy(value, in_width, key in path_keys):
                continue
            counter[0] += 1
            hits.add(value)
        else:
            _walk(value, hits, counter, (key, parent_key))


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
