#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-48 csrf-cochange — which removed lines actually DROPPED CSRF protection?

WHY THIS EXISTS (#191)
----------------------
The gate found removed attributes like this::

    git diff -U0 "${BASE_REF}...HEAD" -- 'lib/Controller/*.php' \\
        | grep -E '^-.*(@NoCSRFRequired|#\\[NoCSRFRequired\\])'

`^-.*` puts no constraint on where in the line the token sits, so a comment
that NAMES the attribute is indistinguishable from an attribute that was
deleted. Measured on nldesign (`development` vs `origin/beta`): the gate was
red, nothing about CSRF had changed, and the matched line was one removed
sentence from a class docblock —

    - * (#[PublicPage] + #[NoCSRFRequired]) and the response contract are owned by

— replaced by another sentence saying the same thing.

WHY THIS ONE IS ESPECIALLY BAD TO LEAVE
---------------------------------------
The cheapest way to clear the finding is to REWORD A COMMENT. That changes
nothing about CSRF and teaches exactly the habit the gate exists to prevent,
so a gate satisfiable by prose is worse than no gate: it manufactures the
appearance of a security review. Same family as #184, where gate-64 grepped a
quoted string literal and so matched every comment and missed every constant.

THE RULE
--------
A removed line counts only when the token is in a CODE POSITION:

  attribute form  after the `-`, optional whitespace, the content STARTS with
                  `#[`, and that attribute list contains `NoCSRFRequired`.
                  `#[NoAdminRequired, NoCSRFRequired]` counts; a sentence with
                  `#[NoCSRFRequired]` in the middle of it does not.

  docblock form   after the `-`, optional whitespace, an optional leading `*`
                  and optional whitespace, the content STARTS with
                  `@NoCSRFRequired`. That is the only position PHP's own
                  docblock parsers accept a tag in, and it is not a position
                  prose reaches.

The nldesign line fails both — its `#[NoCSRFRequired]` sits mid-sentence after
`(` — while a genuine deletion of either form still matches.

Usage::

    check_csrf_removal.py < unified.diff

Prints the removed lines that are real CSRF removals, one per line. Exits 0
always; the OUTPUT is the answer (#209).
"""
from __future__ import annotations

import re
import subprocess
import sys

# `-` then optional whitespace then `#[`, with NoCSRFRequired inside the
# attribute group. `[^]]*` is bounded by the closing bracket so a `#[Foo]`
# followed later on the line by the word NoCSRFRequired in prose cannot match.
ATTRIBUTE_REMOVED = re.compile(r'^-\s*#\[[^]]*\bNoCSRFRequired\b')
# `-` then optional whitespace, an optional docblock star, optional
# whitespace, then the tag AT THE START of the content.
DOCBLOCK_TAG_REMOVED = re.compile(r'^-\s*(?:\*\s*)?@NoCSRFRequired\b')

# A diff header line is `---` / `---` shaped; it is not a removed line of code.
DIFF_HEADER = re.compile(r'^---(\s|$)')
# `+++ b/lib/Controller/X.php` — starts a new file's hunks. `+++` must be
# tested before the `+` addition branch, exactly as `---` is before `-`.
DIFF_FILE_HEADER = re.compile(r'^\+\+\+\s+(?:b/)?(?P<path>\S+)')
# `@@ -12,5 +12,0 @@` — the base-image start line of the hunk.
HUNK_HEADER = re.compile(r'^@@\s+-(?P<start>\d+)(?:,\d+)?\s')


def removals(diff: str) -> list[str]:
    """Removed lines that genuinely DROPPED CSRF protection (paths dropped)."""
    return [line for _path, line, _lineno in removals_with_paths(diff)]


def removals_with_paths(diff: str) -> list:
    """``(path, line)`` for every removed line that dropped CSRF protection.

    A REMOVAL PAIRED WITH AN IDENTICAL ADDITION IS A MOVE, NOT A REMOVAL.

    Relocating a docblock line inside a file emits a `-` and a `+` carrying the
    same bytes. Scanning only `^-` reads that as deleting the annotation, and
    the gate reports a security regression for a diff in which nothing about
    CSRF changed. Measured on larpingapp: #297 moved one comment line while
    reordering `SettingsController`'s docblocks —

        -     * @NoCSRFRequired removed to close the CSRF-forgery surface (closes #206).
        +     * instance-wide configuration write needs. `@NoCSRFRequired` was removed
        +     * @NoCSRFRequired removed to close the CSRF-forgery surface (closes #206).

    — and gate-48 kept `Hydra Gates` red on that repo's `development` branch
    from then on, over a commit that changed no auth posture at all.

    Cancellation is per FILE and by MULTISET. Per file because a line deleted
    from one controller and added to another is a real change of posture for
    the first one; by multiset because a diff that removes a tag twice and
    restores it once has removed it once.

    A RE-INDENTED LINE IS THE SAME LINE (the coding-standard migration).
    ------------------------------------------------------------------
    Cancellation used to compare RAW BYTES, on the stated reasoning that
    "treating a re-indented line as a move would let a reformat swallow a
    genuine deletion". Measured on the fleet-wide move to Nextcloud's coding
    standard (`chore/nextcloud-coding-standard`, larpingapp#313 and 17
    siblings), that reasoning cost more than it bought: php-cs-fixer re-indents
    every controller from 4 spaces to a tab, so

        -    #[NoCSRFRequired]
        +\t#[NoCSRFRequired]

    is emitted for EVERY attribute in the app. On launchpad the helper reported
    25 "removals" against a tree whose `NoCSRFRequired` count is 43 before and
    43 after — the annotation was never dropped, only moved one indent level.
    gate-48 went red on 8 of the 18 migrating apps for that reason alone.

    The fear behind byte-exactness does not survive MULTISET accounting, which
    is what makes the relaxation safe: a re-indentation contributes exactly one
    addition for each removal it causes, so the net count is unchanged and
    nothing cancels that was not restored. Delete one annotation inside an
    otherwise fully re-indented file and the removals outnumber the additions
    by one, so exactly one finding survives — pinned by
    `test_a_genuine_deletion_inside_a_full_reindent_still_reports`, which is
    the positive control for this relaxation and fails if it is over-applied.

    Only leading/trailing whitespace is normalised. The attribute list itself
    is still compared verbatim, so `#[NoAdminRequired, NoCSRFRequired]` can
    never cancel a removed `#[NoCSRFRequired]`.
    """
    # {path: [normalised content of each added line]}, removals in file order.
    added: dict[str | None, list[str]] = {}
    found: list = []
    path: str | None = None
    # BASE-IMAGE LINE NUMBER, tracked from the hunk headers. Five identical
    # `- * @NoCSRFRequired` lines are indistinguishable by CONTENT, so the
    # post-image test below can only be positional. `-U0` emits no context
    # lines, so a `-` advances the base cursor and a `+` does not.
    base_lineno = 0

    for line in diff.splitlines():
        header = DIFF_FILE_HEADER.match(line)
        if header:
            path = header.group('path')
            continue
        hunk = HUNK_HEADER.match(line)
        if hunk:
            base_lineno = int(hunk.group('start'))
            continue
        if line.startswith('+'):
            added.setdefault(path, []).append(line[1:].strip())
            continue
        if not line.startswith('-') or DIFF_HEADER.match(line):
            if line.startswith(' '):
                base_lineno += 1
            continue
        here = base_lineno
        base_lineno += 1
        if ATTRIBUTE_REMOVED.match(line) or DOCBLOCK_TAG_REMOVED.match(line):
            found.append((path, line, here))

    out: list = []
    for file_path, line, here in found:
        pool = added.get(file_path)
        key = line[1:].strip()
        if pool is not None and key in pool:
            # Consume the pairing so a second identical removal still reports.
            pool.remove(key)
            continue
        out.append((file_path, line, here))
    return out


# ---------------------------------------------------------------------------
# 🔴 DELETING THE METHOD AND STRIPPING ITS ANNOTATION ARE NOT THE SAME CHANGE,
#    AND A `-U0` DIFF CANNOT TELL THEM APART
# ---------------------------------------------------------------------------
#
# Everything above reads only `-` lines. A `-U0` diff of
#
#     -    #[NoCSRFRequired]
#     -    public function legacyDashboard(): JSONResponse { ... }
#
# and a `-U0` diff of
#
#     -    #[NoCSRFRequired]
#
# produce the SAME evidence for this helper: one removed attribute line. But
# the first change DELETED the endpoint — there is nothing left for a forged
# request to reach — while the second turned CSRF enforcement ON for a method
# that survives. Only the second is a posture change this gate should judge,
# and only the second can have a frontend counterpart to co-change.
#
# MEASURED on zaakafhandelapp#371: base declared `#[NoCSRFRequired]` six times
# on `DashboardController`, the branch declares it once on the surviving
# `page()`, and the other five methods are GONE. gate-48 reported five
# removals. The PR spent a coordinator decision, a security warning and an
# exclusion marker on a finding about endpoints that no longer exist.
#
# THE TEST, and it is a property of the POST-IMAGE rather than of the diff:
# a removal is out of scope when no `function <name>` survives in that file at
# HEAD, where `<name>` is the method the removed line annotated in the BASE
# image. Both images are read from git, so this needs a repo and a base ref;
# without them the behaviour is unchanged and every removal is reported. THAT
# IS THE FAIL-CLOSED DIRECTION — an unreadable image is never a reason to drop
# a security finding.
_FUNCTION_DECL = re.compile(
    r"\bfunction\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _git_show(repo: str, ref: str, path: str):
    """File contents at *ref*, or ``None`` when it cannot be read."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "show", f"{ref}:{path}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def _annotated_method(image: str, lineno: int, needle: str):
    """Name of the method the removed line at 1-based *lineno* annotates.

    An attribute or docblock tag sits ABOVE its declaration, so the method is
    the next `function <name>(` at or after that line. ``None`` when the line
    is not where the diff said it was — verified against *needle*, so a stale
    or misparsed offset cannot silently address a different method.
    """
    lines = image.splitlines()
    index = lineno - 1
    if index < 0 or index >= len(lines):
        return None
    if lines[index].strip() != needle:
        return None
    m = _FUNCTION_DECL.search("\n".join(lines[index:]))
    return m.group("name") if m is not None else None


def survives_at_head(repo: str, base_ref: str, path: str, line: str,
                     lineno: int = 0) -> bool:
    """True when the method this removal annotated still exists at HEAD.

    Returns True — i.e. "report it" — whenever the question cannot be answered:
    no repo, no base ref, an unreadable image, or a line that cannot be located
    in the base image. An unanswerable question is not a clean bill of health.
    """
    if not repo or not base_ref or not path or not lineno:
        return True
    head_image = _git_show(repo, "HEAD", path)
    if head_image is None:
        # The whole controller file is gone at HEAD. Every endpoint in it is
        # gone with it, so there is nothing left to protect.
        return False
    base_image = _git_show(repo, base_ref, path)
    if base_image is None:
        return True
    name = _annotated_method(base_image, lineno, line[1:].strip())
    if name is None:
        return True
    surviving = {m.group("name") for m in _FUNCTION_DECL.finditer(head_image)}
    return name in surviving


def main(argv: list[str]) -> int:
    repo = base_ref = None
    args = argv[1:]
    while args:
        head = args.pop(0)
        if head == "--repo" and args:
            repo = args.pop(0)
        elif head == "--base" and args:
            base_ref = args.pop(0)
        else:
            print("usage: check_csrf_removal.py [--repo DIR --base REF] "
                  "< unified.diff", file=sys.stderr)
            return 2
    for path, line, lineno in removals_with_paths(sys.stdin.read()):
        if not survives_at_head(repo, base_ref, path or "", line, lineno):
            continue
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
