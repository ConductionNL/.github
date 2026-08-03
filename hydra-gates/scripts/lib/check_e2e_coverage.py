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


def collect_covered_refs(app_dir: Path) -> set[str]:
    """Return the set of ``<spec>::<slug>`` refs found in any e2e test file."""
    covered: set[str] = set()
    e2e_dir = app_dir / "tests" / "e2e"
    if not e2e_dir.is_dir():
        return covered
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
        for m in _E2E_PATH_RE.finditer(text):
            covered.add(f"{m.group('spec')}::{m.group('slug')}")
        for m in _E2E_SHORT_RE.finditer(text):
            covered.add(f"{m.group('spec')}::{m.group('slug')}")
    return covered


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

    covered_refs = collect_covered_refs(app_dir)

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
            elif s["ref"] not in covered_refs:
                findings.append(f"{s['ref']} — missing @e2e")

    for line in sorted(set(findings)):
        print(line)

    count = len(set(findings))
    if count == 0:
        print(f"[gate-{GATE_NUM}] e2e-coverage: PASS — {len(covered_refs)} reference(s) in e2e suite")
    else:
        print(
            f"[gate-{GATE_NUM}] e2e-coverage: FAIL — {count} scenario(s) missing @e2e"
        )
    return count


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
