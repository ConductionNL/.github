#!/usr/bin/env python3
"""
gate-115 — a retired fleet app id or namespace in a cross-app LOOKUP.

WHAT THIS CATCHES
-----------------
Every cross-app reference in this fleet is a duck-typed runtime lookup.
`IAppManager::isInstalled('openconnector')` against an instance running
`integriq` does not error: it returns false. `class_exists()` on a namespace
that moved answers false. `$container->get()` on it throws into a catch that
exists precisely so the app stays installable without its optional peer. A
`/apps/<old>/` path 404s, and the caller reads the 404 as "that app is not
installed" rather than "I asked for the wrong name".

So a stale name never surfaces as a failure. It surfaces as a feature that
quietly stopped working, and it stays that way until somebody goes looking.

MEASURED, ON A REPO WHERE IT HAD ALREADY HAPPENED. Run against dossiq at
4502857 (before PR #2061) this reports 5 findings, which are exactly the 5
detectable defects that PR fixed. Run against the fixed tree it reports 0.
Both directions checked. No allowlist was needed to get there.

WHAT THIS CANNOT SEE, AND THE REASON THAT MATTERS
-------------------------------------------------
This check knows which NAME an app answers to. It can never know which
METHODS or ROUTES that app publishes.

Two of the seven defects in that same dossiq incident were of the second kind
and this check is blind to both:

  - dossiq called filinq's `generateFromTemplate()`. That method has never
    existed on `OCA\\Filinq\\Service\\DocumentService`; the published entry
    point is `generateDocument()`. Repointing the namespace alone left the
    identical text stub in place of every generated PDF.
  - dossiq called `linkToRoute('openconnector.pdok.parcel')`. Integriq
    publishes four PDOK routes and parcel is not among them, under either
    name. Correcting only the id would have turned a quiet empty list into an
    uncaught RouteNotFoundException.

Both are the dangerous shape: a repoint that reads as a fix. A gate that
clears the name half silently reads as coverage of both halves, so this one
says so in its own output on every run, pass or fail. Closing that half means
reading the other app's route table and public method surface, on the model of
gate-67 (openregister-contract-parity). It is not this check.

THE EXCLUSIONS ARE THE RULE, NOT EXCEPTIONS TO IT
-------------------------------------------------
Measured on dossiq, the first three removed all 16 false positives there and
left every true finding standing. None of them is an allowlist and none needs
upkeep.

TWO MORE CAME FROM RUNNING THE FLEET, AND THAT IS THE LESSON. A rate measured
on one repo is a claim about that repo. dossiq holds no cross-app register
slug and writes its block comments with leading asterisks, so neither of those
classes could appear there, and a clean number read as a clean number. The
denominator for a fleet gate has to be the fleet.

  1. Comments are skipped, BLOCKS INCLUDED. Prose quoting an old name is how a
     rename gets explained; 7 of dossiq's 16 were docblocks describing the very
     defect they sat next to. Whether a line is prose is a stateful question
     rather than a prefix one: a `<!-- ... -->` header in a Vue SFC has
     continuation lines starting with an ordinary word, and a prefix rule reads
     each as code. Found the same way exclusion 4 was, by running the fleet
     rather than the one repo the rule was written on.
  2. An old spelling is accepted when the current one is a SIBLING BINDING IN
     THE SAME STATEMENT. Dual-spelling event lists are correct, not stale: an
     app that renamed its namespace without a compatibility alias has to be
     listened for under both, newest first, and flagging the fallback would
     push authors to delete it. That was 3 of the 16.

     SCOPED TO A STATEMENT, NOT THE FILE, and not to a line either. A
     file-wide accept under-reported in the worst direction: launchpad left
     two lookups unrepointed because their targets do not exist, wrote
     comments naming `integriq` and `dossiq` to record what it had read, and
     both findings switched off. The gate said 1 where 2 were stale, and the
     trigger was somebody documenting a known gap. A line-scoped accept would
     have the opposite fault, flagging the fallback in a two-line array.
     Prose never vouches for a binding: only code lines are considered.
  3. An app naming its OWN former id OR its own former namespace is never a
     finding. That was 6 of dossiq's 16,
     all of them `OLD_APP_ID` in migration repair steps or a `SOURCE_APP`
     handshake key the other side matches on and which orphans live records if
     it moves. This is derived from `<id>` in appinfo/info.xml, not
     configured, so it cannot drift.
  4. An OpenRegister REGISTER SLUG naming a retired name IS A FINDING, listed
     under its own heading because the FIX differs, not because the status
     does. This rule has been wrong twice and the history is the point.

     It began as a plain exclusion citing integriq's own MigrateAppConfigKeys:
     "that slug is deliberately NOT renamed". THAT DOCBLOCK WAS STALE, so the
     rule became "report, but do not count, because the policy is unsettled".
     The policy is now settled the other way: the freeze was the error and the
     renames were right. Measured 2026-09-10, NINE apps ship a slug-rename
     repair step, and every renamed app's register json declares the new slug.

     So a consumer naming an old slug reads ZERO ROWS on a migrated instance
     and calls it "no data", which is a defect and not a policy question.

     IT STILL GETS ITS OWN HEADING, because the fix is categorically
     different: both slugs are live across the fleet depending on whether a
     given instance has run the repair, so the answer is a probe against
     OpenRegister rather than swapping a literal. Swapping it breaks every
     instance that has not migrated yet, which is the same bug pointing the
     other way.

     THE OLD SLUG IS NOT ALWAYS THE OLD APP ID. stackiq migrated
     `voorzieningen` -> `stackiq`, never `softwarecatalog`, so a slug is only
     a finding when the app that owns it actually renamed THAT string. And
     the repair step is not always called the same thing: learniq's is
     `RenameRegisterSlug`, everyone else's is `MigrateRegisterSlug`, and
     looking for one fixed filename would have reported learniq as never
     having migrated.

RECORDING AN ANSWER: `@stale-fleet-app-id exclude <reason>`
-----------------------------------------------------------
NOT EVERY STALE NAME HAS A SUCCESSOR TO POINT AT, and those are the ones this
gate would otherwise ask about forever. Three shapes, all read out of the other
app's tree before they were written down:

  - the route was RETIRED, not renamed. integriq served `GET /api/endpoints`
    from a `resources` block until 496f2025 deleted it in the chain-C
    OpenRegister cutover.
  - the target NEVER EXISTED under either name. `git log -S` over integriq's
    3,960 commits, which span the whole openconnector era, finds no
    `PaymentService`, no `WalletOfferConcludedEvent`, no `sources/{source}/call`
    and no `lti/deployments/…/launch`.
  - the class was DELETED. `OCA\\OpenConnector\\Db\\SourceMapper` went with
    14 other mappers in ac47457f and has no `OCA\\Integriq\\Db\\` counterpart.

Repointing any of those produces a lookup that misses exactly as it missed
before, on a diff that reads to the next person as a fix already applied —
strictly worse than the stale name, which at least still says out loud that
something is unfinished. So the answer is to RECORD what was read.

The marker is the package's one convention, `@<tag> exclude <reason>`, with
the reason graded by the shared `exclusion_reason.is_reason_bearing()`. A bare
marker excludes nothing. It attaches to the BINDING — the statement's own
docblock or the comment lines directly above the line — never to the enclosing
method, and a marker that reaches no finding is reported rather than ignored.
An excluded finding is counted and printed on every run, so "0 findings" can
never mean two different things. Register slugs take no marker: a slug is
answered by probing OpenRegister for the name it responds to, not in prose.

Usage:  python3 check_stale_fleet_app_id.py <repo-root>
Exit:   0 clean · 1 findings · 4 nothing in scope (no lib/ or src/)

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2026 Conduction B.V.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402

# Retired app id -> the id it answers to now. `<id>` in appinfo/info.xml is the
# only authority for the right-hand side; this map is the fleet rename record
# from docs.conduction.nl/hydra/operations/renaming-an-app.
IDS = {
    "openconnector": "integriq",
    "docudesk": "filinq",
    "nldesign": "thematiq",
    "softwarecatalog": "stackiq",
    "larpingapp": "larpinq",
    "procest": "dossiq",
    "scholiq": "learniq",
    "decidesk": "decidiq",
    "openbuild": "buildiq",
    "doriath": "keepiq",
    "hrmq": "humaniq",
    "planix": "planninq",
    "mydash": "launchpad",
}

# Retired PSR-4 root -> the root it ships under now.
#
# EVERY PAIR HERE WAS READ OUT OF THAT APP'S OWN composer.json HISTORY, never
# inferred from its id. `openbuild` shipped `OCA\OpenBuilt`, which no naming
# rule would have produced, and guessing would have written a name that has
# never existed. Apps whose former root could not be evidenced are absent
# rather than guessed: an absent pair is a missed finding, an invented one is a
# false accusation.
NAMESPACES = {
    "OpenConnector": "Integriq",
    "DocuDesk": "Filinq",
    "Docudesk": "Filinq",
    "NLDesign": "Thematiq",
    "SoftwareCatalog": "Stackiq",
    "LarpingApp": "Larpinq",
    "Procest": "Dossiq",
    "Scholiq": "Learniq",
    "Decidesk": "Decidiq",
    "OpenBuilt": "Buildiq",
    "Doriath": "Keepiq",
}

# The call shapes whose argument IS an app id or an FQCN. A literal here is a
# routing key or a class name, not prose.
LOOKUP_CALLS = (
    r"is(?:App)?Installed|isEnabledForUser|linkToRoute(?:Absolute)?|"
    r"class_exists|interface_exists|->get"
)

# A line comment, or the OPENER of a block comment. Openers are anchored to
# the start of the line so a `/*` inside a string literal cannot open a phantom
# block and blind the rest of the file.
COMMENT = re.compile(r"^\s*(\*|//|#|/\*|<!--)")
IMPORT = re.compile(r"^\s*use\s+[A-Za-z_\\]")
BLOCK_OPEN = re.compile(r"^\s*(/\*|<!--)")
BLOCK_CLOSE = re.compile(r"(\*/|-->)")
SCAN_DIRS = ("lib", "src", "appinfo")
SCAN_EXT = (".php", ".js", ".ts", ".vue", ".json")

# The exclusion marker, on the package's one convention:
# `@<tag> exclude <reason>`, with the reason graded by the shared
# `exclusion_reason.is_reason_bearing()`. gate-16/19/25/26 read `@spec`,
# `@e2e`, `@contract` and `@visual`; gate-6 reads `@orphan-auth`, gate-52
# `@custom-widget-ratchet`, gate-57 `@orphaned-write-capability`. This is that
# tag for this gate and nothing about it is new.
#
# WHY A NAME FINDING NEEDS ONE AT ALL
# -----------------------------------
# Not every stale name has a successor to point at. Three shapes recur, and
# all three were read out of the other app's tree before they were written
# down:
#
#   - the route was RETIRED, not renamed. integriq served `GET /api/endpoints`
#     from a `resources` block until 496f2025 deleted it in the chain-C
#     OpenRegister cutover; there is no integriq path that answers now.
#   - the target NEVER EXISTED under either name. `git log -S` over integriq's
#     3,960 commits, which span the whole openconnector era, finds no
#     `PaymentService`, no `WalletOfferConcludedEvent` and no
#     `sources/{source}/call`.
#   - the class was DELETED. `OCA\OpenConnector\Db\SourceMapper` went with
#     14 other mappers in ac47457f and has no `OCA\Integriq\Db\` counterpart.
#
# In each of those, swapping the name produces a lookup that misses exactly as
# it missed before, on a diff that reads to the next person as a fix already
# applied. That is strictly worse than the stale name, because the stale name
# still says out loud that something is unfinished. So the answer to these is
# to RECORD what was read, not to repoint — and without a marker, recording it
# leaves the gate raising a question somebody has already answered, which is
# how an answered finding gets re-litigated by whoever turns the gate on.
#
# WHY THIS DOES NOT REOPEN "PROSE NEVER VOUCHES FOR A BINDING"
# -----------------------------------------------------------
# It looks like the rule exclusion 2 exists to prevent: a comment switching a
# finding off. The difference is that a marker is an EXPLICIT ACT NAMING THIS
# GATE, and the thing exclusion 2 got wrong was INCIDENTAL prose — launchpad
# documented a known gap, the words `integriq` and `dossiq` appeared in the
# file, and two live findings went dark with nobody intending it. Nobody
# writes `@stale-fleet-app-id exclude` by accident.
#
# It is scoped to the STATEMENT, the same unit exclusion 2 uses, so a marker
# on one binding cannot reach the next one down the file. And an excluded
# finding is COUNTED AND PRINTED on every run: an exclusion that suppressed
# silently would be the silent-exclusion bug wearing the fix's clothes, which
# this checker has already made once (see the slug/use-site ordering below).
#
# WHERE THE MARKER GOES, AND WHAT HAPPENS WHEN IT IS PUT SOMEWHERE ELSE
# ---------------------------------------------------------------------
# It attaches to the BINDING: the statement's own docblock, or the comment
# lines directly above the line, which are inside the statement's range
# because a range opens where the previous statement's terminator closed. That
# is where these get written anyway — every one of the ten answered findings
# this shipped for already had its evidence in a comment sitting directly
# above the stale line, or in the docblock of the constant holding it.
#
# The ENCLOSING METHOD's docblock is deliberately out of scope: a marker there
# would cover every stale binding in the body, including ones added later that
# nobody read the other repo about.
#
# But a rule that just quietly does not apply is the failure mode this whole
# package is about, so a marker that exists in the file and reaches no finding
# is REPORTED as misplaced rather than ignored. Getting that wrong is a
# question — "why is my exclusion not working" — and a question with an answer
# printed next to it costs minutes instead of an afternoon.
#
# A BARE `@stale-fleet-app-id exclude` WITH NO REASON DOES NOT EXCLUDE. The
# finding stands and the bare marker is reported, matching every other gate in
# the suite since .github#400/#412 — the whole value of an exclusion here is
# the evidence, so an exclusion with no evidence is the one shape that must
# not work.
#
# SLUG FINDINGS TAKE NO MARKER, ON PURPOSE. A stale name can be answered by
# reading the other repo; a stale register slug cannot be answered in prose at
# all. Both slugs are live across the fleet depending on whether a given
# instance has run the rename repair, so the fix is a probe for the slug the
# register actually answers to. Nothing anybody writes in a comment makes an
# old slug return rows on a migrated instance, and offering a marker there
# would only offer a way to silence a defect that is still a defect.
EXCLUDE_RE = re.compile(exclude_pattern("stale-fleet-app-id"))


def file_markers(lines: list[str]) -> list[tuple[int, bool]]:
    """Every exclusion marker in the file, as ``(line index, has a reason)``.

    Collected once per file rather than per finding so that a marker which
    reaches NO finding can be reported. A marker written in the enclosing
    method's docblock is out of scope on purpose, and a scope rule that just
    quietly does not apply is indistinguishable from a broken one.

    :param lines: Every raw line of the file, prose included.
    :return: One entry per marker found.
    """
    out: list[tuple[int, bool]] = []
    for i, line in enumerate(lines):
        m = EXCLUDE_RE.search(line)
        if m is None:
            continue
        # Each checker strips the trailing comment syntax of the file type it
        # reads; this one reads four, and two of them close a comment on the
        # marker's own line: `*/` a PHP or JS docblock, `-->` a Vue template
        # comment. Leaving those attached makes `*/` alone read as a reason.
        reason = m.group("reason").strip()
        for tail in ("*/", "-->"):
            if reason.endswith(tail):
                reason = reason[:-len(tail)].strip()
        out.append((i, is_reason_bearing(reason)))
    return out


def excluded(markers: list[tuple[int, bool]],
             span: tuple[int, int]) -> tuple[bool, bool]:
    """Whether the statement at *span* carries a reason-bearing marker.

    :param markers: Every marker in the file, from :func:`file_markers`.
    :param span:    The inclusive line-index range of the statement.
    :return: ``(excluded, saw_a_bare_marker in this span)``.
    """
    start, end = span
    bare = False
    for idx, has_reason in markers:
        if not start <= idx <= end:
            continue
        if has_reason:
            return True, False
        bare = True
    return False, bare


VISION_LIMIT = (
    "[gate-115] stale-fleet-app-id: this gate reads NAMES only. It cannot see "
    "whether a method or route you point at exists on the other side, and a "
    "repoint that lands on a missing method fails exactly as silently as the "
    "stale name did. Closing that half needs cross-repo surface reading "
    "(gate-67's model). This is not it."
)


def code_lines(lines: list[str]) -> list[str | None]:
    """Each line, or None where it is prose.

    Whether a line is prose is a STATEFUL question, not a prefix one. A block
    comment written without leading asterisks, the house style for the
    `<!-- ... -->` header of a Vue SFC, has continuation lines starting with an
    ordinary word, and a prefix rule reads every one of them as code. That is
    how learniq's App.vue header, which explains in prose which routes it calls
    on integriq, was reported as two stale bindings.
    """
    out: list[str | None] = []
    in_block = False
    for line in lines:
        if in_block:
            out.append(None)
            if BLOCK_CLOSE.search(line):
                in_block = False
            continue
        if BLOCK_OPEN.match(line) and not BLOCK_CLOSE.search(line):
            in_block = True
            out.append(None)
            continue
        out.append(None if COMMENT.match(line) else line)
    return out


def _next_code(code: list[str | None], i: int) -> str | None:
    """The next line that is not prose, or None."""
    for nxt in code[i + 1:]:
        if nxt is not None:
            return nxt
    return None


def statement_blocks(code: list[str | None]) -> list[str]:
    """For each line, the text of the statement it belongs to.

    THE DUAL-SPELLING ACCEPT IS SCOPED TO A STATEMENT, NOT THE FILE, and that
    is the whole point of this function.

    A file-wide accept looked principled and under-reported in the worst
    possible direction. launchpad's sweep left two lookups deliberately
    unrepointed because their targets do not exist, and wrote comments naming
    `integriq` and `dossiq` to record what had been read. Those names then
    appeared somewhere in the file, so the file-wide test suppressed both
    findings. Documenting a known gap is exactly the behaviour we want, and it
    was what switched the gate off. The count read 1 where 2 were stale.

    A statement is the right unit because it is the unit the real dual
    registrations occupy. They are array literals listing both spellings,
    newest first:

        private const DECISION_CONCLUDED_EVENTS = [
            'OCA\\Decidiq\\Event\\DecisionConcludedEvent',
            'OCA\\Decidesk\\Event\\DecisionConcludedEvent',
        ];

    Both names sit in one statement, so a line-scoped accept would flag the
    fallback and push authors to delete it, re-breaking every unmigrated
    instance. A statement-scoped accept covers the array and stops at its
    semicolon.

    Prose does not count either way: only code lines are joined, so a comment
    naming the successor can no longer vouch for a binding.
    """
    ranges = statement_ranges(code)
    blocks: list[str] = [""] * len(code)
    for i, (start, end) in enumerate(ranges):
        blocks[i] = "\n".join(x for x in code[start:end + 1] if x is not None)
    return blocks


def statement_ranges(code: list[str | None]) -> list[tuple[int, int]]:
    """For each line, the half-open-inclusive line range of its statement.

    SPLIT OUT OF `statement_blocks` SO THERE IS ONE DEFINITION OF "STATEMENT".
    `statement_blocks` joins the CODE in a statement, which is what the
    dual-spelling accept needs; the exclusion marker needs the same unit
    expressed as line numbers, so it can read the PROSE inside it too. Two
    functions each deciding for themselves where a statement ends would drift,
    and the drift would show up as an exclusion that silently stops applying.

    A range starts on the line after the previous statement's terminator, so
    the docblock or comment written above a statement is INSIDE that
    statement's range rather than outside it. That is what makes a marker
    placed where an author would naturally write it — in the comment
    explaining the finding — attach to the finding below it.
    """
    ranges: list[tuple[int, int]] = [(0, 0)] * len(code)
    start = 0
    for i, line in enumerate(code):
        if line is None:
            continue
        # AN IMPORT BLOCK IS ONE DECLARATION REGION. A dual-spelling pair can
        # be written as two aliased imports rather than two array entries:
        #
        #     use OCA\Decidiq\Event\DecisionConcludedEvent as DecidiqEvent;
        #     use OCA\Decidesk\Event\DecisionConcludedEvent as DecideskEvent;
        #
        # Each `use` ends in its own semicolon, so splitting on semicolons puts
        # the fallback in a statement of its own and flags it. That is the same
        # construct exclusion 2 already accepts, at a different syntax level, so
        # a run of consecutive imports is held open as one block.
        if IMPORT.match(line) and _next_code(code, i) is not None and IMPORT.match(_next_code(code, i)):
            continue
        if line.rstrip().endswith((";", "{", "}")):
            for j in range(start, i + 1):
                ranges[j] = (start, i)
            start = i + 1
    if start < len(code):
        last = len(code) - 1
        for j in range(start, len(code)):
            ranges[j] = (start, last)
    return ranges



def const_used_in_lookup(name: str, code: list[str | None], lookup, path) -> bool:
    """Whether a constant of this name is referenced from a lookup shape.

    The alternative is judging a constant by its NAME, which cannot tell a
    lookup key from a value written into stored data. hermiq's
    `SOURCE_APP_STAMP = 'scholiq'` is persisted into a required `sourceApp`
    schema property whose seeded rows already carry it; dossiq's
    `OPENCONNECTOR_APP = 'openconnector'` is passed straight to
    `isInstalled()`. Same shape, opposite verdicts, and only the use site
    separates them.

    Only code lines count, for the same reason prose never vouches for a
    binding elsewhere in this checker. Unresolved is treated as NOT a lookup,
    so the ambiguous case is a miss rather than a false accusation. The lookup shapes are checked directly on
    every other line, so a constant that is genuinely used in one is normally
    caught at the call site anyway.
    """
    if not name:
        return False
    ref = re.compile(r"(?:self|static|\$this)\s*(?:::|->)\s*" + re.escape(name) + r"\b")
    # CODE LINES ONLY. Reading raw text let a comment vouch: a note saying
    # "self::NAME is never passed to isInstalled()" contains both the
    # reference and a lookup call, and would mark the constant as used.
    for line in code:
        if line is None or not ref.search(line):
            continue
        if lookup.search(line) or path.search(line):
            return True
        # `isInstalled(self::NAME)` matches `lookup` only when the argument is
        # a literal, so also accept the shapes that take a constant.
        if re.search(r"(?:is(?:App)?Installed|isEnabledForUser|linkToRoute(?:Absolute)?"
                     r"|class_exists|interface_exists|->get)\s*\(", line):
            return True
    return False


def own_former_names(root: str) -> tuple[str | None, str | None]:
    """This app's own retired id AND retired namespace.

    An app naming either of its own former names is always a migration or a
    frozen handshake key, never a lookup into another app. Both halves matter
    and missing the second one under-reports nothing but over-reports plenty:
    integriq's `MigrateStoredJobClasses` holds
    `OLD_CLASS_PREFIX = 'OCA\\OpenConnector\\'`, thematiq's
    `MigrateStoredClassNames` names `OCA\\NLDesign\\Mail\\...`, and stackiq's
    `MigrateBackgroundJobClasses` lists four `OCA\\SoftwareCatalog\\...` job
    classes. Every one of those is that app rewriting rows it wrote itself
    under its old name, which is the migration working, not a stale binding.

    Derived from `<id>` and `<namespace>` rather than configured, so it cannot
    drift out of date.
    """
    info = os.path.join(root, "appinfo", "info.xml")
    if not os.path.isfile(info):
        return None, None
    try:
        root_el = ET.parse(info).getroot()
    except ET.ParseError:
        return None, None
    app_id = (root_el.findtext("id") or "").strip()
    ns = (root_el.findtext("namespace") or "").strip()
    old_id = next((o for o, n in IDS.items() if n == app_id), None)
    old_ns = next((o for o, n in NAMESPACES.items() if n == ns), None)
    return old_id, old_ns


def scan_files(root: str) -> list[str]:
    """Tracked files under the scanned directories, git-aware, walk as fallback."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", *SCAN_DIRS],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode == 0 and out.stdout.strip():
            return [f for f in out.stdout.split() if f.endswith(SCAN_EXT)]
    except (OSError, subprocess.SubprocessError):
        pass

    found = []
    for d in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, d)):
            dirnames[:] = [x for x in dirnames if x not in ("node_modules", "vendor")]
            for fn in filenames:
                if fn.endswith(SCAN_EXT):
                    found.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return found


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not any(os.path.isdir(os.path.join(root, d)) for d in SCAN_DIRS):
        print("[gate-115] stale-fleet-app-id: no lib/, src/ or appinfo/ here.")
        return 4

    mine, mine_ns = own_former_names(root)
    ids = {k: v for k, v in IDS.items() if k != mine}
    namespaces = {k: v for k, v in NAMESPACES.items() if k != mine_ns}
    id_alt = "|".join(ids)

    lookup = re.compile(
        rf"(?:{LOOKUP_CALLS})\(\s*['\"][^'\"]*\b({id_alt})\b", re.I)
    path = re.compile(rf"/apps/({id_alt})/", re.I)
    nspat = re.compile(r"OCA[\\]{1,2}(" + "|".join(namespaces) + r")[\\]")
    # A binding whose value is EXACTLY a retired id. A substring such as
    # 'decidesk-default' is a stored connection id and is deliberately not
    # matched: renaming stored data orphans it.
    # A binding whose value is EXACTLY a retired id. Judged by its USE SITE
    # below, never by its name, which is also what keeps `nldesign` safe:
    # that word is BOTH a retired app id and the live design-system id
    # nextcloud-vue hard-compares against (`theme.source !== 'nldesign'`
    # bails). `source: 'nldesign'` feeds no lookup, so it is not a finding,
    # while `/apps/nldesign/...` still is because the path rule reads a
    # context that can only mean the app. No carve-out is needed for it, and
    # an earlier draft that added one was removed as dead special-casing.
    bind = re.compile(
        rf"(?:const\s+(?P<name>\w+)\s*=|(?P<key>\w+)\s*[:=]>?)"
        rf"\s*['\"]({id_alt})['\"]\s*[;,)]", re.I)
    # An OpenRegister register slug, by the name it is bound to or the argument
    # it is passed as. Stored data, frozen on purpose. See exclusion 4 above.
    # Anchored on the END of the binding name (…REGISTER, …SLUG) so
    # `CONNECTOR_REGISTER` and `OPENCONNECTOR_REGISTER_SLUG` are excluded while
    # a name that merely starts with the word, such as `REGISTERED_APP`, is
    # still judged.
    slug = re.compile(
        r"(?:\w*(?:REGISTER|SLUG)\s*=|\bregister\s*[:=]>?\s*['\"])", re.I)

    findings: list[str] = []
    slug_hits: list[str] = []
    excluded_hits: list[str] = []
    bare_markers: list[str] = []
    misplaced: list[str] = []
    for rel in scan_files(root):
        if rel.endswith("FleetAppId.php"):
            continue  # the rename map itself
        try:
            # errors="replace" rather than a bare open: a repo can carry a
            # non-UTF-8 fixture under lib/, and one decode error must not abort
            # the scan of every file after it. A replaced byte cannot match any
            # pattern here, so a mangled line can only ever be a miss.
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue

        # Whether a line is prose is a STATEFUL question, not a prefix one. A
        # block comment written without leading asterisks — the house style for
        # the `<!-- ... -->` header of a Vue SFC — has continuation lines that
        # start with an ordinary word, and a prefix rule reads every one of
        # them as code. That is how learniq's App.vue header, which explains in
        # prose which routes it calls on integriq, was reported as two stale
        # bindings.
        lines = text.split("\n")
        code = code_lines(lines)
        blocks = statement_blocks(code)
        ranges = statement_ranges(code)
        markers = file_markers(lines)
        reached: set[int] = set()

        for lineno, line in enumerate(lines, 1):
            if code[lineno - 1] is None:
                continue
            m = lookup.search(line) or path.search(line) or nspat.search(line) or bind.search(line)
            if m is None:
                continue

            # ORDER MATTERS HERE. The slug check runs BEFORE the use-site test,
            # because a slug constant is never "used as a lookup id" and would
            # otherwise be dropped by that test and never recorded. Getting
            # this the other way round made the advisory print nothing while
            # the count still read zero, which is the silent-exclusion bug
            # wearing the fix's clothes.
            if slug.search(line):
                slug_hits.append(
                    f"  {rel}:{lineno}  [register slug {m.group(m.lastindex)}]  {line.strip()[:110]}")
                continue

            # A CONSTANT HOLDING A BARE ID IS ONLY A FINDING WHEN IT IS
            # ACTUALLY USED AS ONE. Whether the value is a lookup key or a
            # persisted stamp is not readable from its name, and guessing from
            # the name is how hermiq's `SOURCE_APP_STAMP = 'scholiq'` was
            # reported: `sourceApp` is a required schema property and three
            # seeded rows already carry that value, so renaming it in code
            # splits the field into two vocabularies rather than migrating it.
            # So a constant is judged by its USE SITE.
            if lookup.search(line) is None and path.search(line) is None \
                    and nspat.search(line) is None:
                if not const_used_in_lookup(m.groupdict().get("name"), code, lookup, path):
                    continue
            old = m.group(m.lastindex)
            new = namespaces.get(old) or ids.get(old.lower())
            # A dual-spelling list is correct, not stale — but only when the
            # current name is a SIBLING BINDING in the same statement.
            if new and new in blocks[lineno - 1]:
                continue
            # RECORDED BY A HUMAN WHO READ THE OTHER REPO. Last, so a marker
            # can only ever silence something that WOULD have been reported:
            # placing this test earlier would let a marker "exclude" a line
            # that was never a finding, and the count would read as evidence
            # that somebody had answered a question nobody had asked.
            is_excluded, bare = excluded(markers, ranges[lineno - 1])
            span = ranges[lineno - 1]
            reached.update(i for i, _ in markers if span[0] <= i <= span[1])
            if is_excluded:
                excluded_hits.append(
                    f"  {rel}:{lineno}  [{old} -> {new}]  {line.strip()[:110]}")
                continue
            if bare:
                bare_markers.append(f"  {rel}:{lineno}")
            findings.append(f"  {rel}:{lineno}  [{old} -> {new}]  {line.strip()[:110]}")

        misplaced.extend(
            f"  {rel}:{i + 1}  {lines[i].strip()[:110]}"
            for i, _ in markers if i not in reached)

    own = ", ".join(x for x in (mine, mine_ns) if x)
    print(f"[gate-115] stale-fleet-app-id: {len(findings)} cross-app lookup(s) "
          f"naming a retired id or namespace"
          + (f" (this app's own former name(s), {own}, are excluded)" if own else ""))
    print(VISION_LIMIT)
    for f in findings:
        print(f)

    # AN EXCLUSION IS PRINTED, ALWAYS. A marker that removed a line from the
    # count and left no trace would make "0 findings" mean two different
    # things — nothing stale, or somebody decided the stale thing was fine —
    # and a reader has no way to tell those apart. This gate has already made
    # the silent version of that mistake once, in the slug/use-site ordering
    # above, where the advisory printed nothing while the count still read
    # zero. So the recorded answers stay visible on a clean run.
    if excluded_hits:
        print(f"[gate-115] stale-fleet-app-id: {len(excluded_hits)} finding(s) "
              f"recorded with a reason-bearing @stale-fleet-app-id exclude marker "
              f"— read the reason beside each before trusting it, and re-check it "
              f"against the other app's tree when that app changes")
        for f in excluded_hits:
            print(f)

    if bare_markers:
        print(f"[gate-115] stale-fleet-app-id: {len(bare_markers)} bare "
              f"@stale-fleet-app-id exclude marker(s) with no reason — these "
              f"exclude NOTHING and the finding stands. The evidence is the whole "
              f"point of the marker: name what you read in the other repo and "
              f"what you found there")
        for f in bare_markers:
            print(f)

    if misplaced:
        print(f"[gate-115] stale-fleet-app-id: {len(misplaced)} @stale-fleet-app-id "
              f"exclude marker(s) that reach no finding. The marker attaches to the "
              f"BINDING — the statement's own docblock, or the comment lines directly "
              f"above the line — not to the enclosing method, and not to a register "
              f"slug, which is answered by probing OpenRegister rather than in prose")
        for f in misplaced:
            print(f)

    if slug_hits:
        print(f"[gate-115] stale-fleet-app-id: {len(slug_hits)} OpenRegister register "
              f"slug reference(s) naming a slug the owning app has migrated away from")
        print("[gate-115] stale-fleet-app-id: these are DEFECTS, listed separately "
              "because the fix differs. A consumer naming an old slug reads zero rows "
              "on a migrated instance and calls it 'no data', which is quieter than a "
              "404. Nine apps ship a slug-rename repair step and every renamed app's "
              "register json declares the new slug. DO NOT SWAP THE LITERAL: both "
              "slugs are live across the fleet depending on whether an instance has "
              "run that repair, so swapping breaks every instance that has not. Probe "
              "OpenRegister for the slug the register actually answers to.")
        for f in slug_hits:
            print(f)

    return 1 if (findings or slug_hits) else 0


if __name__ == "__main__":
    sys.exit(main())
