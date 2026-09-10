#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 114 helper. header-action-budget.

Counts the buttons a page declares in its header actions bar
(``config.headerActions[]``) across the EFFECTIVE manifest, and refuses a
page whose count GREW against the delta base.

WHY THIS EXISTS
---------------
Two surfaces in the same app, over the same fifteen changes, in dossiq:

  * The main navigation had a budget of four to six entries and an ADR that
    enforced it. It held at five.
  * The case page tabs had no budget. They went from ten to fourteen, and a
    refactor spent days cutting them back to six. Four of the eight that went
    turned out to duplicate a sidebar tab that was already on the page.

The case header actions bar went from one to twelve in the same period, and
nobody was counting. Measured on dossiq at ``development`` on 2026-09-09:
eleven of those twelve landed on a single day, 2026-09-08, and not one has
ever been removed. Every one arrived in a green PR, because no check in the
package reads this array.

The pattern is that whatever is not counted is where the complexity goes.
This gate puts a number on the bar so the next growth is visible while it is
happening, not after a user reports the page is unusable.

WHY A RATCHET AND NOT A CEILING
-------------------------------
A ceiling asks someone to guess the right number today. Nobody knows whether
the case page should carry four actions or seven, and a guess that lands too
high enforces nothing while a guess that lands too low blocks work that is
fine. A ratchet asks a smaller question that has an answer: is this page's
bar longer than it was yesterday. Same shape as ADR-100's custom-page
ratchet and ADR-049's custom-widget ratchet, both of which compare against
the base ref and keep no checked-in baseline to go stale.

THE RATCHET IS PER PAGE, THE CENSUS IS PER APP
----------------------------------------------
An app-wide total would let a page grow as long as another page shrank, and
the complaint is never about the app's total. It is about one bar. So the
finding is per page. The app-wide census is printed anyway, on every run,
because a gate that is silent when it passes cannot be shown to have run.

A page that exists at head and not at base has nothing to compare against
and raises no finding. That covers a genuinely new page, and it also covers
a renamed one: a rename reads as a removal plus an addition, and this gate
cannot tell those apart. The census still reports the new page's count, so
a bar that arrives long is visible in the output even though it is not a
finding.

WARNING FIRST, NOT BLOCKING
---------------------------
Every finding is a WARN and the exit code stays 0. This package resolves at
``@main`` for all 21 core apps, so a blocking gate lands fleet-wide the
minute it merges and fails every repository carrying inherited debt. A new
gate ships advisory. Promotion to blocking is a deliberate edit here and in
``test_check_header_action_budget.py``, which pins the exit code, so it
cannot happen by accident.

