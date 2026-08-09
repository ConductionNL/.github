#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-19 e2e-coverage — diff-scoped @e2e scenario traceability enforcer.

Two scenario formats are supported:

**Format A — heading-based (classic):**

    #### Scenario: <title>

    <prose / WHEN-THEN bullet list>

**Format B — numbered list under a bold marker (alternative):**

    ### REQ-DECOMP-001: <title>
    <prose>

    **Scenarios:**

    1. **GIVEN** ... **WHEN** ... **THEN** ...
    2. **GIVEN** ... **WHEN** ... **THEN** ...

Both formats must appear inside ``openspec/specs/<spec-name>/spec.md`` files
that are ADDED or MODIFIED in a PR. Every such scenario must be referenced by
at least one Playwright e2e test file under ``tests/e2e/**`` (``*.spec.ts``,
``*.spec.js``, ``*.test.ts``, ``*.test.js``). This closes the loop between the
*what-should-happen* (the scenario in the spec) and the *automated proof* (the
e2e test that asserts it in a browser).

The gate is the e2e companion to gate-16 (``check_spec_coverage.py``), which
enforces that code methods carry ``@spec`` back-references. Together they give a
spec → code → test traceability chain.

Annotation convention
======================

In an e2e test file, reference a scenario with **either** form (in a comment or
inside a test title/describe string):

    // @e2e openspec/specs/<spec-name>/spec.md#<scenario-slug>
    // @e2e <spec-name>::<scenario-slug>

**Format A slug:** kebab-case of the ``#### Scenario:`` heading text
(lower-case, punctuation stripped, words joined with ``-``).

**Format B slug:** ``<parent-req-slug>-scenario-<n>`` where ``parent-req-slug``
is the kebab-case of the enclosing ``### REQ-...:`` or ``### Requirement:``
heading (text after the colon, or the full heading if no colon), and ``<n>`` is
the 1-based number of the item under ``**Scenarios:**``.  The slug is
deterministic regardless of prose content so renaming scenario text does not
break existing ``@e2e`` annotations.

Example::

    // @e2e ai-chat-companion::widget-receives-context-on-a-detail-page
    // @e2e openspec/specs/ai-chat-companion/spec.md#widget-receives-context-on-a-detail-page
    // @e2e method-decomposition::req-decomp-001-settingscontroller-decomposition-scenario-1

Exclusions
==========

A scenario can be excluded from e2e-coverage enforcement by placing
``@e2e exclude <reason>`` in the spec's scenario block or its parent requirement
block (reason required — a bare ``@e2e exclude`` is non-compliant, just like
gate-16's ``@spec exclude`` rule).

For Format B (numbered scenarios): an ``@e2e exclude`` anywhere in the numbered
item's text, or on/under the parent ``### REQ-...:`` heading, excludes that
numbered scenario.

A **whole-spec** can be excluded by placing ``@e2e exclude <reason>`` on a line
directly after the spec's title / ``## Purpose`` section header. This is the
correct mechanism for pure-backend or API-contract specs that are covered by
Newman/PHPUnit instead of Playwright.

Diff scope
==========

In gate mode (default), the gate is diff-scoped via ``HYDRA_GATE_BASE_REF``
(default ``origin/development``): only scenarios in spec files that are ADDED or
MODIFIED in the PR are checked. Scenarios in untouched spec files are never
flagged. Exit code = number of uncovered (or bare-exclude) scenarios.

Report mode (``--mode report``) scans the entire ``openspec/specs/`` tree and
emits a JSON summary — not diff-scoped, always exits 0.

Usage::

    # Gate mode (diff-scoped):
    HYDRA_GATE_BASE_REF=origin/development python3 scripts/lib/check_e2e_coverage.py [app-dir]

    # Report mode (full-repo):
    python3 scripts/lib/check_e2e_coverage.py [app-dir] --mode report
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9\s-]")
_SLUG_SPACES_RE = re.compile(r"[\s_]+")


def _slugify(text: str) -> str:
    """Convert a scenario heading to a kebab-case slug.

    Matches the convention used by spec authors: lower-case, strip
    punctuation (except hyphens), collapse whitespace to single ``-``.
    """
    t = text.lower()
    t = _SLUG_STRIP_RE.sub("", t)
    t = _SLUG_SPACES_RE.sub("-", t.strip())
    t = re.sub(r"-{2,}", "-", t)
    return t.strip("-")


# ---------------------------------------------------------------------------
# Spec parsing
# ---------------------------------------------------------------------------

# Headings — Format A (classic)
_SCENARIO_RE = re.compile(r"^#{4}\s+Scenario:\s*(.+)", re.IGNORECASE)
# Headings — any ### heading that may parent scenarios (Requirement: OR REQ-*: patterns)
_REQUIREMENT_RE = re.compile(r"^#{3}\s+(?:Requirement:|REQ-[A-Z0-9_-]+:)\s*(.*)", re.IGNORECASE)
_PURPOSE_RE = re.compile(r"^(#{1,2}\s+(?:Purpose|.*Specification))", re.IGNORECASE)

# Format B — bold **Scenarios:** / **Scenario:** marker line
_ALT_SCENARIOS_MARKER_RE = re.compile(r"^\*\*Scenarios?:\*\*\s*$", re.IGNORECASE)
# Format B — numbered scenario item: starts with "N. **GIVEN**" or "N. **WHEN**"
_ALT_SCENARIO_ITEM_RE = re.compile(
    r"^(?P<n>\d+)\.\s+\*\*(?:GIVEN|WHEN)\b", re.IGNORECASE
)

# Exclusion marker: `@e2e exclude <reason>` (inline or on its own line)
_EXCLUDE_RE = re.compile(r"@e2e\s+exclude\b[ \t]*(?P<reason>.*?)\s*$")

# Whole-spec exclusion must be a STANDALONE directive line: the `@e2e exclude`
# token is the dominant content of the line, optionally prefixed by markdown
# bullet / blockquote / heading markers. Prose that merely *mentions*
# `@e2e exclude` mid-sentence (e.g. a Purpose paragraph "...scenarios annotated
# @e2e exclude below") must NOT exclude the entire spec.
_WHOLE_SPEC_EXCLUDE_RE = re.compile(
    r"^[ \t>*#\-]*@e2e\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"
)


def _parse_exclusion(text: str) -> tuple[bool, str | None]:
    """Check whether ``text`` carries an ``@e2e exclude`` marker (inline OK).

    Returns ``(excluded, reason_or_None)``.
    ``reason`` is ``None`` when the marker is bare (non-compliant).
    Used for requirement-level and scenario-level exclusion, where an inline
    `@e2e exclude <reason>` appended to a heading or bullet is intentional.
    """
    m = _EXCLUDE_RE.search(text)
    if not m:
        return False, None
    reason = m.group("reason").strip()
    return True, reason if reason else None


def _parse_whole_spec_exclusion(text: str) -> tuple[bool, str | None]:
    """Whole-spec exclusion — only fires on a STANDALONE `@e2e exclude` line.

    Unlike :func:`_parse_exclusion` (which searches anywhere in the line), this
    anchors the directive to the line start (after optional markdown markers),
    so a descriptive sentence that happens to contain the phrase does not
    silently exclude the whole spec.
    """
    m = _WHOLE_SPEC_EXCLUDE_RE.match(text)
    if not m:
        return False, None
    reason = m.group("reason").strip()
    return True, reason if reason else None


def _make_scenario_entry(
    spec_name: str,
    scenario_label: str,
    slug: str,
    whole_spec_excluded: bool,
    whole_spec_reason: str | None,
    whole_spec_bare: bool,
    current_req_excluded: bool,
    current_req_bare: bool,
    scen_block_lines: list[str],
) -> dict:
    """Build a scenario result dict applying the exclusion priority chain."""
    scen_excluded = False
    scen_reason: str | None = None
    scen_bare = False
    for bl in scen_block_lines:
        exc, reason = _parse_exclusion(bl)
        if exc:
            scen_excluded = True
            scen_reason = reason
            scen_bare = reason is None
            break

    # Priority: whole-spec > requirement-level > scenario-level
    if whole_spec_excluded:
        final_excluded = True
        final_reason = whole_spec_reason
        final_bare = whole_spec_bare
    elif current_req_excluded:
        final_excluded = True
        final_reason = None if current_req_bare else "<inherited from requirement>"
        final_bare = current_req_bare
    elif scen_excluded:
        final_excluded = True
        final_reason = scen_reason
        final_bare = scen_bare
    else:
        final_excluded = False
        final_reason = None
        final_bare = False

    return {
        "spec": spec_name,
        "scenario": scenario_label,
        "slug": slug,
        "ref": f"{spec_name}::{slug}",
        "excluded": final_excluded,
        "exclude_reason": final_reason,
        "bare_exclude": final_bare,
    }


def parse_spec_scenarios(spec_path: Path) -> list[dict]:
    """Parse a spec.md and return a list of scenario dicts.

    Two scenario formats are recognised:

    **Format A (classic heading)**::

        #### Scenario: <title>
        <body lines>

    Slug: ``_slugify(title)``

    **Format B (numbered list under bold Scenarios: marker)**::

        ### REQ-XYZ-001: <req title>
        <prose>

        **Scenarios:**

        1. **GIVEN** ... **WHEN** ... **THEN** ...
        2. **GIVEN** ... **WHEN** ... **THEN** ...

    Slug: ``<parent-req-slug>-scenario-<n>`` where ``parent-req-slug`` is
    derived from the enclosing ``### REQ-...:`` or ``### Requirement:`` heading
    and ``<n>`` is the 1-based item number.

    Each returned dict::

        {
            "spec": str,         # spec-name (dir name)
            "scenario": str,     # human-readable label
            "slug": str,         # kebab slug
            "ref": str,          # "<spec>::<slug>"
            "excluded": bool,
            "exclude_reason": str | None,   # None means bare (non-compliant)
            "bare_exclude": bool,           # True when excluded but no reason
        }
    """
    spec_name = spec_path.parent.name
    try:
        lines = spec_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    results: list[dict] = []

    # ---- detect a whole-spec exclusion: @e2e exclude before the first ### heading
    whole_spec_excluded = False
    whole_spec_reason: str | None = None
    whole_spec_bare = False
    for line in lines:
        if _REQUIREMENT_RE.match(line):
            break
        excluded, reason = _parse_whole_spec_exclusion(line)
        if excluded:
            whole_spec_excluded = True
            whole_spec_reason = reason
            whole_spec_bare = reason is None
            break

    # ---- walk the spec collecting scenarios (both formats) ----
    current_req_excluded = False
    current_req_bare = False
    current_req_slug = ""          # slug of the current ### heading (for Format B)

    # Format A state
    current_scenario_a: str | None = None
    scenario_a_lines: list[str] = []
    in_scenario_a = False

    # Format B state
    in_alt_scenarios_block = False   # True after seeing **Scenarios:**
    # pending numbered item being accumulated
    current_alt_n: int | None = None
    current_alt_lines: list[str] = []

    def _flush_scenario_a() -> None:
        nonlocal current_scenario_a, scenario_a_lines, in_scenario_a
        if current_scenario_a is None:
            return
        slug = _slugify(current_scenario_a)
        results.append(_make_scenario_entry(
            spec_name, current_scenario_a, slug,
            whole_spec_excluded, whole_spec_reason, whole_spec_bare,
            current_req_excluded, current_req_bare,
            scenario_a_lines,
        ))
        current_scenario_a = None
        scenario_a_lines = []
        in_scenario_a = False

    def _flush_alt_item() -> None:
        nonlocal current_alt_n, current_alt_lines
        if current_alt_n is None:
            return
        n = current_alt_n
        slug = f"{current_req_slug}-scenario-{n}" if current_req_slug else f"scenario-{n}"
        label = f"{current_req_slug} scenario {n}" if current_req_slug else f"scenario {n}"
        results.append(_make_scenario_entry(
            spec_name, label, slug,
            whole_spec_excluded, whole_spec_reason, whole_spec_bare,
            current_req_excluded, current_req_bare,
            current_alt_lines,
        ))
        current_alt_n = None
        current_alt_lines = []

    for line in lines:
        # ---- ### requirement heading (both formats share this) ----
        req_m = _REQUIREMENT_RE.match(line)
        if req_m:
            _flush_scenario_a()
            _flush_alt_item()
            in_scenario_a = False
            in_alt_scenarios_block = False
            current_req_excluded = False
            current_req_bare = False
            # Build slug from the text after the colon in the heading label.
            # The regex captures the text after the colon in group 1.
            heading_text = req_m.group(1).strip()
            # Also include any prefix before the captured group to form a full slug.
            # E.g. "### REQ-DECOMP-001: SettingsController Decomposition"
            # → full heading line minus leading hashes → "REQ-DECOMP-001: SettingsController..."
            # We want to slugify the whole meaningful part.
            full_heading = re.sub(r"^#{3}\s+", "", line).strip()
            current_req_slug = _slugify(full_heading)
            # Check the heading line itself for inline @e2e exclude
            exc, reason = _parse_exclusion(line)
            if exc:
                current_req_excluded = True
                current_req_bare = reason is None
            continue

        # ---- Format A: #### Scenario: heading ----
        scen_m = _SCENARIO_RE.match(line)
        if scen_m:
            _flush_scenario_a()
            _flush_alt_item()
            in_alt_scenarios_block = False
            current_scenario_a = scen_m.group(1).strip()
            in_scenario_a = True
            continue

        # ---- Format B: **Scenarios:** / **Scenario:** marker ----
        if _ALT_SCENARIOS_MARKER_RE.match(line):
            _flush_scenario_a()
            in_scenario_a = False
            in_alt_scenarios_block = True
            continue

        # ---- Format B: numbered item inside **Scenarios:** block ----
        if in_alt_scenarios_block:
            item_m = _ALT_SCENARIO_ITEM_RE.match(line)
            if item_m:
                _flush_alt_item()
                current_alt_n = int(item_m.group("n"))
                current_alt_lines = [line]
                continue
            # continuation line for the current numbered item
            if current_alt_n is not None:
                # Stop collecting if we hit a new ### heading (handled above)
                # or a blank line after the item content (next item will pick up)
                current_alt_lines.append(line)
                continue
            # blank/prose line while in alt block but no active item
            continue

        # ---- accumulate Format A scenario body ----
        if in_scenario_a:
            scenario_a_lines.append(line)
        else:
            # requirement body — check for requirement-level @e2e exclude
            exc, reason = _parse_exclusion(line)
            if exc and not current_req_excluded:
                current_req_excluded = True
                current_req_bare = reason is None

    _flush_scenario_a()
    _flush_alt_item()
    return results


# ---------------------------------------------------------------------------
# E2e test scanning
# ---------------------------------------------------------------------------

# Accept either annotation form:
#   @e2e openspec/specs/<spec>/<anything>spec.md#<slug>
#   @e2e <spec>::<slug>
# Both may appear in comments, test titles, describe strings — anywhere.
_E2E_PATH_RE = re.compile(
    r"@e2e\s+openspec/specs/(?P<spec>[^/]+)/[^\s#]*#(?P<slug>[A-Za-z0-9_-]+)"
)
_E2E_SHORT_RE = re.compile(
    r"@e2e\s+(?P<spec>[A-Za-z0-9_-]+)::(?P<slug>[A-Za-z0-9_-]+)"
)


# ---------------------------------------------------------------------------
# A PERMANENTLY-SKIPPED TEST IS NOT COVERAGE
#
# Observed on decidesk: four tests with EMPTY BODIES and a hardcoded
# `test.skip(true, ...)`. Each carried an `@e2e` tag, each was counted as
# traceability, and together they asserted NOTHING. That is a dead gate by
# construction — the tag says a scenario is proven, the test proves nothing,
# and the gate cannot tell the difference.
#
# What is dead:
#   test.skip('name', ...)      the modifier form — declares a skipped test
#   it.skip(...) / xit / xtest / test.fixme(...)
#   describe.skip(...)          takes every test inside it with it
#   test.skip(true)             an UNCONDITIONAL skip at the top of a body
#   test.skip()                 argument-less, same thing
#   an empty body               nothing but whitespace and comments
#
# What is NOT dead, and must keep counting:
#   test.skip(browserName === 'firefox', 'flaky on gecko')
#   test.skip(!process.env.CI, 'needs a CI fixture')
#
# ...because those run somewhere. A RUNTIME CONDITION is a real test with a
# guard; a literal `true` is a test someone turned off. Conflating them would
# swap this gate's blindness for a different one — refusing legitimate
# conditional skips — so the discriminator is the argument, not the call.
# `\b` is not enough of a boundary: it matches the `test` in `rx.test(text)`,
# and JavaScript's RegExp.prototype.test is not Playwright's test(). On
# openconnector, `dead-letter-replay.spec.ts` has
#
#     IGNORED_CONSOLE_PATTERNS.some((rx) => rx.test(text))
#
# in a helper ABOVE its tests, and the forward search from the file-level
# `@e2e` tags landed on it. `_ref_is_live` then read that call's "body" —
# there is none — and reported all 11 refs as "referenced only by a test that
# never runs", about a file whose tests run fine.
#
# `(?<![.\w$])` rejects a member call (`rx.test`, `foo.it`) and an identifier
# that merely ends in one (`latest(`, `submit(`), while leaving a bare
# `test(` / `it(` / `describe(` at a statement boundary matching.
#
# THAT LOOKBEHIND ALSO REJECTED PLAYWRIGHT'S OWN CANONICAL SPELLING.
# `test.describe.skip(` is the form every fleet repo actually writes, and the
# pattern above could not match it anywhere: at `test` the optional `mod`
# needs `.skip|.fixme|.failing` and finds `.describe`, so the required `\(`
# fails; at `describe` the lookbehind sees the preceding `.` and refuses. The
# whole construct was INVISIBLE — not "seen and judged live", never seen.
# Measured on the reproduction in #210: BOTH the tag above a
# `test.describe.skip` and the tag inside one came back LIVE, so the issue's
# own claim that the `above` case was handled correctly was too generous.
#
# The fix is an explicit, optional `test.` / `it.` NAMESPACE segment. It is
# named rather than general (`\w+\.`) on purpose: `rx.test(` and `foo.it(`
# must still be rejected, and only Playwright's two roots may open a block.
# The `.serial` / `.parallel` / `.only` segments are Playwright's other
# describe modifiers and are NOT switched-off markers — a `describe.only` runs
# (and suppresses everything else), so it stays live.
_TEST_DECL_RE = re.compile(
    r"(?<![.\w$])(?:(?:test|it)\s*\.\s*)?(?P<fn>test|it|describe)"
    r"(?:\s*\.\s*(?:serial|parallel))?"
    r"(?P<mod>\s*\.\s*(?:skip|fixme|failing))?"
    r"(?:\s*\.\s*only)?"
    r"\s*\(",
)
_XTEST_RE = re.compile(r"\b(?:xit|xtest|xdescribe)\s*\(")
# `test.skip(true)` / `test.skip( 1 )` / `test.skip()` — no runtime condition.
_UNCONDITIONAL_SKIP_RE = re.compile(
    r"\b(?:test|it)\s*\.\s*skip\s*\(\s*(?:\)|true\s*[,)]|1\s*[,)])"
)


def _strip_comments(text: str) -> str:
    """Remove // and /* */ comments so an empty body is not mistaken for a
    documented one. Crude but sufficient: this only ever decides "is there any
    executable statement here", never what the statement means."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"(?m)//.*$", " ", text)
    return text


