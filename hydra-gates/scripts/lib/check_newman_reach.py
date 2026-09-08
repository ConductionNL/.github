#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-112 newman-reach — a committed Postman collection that CI never runs.

WHY THIS EXISTS
===============

The Newman job in ``quality.yml`` runs the collections it finds under ONE
configured directory, ``newman-collection-path`` (default ``tests/integration``).
Anything committed elsewhere is never executed, and nothing says so. A repo can
carry hundreds of written, reviewed API assertions and run none of them, while
its Newman job reports green over whatever happens to sit in the right folder.

MEASURED 2026-09-08 across the 21 core apps, from ``origin/development`` of
each:

    committed in a *.postman_collection.json     3,067 requests
    executed by CI                               1,444 requests
    NEVER EXECUTED                               1,623 requests   (53%)

    dossiq         946 requests, `enable-newman: false`
    openregister   315 requests in tests/newman/ and tests/postman/,
                   neither of which is the configured path
    learniq         90 requests, `enable-newman: false`
    opencatalogi    84 requests in tests/federation/
    stackiq         57 requests, `enable-newman: false`

Two apps are worse than unreached. hermiq and portaliq each ship the untouched
scaffold collection: ONE request, to ``/status.php``, asserting that Nextcloud
itself is running. Their Newman job is green and has never made a single
assertion about the app.

WHAT IT REPORTS
===============

**V1 — collections exist and Newman is switched off.** Every request in the
repo is dead. The caller sets ``enable-newman: false``, or never sets it and
the input defaults to false.

**V2 — a collection outside the configured path.** It runs nowhere. Either move
it under ``newman-collection-path``, point that input at it, or delete it. A
collection kept "for reference" beside ones that run is indistinguishable, to
every future reader, from one that runs.

**V3 — a collection that asserts nothing.** Zero ``pm.test`` blocks across
every request. Newman will execute it, report requests sent, and pass. A
request without an assertion is a page view, not a test.

**V4 — the scaffold, still unedited.** Every request targets ``/status.php``.
That is the app template's health check. It proves Nextcloud booted, which the
rest of the job already required.

EXCLUSION
=========

A collection is excluded by putting ``@newman exclude <reason>`` in its
``info.description``. That field is the only place a Postman collection can
carry a comment, and it survives a round trip through the Postman UI. The
reason must be reason-bearing, exactly as gate-16 and gate-19 require.

Usage::

    # Gate mode:
    python3 scripts/lib/check_newman_reach.py [app-dir]

    # Report mode (JSON, always exits 0):
    python3 scripts/lib/check_newman_reach.py [app-dir] --mode report
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402

GATE_NUM = 112
GATE_NAME = "newman-reach"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_NOT_APPLICABLE = 4

# Directories that never hold a collection this repo is responsible for
# running. `lib/Resources/template/` is buildiq's shipped app scaffold: its
# collection is a TEMPLATE for generated apps, not a suite for buildiq.
_SKIP_DIR_PARTS = (
    "node_modules", "vendor", ".git", "dist", "build", "coverage",
    "playwright-report", "test-results",
)
_SKIP_PATH_SUBSTRINGS = ("lib/Resources/template/",)

_COLLECTION_GLOB = "*.postman_collection.json"
_EXCLUDE_RE = re.compile(exclude_pattern("newman"), re.MULTILINE)

# `newman-collection-path: "tests/postman"` / `newman-collection-path: tests/e2e`
_PATH_RE = re.compile(
    r"^\s*newman-collection-path\s*:\s*[\"']?([^\"'#\s]+)", re.MULTILINE
)
_ENABLE_RE = re.compile(r"^\s*enable-newman\s*:\s*(true|false)\b", re.MULTILINE)

_DEFAULT_PATH = "tests/integration"


