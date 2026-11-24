#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""Gate 124 perf-budget, and the Newman half of the speed budget (hydra ADR-124).

Every API request answers within 100 ms of server time and every main page is
usable within 300 ms, warm. CI runners are shared and slower, so pull-request
and push runs use three times that: 300 ms and 1000 ms. The run's budget comes
from PERF_API_BUDGET_MS and PERF_PAGE_BUDGET_MS.

An app declares its main pages, and any temporary exception, in
``tests/performance/budget.json``. The Playwright half lives in
``@conduction/nextcloud-vue/testing/performance``.

Subcommands
-----------
check <app>
    The gate. Fails when the app has no valid budget file, no Playwright spec
    that runs it, an exception without a reason or past its expiry, or Postman
    collections that do not run through the shared workflow (which is what
    applies the request budget).
inject <collection> <out>
    Writes a copy of a Postman collection with a collection-level test that
    asserts every request's response time against the run's budget.
report <export.json>...
    Prints the per-request time table from Newman JSON exports, slowest first,
    and appends it to $GITHUB_STEP_SUMMARY when requests are over budget.

Exit codes for ``check``: 0 pass, 1 findings, 2 error, 4 not applicable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_newman_reach import _iter_collections, read_caller_config  # noqa: E402

GATE = "[gate-124] perf-budget"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_NOT_APPLICABLE = 4

PAGE_TARGET_MS = 300
API_TARGET_MS = 100
BUDGET_FILE = Path("tests") / "performance" / "budget.json"
# An exception is a dated promise, not a standing waiver.
MAX_EXCEPTION_DAYS = 92
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
SPEC_SUFFIXES = (".spec.ts", ".spec.js", ".spec.mjs", ".spec.cjs", ".test.ts", ".test.js")
SKIP_DIRS = {"node_modules", "vendor", ".git", "dist", "build", "coverage", "playwright-report", "test-results"}
_SPEC_IMPORT = re.compile(r"nextcloud-vue/testing/performance")
_SPEC_CALL = re.compile(r"\bdefinePerformanceSpec\s*\(")
_SHARED_WORKFLOW = re.compile(r"uses:\s*ConductionNL/\.github/\.github/workflows/quality\.yml@")
_DIRECT_NEWMAN = re.compile(r"^(?!\s*#).*\bnewman\s+run\b", re.MULTILINE)
_APP_ID = re.compile(r"<id>\s*([^<\s]+)\s*</id>")


def today() -> dt.date:
    """The run date, overridable for tests through PERF_BUDGET_TODAY."""
    forced = os.environ.get("PERF_BUDGET_TODAY", "").strip()
    return dt.date.fromisoformat(forced) if forced else dt.datetime.now(dt.timezone.utc).date()


def env_budget(name: str, fallback: int) -> int:
    """A positive integer budget from the environment."""
    try:
        value = int(os.environ.get(name, "").strip())
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def _text(value) -> bool:
    """Whether ``value`` is a non-blank string."""
    return isinstance(value, str) and value.strip() != ""


def _parse_day(value) -> dt.date | None:
    """A ``YYYY-MM-DD`` string as a date, or None."""
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def validate_budget(budget, app_id: str | None, now: dt.date) -> list[str]:
    """Problems with a parsed budget file; empty when it is valid.

    :param budget: Parsed ``budget.json``.
    :param app_id: The id from ``appinfo/info.xml``, when known.
    :param now: The run date.
    :return: One message per problem.
    """
    if not isinstance(budget, dict):
        return ["budget.json must be a JSON object"]
    problems = _app_problems(budget.get("app"), app_id)
    names: set[str] = set()
    pages = budget.get("pages") if isinstance(budget.get("pages"), list) else []
    if not pages:
        problems.append('"pages" must list at least one main page')
    for i, page in enumerate(pages):
        problems.extend(_page_problems(i, page, names))
    exceptions = budget.get("exceptions", [])
    if not isinstance(exceptions, list):
        return problems + ['"exceptions" must be a list']
    for i, exc in enumerate(exceptions):
        problems.extend(_exception_problems(f"exceptions[{i}]", exc, names, now))
    return problems