def _close_paren(text: str, open_paren: int) -> int | None:
    """Index of the `)` matching the `(` at *open_paren*, or None."""
    depth = 0
    i = open_paren
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _is_switched_off(decl: str) -> bool:
    """True when *decl* opens a block that never runs.

    Reads the `mod` group of the declaration regex rather than re-deriving it,
    so `test.describe.skip(` and `describe.skip(` are judged by one rule. The
    hand-written pattern this replaces required the modifier to follow the
    ROOT identifier (`(?:test|it|describe)\\s*\\.\\s*(?:skip|…)`) and therefore
    could not see the namespaced form at all.
    """
    if _XTEST_RE.match(decl):
        return True
    m = _TEST_DECL_RE.match(decl)
    return bool(m and m.group("mod"))


def _decl_spans(text: str) -> list[tuple[int, int, str]]:
    """Every test/describe declaration in *text*, as (start, end, decl_text).

    `end` is the index of the declaration's closing paren, so `start..end`
    spans the whole call including its callback body.
    """
    spans: list[tuple[int, int, str]] = []
    for rex in (_TEST_DECL_RE, _XTEST_RE):
        for m in rex.finditer(text):
            close = _close_paren(text, m.end() - 1)
            if close is None:
                continue
            spans.append((m.start(), close, text[m.start():close + 1]))
    spans.sort()
    return spans


