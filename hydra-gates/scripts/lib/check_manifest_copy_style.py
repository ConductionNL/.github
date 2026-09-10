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

THE APP STORE DESCRIPTION, ADDED 2026-09-09, AS A WARNING.

The gate read `src/manifest.json` and nothing else, so `appinfo/info.xml` was
never checked. That file IS the App Store description: it is the most public
prose any of these apps ships, the first thing a stranger reads, and the one
surface no reviewer opens because it is not a screen.

MEASURED 2026-09-09 over all 21 core apps at `development`. Their info.xml
files carry 477 em-dashes: 204 inside `<description>` / `<summary>`, and 273
inside XML comments. TWENTY OF TWENTY-ONE apps have at least one in the public
copy. Only dossiq is clean, and only because it was fixed the same day
(dossiq#2036), which is what prompted this.

    launchpad 26 · stackiq 22 · pipelinq 22 · openregister 16 · opencatalogi 16
    decidiq 16 · keepiq 16 · planninq 15 · humaniq 13 · learniq 9 · shillinq 6
    buildiq 6 · hermiq 6 · integriq 4 · larpinq 3 · thematiq 2 · portaliq 2
    zaakafhandelapp 2 · filinq 1 · versioniq 1 · dossiq 0

SO IT SHIPS AS A WARNING, NOT A FAILURE. A new scope that blocks on the day it
lands reddens twenty of twenty-one repositories on inherited debt, and this
repository is resolved at `@main` by every one of them, so a merge is
fleet-wide the same minute. The manifest scope stays blocking, because it is
already green fleet-wide and regressions there must not ship. The App Store
scope reports and does not block, until the 204 are cleared.

ONLY `<description>` AND `<summary>`. Not the XML comments, even though they
hold 273 of the 477. A comment is developer prose, addressed to whoever opens
the file next; voice.md governs what a READER sees. Flagging comments would
hand every app a chore whose completion changes nothing a user reads, and it
is the same mistake `_meta` taught this checker once already, where 22 of
shillinq's 47 findings were build provenance dressed as copy.

THE EXIT CODE IS UNCHANGED, deliberately. `checked N manifest string(s)` still
counts manifest strings only, and the return value is still driven by manifest
findings alone, so the runner's empty-scope logic and the acceptance matrix's
planted-FAIL / clean-PASS arms keep meaning exactly what they meant. The App
Store findings arrive on their own `warned N` line. One consequence worth
naming: a repo with an info.xml and NO manifest still reports `na`, and its
App Store warnings sit in the log unheaded. No fleet app is in that state, and
turning the advisory into a verdict is the change to make when the 204 are
gone, not before.
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
            # Underscore-prefixed blocks are internal metadata, never rendered.
            # `_meta` is the live case: 38 shillinq fragments carry one, holding
            # spdx-license, spdx-copyright, change, adr and a description that
            # documents the fragment for developers. Flagging those produced 22
            # false findings out of 47 on that app alone, and "fixing" them
            # would have rewritten build provenance as if it were user copy.
            if key.startswith("_"):
                continue
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


# `<description>` and `<summary>` are the two elements a stranger reads on the
# App Store page. `<name>` is a proper noun and carries no prose. Everything
# else in info.xml is machinery: versions, dependencies, repair steps, routes.
APPSTORE_ELEMENTS = ("description", "summary")

# Non-greedy, DOTALL: these elements span lines and carry CDATA. The CDATA
# wrapper is stripped rather than parsed, because a real XML parser here would
# turn an unparseable info.xml into this gate's crash instead of
# gate-manifest-validation's finding.
APPSTORE_BLOCK = re.compile(
    r"<(%s)\b[^>]*>(.*?)</\1>" % "|".join(APPSTORE_ELEMENTS), re.S
)
CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)
XML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _appstore_findings(root):
    """
    Collect style findings in the App Store copy of appinfo/info.xml.

    Comments are stripped BEFORE the elements are matched, so a commented-out
    description cannot produce a finding nobody can act on.

    :param root: repository root to scan.
    :return: (list of (path, value, reasons), count of strings inspected).
    """
    path = os.path.join(root, "appinfo", "info.xml")
    if not os.path.isfile(path):
        return [], 0

    try:
        with open(path, "r", encoding="utf-8") as handle:
            xml = handle.read()
    except OSError as exc:
        print("SKIP appinfo/info.xml: unreadable (%s)" % exc)
        return [], 0

    xml = XML_COMMENT.sub("", xml)

    hits = []
    counted = 0
    for match in APPSTORE_BLOCK.finditer(xml):
        element = match.group(1)
        value = match.group(2)
        inner = CDATA.search(value)
        if inner:
            value = inner.group(1)
        if not value.strip():
            continue
        counted += 1
        reasons = _findings_for(value)
        if reasons:
            line = xml.count("\n", 0, match.start()) + 1
            hits.append(("appinfo/info.xml:%d <%s>" % (line, element), value, reasons))

    return hits, counted


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


def _report_appstore(hits, counted):
    """
    Print the App Store findings as a non-blocking advisory.

    :param hits: list of (path, value, reasons).
    :param counted: how many App Store strings were inspected.
    :return: None
    """
    for where, value, reasons in hits:
        excerpt = value.strip().replace("\n", " ")
        excerpt = excerpt if len(excerpt) <= 120 else excerpt[:117] + "..."
        print("WARN %s: %s" % (where, ", ".join(reasons)))
        print("     %s" % excerpt)

    if hits:
        print("")
        print("The App Store description breaks voice.md §8. This is ADVISORY:")
        print("it does not fail the gate yet, because 20 of 21 fleet apps carry")
        print("the same debt (204 findings, measured 2026-09-09) and this")
        print("repository resolves at @main for all of them. Fix it anyway: this")
        print("is the first prose a stranger reads about the app.")

    print("warned %d app-store string(s)" % counted)


def main(argv):
    """
    Entry point.

    :param argv: argv, where argv[1] is the repository root (default ".").
    :return: 0 clean, 1 findings, 4 no manifest in this repo.
    """
    root = argv[1] if len(argv) > 1 else "."

    # Read the App Store copy FIRST, so its advisory is printed even on a repo
    # that ships no manifest and therefore returns `na` below.
    store_hits, store_counted = _appstore_findings(root)

    files = _manifest_files(root)
    if not files:
        _report_appstore(store_hits, store_counted)
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

    _report_appstore(store_hits, store_counted)

    print("checked %d manifest string(s)" % counter[0])

    # THE RETURN VALUE READS `hits` AND NOT `store_hits`, AND THAT IS THE WHOLE
    # DESIGN. The App Store scope is advisory until the fleet's 204 findings are
    # cleared. `test_check_manifest_copy_style.py` asserts an info.xml-only tree
    # exits 0; wire `store_hits` in here and that arm goes red, which is the
    # point of it.
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