def _iter_collections(app_dir: Path) -> list[Path]:
    """Every Postman collection committed in the repo.

    :param app_dir: The app root.
    :return: Sorted list of collection paths.
    """
    found: list[Path] = []
    for p in app_dir.rglob(_COLLECTION_GLOB):
        if not p.is_file():
            continue
        rel = p.relative_to(app_dir).as_posix()
        if any(part in _SKIP_DIR_PARTS for part in p.relative_to(app_dir).parts):
            continue
        if any(s in rel for s in _SKIP_PATH_SUBSTRINGS):
            continue
        found.append(p)
    return sorted(found)


def read_caller_config(app_dir: Path) -> tuple[bool, str, str | None]:
    """What does this repo's own workflow tell the Newman job to do?

    Read from the caller workflow rather than assumed, because the default and
    the configured value differ in five of the fleet's repos and the difference
    is the whole finding.

    :param app_dir: The app root.
    :return: ``(enabled, collection_path, workflow_rel_path_or_None)``.
    """
    wf_dir = app_dir / ".github" / "workflows"
    if not wf_dir.is_dir():
        return False, _DEFAULT_PATH, None
    for wf in sorted(wf_dir.glob("*.y*ml")):
        try:
            text = wf.read_text(encoding="utf-8")
        except OSError:
            continue
        if "quality.yml" not in text and "enable-newman" not in text:
            continue
        enable = _ENABLE_RE.search(text)
        if enable is None:
            continue
        path = _PATH_RE.search(text)
        return (
            enable.group(1) == "true",
            path.group(1) if path else _DEFAULT_PATH,
            str(wf.relative_to(app_dir)),
        )
    return False, _DEFAULT_PATH, None


def _walk_items(items, path=()):
    for it in items or []:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "?")
        if "item" in it:
            yield from _walk_items(it["item"], path + (name,))
        else:
            yield path + (name,), it


def _request_url(item: dict) -> str:
    req = item.get("request") or {}
    if isinstance(req, str):
        return req
    url = req.get("url")
    if isinstance(url, dict):
        return url.get("raw", "") or ""
    return url or ""


def inspect_collection(path: Path) -> dict:
    """Summarise one collection: requests, assertions, exclusion, shape.

    :param path: The collection file.
    :return: A dict of facts about it.
    """
    out = {
        "requests": 0, "assertions": 0, "excluded": False,
        "exclude_reason": None, "bare_exclude": False,
        "only_status_php": False, "unreadable": False,
    }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out["unreadable"] = True
        return out
    if not isinstance(data, dict):
        out["unreadable"] = True
        return out

    description = ((data.get("info") or {}).get("description") or "")
    if isinstance(description, dict):
        description = description.get("content") or ""
    marker = _EXCLUDE_RE.search(str(description))
    if marker:
        out["excluded"] = True
        reason = (marker.group("reason") or "").strip() if "reason" in (
            marker.groupdict() or {}
        ) else ""
        out["exclude_reason"] = reason or None
        out["bare_exclude"] = not is_reason_bearing(reason or None)

    urls: list[str] = []
    # `pm.test(` is the only assertion form Newman counts. Searched over the
    # whole serialised collection so a test script attached at collection,
    # folder or request level is all found, which is where the fleet puts them.
    out["assertions"] = json.dumps(data).count("pm.test(")
    for _p, item in _walk_items(data.get("item")):
        out["requests"] += 1
        urls.append(_request_url(item))
    out["only_status_php"] = bool(urls) and all("status.php" in u for u in urls)
    return out


