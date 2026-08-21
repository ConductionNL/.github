#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 69 helper — page-type-discipline.

Every page in a manifest should be one of the three typed archetypes —
``index``, ``detail``, ``dashboard`` — and should actually render that type's
page component. Measured across the 19-app fleet on 2026-08-20: 1,427 pages,
of which 319 were something else and 58 of those were an index / detail /
dashboard page wearing a ``type: "custom"`` costume.

Three rules, each mechanical and each with a distinct failure mode:

**(a) Typed-component integrity.** A page declaring ``type: index|detail|
dashboard`` must not carry page-level ``widgets[]`` targeting the ``body``
slot. ``CnPageRenderer`` renders a body-slot ``CnWidgetGrid`` INSTEAD of the
typed component::

    <CnWidgetGrid v-if="widgetsBySlot.has('body')" … />
    <component :is="resolvedComponent" v-else-if="resolvedComponent" … />

so such a page silently never mounts ``CnDetailPage`` / ``CnIndexPage`` /
``CnDashboardPage`` and loses its header, max-width, padding, sidebar and grid
discipline. This is ConductionNL/hrmq#112: 47 detail pages rendered at a
different width from the rest of the fleet with no error anywhere. Nine pages
fleet-wide still do this, so the rule hard-fails.

Note the direction of the trap: the v2 schema DOCUMENTS page-level
``widgets[]`` as preferred and calls ``config.widgets`` legacy, while only
``config.widgets`` reaches the typed component. The app that follows the
documentation gets the worse result.

**(b) Mislabelled custom pages.** A ``type: "custom"`` page whose component
already imports ``CnIndexPage`` / ``CnDetailPage`` / ``CnDashboardPage`` is a
typed page with extra steps — the manifest could declare it directly. 58 such
pages exist, carrying ~29,700 lines of shell. Diff-scoped, so legacy debt only
blocks the PR that touches it.

**(c) Custom-page ratchet.** The app's total ``type: "custom"`` page count must
not exceed the count on the base ref, and any ADDED custom page must carry a
``_note`` justifying why no typed archetype fits. Follows the gate-29
custom-widget ratchet convention (count vs BASE_REF, no checked-in baseline to
drift). Legitimately bespoke screens do exist — POS terminals, mobile scanner
flows, lesson players, live meetings, public portals, print previews — so the
rule governs GROWTH rather than forbidding the category.

Diff-scoping (ADR-020): rules (a) and (b) inspect only pages the diff touches,
by page-object line span vs ``HYDRA_GATE_BASE_REF``. Rule (c) is app-wide by
construction — a ratchet needs both totals.

Usage:
    check_page_type_discipline.py <log-path> <manifest.json> [<manifest.json> ...]

Exit codes:
    0 — inspected (findings, if any, are written to <log-path>)
    2 — malformed invocation; the runner surfaces this as SKIPPED (wiring)
        rather than PASS, so a mis-wired call can never read as a clean gate.
