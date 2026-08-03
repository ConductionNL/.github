#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-26 visual-coverage — diff-scoped new-page-component visual-regression enforcer.

A new Vue **page / view** component ADDED in the PR diff MUST have a
visual-regression proof. A page component is one of:

  * a ``.vue`` file ADDED under ``src/views/`` or ``src/pages/`` (the two
    conventional page-host directories), OR
  * a ``.vue`` component referenced as a manifest ``"type": "page"`` entry in
    ``src/manifest.json`` whose ``component`` file was ADDED in the diff.

For each such page, the gate requires at least one of:

  1. A **visual-regression spec or baseline** under ``tests/e2e/visual/**`` that
     references the component (by file stem, manifest page id, or a
     ``toHaveScreenshot`` / ``toMatchSnapshot`` baseline named after it).
  2. An **e2e workflow test** anywhere under ``tests/e2e/**`` that references the
     component (drives the page in a browser).
  3. A reason-bearing ``@visual exclude <reason>`` marker inside the ``.vue``
     file (a ``<!-- @visual exclude ... -->`` comment or a code comment).

A bare ``@visual exclude`` (no reason) is non-compliant — flagged like a missing
baseline, mirroring gate-16/gate-19/gate-25.

This is the visual-layer companion to gate-19 (behavioural e2e) and gate-25
(API contract). New screens cannot merge without a pixel/structural baseline or
an explicit, audited waiver.

Diff scope
==========

ADDED ``.vue`` files are derived from ``git diff --diff-filter=A`` against
``$HYDRA_GATE_BASE_REF`` (default ``origin/development``). For manifest pages,
the page is in scope only when its ``component`` file is itself an ADDED file in
the diff — so re-pointing an existing manifest entry at an existing component
never trips the gate. Pre-existing pages (untouched legacy debt) are never
flagged — ADR-020.

Usage::

    HYDRA_GATE_BASE_REF=origin/development python3 scripts/lib/check_visual_coverage.py [app-dir]
    python3 scripts/lib/check_visual_coverage.py [app-dir] --mode report
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

GATE_NUM = 26

_PAGE_DIRS = ("src/views/", "src/pages/")

_VISUAL_EXCLUDE_RE = re.compile(
    r"@visual\s+exclude\b[ \t]*(?P<reason>.*?)\s*$", re.MULTILINE
)


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


def added_files(base_ref: str, cwd: Path) -> set[str]:
    """Return relative paths of files ADDED (status A) in the PR diff."""
    out = _git(["diff", "--diff-filter=A", "--name-only", f"{base_ref}...HEAD"], cwd)
    if not out.strip():
        out = _git(["diff", "--diff-filter=A", "--name-only", base_ref], cwd)
    return {line.strip() for line in out.splitlines() if line.strip()}


# ---------------------------------------------------------------------------
# Page discovery
# ---------------------------------------------------------------------------


def _manifest_page_components(app_dir: Path) -> dict[str, str]:
    """Return {component-relpath: page-id} for every ``"type": "page"`` entry in
    src/manifest.json whose ``component`` resolves to a src/ .vue file.

    The manifest may store the component as a bare name (``"Dashboard"``) or a
    path (``"views/Dashboard.vue"`` / ``"src/views/Dashboard.vue"``). We resolve
    each to a repo-relative ``src/...vue`` path when one exists on disk; bare
    names are matched against any ``src/**/<name>.vue``.
    """
    manifest = app_dir / "src" / "manifest.json"
    if not manifest.is_file():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    result: dict[str, str] = {}

    def _resolve(component: str) -> str | None:
        if not component:
            return None
        cand = component
        if not cand.endswith(".vue"):
            cand = cand + ".vue"
        # Try a few prefixings.
        for variant in (cand, f"src/{cand}", f"src/views/{cand}", f"src/pages/{cand}"):
            if (app_dir / variant).is_file():
                return variant.replace("\\", "/")
        # Bare name → search.
        stem = Path(cand).name
        for p in (app_dir / "src").rglob(stem):
            if p.is_file():
                return str(p.relative_to(app_dir)).replace("\\", "/")
        return None

    def _walk(node):
        if isinstance(node, dict):
            if str(node.get("type", "")).lower() == "page":
                comp = node.get("component") or node.get("componentName") or ""
                rel = _resolve(comp) if isinstance(comp, str) else None
                if rel:
                    page_id = str(node.get("id") or node.get("name") or Path(rel).stem)
                    result[rel] = page_id
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(data)
    return result


def discover_new_pages(app_dir: Path, added: set[str]) -> list[dict]:
    """Return new page components in the diff.

    Each dict: {path, id, source} where source is 'dir' or 'manifest'.
    Deduplicated by path.
    """
    pages: dict[str, dict] = {}
    # 1. ADDED .vue files under src/views or src/pages.
    for rel in added:
        if rel.endswith(".vue") and any(rel.startswith(d) for d in _PAGE_DIRS):
            pages[rel] = {"path": rel, "id": Path(rel).stem, "source": "dir"}
    # 2. Manifest type:"page" entries whose component file was ADDED.
    manifest_pages = _manifest_page_components(app_dir)
    for rel, page_id in manifest_pages.items():
        if rel in added and rel not in pages:
            pages[rel] = {"path": rel, "id": page_id, "source": "manifest"}
    return list(pages.values())


# ---------------------------------------------------------------------------
# Coverage scanning
# ---------------------------------------------------------------------------


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _visual_exclude_status(vue_text: str) -> tuple[bool, str | None]:
    """(excluded, reason). reason None means bare exclude (non-compliant)."""
    m = _VISUAL_EXCLUDE_RE.search(vue_text)
    if not m:
        return (False, None)
    reason = m.group("reason").strip()
    # Strip a trailing HTML-comment / block-comment close if it sits on the
    # same line as the marker (e.g. `<!-- @visual exclude <reason> -->`).
    for close in ("-->", "*/"):
        if reason.endswith(close):
            reason = reason[: -len(close)].strip()
    return (True, reason if reason else None)


def _e2e_corpus(app_dir: Path, visual_only: bool) -> str:
    """Concatenated text of e2e test files.

    visual_only=True → only tests/e2e/visual/**.
    visual_only=False → all of tests/e2e/**.
    """
    root = app_dir / "tests" / "e2e"
    if visual_only:
        root = root / "visual"
    if not root.is_dir():
        return ""
    buf: list[str] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".ts", ".js", ".png", ".txt", ".json"):
            # Binary PNG baselines: we only need their FILENAME to match, so
            # record the name rather than the bytes.
            if p.suffix == ".png":
                buf.append(p.name)
            else:
                buf.append(_read(p))
    return "\n".join(buf)


def is_covered(page: dict, visual_corpus: str, e2e_corpus: str) -> bool:
    """True if a visual baseline/spec or an e2e test references the page."""
    stem = Path(page["path"]).stem
    pid = page["id"]
    needles = {stem, pid}
    # Visual layer (preferred): the stem or page id appears in tests/e2e/visual/**.
    for needle in needles:
        if needle and needle in visual_corpus:
            return True
    # Fallback: any e2e test references the component file or its stem/id.
    if page["path"] in e2e_corpus:
        return True
    for needle in needles:
        if needle and re.search(rf"\b{re.escape(needle)}\b", e2e_corpus):
            return True
    return False


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def _collect(app_dir: Path, base_ref: str) -> list[dict]:
    added = added_files(base_ref, app_dir)
    return discover_new_pages(app_dir, added)


def run_gate(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "origin/development")
    pages = _collect(app_dir, base_ref)
    if not pages:
        print(f"[gate-{GATE_NUM}] visual-coverage: PASS — no new page components in diff")
        return 0
    visual_corpus = _e2e_corpus(app_dir, visual_only=True)
    e2e_corpus = _e2e_corpus(app_dir, visual_only=False)
    findings: list[str] = []
    for page in pages:
        excluded, reason = _visual_exclude_status(_read(app_dir / page["path"]))
        if excluded and reason:
            continue
        if excluded and reason is None:
            findings.append(f"{page['path']} — @visual exclude without reason (reason required)")
            continue
        if not is_covered(page, visual_corpus, e2e_corpus):
            findings.append(
                f"{page['path']} — new page component missing visual-regression "
                f"baseline (tests/e2e/visual/**) / e2e test / @visual exclude"
            )
    for line in sorted(set(findings)):
        print(line)
    count = len(set(findings))
    if count == 0:
        print(
            f"[gate-{GATE_NUM}] visual-coverage: PASS — "
            f"{len(pages)} new page(s), all have a visual proof"
        )
    else:
        print(
            f"[gate-{GATE_NUM}] visual-coverage: FAIL — "
            f"{count} new page component(s) without a visual baseline"
        )
    return count


def run_report(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "origin/development")
    pages = _collect(app_dir, base_ref)
    visual_corpus = _e2e_corpus(app_dir, visual_only=True)
    e2e_corpus = _e2e_corpus(app_dir, visual_only=False)
    covered = uncovered = excluded = 0
    rows = []
    for page in pages:
        ex, reason = _visual_exclude_status(_read(app_dir / page["path"]))
        if ex and reason:
            excluded += 1
            state = "excluded"
        elif is_covered(page, visual_corpus, e2e_corpus):
            covered += 1
            state = "covered"
        else:
            uncovered += 1
            state = "uncovered"
        rows.append({"path": page["path"], "id": page["id"], "source": page["source"], "state": state})
    out = {
        "mode": "report",
        "gate": GATE_NUM,
        "app": app_dir.name,
        "totals": {
            "new_pages": len(pages),
            "covered": covered,
            "excluded": excluded,
            "uncovered": uncovered,
        },
        "pages": rows,
    }
    print(json.dumps(out, indent=2))
    return 0


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
