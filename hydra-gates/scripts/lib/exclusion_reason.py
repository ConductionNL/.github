#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""exclusion_reason — the ONE definition of "this exclusion carries a reason".

WHY THIS FILE EXISTS (.github#400)
==================================
Four gates let a change opt out of coverage by writing a reason next to the
marker::

    @spec     exclude <reason>     gate-16  spec-coverage
    @e2e      exclude <reason>     gate-19  e2e-coverage      (scenario, requirement AND whole-spec)
    @contract exclude <reason>     gate-25  contract-coverage
    @visual   exclude <reason>     gate-26  visual-coverage

All four captured the reason with the same regex and then asked the same
question about it — ``if reason:`` — which is Python truthiness, i.e. "is this
string non-empty". So::

    @spec exclude       ->  reason == ""    ->  falsy  ->  correctly REFUSED
    @spec exclude .     ->  reason == "."   ->  TRUTHY ->  credited as a reason

One full stop is the entire difference between a blocked PR and a green one.
Reproduced through the real wrapper on two repositories that were byte-identical
apart from that character.

THE COST OF THE BUG IS NOT ONE GATE
-----------------------------------
`#345` scores an exclusion as POSITIVE coverage, and `#356` lets a
requirement-level (or, in gate-19, whole-spec) marker blanket every sibling
scenario beneath it. Stack the three and a single punctuation mark can credit
dozens of scenarios as covered and add one to the distinct-reason count the
programme reads as evidence that exclusions were considered.

WHY A SHARED MODULE AND NOT FOUR PATCHES
----------------------------------------
The regex-plus-truthiness pair existed in four files. That is why it survived:
fixing gate-16 alone leaves three copies, and the next reader of
``check_visual_coverage.py`` has no way to know the rule lives somewhere else.
The predicate is defined ONCE here and imported. A fifth exclusion gate gets the
rule by construction rather than by copy-paste.

WHAT THIS MODULE DELIBERATELY DOES *NOT* DECIDE
-----------------------------------------------
The standing rule is that **an exemption's reason is a testable claim**: reasons
naming a *test artifact* hold, reasons naming a *state of the world* rot. That
is a SEMANTIC property, and no character count can measure it. ``@e2e exclude
not applicable here`` is twenty characters and says nothing; ``@e2e exclude
covered by`` is ten and is a truncated sentence. A length threshold that pretends
to grade reason QUALITY just teaches people to pad.

So this module draws a deliberately narrow line: it rejects reasons that are
STRUCTURALLY DEGENERATE — a marker that cannot be naming anything at all. It
does not, and must not, be read as certifying that what survives is a good
reason. Judging that needs a purpose-built check (see the residuals in the
`#400` findings note), not a `len()`.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------

# 1. AT LEAST ONE LETTER OR DIGIT.
#
# This is the rule that closes `#400`. Note it is deliberately stricter than
# "at least one word character": Python's ``\w`` also matches the underscore, so
# a reason of ``___`` would satisfy a ``\w`` rule while being exactly as
# meaningless as ``.``. Measured over all 18 core apps, the two rules reject the
# IDENTICAL set, so the stricter one is free.
_ALNUM_RE = re.compile(r"[^\W_]", re.UNICODE)

# 2. AT LEAST THIS MANY CHARACTERS, after the caller's normalisation.
#
# WHY 3, AND WHY NOT MORE — this number is a judgement call, so here is the
# reasoning rather than just the constant.
#
# The alphanumeric rule above cannot reject ``x``, ``ok`` or ``na``, which are
# no more testable than ``.``; the floor exists only for those. It is NOT an
# attempt to grade reasons (see the module docstring).
#
# Measured over all 18 core apps: a floor of 3, 8 or even 10 newly rejects
# NOTHING that a checker actually credits today. So the number was not chosen by
# what is affordable — all of them are free — but by what a character count can
# honestly claim.
#
# THIS PACKAGE ALREADY DISAGREES WITH ITSELF ABOUT THE ANSWER, and that is worth
# knowing before anyone "harmonises" it:
#
#   run-hydra-gates.sh gate-level opt-outs  `.{20,}`   20 chars
#   check_orphaned_write_capability.py      `.{10,}`   10 chars
#   these four gates, before .github#400    (any non-empty string)
#
# A gate-level opt-out written in a PR body waives an ENTIRE gate, so a high bar
# there is proportionate. These four markers are per-method and per-scenario and
# are used ~11,600 times across the fleet; they are a different act. Raising
# their bar from "any character" to 10 would be a POLICY change about how the
# fleet writes exclusions, not a bug fix, and it does not belong in the repair
# of #400. It is filed as a question for a human rather than decided here.
#
# So: 3, which is far enough below the data to have margin (the lowest reason
# length a checker actually credits is 10), and low enough that it is plainly a
# degenerate-token filter rather than a quality bar it cannot enforce.
#
# Raising this later is a ratchet and must be re-measured against the fleet
# first — at 11 it newly rejects 3 live reasons, all of them the truncated
# ``covered by``.
REASON_MIN_CHARS = 3


def is_reason_bearing(reason: str | None) -> bool:
    """Does ``reason`` count as a justification for an exclusion marker?

    ``reason`` is the text already normalised by the caller (each checker strips
    the trailing comment syntax of the file type it reads — ``*/`` for PHP
    docblocks, ``-->`` for Vue templates — and those differ legitimately, so
    normalisation stays with the caller and only the VERDICT is shared).

    Returns ``True`` only when the reason has at least one letter or digit and
    is at least :data:`REASON_MIN_CHARS` characters long.

    This replaces a bare ``if reason:`` truthiness test in four checkers, under
    which every non-empty string — including ``.`` — was a reason (`#400`).
    """
    if not reason:
        return False
    if len(reason) < REASON_MIN_CHARS:
        return False
    return _ALNUM_RE.search(reason) is not None


def why_rejected(reason: str | None) -> str:
    """A short, human-facing explanation for use in a gate finding.

    Kept beside the predicate so the message cannot drift out of step with the
    rule it describes.
    """
    if not reason:
        return "no reason given"
    if len(reason) < REASON_MIN_CHARS:
        return (
            f"reason {reason!r} is shorter than {REASON_MIN_CHARS} characters — "
            f"too short to name anything"
        )
    if _ALNUM_RE.search(reason) is None:
        return (
            f"reason {reason!r} contains no letter or digit — punctuation is "
            f"not a justification"
        )
    return ""


# ---------------------------------------------------------------------------
# The marker pattern
# ---------------------------------------------------------------------------


def exclude_pattern(tag: str, *, standalone: bool = False) -> str:
    """Return the regex SOURCE for a ``@<tag> exclude <reason>`` marker.

    ``standalone=True`` additionally anchors the marker to the start of the line
    (after optional markdown bullet / blockquote / heading markers). gate-19's
    WHOLE-SPEC form needs that: without the anchor, a Purpose paragraph reading
    "...scenarios annotated @e2e exclude below" silently excludes an entire spec
    file (`#358`). The scenario- and requirement-level forms are intentionally
    unanchored, because an inline marker appended to a heading or bullet is the
    documented way to write them.

    Returned as a source string, not a compiled pattern, so each caller keeps
    control of its own flags (``check_visual_coverage`` searches whole-file text
    and needs ``re.MULTILINE``; the others match line by line and must not).
    """
    lead = r"^[ \t>*#\-]*" if standalone else ""
    return lead + rf"@{tag}\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"