"""

import glob
import json
import os
import re
import subprocess
import sys

TYPED = ("index", "detail", "dashboard")

# A component that renders one of these IS that archetype.
TYPED_COMPONENT = {
    "CnIndexPage": "index",
    "CnDetailPage": "detail",
    "CnDashboardPage": "dashboard",
}

_USAGE = (
    "usage: check_page_type_discipline.py <log-path> <manifest.json> [...]\n"
    "\n"
    "This helper does NOT take options. It is invoked with a log path followed\n"
    "by one or more manifest files. A call that does not match that shape\n"
    "returns 2 so the runner reports SKIPPED (wiring) — 'no verdict was\n"
    "produced' — instead of an empty, successful-looking run.\n"
)


def _run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


def _succeeds(cmd):
    """Exit status only — for probes whose SUCCESS produces no output.

    `git cat-file -e <ref>:<path>` prints nothing and signals through its exit
    code, so reading _run()'s empty string as failure inverted the answer: a
    tracked, unchanged manifest looked untracked, the helper fell back to
    'inspect every page', and diff-scoping silently did nothing. Observed on
    doriath — 4 findings on a manifest identical to the base ref.
    """
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0
    except Exception:
        return False


def _changed_lines(file_path, base_ref):
    """1-indexed line numbers ADDED or MODIFIED vs base_ref, or None for all."""
    if not base_ref:
        return None
    diff = _run(["git", "diff", "-U0", f"{base_ref}...HEAD", "--", file_path])
    if not diff:
        # No diff output has two causes: the file is unchanged (scope = nothing),
        # or it does not exist at base and is entirely new (scope = everything).
        # Distinguish them by EXIT STATUS, not by empty stdout.
        exists_at_base = _succeeds(["git", "cat-file", "-e", f"{base_ref}:{file_path}"])
        return set() if exists_at_base else None
    changed = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start = int(m.group(1))
        count = int(m.group(2) or 1)
        changed.update(range(start, start + count))
    return changed


def _page_spans(path):
    """Map page id -> (first_line, last_line) by scanning the raw text.

    json alone loses position, and the diff scope needs it. Walks the pages
    array tracking brace depth; good enough for the manifests this fleet
    ships, which are machine-formatted one key per line.
    """
    spans = {}
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except OSError:
        return spans
    in_pages = False
    depth = 0
    start = None
    pid = None
    for i, line in enumerate(lines, 1):
        if not in_pages:
            if re.match(r'^\s*"pages"\s*:\s*\[', line):
                in_pages = True
            continue
        if start is None and re.match(r"^\s*\{\s*$", line):
            start = i
            depth = 1
            pid = None
            continue
        if start is not None:
            depth += line.count("{") + line.count("[")
            depth -= line.count("}") + line.count("]")
            m = re.match(r'^\s*"id"\s*:\s*"([^"]+)"', line)
            if m and pid is None:
                pid = m.group(1)
            if depth <= 0:
                if pid:
                    spans[pid] = (start, i)
                start = None
    return spans


def _src_dir(path):
    marker = os.sep + "src" + os.sep
    norm = os.path.normpath(path)
    idx = norm.find(marker)
    if idx == -1:
        return os.path.dirname(norm)
    return norm[: idx + len(os.sep + "src")]


def _find_component(src_dir, name):
    if not name:
        return None
    hits = glob.glob(os.path.join(src_dir, "**", f"{name}.vue"), recursive=True)
    return hits[0] if hits else None


def _renders_typed_component(src_dir, name):
    """Which typed page component this custom page's component renders, if any."""
    path = _find_component(src_dir, name)
    if not path:
        return None, None
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None, None
    for marker, archetype in TYPED_COMPONENT.items():
        # An import or a tag both count — either way it is what renders.
        if re.search(r"\b" + marker + r"\b", text):
            return archetype, path
    return None, path


def _pages_of(doc):
    if isinstance(doc, dict) and isinstance(doc.get("pages"), list):
        return doc["pages"]
    return []


def _custom_count_at(base_ref, paths):
    """Total type:"custom" pages across these manifests on the base ref."""
    total = 0
    for p in paths:
        blob = _run(["git", "show", f"{base_ref}:{p}"])
        if not blob:
            continue
        try:
            doc = json.loads(blob)
        except ValueError:
            continue
        total += sum(1 for pg in _pages_of(doc) if pg.get("type") == "custom")
    return total