def _switched_off_ancestor(text: str, pos: int) -> str | None:
    """The innermost switched-off block ENCLOSING *pos*, if any.

    WHY THIS EXISTS (#210)
    ----------------------
    `_enclosing_block` only ever searches FORWARD, because the convention this
    module documents puts the tag in a comment immediately ABOVE the test it
    annotates. That is right for the test, and blind to everything wrapping it:

        test.describe.skip('outer', () => {
            // @e2e demo::something
            test('inner', async ({ page }) => { … })   <-- forward search lands here
        })

    The forward search finds the inner, un-skipped `test()`, reports it live,
    and the enclosing `describe.skip` — which is ABOVE the tag and takes every
    test inside it with it — is never consulted. The tag counted as coverage
    while nothing ran, and this is the position the convention itself tells
    people to write the tag in.

    Measured in the fleet at the time of the fix: 16 spec scenarios across
    openconnector (11) and scholiq (5).

    The rule is the same one the module docstring already states for
    `describe.skip(...)`; only the ancestor direction was missing. An ancestor
    that merely carries `.only` / `.serial` / `.parallel` is NOT switched off.
    """
    innermost: str | None = None
    for start, end, decl in _decl_spans(text):
        if start >= pos:
            break            # spans are sorted; nothing later can enclose pos
        if end < pos:
            continue         # closed before the tag — a sibling, not a parent
        if _is_switched_off(decl):
            innermost = decl
    return innermost