READS THE FRAGMENTS TOO
-----------------------
``src/manifest.d/*.json`` is merged over ``src/manifest.json`` at runtime
via ``require.context`` (ADR-037), pages concatenated in sorted filename
order. A checker that opens only the base manifest is blind to whatever the
fragments add. dossiq ships three fragments, shillinq eighty-seven.

Usage:
    check_header_action_budget.py <app-dir>

Reads the base ref from ``$HYDRA_GATE_BASE_REF``. Without one, the census
runs and the ratchet does not, and the missing ``base=`` line is how the
runner knows to say so.

Output contract:
    checked N page(s) in the effective manifest      terminal line, always
    [header-action-budget] findings=N                always, on a finished run
    [header-action-budget] base=N head=M delta=+K    only when a base was given

Exit:
    0  finished. Read ``findings=`` for the verdict, not this byte.
    2  the manifest could not be read.
    4  nothing to judge: no src/manifest.json, or it declares no pages.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

FIELD = "headerActions"


def _run(args):
    """
    Run a git command and return its stdout, or None when it fails.

    :param args: argv list handed to subprocess.
    :return: stdout as a string, or None.
    """
    try:
        out = subprocess.run(
            args, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _manifest_paths(app_dir):
    """
    Every manifest file that contributes pages, in the order main.js merges them.

    :param app_dir: repository root to read.
    :return: list of paths relative to app_dir, base manifest first.
    """
    paths = []
    if os.path.isfile(os.path.join(app_dir, "src", "manifest.json")):
        paths.append("src/manifest.json")
    fragments = glob.glob(os.path.join(app_dir, "src", "manifest.d", "*.json"))
    for f in sorted(fragments):
        paths.append(os.path.relpath(f, app_dir).replace(os.sep, "/"))
    return paths


def _census_from_docs(docs):
    """
    Header action counts per page id across already-parsed manifest documents.

    :param docs: list of parsed manifest dicts, in merge order.
    :return: (dict of page id to count, number of pages seen).
    """
    counts = {}
    seen = 0
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for page in doc.get("pages") or []:
            if not isinstance(page, dict):
                continue
            pid = page.get("id")
            if not isinstance(pid, str) or not pid:
                continue
            seen += 1
            config = page.get("config")
            actions = config.get(FIELD) if isinstance(config, dict) else None
            counts[pid] = len(actions) if isinstance(actions, list) else 0
    return counts, seen


def _head_census(app_dir, paths):
    """
    Header action counts on the working tree.

    :param app_dir: repository root to read.
    :param paths: manifest paths relative to app_dir.
    :return: (counts, pages seen), or (None, 0) when a file will not parse.
    """
    docs = []
    for rel in paths:
        try:
            with open(os.path.join(app_dir, rel), "r", encoding="utf-8") as fh:
                docs.append(json.load(fh))
        except (OSError, ValueError) as exc:
            print(f"ERROR {rel}: {exc}")
            return None, 0
    return _census_from_docs(docs)


def _base_census(app_dir, base_ref):
    """
    Header action counts on the base ref.

    Re-resolves the manifest paths AT THE BASE rather than reusing head's:
    a fragment added by this change does not exist there, and a fragment
    deleted by it does. Reading head's list against the base would count a
    new fragment's pages as base pages and hide exactly the growth this
    gate is for.

    :param app_dir: repository root to read.
    :param base_ref: git ref to compare against.
    :return: dict of page id to count, or None when the base cannot be read.
    """
    listing = _run(
        ["git", "-C", app_dir, "-c", "safe.directory=*", "ls-tree", "-r",
         "--name-only", base_ref, "src/"],
    )
    if listing is None:
        return None
    rels = [
        p for p in listing.split("\n")
        if p == "src/manifest.json"
        or (p.startswith("src/manifest.d/") and p.endswith(".json"))
    ]
    rels.sort(key=lambda p: (p != "src/manifest.json", p))
    docs = []
    for rel in rels:
        blob = _run(["git", "-C", app_dir, "-c", "safe.directory=*",
                     "show", f"{base_ref}:{rel}"])
        if blob is None:
            continue
        try:
            docs.append(json.loads(blob))
        except ValueError:
            # A manifest that did not parse AT THE BASE is not this change's
            # problem, and treating it as zero pages would report every page
            # on it as new. Refuse the whole comparison instead.
            print(f"ERROR {base_ref}:{rel} does not parse as JSON")
            return None
    counts, _ = _census_from_docs(docs)
    return counts


def main(argv):
    """
    Count header actions, report the census, and ratchet against the base.

    :param argv: sys.argv.
    :return: process exit status.
    """
    app_dir = argv[1] if len(argv) > 1 else "."
    paths = _manifest_paths(app_dir)
    if not paths:
        print("checked 0 page(s) in the effective manifest")
        return 4

    head, seen = _head_census(app_dir, paths)
    if head is None:
        return 2
    if seen == 0:
        print("checked 0 page(s) in the effective manifest")
        return 4

    with_actions = {pid: n for pid, n in head.items() if n > 0}
    for pid in sorted(with_actions, key=lambda p: (-with_actions[p], p)):
        print(f"[header-action-budget] {pid}: {with_actions[pid]}")
    total = sum(head.values())
    top = max(with_actions.items(), key=lambda kv: (kv[1], kv[0]))[0] if with_actions else "none"
    print(
        f"[header-action-budget] pages={len(head)} "
        f"with-actions={len(with_actions)} total={total} "
        f"max={max(with_actions.values()) if with_actions else 0} on {top}",
    )

    findings = 0
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "").strip()
    if base_ref:
        base = _base_census(app_dir, base_ref)
        if base is None:
            print(
                "[header-action-budget] the base ref could not be read, so the "
                "ratchet did not run. The census above still stands.",
            )
        else:
            base_total = sum(base.values())
            delta = total - base_total
            print(
                f"[header-action-budget] base={base_total} head={total} "
                f"delta={delta:+d}",
            )
            for pid in sorted(head):
                if pid not in base:
                    continue
                if head[pid] <= base[pid]:
                    continue
                findings += 1
                print(
                    f"WARN {pid}: header actions went {base[pid]} to "
                    f"{head[pid]} (+{head[pid] - base[pid]}). An actions bar "
                    f"grows one button at a time and nobody reads twelve. "
                    f"Before adding one, check whether the page already "
                    f"reaches it: a sidebar tab, a panel's own Add control, or "
                    f"a widget button is the same gesture one click deeper, and "
                    f"a second copy in the header is the duplication this "
                    f"ratchet is here to catch. If the button belongs in the "
                    f"bar, say in the page's _note which one it replaces.",
                )

    print(f"[header-action-budget] findings={findings}")
    print(f"checked {seen} page(s) in the effective manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