def _app_problems(app, app_id: str | None) -> list[str]:
    """Problems with the ``app`` field."""
    if not _text(app):
        return ['"app" must name the app id']
    if app_id and app != app_id:
        return [f'"app" is "{app}" but appinfo/info.xml declares "{app_id}"']
    return []


def _page_problems(i: int, page, names: set[str]) -> list[str]:
    """Problems with one page entry; records its name in ``names``."""
    name = page.get("name") if isinstance(page, dict) else None
    if not _text(name):
        return [f'pages[{i}] needs a "name"']
    problems = [f'pages[{i}] repeats the name "{name}"'] if name in names else []
    names.add(name)
    path = page.get("path")
    if not isinstance(path, str) or not path.startswith("/"):
        problems.append(f'pages[{i}] ("{name}") needs a "path" starting with /')
    if "ready" in page and not _text(page["ready"]):
        problems.append(f'pages[{i}] ("{name}") has an empty "ready" selector')
    return problems


def _exception_problems(where: str, exc, names: set[str], now: dt.date) -> list[str]:
    """Problems with one exception entry."""
    if not isinstance(exc, dict):
        return [f"{where} must be an object"]
    problems = _target_problems(where, exc, names)
    budget_ms = exc.get("budgetMs")
    if not isinstance(budget_ms, int) or isinstance(budget_ms, bool) or budget_ms <= 0:
        problems.append(f'{where} needs a positive integer "budgetMs"')
    if not _text(exc.get("reason")) or len(exc["reason"].strip()) < 10:
        problems.append(f'{where} needs a "reason" that says why')
    return problems + _expiry_problems(where, exc.get("expires"), now)


def _target_problems(where: str, exc: dict, names: set[str]) -> list[str]:
    """An exception names exactly one known page or one request."""
    problems = []
    if [_text(exc.get(k)) for k in ("page", "request")].count(True) != 1:
        problems.append(f'{where} must name exactly one "page" or "request"')
    if "page" in exc and exc["page"] not in names:
        problems.append(f'{where} names page "{exc["page"]}", which is not in "pages"')
    return problems


def _expiry_problems(where: str, expires, now: dt.date) -> list[str]:
    """An exception expires on a real date, not past and not too far ahead."""
    expiry = _parse_day(expires)
    if expiry is None:
        return [f'{where} needs an "expires" date as YYYY-MM-DD']
    if expiry < now:
        return [f"{where} expired on {expires}: fix the slow page or request, or renew it with a new reason"]
    if (expiry - now).days > MAX_EXCEPTION_DAYS:
        return [f"{where} expires {expires}, more than {MAX_EXCEPTION_DAYS} days ahead"]
    return []