def _enclosing_block(text: str, pos: int) -> tuple[str, str] | None:
    """The nearest `test(`/`it(`/`describe(` declaration at or after *pos*, as
    (declaration_text, body_text).

    An `@e2e` tag conventionally sits in a comment immediately ABOVE the test
    it annotates, so the search runs forward from the tag. See
    :func:`_switched_off_ancestor` for the other direction, which this
    function deliberately does not cover.
    """
    m = _TEST_DECL_RE.search(text, pos)
    xm = _XTEST_RE.search(text, pos)
    if xm and (not m or xm.start() < m.start()):
        decl_start, open_paren = xm.start(), xm.end() - 1
    elif m:
        decl_start, open_paren = m.start(), m.end() - 1
    else:
        return None
    # Walk to the matching close paren of the declaration.
    i = _close_paren(text, open_paren)
    if i is None:
        return None
    whole = text[decl_start:i + 1]
    # THE BODY IS THE LAST BRACE-BALANCED GROUP, FOUND FROM THE END.
    #
    # Not the first `{`: in `test('name', async ({ page }) => { … })` the first
    # brace opens the fixture DESTRUCTURING, so a forward search returns
    # `{ page }) => {})` and an empty body then looks non-empty. Scanning back
    # from the closing paren finds the callback body itself.
    j = len(whole) - 2                      # skip the final ')'
    while j >= 0 and whole[j].isspace():
        j -= 1
    body = ""
    if j >= 0 and whole[j] == "}":
        depth = 0
        k = j
        while k >= 0:
            if whole[k] == "}":
                depth += 1
            elif whole[k] == "{":
                depth -= 1
                if depth == 0:
                    break
            k -= 1
        if k >= 0:
            body = whole[k:j + 1]
    return whole, body