def analyse(app_dir: Path) -> dict:
    """Full picture for one app.

    :param app_dir: The app root.
    :return: A report dict.
    """
    enabled, cfg_path, wf = read_caller_config(app_dir)
    collections = _iter_collections(app_dir)
    cfg_dir = (app_dir / cfg_path).resolve()

    rows = []
    for c in collections:
        facts = inspect_collection(c)
        # Reachable means: inside the configured directory, at any depth. The
        # workflow's own loop recurses there as of `quality.yml` 2026-09-08.
        try:
            inside = cfg_dir in c.resolve().parents
        except OSError:
            inside = False
        facts["path"] = c.relative_to(app_dir).as_posix()
        facts["inside_configured_path"] = inside
        facts["runs"] = bool(enabled and inside)
        rows.append(facts)

    findings: list[dict] = []
    live = [r for r in rows if not r["excluded"] or r["bare_exclude"]]

    if rows and not enabled:
        findings.append({
            "code": "V1",
            "detail": (
                f"{sum(r['requests'] for r in rows)} request(s) across "
                f"{len(rows)} collection(s) are committed, and this repo's "
                f"caller does not enable Newman"
                + (f" ({wf})" if wf else " (no caller workflow found)")
                + ". Not one of them has ever run."
            ),
            "paths": [r["path"] for r in rows],
        })
    else:
        for r in live:
            if not r["inside_configured_path"]:
                findings.append({
                    "code": "V2",
                    "detail": (
                        f"{r['path']} holds {r['requests']} request(s) and sits "
                        f"outside newman-collection-path ('{cfg_path}'), so CI "
                        f"never runs it. Move it under '{cfg_path}', repoint "
                        f"that input, or delete it."
                    ),
                    "paths": [r["path"]],
                })
            elif r["requests"] and not r["assertions"]:
                findings.append({
                    "code": "V3",
                    "detail": (
                        f"{r['path']} sends {r['requests']} request(s) and "
                        f"declares no pm.test. Newman will run it and pass. A "
                        f"request without an assertion is a page view."
                    ),
                    "paths": [r["path"]],
                })
            elif r["only_status_php"]:
                findings.append({
                    "code": "V4",
                    "detail": (
                        f"{r['path']} is the unedited app scaffold: every "
                        f"request targets /status.php, which asserts that "
                        f"Nextcloud booted and nothing about this app."
                    ),
                    "paths": [r["path"]],
                })

    for r in rows:
        if r["bare_exclude"]:
            findings.append({
                "code": "V5",
                "detail": (
                    f"{r['path']} carries a bare `@newman exclude` with no "
                    f"reason. An exclusion without a reason cannot be reviewed "
                    f"and cannot expire."
                ),
                "paths": [r["path"]],
            })

    return {
        "app": app_dir.name,
        "newman_enabled": enabled,
        "collection_path": cfg_path,
        "caller_workflow": wf,
        "collections": rows,
        "totals": {
            "collections": len(rows),
            "requests": sum(r["requests"] for r in rows),
            "requests_that_run": sum(r["requests"] for r in rows if r["runs"]),
            "assertions": sum(r["assertions"] for r in rows),
        },
        "findings": findings,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", nargs="?", default=".")
    parser.add_argument("--mode", choices=("gate", "report"), default="gate")
    args = parser.parse_args(argv[1:])

    app_dir = Path(args.app_dir).resolve()
    if not app_dir.is_dir():
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: ERROR — {app_dir} is not a "
            f"readable directory, so nothing was inspected."
        )
        return EXIT_ERROR

    try:
        result = analyse(app_dir)
    except Exception as exc:  # noqa: BLE001 — a crash must not read as PASS
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: ERROR — {type(exc).__name__}: {exc}")
        return EXIT_ERROR

    if args.mode == "report":
        print(json.dumps(result, indent=2))
        return EXIT_PASS

    if not result["collections"]:
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: NOT APPLICABLE — this repo commits "
            f"no *.postman_collection.json, so there is no API suite to reach."
        )
        return EXIT_NOT_APPLICABLE

    findings = result["findings"]
    t = result["totals"]
    if not findings:
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: PASS — {t['requests']} request(s) "
            f"in {t['collections']} collection(s), all reachable by CI and all "
            f"asserting something."
        )
        return EXIT_PASS

    print(
        f"[gate-{GATE_NUM}] {GATE_NAME}: FAIL — {len(findings)} finding(s). "
        f"{t['requests_that_run']} of {t['requests']} committed request(s) run."
    )
    for f in findings:
        print(f"  {f['code']}  {f['detail']}")
    print(
        "  Fix: move the collection under newman-collection-path, repoint that "
        "input, delete it, or put `@newman exclude <reason>` in the "
        "collection's info.description."
    )
    return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main(sys.argv))
