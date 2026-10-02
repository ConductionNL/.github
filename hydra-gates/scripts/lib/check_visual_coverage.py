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
``$HYDRA_GATE_BASE_REF`` **when the caller sets it**. With no base ref the run
is a FULL-TREE audit — every page component in the app — because a caller who
asked for no scoping must not have its request silently narrowed to a diff
(.github#242). For manifest pages,
the page is in scope only when its ``component`` file is itself an ADDED file in
the diff — so re-pointing an existing manifest entry at an existing component
never trips the gate. Pre-existing pages (untouched legacy debt) are never
flagged — ADR-020.

Usage::

    HYDRA_GATE_BASE_REF=origin/development python3 scripts/lib/check_visual_coverage.py [app-dir]
    python3 scripts/lib/check_visual_coverage.py [app-dir] --mode report

Exit status is a STATUS, never a count
======================================

``run_gate`` used to ``return count`` — the number of uncovered page
components — straight into ``sys.exit``. An exit status is ONE BYTE, so the
count was taken mod 256 on its way out, and the caller
(``run-hydra-gates.sh`` gate-26) read that byte as the finding count:

    260 uncovered pages  ->  exit 4    ->  "[gate-26] FAIL — 4 ..."
    256 uncovered pages  ->  exit 0    ->  "[gate-26] visual-coverage: PASS"

Both were measured on openregister on 2026-08-08 with this file's own stdout
reading ``FAIL — 256 new page component(s) without a visual baseline`` on the
same run that the gate reported PASS. Two numbers for one measurement means
one of them came through a lossy channel. This is the identical defect
ConductionNL/.github#209 fixed in gate-19's helper.

The status vocabulary now matches gate-25's helper
(``check_contract_coverage.py``), which the runner already knows how to read:

    0  pass — pages were inspected (or there were none) and all are covered
    1  fail — at least one uncovered page; the COUNT is on stdout as
              ``FAIL — <n> new page component(s)``
    2  error
    3  empty scope — the diff added no page component, so nothing was
              inspected. NOT APPLICABLE, not a pass (#268).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402
from source_scope import js_code_mask, js_comment_mask, js_comments_only_mask  # noqa: E402

GATE_NUM = 26

# Exit STATUS vocabulary — see the module docstring. Never a finding count.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_EMPTY_SCOPE = 3

_PAGE_DIRS = ("src/views/", "src/pages/")

# What counts as a <reason> is decided by exclusion_reason.is_reason_bearing(),
# shared with gates 16, 19 and 25 — all four graded it with plain truthiness, so
# `@visual exclude .` was a reason (.github#400). MULTILINE stays here: this is
# the only one of the four that searches whole-file text rather than one line.
_VISUAL_EXCLUDE_RE = re.compile(exclude_pattern("visual"), re.MULTILINE)


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


_DEFAULT_IMPORT_RE = re.compile(
    r"""import\s+([A-Za-z_$][\w$]*)\s+from\s*['"]([^'"]+\.vue)['"]""")

_ALIAS_CACHE: dict[str, dict[str, str]] = {}


def _alias_map(app_dir: Path) -> dict[str, str]:
    """{imported identifier: repo-relative .vue path} across all of src/.

    A manifest page's ``component`` is the name the app REGISTERED, which need
    not match the filename — see the note in ``_resolve``. This follows the
    default-import statement that created the alias.
    """
    key = str(app_dir.resolve())
    cached = _ALIAS_CACHE.get(key)
    if cached is not None:
        return cached
    out: dict[str, str] = {}
    for path in _src_code_files(app_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for ident, spec in _DEFAULT_IMPORT_RE.findall(text):
            if spec.startswith("."):
                target = (path.parent / spec).resolve()
            elif spec.startswith("@/"):
                target = (app_dir / "src" / spec[2:]).resolve()
            elif spec.startswith("src/"):
                target = (app_dir / spec).resolve()
            else:
                continue
            try:
                rel = str(target.relative_to(app_dir.resolve())).replace("\\", "/")
            except ValueError:
                continue
            if target.is_file():
                out.setdefault(ident, rel)
    _ALIAS_CACHE[key] = out
    return out


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
        # THE MANIFEST NAMES THE REGISTERED COMPONENT, NOT THE FILE.
        # `customComponents.js` registers a `.vue` under a different identifier:
        #
        #   import PortfolioReportView from './views/organisaties/PortfolioReport.vue'
        #
        # and the manifest page says `"component": "PortfolioReportView"`. No
        # filename anywhere is `PortfolioReportView.vue`, so every lookup above
        # misses and a REAL routed page (`/portfolio-report` on softwarecatalog)
        # resolves to nothing. Follow the alias.
        return _alias_map(app_dir).get(component)

    def _record(node) -> None:
        comp = node.get("component") or node.get("componentName") or ""
        rel = _resolve(comp) if isinstance(comp, str) else None
        if rel:
            page_id = str(node.get("id") or node.get("name") or Path(rel).stem)
            result[rel] = page_id

    def _walk(node):
        if isinstance(node, dict):
            if str(node.get("type", "")).lower() == "page":
                _record(node)
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(data)

    # MANIFEST V2: `type:"page"` NEVER OCCURS (.github#309)
    # ----------------------------------------------------
    # A v2 manifest declares its screens in a top-level `pages[]` array whose
    # entries carry an `id`, a `route` and a `type` drawn from the RENDERER
    # vocabulary — `index`, `detail`, `logs`, `dashboard`, `custom`, … — so the
    # `type == "page"` test above matched NOTHING. Measured on openconnector:
    # 35 declared pages, `_manifest_page_components()` resolved **0**. The
    # manifest half of this gate has been dead on every v2 app, leaving only
    # the src/views/ directory heuristic — which is the very thing #309 is
    # about.
    #
    # A v2 entry is a page because it has a ROUTE. Only `type:"custom"` entries
    # name a `component`; the rest are drawn by the manifest renderer and have
    # no .vue file of their own, so there is nothing to demand a baseline for
    # and they correctly contribute nothing here.
    pages_node = data.get("pages") if isinstance(data, dict) else None
    if isinstance(pages_node, list):
        for entry in pages_node:
            if isinstance(entry, dict) and entry.get("route"):
                _record(entry)
    return result


# ---------------------------------------------------------------------------
# A DIRECTORY IS NOT A PAGE (.github#309)
# ---------------------------------------
# Rule (a) below — "a .vue ADDED under src/views/" — is a PATH-SHAPED PROXY for
# a semantic property. Any child component that happens to live beside its page
# was classified as a page. Measured full-tree:
#
#   openconnector    40 findings, of which src/views/Rule/actionForms/*.vue,
#                    src/views/Synchronization/*Mapping*.vue and
#                    src/views/admin/DsoPkiSettings.vue are not pages at all
#                    (#309 measured 13 diff-scoped, 6 of them real)
#   softwarecatalog  8 of 11 false (73%), all under src/views/settings/sections/**
#                    and src/views/widgets/**
#
# Why the inflation is worse than a wrong number: for a NON-page, only the
# third remedy the finding offers is reachable — `@visual exclude <reason>`. So
# an over-matching heuristic systematically MANUFACTURES WAIVERS, and a fleet
# trained to write waivers for false positives will write them for true ones.
# `DsoPkiSettings.vue` is the sharpest case — NC renders it server-side through
# the settings framework, so no amount of SPA e2e will ever "drive the page".
#
# The replacement asks for REACHABILITY, which is what "page" actually means,
# and it is deliberately CONSERVATIVE: a file is dropped only when there is
# positive evidence it is somebody's child. Absence of evidence keeps it in
# scope, so a genuinely new page nothing has wired up yet is still flagged.
#
#   PAGE    named by a manifest `"type": "page"` entry            (routable), or
#           referenced from a router module                       (routable), or
#           imported by NOTHING in src/                (cannot be proved a child)
#   CHILD   imported by some other src/ component that is not a router, and
#           named by neither the manifest nor a router
# ---------------------------------------------------------------------------
_ROUTER_SIGNALS = ("createRouter(", "new VueRouter(", "vue-router", "createWebHashHistory")
_SRC_CODE_EXT = (".vue", ".js", ".ts", ".mjs", ".jsx", ".tsx")


def _src_code_files(app_dir: Path) -> list[Path]:
    src = app_dir / "src"
    if not src.is_dir():
        return []
    out: list[Path] = []
    for p in src.rglob("*"):
        if p.is_file() and p.suffix in _SRC_CODE_EXT:
            if "node_modules" in p.parts:
                continue
            out.append(p)
    return out


def _import_graph(app_dir: Path) -> tuple[set[str], set[str]]:
    """(imported_by_non_router, referenced_by_router) as sets of file stems.

    Stems, not resolved paths: an import is written `./Rule/actionForms/UploadForm.vue`
    or `@/views/UploadForm`, and resolving every alias form correctly is more
    machinery than this decision needs. A stem collision can only ever make the
    gate MORE conservative in the router set and less so in the child set, so
    the tie-break below prefers 'page' whenever both fire.
    """
    imported_non_router: set[str] = set()
    referenced_by_router: set[str] = set()
    import_re = re.compile(
        r"""(?:import\s+[^;\n]*?from\s*|import\s*\(\s*|require\s*\(\s*)['"]([^'"]+)['"]""")
    for path in _src_code_files(app_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(app_dir)).replace("\\", "/")
        is_router = (
            "/router/" in f"/{rel}"
            or Path(rel).stem.lower() in {"router", "routes"}
            or any(sig in text for sig in _ROUTER_SIGNALS)
        )
        for spec in import_re.findall(text):
            stem = Path(spec).name
            if stem.endswith(".vue"):
                stem = stem[:-4]
            if not stem:
                continue
            if is_router:
                referenced_by_router.add(stem)
            else:
                # A file importing ITSELF is not a parent of itself.
                if stem != Path(rel).stem:
                    imported_non_router.add(stem)
    return imported_non_router, referenced_by_router


def _is_child_component(rel: str, manifest_pages: dict[str, str],
                        imported_non_router: set[str],
                        referenced_by_router: set[str]) -> bool:
    """True when *rel* is positively evidenced to be somebody's child."""
    if rel in manifest_pages:
        return False                      # the manifest says it is a page
    stem = Path(rel).stem
    if stem in referenced_by_router:
        return False                      # the router says it is a page
    return stem in imported_non_router    # only then is it a child


def discover_new_pages(app_dir: Path, added: set[str]) -> list[dict]:
    """Return new page components in the diff.

    Each dict: {path, id, source} where source is 'dir' or 'manifest'.
    Deduplicated by path.
    """
    pages: dict[str, dict] = {}
    manifest_pages = _manifest_page_components(app_dir)
    imported_non_router, referenced_by_router = _import_graph(app_dir)
    # 1. ADDED .vue files under src/views or src/pages that are REACHABLE.
    for rel in added:
        if rel.endswith(".vue") and any(rel.startswith(d) for d in _PAGE_DIRS):
            if _is_child_component(rel, manifest_pages, imported_non_router,
                                   referenced_by_router):
                continue
            pages[rel] = {"path": rel, "id": Path(rel).stem, "source": "dir"}
    # 2. Manifest type:"page" entries whose component file was ADDED. A manifest
    #    page is ALWAYS in scope — it is routable by declaration.
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
    # `reason if reason else None` was .github#400. The normalisation above is
    # Vue-specific and stays local; only the VERDICT is shared.
    return (True, reason if is_reason_bearing(reason) else None)


def _e2e_corpus(app_dir: Path, visual_only: bool, include_visual: bool = True) -> str:
    """Concatenated EXECUTABLE text of e2e test files.

    visual_only=True → only tests/e2e/visual/**.
    visual_only=False → all of tests/e2e/**.
    include_visual=False → tests/e2e/visual/** contributes NOTHING, in either
    mode. The caller passes it when CI never runs that directory; see
    ``visual_suite_runs_in_ci``.

    A COMMENT IS NOT A BASELINE (.github#358)
    -----------------------------------------
    This corpus used to be the raw bytes of every file, and ``is_covered()``
    asks nothing more than "does the component's name appear in it". So it did:

        // NOTE: we still owe a baseline for Dashboard — see the issue.

    A sentence saying you have NOT done the thing satisfied the gate that
    checks whether you have done it. Reproduced on a two-file fixture: the
    comment-only arm and a real spec that navigates to the page and calls
    ``toHaveScreenshot`` both print

        [gate-26] visual-coverage: PASS — 1 new page(s), all have a visual proof

    byte for byte. Measured in the fleet as docudesk 7, openregister 6,
    opencatalogi 3, procest 2, softwarecatalog 2, pipelinq 2 — and doriath
    *triggered* it while writing the warning paragraph that documents it, which
    is the sharpest possible statement of the problem: the better your comments,
    the greener the gate.

    So ``.ts``/``.js`` files enter the corpus through
    ``source_scope.js_comment_mask``, which blanks comments and regex literals
    and KEEPS string literals. Strings have to stay: ``page.goto('/dashboard')``,
    ``toHaveScreenshot('Dashboard.png')`` and a locator are all real references
    to the screen, and blanking them would turn a noisy gate into a dead one —
    the mistake `.github#230` records for gate-58. Offsets are preserved, so the
    mask is a drop-in for the raw text.

    ``.png`` baselines contribute their FILENAME (that is the whole reference),
    and ``.json``/``.txt`` snapshots are data rather than prose and are left
    alone.
    """
    root = app_dir / "tests" / "e2e"
    visual_root = root / "visual"
    if visual_only:
        if not include_visual:
            return ""
        root = visual_root
    if not root.is_dir():
        return ""
    buf: list[str] = []
    for p in root.rglob("*"):
        if not include_visual and (p == visual_root or visual_root in p.parents):
            continue
        if p.is_file() and p.suffix in (".ts", ".js", ".png", ".txt", ".json"):
            # Binary PNG baselines: we only need their FILENAME to match, so
            # record the name rather than the bytes.
            if p.suffix == ".png":
                buf.append(p.name)
            elif p.suffix in (".ts", ".js"):
                buf.append(js_comment_mask(_read(p)))
            else:
                buf.append(_read(p))
    return "\n".join(buf)


# ---------------------------------------------------------------------------
# A BASELINE CI NEVER RUNS IS NOT A PROOF (keepiq#198)
# ---------------------------------------------------------------------------
# `tests/e2e/visual/**` used to be credited unconditionally, and FIRST. But the
# fleet's CI Playwright configs (keepiq, pipelinq, ...) put `'**/visual/**'` in
# their only project's `testIgnore`, because the PNGs are generated on a
# developer machine and would diff on the runner. So a new page whose only
# proof was a baseline passed this gate while CI never opened it.
#
# The credit now follows what CI EXECUTES. The CI job runs
# `npx playwright test --config=<playwright-test-path>/playwright.config.ts`
# (falling back to ./playwright.config.ts) with no `--project`, so every
# declared project runs. The visual directory is credited only when
#
#   * some entry of `projects: [...]` would collect it: its effective
#     `testIgnore` (its own, which REPLACES the top-level one in Playwright,
#     else the top-level one) does not name `visual`, its effective `testDir`
#     (its own, else the top-level one, else the config's directory) contains
#     or is inside tests/e2e/visual, and its `testMatch`, when it has one,
#     names `visual` or matches any directory (`**/...`).
#
# Anything else, including no config at all, withholds the credit. Executed
# e2e tests outside tests/e2e/visual and `@visual exclude <reason>` still count.
# ---------------------------------------------------------------------------
_TEST_PATH_RE = re.compile(r"^\s*playwright-test-path\s*:\s*['\"]?([^'\"#\s]+)", re.MULTILINE)
_DEFAULT_TEST_PATH = "tests/e2e"


def _playwright_test_path(app_dir: Path) -> str:
    """The `playwright-test-path` the app's CI passes, else the default.

    `PLAYWRIGHT_TEST_PATH` in the environment wins (the quality workflow sets
    it from the input); otherwise the app's own caller workflow is read.
    """
    env = os.environ.get("PLAYWRIGHT_TEST_PATH", "").strip()
    if env:
        return env.rstrip("/")
    wf_dir = app_dir / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.y*ml")):
            m = _TEST_PATH_RE.search(_read(wf))
            if m and "${{" not in m.group(1):
                return m.group(1).rstrip("/")
    return _DEFAULT_TEST_PATH


def _ci_playwright_config(app_dir: Path) -> Path | None:
    cand = app_dir / _playwright_test_path(app_dir) / "playwright.config.ts"
    if cand.is_file():
        return cand
    root = app_dir / "playwright.config.ts"
    return root if root.is_file() else None


def _match_close(code: str, i: int) -> int:
    """Index just past the bracket that closes the one at *i* (on a code mask)."""
    pairs = {"[": "]", "{": "}", "(": ")"}
    stack = [pairs[code[i]]]
    j = i + 1
    while j < len(code) and stack:
        c = code[j]
        if c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
        j += 1
    return j


def _top_level_keys(code: str, a: int, b: int) -> dict[str, tuple[int, int]]:
    """{key: (value_start, value_end)} for the keys at depth 0 of code[a:b]."""
    out: dict[str, tuple[int, int]] = {}
    key_re = re.compile(r"([A-Za-z_$][\w$]*)\s*:")
    i = a
    while i < b:
        c = code[i]
        if c in "[{(":
            i = _match_close(code, i)
            continue
        m = key_re.match(code, i)
        if m and (i == a or not (code[i - 1].isalnum() or code[i - 1] in "_$")):
            vs = m.end()
            j = vs
            while j < b and code[j] != ",":
                if code[j] in "[{(":
                    j = _match_close(code, j)
                    continue
                j += 1
            out.setdefault(m.group(1), (vs, j))
            i = j + 1
            continue
        i += 1
    return out


def _resolve_test_dir(raw: str, config_dir: Path) -> Path:
    """Best-effort value of a `testDir:` expression. Unknown shapes mean the
    config's own directory, which is Playwright's default."""
    # `__dirname`, `'./x'`, `path.join(__dirname, 'x')` and
    # `path.resolve(__dirname, '..', 'x')` all reduce to the config directory
    # joined with the string literals in order.
    parts = re.findall(r"""['"]([^'"]*)['"]""", raw)
    path = config_dir
    for part in parts:
        path = path / part
    return path.resolve()


def _names_visual(raw: str) -> bool:
    return "visual" in raw


def visual_suite_runs_in_ci(app_dir: Path) -> tuple[bool, str]:
    """(runs, why). True only when the CI Playwright config collects
    tests/e2e/visual/**. See the block comment above."""
    visual_dir = (app_dir / "tests" / "e2e" / "visual").resolve()
    config = _ci_playwright_config(app_dir)
    if config is None:
        return (False, f"no CI Playwright config at {_playwright_test_path(app_dir)}/playwright.config.ts")
    text = js_comments_only_mask(_read(config))
    code = js_code_mask(_read(config))
    rel_cfg = str(config.relative_to(app_dir))
    m = re.search(r"defineConfig\s*\(\s*\{", code) or re.search(r"export\s+default\s*\{", code)
    if not m:
        return (False, f"{rel_cfg}: no defineConfig({{...}}) / export default {{...}} object found")
    obj_a = m.end() - 1
    obj_b = _match_close(code, obj_a)
    top = _top_level_keys(code, obj_a + 1, obj_b - 1)
    top_ignore = text[slice(*top["testIgnore"])] if "testIgnore" in top else None
    if "projects" not in top:
        return (False, f"{rel_cfg}: declares no projects, so none runs visual/")
    top_dir = _resolve_test_dir(text[slice(*top["testDir"])], config.parent) if "testDir" in top else config.parent.resolve()
    top_match = text[slice(*top["testMatch"])] if "testMatch" in top else None
    pa, pb = top["projects"]
    arr = code.find("[", pa, pb)
    if arr < 0:
        return (False, f"{rel_cfg}: projects is not an array literal")
    arr_end = _match_close(code, arr)
    i = arr + 1
    while i < arr_end - 1:
        if code[i] == "{":
            end = _match_close(code, i)
            keys = _top_level_keys(code, i + 1, end - 1)
            name_raw = text[slice(*keys["name"])].strip() if "name" in keys else "?"
            i = end
            # A project's own testIgnore REPLACES the top-level one in
            # Playwright; it does not add to it.
            ignore = text[slice(*keys["testIgnore"])] if "testIgnore" in keys else top_ignore
            if ignore is not None and _names_visual(ignore):
                continue
            tdir = _resolve_test_dir(text[slice(*keys["testDir"])], config.parent) if "testDir" in keys else top_dir
            if not (tdir == visual_dir or tdir in visual_dir.parents or visual_dir in tdir.parents):
                continue
            match = text[slice(*keys["testMatch"])] if "testMatch" in keys else top_match
            if match is not None and not (_names_visual(match) or "**/" in match):
                continue
            return (True, f"{rel_cfg}: project {name_raw} runs tests/e2e/visual")
        i += 1
    return (False, f"{rel_cfg}: no project collects tests/e2e/visual (ignored or outside its testDir)")


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


def _all_page_components(app_dir: Path) -> set[str]:
    """Every page component in the tree, ignoring the diff entirely."""
    found: set[str] = set()
    for d in _PAGE_DIRS:
        root = app_dir / d
        if root.is_dir():
            for p in root.rglob("*.vue"):
                found.add(str(p.relative_to(app_dir)).replace("\\", "/"))
    found.update(_manifest_page_components(app_dir).keys())
    return found


def _collect(app_dir: Path, base_ref: str | None) -> list[dict]:
    if base_ref:
        return discover_new_pages(app_dir, added_files(base_ref, app_dir))
    # SCOPE IS THE CALLER'S DECISION, AND IT IS NOT DEFAULTED (.github#242,
    # applied here). This helper defaulted `HYDRA_GATE_BASE_REF` to
    # `origin/development` even on a run the caller had asked NOT to scope, so
    # a full-tree audit was silently narrowed to a diff, came back empty, and
    # printed a verdict having opened nothing — the same defect #242 fixed in
    # gate-25's helper, where the honest full-tree number on openconnector was
    # 32 endpoints against a scoped PASS. With no base ref, audit every page.
    return discover_new_pages(app_dir, _all_page_components(app_dir))


def run_gate(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF") or None
    pages = _collect(app_dir, base_ref)
    if not pages:
        # EMPTY SCOPE IS NOT A PASS (#268). The diff added no page component,
        # so this run inspected nothing and has no verdict to give about the
        # repository. The caller reports NOT APPLICABLE.
        if base_ref:
            print(
                f"[gate-{GATE_NUM}] visual-coverage: EMPTY SCOPE — "
                f"the diff against '{base_ref}' ADDED no page component, so no "
                f"screen was inspected"
            )
            return EXIT_EMPTY_SCOPE
        print(
            f"[gate-{GATE_NUM}] visual-coverage: NOT APPLICABLE — this app has "
            f"no page component at all (nothing under src/views|src/pages, no "
            f"manifest \"type\":\"page\" entry resolving to a .vue)"
        )
        return EXIT_EMPTY_SCOPE
    visual_runs, visual_why = visual_suite_runs_in_ci(app_dir)
    if not visual_runs and (app_dir / "tests" / "e2e" / "visual").is_dir():
        print(
            f"[gate-{GATE_NUM}] tests/e2e/visual/** is NOT credited: {visual_why}. "
            f"Only executed e2e tests and @visual exclude count."
        )
    visual_corpus = _e2e_corpus(app_dir, visual_only=True, include_visual=visual_runs)
    e2e_corpus = _e2e_corpus(app_dir, visual_only=False, include_visual=visual_runs)
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
                f"baseline that CI runs (tests/e2e/visual/**) / e2e test / @visual exclude"
            )
    for line in sorted(set(findings)):
        print(line)
    count = len(set(findings))
    if count == 0:
        print(
            f"[gate-{GATE_NUM}] visual-coverage: PASS — "
            f"{len(pages)} new page(s), all have a visual proof"
        )
        return EXIT_PASS
    # THE COUNT TRAVELS ON STDOUT. Returning it as the exit status truncated it
    # to one byte and made 256 findings indistinguishable from zero — see the
    # module docstring.
    print(
        f"[gate-{GATE_NUM}] visual-coverage: FAIL — "
        f"{count} new page component(s) without a visual baseline"
    )
    return EXIT_FAIL


def run_report(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF") or None
    pages = _collect(app_dir, base_ref)
    visual_runs, visual_why = visual_suite_runs_in_ci(app_dir)
    visual_corpus = _e2e_corpus(app_dir, visual_only=True, include_visual=visual_runs)
    e2e_corpus = _e2e_corpus(app_dir, visual_only=False, include_visual=visual_runs)
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
        "visual_suite_credited": visual_runs,
        "visual_suite_reason": visual_why,
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