def _has_own_unconditional_skip(block_body: str) -> bool:
    """An unconditional `test.skip(true)` belonging to THIS block, not a child.

    WHY THE OWNERSHIP TEST IS NEEDED
    --------------------------------
    Once `test.describe(` became visible to the declaration regex, a file-level
    tag started resolving to the enclosing describe rather than to the first
    test inside it — which is more accurate, but it also handed this check a
    body containing OTHER TESTS. A plain `_UNCONDITIONAL_SKIP_RE.search()` over
    that body then found a `test.skip(true, …)` written inside ONE nested test
    and condemned the whole group.

    Measured on launchpad `spec-coverage.spec.ts`: the header tag at :15 went
    from live to dead because a single nested test at :185 guards itself with
    `test.skip(true, 'allowUserDashboards is false in this environment')`. The
    other tests in that describe run fine. Killing the ref for that is the
    gate's blindness with the sign flipped, and it is not an improvement.

    Playwright does allow a group-level `test.skip()` — called directly in a
    describe body it skips every test in the group — so the check is kept, and
    only NESTED occurrences are disowned. An occurrence that starts exactly
    where a declaration span starts IS the skip call itself (`test.skip(true)`
    is both), so `<` is strict on the left.
    """
    nested = [(s, e) for s, e, _d in _decl_spans(block_body)]
    for m in _UNCONDITIONAL_SKIP_RE.finditer(block_body):
        if any(s < m.start() < e for s, e in nested):
            continue
        if _skip_is_guarded(block_body, m.start()):
            continue
        return True
    return False


