#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""
Gate 96 — manifest-copy-style.

The Conduction voice bans em-dashes. `writing/references/voice.md` §8 says it
plainly: "Em-dashes (—) and double-dashes (--) are AI tells. Replace with a
period, a comma, or a colon." The `writing` skill's REVIEW mode even uses a
walkthrough `steps[0].body` em-dash as its worked example.

The rule was already right. On 2026-08-26 a sweep of shipped walkthrough copy
found TWENTY-FIVE em-dashes across NINE apps anyway:

    opencatalogi 6 · pipelinq 5 · docudesk 3 · larpingapp 3
    decidesk 2 · procest 2 · softwarecatalog 2 · hermiq 1 · shillinq 1

Only openbuild was clean. The first one a user actually reported was
dossiq step 1: "a quick spin through case handling — we'll register a case".

WHY A GATE, WHEN THE RULE ALREADY EXISTS. Because a skill is opt-in. It
applies when an author chooses to load it, and manifest copy is routinely
written by hand or by an agent that never invoked the writing skill. Nothing
in the pipeline reads that copy at all: `check:manifest` validates the manifest
against a JSON Schema, and JSON Schema has no opinion about prose. So the rule
lived in a document, the copy shipped past it, and the only detector was a
human noticing on screen.

That is the shape a gate is for. The rule is not new; the enforcement is.

WHAT IS CHECKED. Every user-visible string in the manifest — the fields a
reader actually sees:

    title, body, task, label, description, emptyText, placeholder,
    subtitle, helpText

in `src/manifest.json` AND in `src/manifest.d/*.json`. The fragments matter:
they are merged into the manifest at runtime by `require.context`, so a
checker that reads only `src/manifest.json` is blind to whatever they add.
Eight fleet apps use fragments; shillinq has 87 of them.

WHAT IS NOT CHECKED. En-dashes (–) between digits, which voice.md explicitly
permits for numeric ranges ("2020–2024"). An en-dash anywhere else is flagged.
URLs and identifiers are skipped: a `--` inside a query string is not prose.

FULL-TREE, not diff-scoped. The em-dashes are already in the tree. A
diff-scoped version would report clean on every PR that does not happen to
touch the manifest, which is nearly all of them, and the 25 would sit there
indefinitely wearing a green tick.
"""

import json
import os
import re
import sys

# Fields a human actually reads. Kept explicit rather than "every string in
# the tree" so that route names, component ids, icon names and schema slugs —
# none of which are prose — cannot produce a finding.
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

EM_DASH = "—"
EN_DASH = "–"

# An en-dash BETWEEN DIGITS is a numeric range, which voice.md §8 allows.
# Anything else is the AI tell.
NUMERIC_RANGE = re.compile(r"(?<=\d)%s(?=\d)" % EN_DASH)

# `--` inside a URL or a CLI example is not an em-dash substitute. Strip the
# obvious non-prose carriers before looking for it.
URLISH = re.compile(r"https?://\S+|`[^`]*`")


def _findings_for(value):
    """
    Return the list of style violations in one string.

    :param value: the string to inspect.
    :return: list of short reason strings; empty when the value is clean.
    """
    out = []
    if EM_DASH in value:
        out.append("em-dash")
    stripped = NUMERIC_RANGE.sub("", value)
    if EN_DASH in stripped:
        out.append("en-dash outside a numeric range")
    prose = URLISH.sub("", value)
    if "--" in prose:
        out.append("double-dash")
    return out


def _walk(node, path, hits, counter):
    """
    Walk a manifest node, collecting findings for user-visible strings.

    :param node: the current dict / list / scalar.
    :param path: JSON-ish path to the current node, for the report.
    :param hits: accumulator of (path, value, reasons).
    :param counter: single-element list used as a mutable string count.
    :return: None
    """
    if isinstance(node, dict):
        for key, value in node.items():
            child = "%s.%s" % (path, key) if path else key
            if key in VISIBLE_FIELDS and isinstance(value, str) and value.strip():
                counter[0] += 1
                reasons = _findings_for(value)
                if reasons:
                    hits.append((child, value, reasons))
            else:
                _walk(value, child, hits, counter)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, "%s[%d]" % (path, index), hits, counter)


def _manifest_files(root):
    """
    Collect the manifest and every runtime-merged fragment.

    :param root: repository root to scan.
    :return: list of file paths, in load order.
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
    :return: 0 clean, 1 findings, 4 no manifest in this repo.
    """
    root = argv[1] if len(argv) > 1 else "."
    files = _manifest_files(root)
    if not files:
        print("checked 0 manifest string(s)")
        return 4

    hits = []
    counter = [0]
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            # A manifest that will not parse is gate-manifest-validation's
            # finding, not this gate's. Say so and keep going rather than
            # reporting a style verdict over a file never read.
            print("SKIP %s: unreadable (%s)" % (os.path.relpath(path, root), exc))
            continue
        _walk(data, os.path.relpath(path, root), hits, counter)

    for where, value, reasons in hits:
        excerpt = value if len(value) <= 120 else value[:117] + "..."
        print("FAIL %s: %s" % (where, ", ".join(reasons)))
        print("     %s" % excerpt)

    if hits:
        print("")
        print("voice.md §8: em-dashes and double-dashes are AI tells.")
        print("Replace with a period, a comma, or a colon.")
        print("En-dashes are allowed only between digits, as a numeric range.")

    print("checked %d manifest string(s)" % counter[0])
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