def _app_id(app_dir: Path) -> str | None:
    info = app_dir / "appinfo" / "info.xml"
    if not info.is_file():
        return None
    match = _APP_ID.search(info.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def _iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def find_perf_spec(app_dir: Path) -> Path | None:
    """The Playwright spec that runs the budget, if any."""
    tests = app_dir / "tests"
    if not tests.is_dir():
        return None
    for path in sorted(_iter_files(tests)):
        if not path.name.endswith(SPEC_SUFFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _SPEC_IMPORT.search(text) and _SPEC_CALL.search(text):
            return path
    return None


def newman_findings(app_dir: Path) -> tuple[int, list[str]]:
    """Whether the app's Postman collections run under the request budget.

    The shared workflow applies the budget, so a collection is wired when the
    app calls that workflow with Newman enabled and runs no ``newman run`` of
    its own.

    :return: ``(collection_count, findings)``.
    """
    collections = _iter_collections(app_dir)
    if not collections:
        return 0, []
    findings: list[str] = []
    wf_dir = app_dir / ".github" / "workflows"
    texts = {}
    if wf_dir.is_dir():
        texts = {wf: wf.read_text(encoding="utf-8", errors="replace") for wf in sorted(wf_dir.glob("*.y*ml"))}
    if not any(_SHARED_WORKFLOW.search(t) for t in texts.values()):
        findings.append(f"{len(collections)} Postman collection(s), and no workflow calls the shared quality.yml, which applies the request budget")
    else:
        enabled, _path, wf = read_caller_config(app_dir)
        if not enabled:
            findings.append(f"{len(collections)} Postman collection(s), and {wf or 'the caller workflow'} does not set enable-newman: true, so no request is timed")
    for wf, text in texts.items():
        if _DIRECT_NEWMAN.search(text):
            findings.append(f"{wf.relative_to(app_dir)} runs `newman run` itself, outside the shared workflow, so its requests are not held to the budget")
    return len(collections), findings


def budget_file_findings(app_dir: Path, app_id: str) -> tuple[int, list[str]]:
    """Findings on the app's budget file.

    :return: ``(page_count, findings)``.
    """
    budget_path = app_dir / BUDGET_FILE
    if not budget_path.is_file():
        return 0, [f"{BUDGET_FILE} is missing: declare the app's main pages there (ADR-124)"]
    try:
        budget = json.loads(budget_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return 0, [f"{BUDGET_FILE} is not valid JSON: {exc}"]
    pages = len(budget.get("pages") or []) if isinstance(budget, dict) else 0
    return pages, [f"{BUDGET_FILE}: {p}" for p in validate_budget(budget, app_id, today())]


def check(app_dir: Path) -> int:
    """Run gate 124 on one app."""
    app_id = _app_id(app_dir)
    if app_id is None:
        print(f"{GATE}: not applicable: no appinfo/info.xml, so this is not a Nextcloud app with pages to budget")
        return EXIT_NOT_APPLICABLE
    pages, findings = budget_file_findings(app_dir, app_id)
    spec = find_perf_spec(app_dir)
    if spec is None:
        findings.append("no Playwright spec under tests/ calls definePerformanceSpec from @conduction/nextcloud-vue/testing/performance, so no page is measured")
    collections, newman = newman_findings(app_dir)
    findings.extend(newman)
    for finding in findings:
        print(f"  {finding}")
    if findings:
        print(f"{GATE}: FAIL: {len(findings)} finding(s)")
        return EXIT_FAIL
    print(f"{GATE}: checked {pages} page(s) in {BUDGET_FILE}, spec {spec.relative_to(app_dir)}, {collections} Postman collection(s) under the request budget")
    return EXIT_PASS


def _load_exceptions(budget_file: str | None, now: dt.date) -> list[dict]:
    """The unexpired request exceptions from a budget file."""
    if not budget_file or not Path(budget_file).is_file():
        return []
    budget = json.loads(Path(budget_file).read_text(encoding="utf-8"))
    live = []
    for exc in budget.get("exceptions") or []:
        if not isinstance(exc, dict) or not exc.get("request"):
            continue
        expiry = _parse_day(exc.get("expires"))
        if expiry is None or expiry < now:
            print(f"perf-budget: the exception for {exc['request']} expired on {exc.get('expires')}, so the normal budget applies")
            continue
        live.append(exc)
    return live


def glob_to_regex(glob: str) -> str:
    """A path glob as an anchored regular expression both Python and JavaScript read.

    ``*`` matches any run of characters, including ``/``.
    """
    return "^" + ".*".join(re.sub(r"([.+?^${}()|\[\]\\/])", r"\\\1", part) for part in glob.split("*")) + "$"


def request_matcher(spec: str) -> dict:
    """How the injected script recognises one exception.

    ``"GET /index.php/apps/x/api/*"`` matches method and path with ``*``
    wildcards; anything else matches the request name exactly.
    """
    method, _, rest = spec.partition(" ")
    if method in HTTP_METHODS and rest.startswith("/"):
        return {"method": method, "path": glob_to_regex(rest)}
    return {"name": spec}


def build_test_script(budget_ms: int, exceptions: list[dict]) -> list[str]:
    """The collection-level Postman test, as script lines."""
    scale = budget_ms / API_TARGET_MS
    rules = []
    for exc in exceptions:
        rule = request_matcher(exc["request"])
        rule["limit"] = round(exc["budgetMs"] * scale)
        rule["note"] = f"exception until {exc['expires']}: {exc['reason']}"
        rules.append(rule)
    return [
        "// Injected by the shared quality workflow: hydra ADR-124, the request budget.",
        "(function () {",
        f"    var budget = {budget_ms};",
        f"    var rules = {json.dumps(rules)};",
        "    var name = pm.info.requestName;",
        "    var method = pm.request.method;",
        "    var path = pm.request.url.getPath();",
        "    var limit = budget, note = '';",
        "    rules.some(function (r) {",
        "        var hit = r.name ? r.name === name : (r.method === method && new RegExp(r.path).test(path));",
        "        if (hit) { limit = r.limit; note = ' (' + r.note + ')'; }",
        "        return hit;",
        "    });",
        "    pm.test('[budget] ' + method + ' ' + path + ' answers within ' + limit + ' ms' + note, function () {",
        "        pm.expect(pm.response.responseTime, name + ' took ' + pm.response.responseTime + ' ms').to.be.at.most(limit);",
        "    });",
        "})();",
    ]


def inject(collection: Path, out: Path, budget_ms: int, exceptions: list[dict]) -> None:
    """Write ``collection`` to ``out`` with the budget test added at collection level."""
    data = json.loads(collection.read_text(encoding="utf-8"))
    events = [e for e in data.get("event") or [] if (e.get("script") or {}).get("id") != "adr-124-budget"]
    events.append({
        "listen": "test",
        "script": {"id": "adr-124-budget", "type": "text/javascript", "exec": build_test_script(budget_ms, exceptions)},
    })
    data["event"] = events
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data), encoding="utf-8")


def _url_path(url) -> str:
    if isinstance(url, str):
        return url
    if isinstance(url, dict):
        path = url.get("path") or []
        return "/" + "/".join(str(p) for p in path) if isinstance(path, list) else str(path)
    return "?"


def _execution_row(ex: dict) -> dict | None:
    """One timed request from a Newman execution, or None when it got no response."""
    response = ex.get("response") or {}
    if "responseTime" not in response:
        return None
    request = ex.get("request") or {}
    budget = [a for a in ex.get("assertions") or [] if str(a.get("assertion", "")).startswith("[budget]")]
    return {
        "name": (ex.get("item") or {}).get("name", "?"),
        "method": request.get("method", "?"),
        "path": _url_path(request.get("url")),
        "status": response.get("code"),
        "ms": int(response.get("responseTime") or 0),
        "over": any(a.get("error") for a in budget),
    }


def read_exports(paths: list[Path]) -> list[dict]:
    """Every timed request in the Newman JSON exports, slowest first."""
    rows = []
    for path in paths:
        try:
            run = json.loads(path.read_text(encoding="utf-8"))["run"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        rows.extend(r for r in map(_execution_row, run.get("executions") or []) if r is not None)
    return sorted(rows, key=lambda r: r["ms"], reverse=True)


def report(paths: list[Path], budget_ms: int) -> int:
    """Print the time table; full when any request is over budget."""
    rows = read_exports(paths)
    over = [r for r in rows if r["over"]]
    print(f"perf-budget: {len(rows)} request(s) timed against {budget_ms} ms; {len(over)} over budget")
    if not rows:
        return EXIT_PASS
    shown = rows if over else rows[:10]
    lines = ["| ms | verdict | status | request | name |", "|---:|---|---:|---|---|"]
    for r in shown:
        verdict = "OVER" if r["over"] else "ok"
        lines.append(f"| {r['ms']} | {verdict} | {r['status']} | {r['method']} {r['path']} | {r['name']} |")
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if over and summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Request budget: {len(over)} of {len(rows)} request(s) over {budget_ms} ms\n\n")
            fh.write("\n".join(lines) + "\n\n")
    return EXIT_PASS


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("app_dir", nargs="?", default=".")
    p_inject = sub.add_parser("inject")
    p_inject.add_argument("collection")
    p_inject.add_argument("out")
    p_inject.add_argument("--budget-file")
    p_report = sub.add_parser("report")
    p_report.add_argument("exports", nargs="*")
    args = parser.parse_args(argv)
    budget_ms = env_budget("PERF_API_BUDGET_MS", API_TARGET_MS)
    try:
        if args.cmd == "check":
            return check(Path(args.app_dir))
        if args.cmd == "inject":
            inject(Path(args.collection), Path(args.out), budget_ms, _load_exceptions(args.budget_file, today()))
            return EXIT_PASS
        return report([Path(p) for p in args.exports], budget_ms)
    except (OSError, ValueError) as exc:
        print(f"{GATE}: error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