# Openers that make the block they introduce conditional. `try` is here because
# a `test.skip(true)` in a try-body runs only while no earlier statement in that
# body threw; `finally` is deliberately absent — it always runs.
# ANCHORED AT THE END on purpose. A window-scan here matched the `try` in
# `} finally {` and called a finally-block guarded — the exact inversion this
# check exists to avoid. Only the token immediately before the `{` opens it.
_GUARD_OPENER_RE = re.compile(
    r"(?:^|[;{}\s)])(?:if|else\s+if|else|catch|for|while|switch|try)\s*"
    r"(?:\((?:[^()]|\([^()]*\))*\)\s*)?$",
)


def _skip_is_guarded(body: str, skip_pos: int) -> bool:
    """Is the `test.skip(true, …)` at *skip_pos* inside a conditional construct?

    WHY THIS EXISTS
    ---------------
    `test.skip(true, 'reason')` is NOT the syntax for "this test is switched
    off". It is Playwright's *skip from this point* form, and the condition
    lives at the CALL SITE:

        if (!response) { test.skip(true, 'container not reachable'); return }

    That test runs, and passes, whenever the guard is false. Treating it as
    permanently skipped is how this check came to report "referenced only by a
    test that never runs" about a test that ran and passed in the same CI run.

    Measured across 11 repos: **118** `test.skip(true, …)` call sites, of which
    **114 are guarded** and only **4** are genuinely unconditional. So the rule
    without this test misfires on ~96% of what it inspects.

    The false positive is worse than a normal one because the gate's prescribed
    remedy is `@e2e exclude` — so complying DELETES a true coverage claim and
    marks a tested scenario permanently untestable.

    HOW
    ---
    Walk backwards tracking brace depth to find the innermost `{` still open at
    *skip_pos*, then ask what introduced it. Repeat outward: a skip nested three
    blocks deep inside an `if` is still guarded. Stops at the enclosing test
    body, whose opener is the `test(`/`it(` callback — not a guard.
    """
    depth = 0
    i = skip_pos - 1
    while i >= 0:
        ch = body[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                # Innermost still-open block. What opened it?
                head = body[max(0, i - 200):i]
                if _GUARD_OPENER_RE.search(head):
                    return True
                # Not a guard (a function body, an object literal, the test
                # callback). Keep walking outward — an `if` may enclose it.
            else:
                depth -= 1
        i -= 1
    return False


def _ref_is_live(text: str, pos: int) -> bool:
    """Does the test enclosing the `@e2e` tag at *pos* actually assert
    anything?"""
    # OUTWARD FIRST. A switched-off ancestor takes everything inside it with
    # it, so no amount of body in the inner test can rescue the ref. Asking
    # the forward search first would find that inner test and answer "live".
    if _switched_off_ancestor(text, pos) is not None:
        return False
    block = _enclosing_block(text, pos)
    if block is None:
        # No enclosing test at all — a file-level tag. Treated as live: this
        # function exists to catch tests that were switched OFF, not to
        # invent a structural requirement the gate never had.
        return True
    decl, body = block
    head = decl[:decl.find("{") if "{" in decl else len(decl)]
    if _is_switched_off(decl):
        return False
    stripped = _strip_comments(body)
    if _has_own_unconditional_skip(stripped):
        return False
    inner = stripped.strip()
    if inner.startswith("{"):
        inner = inner[1:]
    if inner.endswith("}"):
        inner = inner[:-1]
    if not inner.strip():
        return False
    del head
    return True


def collect_covered_refs(app_dir: Path) -> set[str]:
    """Return the set of ``<spec>::<slug>`` refs found in any e2e test file.

    Only refs whose enclosing test actually runs are returned; see
    ``collect_ref_status`` for the dead ones and why.
    """
    live, _dead = collect_ref_status(app_dir)
    return live


def collect_ref_status(app_dir: Path) -> tuple[set[str], dict[str, str]]:
    """(live refs, {dead ref: reason}) across the app's e2e suite.

    A ref is live if ANY test referencing it runs. One skipped copy alongside
    a real one is not a regression, so the dead map only keeps refs with no
    live reference at all.
    """
    live: set[str] = set()
    dead: dict[str, str] = {}
    e2e_dir = app_dir / "tests" / "e2e"
    if not e2e_dir.is_dir():
        return live, dead
    for p in e2e_dir.rglob("*"):
        if not p.is_file():
            continue
        if not (p.suffix in (".ts", ".js") and (
            p.stem.endswith(".spec") or p.stem.endswith(".test")
            or ".spec." in p.name or ".test." in p.name
        )):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for rex in (_E2E_PATH_RE, _E2E_SHORT_RE):
            for m in rex.finditer(text):
                ref = f"{m.group('spec')}::{m.group('slug')}"
                if _ref_is_live(text, m.end()):
                    live.add(ref)
                    dead.pop(ref, None)
                elif ref not in live:
                    dead[ref] = (
                        f"referenced only by a test that never runs "
                        f"({p.relative_to(app_dir)})"
                    )
    return live, dead


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-c", "safe.directory=*", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout
    except OSError:
        return ""


def changed_spec_files(base_ref: str, app_dir: Path) -> set[str]:
    """Return relative paths of spec.md files touched in the PR diff."""
    diff = _git(["diff", "-U0", "--diff-filter=ACMR", "--name-only",
                 f"{base_ref}...HEAD"], app_dir)
    if not diff.strip():
        diff = _git(["diff", "-U0", "--diff-filter=ACMR", "--name-only",
                     base_ref], app_dir)
    paths: set[str] = set()
    for line in diff.splitlines():
        line = line.strip()
        if line.startswith("openspec/specs/") and line.endswith("spec.md"):
            paths.add(line)
    return paths


# ---------------------------------------------------------------------------
# Gate number for self-identification in output lines
# ---------------------------------------------------------------------------
GATE_NUM = 19


# ---------------------------------------------------------------------------
# Report mode
# ---------------------------------------------------------------------------


def run_report(app_dir: Path) -> int:
    """Full-repo scan. Emits JSON, always exits 0."""
    spec_root = app_dir / "openspec" / "specs"
    if not spec_root.is_dir():
        out = {
            "mode": "report",
            "app": app_dir.name,
            "totals": {"scenarios": 0, "covered": 0, "excluded": 0, "uncovered": 0},
            "uncovered": [],
            "coverage_pct": None,
        }
        print(json.dumps(out, indent=2))
        return 0

    covered_refs = collect_covered_refs(app_dir)

    all_scenarios: list[dict] = []
    for spec_md in sorted(spec_root.glob("*/spec.md")):
        all_scenarios.extend(parse_spec_scenarios(spec_md))

    totals = {"scenarios": len(all_scenarios), "covered": 0, "excluded": 0, "uncovered": 0}
    uncovered: list[dict] = []

    for s in all_scenarios:
        if s["excluded"] and not s["bare_exclude"]:
            totals["excluded"] += 1
        elif s["ref"] in covered_refs:
            totals["covered"] += 1
        else:
            totals["uncovered"] += 1
            uncovered.append({"ref": s["ref"], "spec": s["spec"], "scenario": s["scenario"]})

    denominator = totals["scenarios"] - totals["excluded"]
    coverage_pct = round(totals["covered"] / denominator * 100, 1) if denominator > 0 else None

    out = {
        "mode": "report",
        "app": app_dir.name,
        "totals": totals,
        "uncovered": uncovered,
        "coverage_pct": coverage_pct,
    }
    print(json.dumps(out, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Gate mode (diff-scoped)
# ---------------------------------------------------------------------------


def run_gate(app_dir: Path) -> int:
    """Diff-scoped gate. Returns the number of uncovered scenarios."""
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "origin/development")
    touched = changed_spec_files(base_ref, app_dir)

    if not touched:
        print(f"[gate-{GATE_NUM}] e2e-coverage: PASS — no spec files in diff")
        return 0

    covered_refs, dead_refs = collect_ref_status(app_dir)

    findings: list[str] = []
    for rel in sorted(touched):
        spec_md = app_dir / rel
        if not spec_md.is_file():
            continue
        scenarios = parse_spec_scenarios(spec_md)
        for s in scenarios:
            if s["excluded"] and not s["bare_exclude"]:
                # Legitimately excluded — not required
                continue
            if s["bare_exclude"]:
                # Bare @e2e exclude without reason — non-compliant, flag it
                findings.append(
                    f"{s['ref']} — @e2e exclude without reason (reason required)"
                )
            elif s["ref"] in dead_refs:
                # Named, but by a test that never runs. Saying "missing @e2e"
                # here would send someone to add a tag that is already there.
                findings.append(
                    f"{s['ref']} — @e2e tag present but the test does not run: "
                    f"{dead_refs[s['ref']]}. A permanently-skipped or empty test is "
                    f"not coverage: unskip it, give it a body, or replace the tag "
                    f"with a reason-bearing `@e2e exclude`."
                )
            elif s["ref"] not in covered_refs:
                findings.append(f"{s['ref']} — missing @e2e")

    for line in sorted(set(findings)):
        print(line)

    count = len(set(findings))
    if count == 0:
        print(f"[gate-{GATE_NUM}] e2e-coverage: PASS — {len(covered_refs)} reference(s) in e2e suite")
    else:
        print(
            f"[gate-{GATE_NUM}] e2e-coverage: FAIL — {count} scenario(s) without a running e2e test"
        )
    # An exit code is one byte. Returning the raw count means 266 leaves as
    # 10, and — the case that matters — a count of exactly 256 leaves as 0,
    # which the caller reads as PASS on 256 uncovered scenarios.
    #
    # The printed summary above carries the true number and is what the bash
    # gate now reports; this is only the pass/fail signal, so it is clamped
    # into the byte and never allowed to wrap to zero while findings exist.
    return min(count, 255)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    mode = "gate"
    app = "."
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--mode" and i + 1 < len(rest):
            mode = rest[i + 1]
            i += 2
            continue
        app = rest[i]
        i += 1
    app_dir = Path(app).resolve()
    if mode == "report":
        return run_report(app_dir)
    return run_gate(app_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