def check_file(path, findings, base_ref):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        findings.append(f"{path}: could not be parsed ({exc})")
        return 0

    changed = _changed_lines(path, base_ref)
    spans = _page_spans(path)
    src_dir = _src_dir(path)
    custom_here = 0

    for page in _pages_of(doc):
        pid = page.get("id", "?")
        ptype = page.get("type")
        if ptype == "custom":
            custom_here += 1

        # Diff scope: skip pages this PR does not touch.
        if changed is not None:
            span = spans.get(pid)
            if span is None:
                continue
            if not any(l in changed for l in range(span[0], span[1] + 1)):
                continue

        # (a) typed page whose body widgets bypass the typed component.
        if ptype in TYPED:
            body = [
                w for w in (page.get("widgets") or [])
                if isinstance(w, dict) and (w.get("slot") or "body") == "body"
            ]
            if body:
                findings.append(
                    f"{path}: page '{pid}' — type:\"{ptype}\" with {len(body)} "
                    f"page-level body widget(s), so CnPageRenderer renders a bare "
                    f"CnWidgetGrid INSTEAD of the typed page component and the page "
                    f"never gets its header, max-width, padding, sidebar or grid "
                    f"discipline. Move them to config.widgets[] + config.layout[] "
                    f"(hrmq#112 did exactly this for 47 pages). Note the v2 schema "
                    f"calls page-level widgets[] 'preferred' — for a typed page it "
                    f"is not."
                )

        # (b) custom page that is really a typed page — UNLESS it says why.
        #
        # A reason-bearing `_note` exempts the page, matching the gate-29
        # custom-widget convention. This is not a formality: every one of the
        # 58 such pages in the fleet carries a note, and the reasons are real —
        # a slot the declarative page type cannot express (softwarecatalog's
        # Suites needs the wizard button in CnIndexPage's #actions), a fetch
        # that does not come from a plain OpenRegister index endpoint
        # (docudesk's Consent reads its own PHP controller), a self-contained
        # composite view. Without this exemption the rule fires on all 58 and
        # is a 100% false-positive against the fleet's own documented practice.
        #
        # So the rule catches the page that reuses a typed component and never
        # says why — and the ratchet in main() governs growth.
        if ptype == "custom":
            note = page.get("_note")
            if isinstance(note, str) and len(note.strip()) >= 40:
                continue
            archetype, comp_path = _renders_typed_component(src_dir, page.get("component"))
            if archetype:
                findings.append(
                    f"{path}: page '{pid}' — declared type:\"custom\" but its "
                    f"component ({os.path.relpath(comp_path, src_dir)}) already "
                    f"renders Cn{archetype.capitalize()}Page, and the page gives "
                    f"no `_note` saying why. Either declare type:\"{archetype}\" "
                    f"and let the manifest render it, or record what the typed "
                    f"page cannot do here — a slot it has no room for, a fetch "
                    f"that is not a plain OpenRegister index."
                )

    return custom_here


def main(argv):
    # A MALFORMED INVOCATION MUST NOT LOOK CLEAN — same contract as gate-55.
    if len(argv) < 3 or any(a.startswith("-") for a in argv[1:]):
        sys.stderr.write(_USAGE)
        return 2

    log_path = argv[1]
    paths = [p for p in argv[2:] if os.path.isfile(p)]
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "").strip()
    findings = []

    head_custom = 0
    for p in paths:
        head_custom += check_file(p, findings, base_ref)

    # (c) ratchet — the custom-page total may not grow.
    if base_ref and paths:
        base_custom = _custom_count_at(base_ref, paths)
        if head_custom > base_custom:
            findings.append(
                f"custom-page ratchet: type:\"custom\" pages went {base_custom} -> "
                f"{head_custom} (+{head_custom - base_custom}). A page that is a "
                f"list, a record or a widget grid should declare index / detail / "
                f"dashboard so it renders through the shared page component. If "
                f"the screen genuinely has no typed archetype — a POS terminal, a "
                f"scanner flow, a player, a public portal — say so in the page's "
                f"_note and the reviewer can weigh it."
            )
        # Always report both sides so a migration can show the count falling.
        # To STDERR, never to the findings log: the runner counts log LINES as
        # findings, so an informational line written there would fail the gate
        # on every run — a gate that can never pass teaches people to ignore it.
        sys.stderr.write(
            f"[page-type-discipline] custom pages: base={base_custom} "
            f"head={head_custom} delta={head_custom - base_custom:+d}\n"
        )

    with open(log_path, "a", encoding="utf-8") as g:
        for msg in findings:
            g.write(msg + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
