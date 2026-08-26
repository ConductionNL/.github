#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""
Gate 95 — adr-number-collision.

An ADR number is a citation key. `ADR-081` appears in commit messages, gate
descriptions, spec deltas and source comments, and every one of those is a
pointer that only works while the number resolves to exactly one document.

On 2026-08-26 hydra carried EIGHT numbers claimed by two or three documents
each — 037, 041, 049, 050, 051, 076, 081, 084 — across 18 files, with 1,640
citing files spread over 20 repositories. `ADR-081` alone meant three
different decisions (Vue 3 migration, money/effort ownership, public surface
placement), and scholiq used `ADR-037` for two different meanings in the same
repository.

The damage is not that the duplicate exists; it is that the ambiguity is
INVISIBLE. Nothing errors. A reader follows `ADR-081` to whichever file the
directory listing shows first and reads a decision that was never the one
cited. By the time it is noticed, the citations cannot be repaired
mechanically, because each one has to be READ to know which document it
meant.

So this checks two properties, both cheap and both exact:

  1. No two files claim the same ADR number.
  2. A file's H1 number matches its filename number — because a title saying
     `# ADR-041` in a file named `adr-101-*.md` is the same ambiguity wearing
     a different hat, and it is what a half-finished renumber leaves behind.

Property 2 is checked ONLY when the H1 declares a number at all. Older ADRs
here predate the `# ADR-NNN:` title convention and say just the topic; that is
a style question, not a collision, and failing them would make this gate noisy
enough to be switched off.

Exit codes follow the hydra-gates contract:
  0 — pass
  1 — at least one collision or mismatch
  4 — na: this repo ships no openspec/architecture ADRs
"""

import os
import re
import sys
from collections import defaultdict

# Matches the number in `adr-081-something.md`. Anchored so a stray file like
# `notes-adr-081.md` is not mistaken for an ADR.
FILENAME_RE = re.compile(r"^adr-(\d+)-.+\.md$")

# Matches `# ADR-081:` / `# ADR-081 —` / `# ADR-081`. Only the FIRST ADR-NNN on
# the H1 line is the file's own number: titles legitimately cite others, e.g.
# "# ADR-049: Declarative Widget Vocabulary (extends ADR-036)".
TITLE_RE = re.compile(r"^#\s+ADR-(\d+)")


def find_adr_dirs(root):
    """Every openspec/architecture directory in the tree, excluding archives.

    Archived changes keep their own copies and are a record of what was true
    when written; renumbering to match the present would make the history
    untrue, so they are deliberately out of scope.
    """
    out = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in ("node_modules", "vendor", ".git", "archive")
        ]
        if os.path.basename(dirpath) == "architecture" and \
                os.path.basename(os.path.dirname(dirpath)) == "openspec":
            out.append(dirpath)
    return sorted(out)


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    adr_dirs = find_adr_dirs(root)
    if not adr_dirs:
        print("no openspec/architecture directory in this repo")
        print("checked 0 ADR file(s)")
        return 4

    failures = []
    checked = 0

    for d in adr_dirs:
        by_number = defaultdict(list)
        for name in sorted(os.listdir(d)):
            m = FILENAME_RE.match(name)
            if not m:
                continue
            checked += 1
            number = m.group(1)
            path = os.path.join(d, name)
            by_number[number].append(name)

            # Property 2 — the title agrees with the filename.
            try:
                with open(path, encoding="utf8", errors="ignore") as fh:
                    first = fh.readline().rstrip("\n")
            except OSError as exc:
                failures.append(
                    "FAIL %s: could not be read (%s)" % (path, exc)
                )
                continue
            tm = TITLE_RE.match(first)
            if tm and tm.group(1) != number:
                failures.append(
                    "FAIL %s: filename says ADR-%s but its title says ADR-%s. "
                    "A citation resolves by number, so the two must agree — "
                    "this is what a half-finished renumber leaves behind."
                    % (path, number, tm.group(1))
                )

        # Property 1 — one number, one document.
        for number, names in sorted(by_number.items()):
            if len(names) > 1:
                failures.append(
                    "FAIL %s: ADR-%s is claimed by %d documents (%s). An ADR "
                    "number is a citation key; while it resolves to more than "
                    "one file, every existing 'ADR-%s' reference is ambiguous "
                    "and nothing reports it. Give all but one of them the next "
                    "free number, keeping it with whichever document the "
                    "fleet's citations actually mean, and leave a redirect "
                    "note in the ones that move."
                    % (d, number, len(names), ", ".join(names), number)
                )

    if checked == 0:
        print("no adr-NNN-*.md files under: %s" % ", ".join(adr_dirs))
        print("checked 0 ADR file(s)")
        return 4

    for line in failures:
        print(line)

    # The terminal summary the runner greps for. Printed on EVERY path that
    # actually inspected something, pass or fail — a gate that prints nothing
    # when it passes cannot be shown to have run.
    print("checked %d ADR file(s)" % checked)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
