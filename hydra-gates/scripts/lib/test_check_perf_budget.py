#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""Tests for gate 124 (check_perf_budget.py): the gate on real app trees, the
injected Newman test, and the per-request time table.

Run: python3 scripts/lib/test_check_perf_budget.py
"""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_perf_budget as perf  # noqa: E402

TODAY = "2026-11-24"
SPEC = (
    "import { test } from '@playwright/test'\n"
    "import { definePerformanceSpec } from '@conduction/nextcloud-vue/testing/performance'\n"
    "definePerformanceSpec(test)\n"
)
CALLER = (
    "jobs:\n  quality:\n    uses: ConductionNL/.github/.github/workflows/quality.yml@main\n"
    "    with:\n      app-name: demo\n      enable-newman: true\n"
)
BUDGET = {
    "app": "demo",
    "pages": [{"name": "Cases", "path": "/index.php/apps/demo/cases"}],
    "exceptions": [
        {"request": "GET /index.php/apps/demo/api/search*", "budgetMs": 250,
         "reason": "Search is unindexed until the index lands", "expires": "2026-12-31"},
    ],
}
COLLECTION = {
    "info": {"name": "demo", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "item": [{"name": "List", "request": {"method": "GET", "url": "{{base_url}}/index.php/apps/demo/api/cases"},
              "event": [{"listen": "test", "script": {"exec": ["pm.test('ok', function () {});"]}}]}],
}


def write(root: Path, rel: str, content) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def make_app(root: Path, **skip) -> Path:
    write(root, "appinfo/info.xml", "<info><id>demo</id></info>")
    if "budget" not in skip:
        write(root, "tests/performance/budget.json", BUDGET)
    if "spec" not in skip:
        write(root, "tests/e2e/performance.spec.ts", SPEC)
    if "collection" not in skip:
        write(root, "tests/integration/demo.postman_collection.json", COLLECTION)
    if "caller" not in skip:
        write(root, ".github/workflows/code-quality.yml", CALLER)
    return root


def run_check(root: Path) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = perf.check(root)
    return rc, out.getvalue()


class GateTest(unittest.TestCase):
    def setUp(self):
        os.environ["PERF_BUDGET_TODAY"] = TODAY
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("PERF_BUDGET_TODAY", None)

    def test_a_wired_app_passes(self):
        rc, out = run_check(make_app(self.root))
        self.assertEqual(rc, perf.EXIT_PASS, out)
        self.assertIn("checked 1 page(s)", out)
        self.assertIn("1 Postman collection(s) under the request budget", out)

    def test_not_an_app_is_not_applicable(self):
        rc, out = run_check(self.root)
        self.assertEqual(rc, perf.EXIT_NOT_APPLICABLE)
        self.assertIn("not applicable", out)

    def test_a_missing_budget_file_fails(self):
        rc, out = run_check(make_app(self.root, budget=True))
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn("tests/performance/budget.json is missing", out)

    def test_a_missing_spec_fails(self):
        rc, out = run_check(make_app(self.root, spec=True))
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn("no Playwright spec", out)

    def test_a_spec_in_node_modules_does_not_count(self):
        make_app(self.root, spec=True)
        write(self.root, "tests/node_modules/x/performance.spec.ts", SPEC)
        rc, _ = run_check(self.root)
        self.assertEqual(rc, perf.EXIT_FAIL)

    def test_newman_switched_off_fails(self):
        make_app(self.root, caller=True)
        write(self.root, ".github/workflows/code-quality.yml", CALLER.replace("true", "false"))
        rc, out = run_check(self.root)
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn("does not set enable-newman: true", out)

    def test_no_shared_workflow_fails(self):
        rc, out = run_check(make_app(self.root, caller=True))
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn("no workflow calls the shared quality.yml", out)

    def test_a_direct_newman_run_fails_but_a_comment_does_not(self):
        make_app(self.root)
        write(self.root, ".github/workflows/api.yml", "jobs:\n  a:\n    steps:\n      # newman run is in quality.yml\n")
        self.assertEqual(run_check(self.root)[0], perf.EXIT_PASS)
        write(self.root, ".github/workflows/api.yml", "jobs:\n  a:\n    steps:\n      - run: npx newman run tests/x.json\n")
        rc, out = run_check(self.root)
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn("runs `newman run` itself", out)

    def test_an_app_without_collections_needs_only_the_page_half(self):
        rc, out = run_check(make_app(self.root, collection=True, caller=True))
        self.assertEqual(rc, perf.EXIT_PASS, out)
        self.assertIn("0 Postman collection(s)", out)

    def test_the_app_id_must_match_info_xml(self):
        make_app(self.root)
        write(self.root, "tests/performance/budget.json", {**BUDGET, "app": "other"})
        rc, out = run_check(self.root)
        self.assertEqual(rc, perf.EXIT_FAIL)
        self.assertIn('appinfo/info.xml declares "demo"', out)


class ExceptionTest(unittest.TestCase):
    now = dt.date(2026, 11, 24)

    def problems(self, **exc):
        entry = {"page": "Cases", "budgetMs": 600, "reason": "The list waits on a slow count", "expires": "2026-12-31"}
        entry.update(exc)
        return perf.validate_budget({**BUDGET, "exceptions": [entry]}, "demo", self.now)

    def test_a_dated_reasoned_exception_is_valid(self):
        self.assertEqual(self.problems(), [])

    def test_an_expired_exception_fails(self):
        self.assertIn("exceptions[0] expired on 2026-11-01", self.problems(expires="2026-11-01")[0])

    def test_an_exception_too_far_ahead_fails(self):
        self.assertIn("more than 92 days ahead", self.problems(expires="2027-06-01")[0])

    def test_an_exception_needs_a_reason_and_one_target(self):
        problems = self.problems(reason="", request="GET /x")
        self.assertIn('exceptions[0] must name exactly one "page" or "request"', problems)
        self.assertIn('exceptions[0] needs a "reason" that says why', problems)

    def test_an_exception_for_an_unknown_page_fails(self):
        self.assertIn('exceptions[0] names page "Nope", which is not in "pages"', self.problems(page="Nope"))


class InjectTest(unittest.TestCase):
    def test_inject_adds_one_budget_test_and_keeps_the_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "c.json", Path(tmp) / "out" / "c.json"
            src.write_text(json.dumps(COLLECTION), encoding="utf-8")
            exc = BUDGET["exceptions"]
            perf.inject(src, out, 300, exc)
            perf.inject(out, out, 300, exc)
            data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["item"], COLLECTION["item"])
        budget_events = [e for e in data["event"] if e["script"].get("id") == "adr-124-budget"]
        self.assertEqual(len(budget_events), 1)
        script = "\n".join(budget_events[0]["script"]["exec"])
        self.assertIn("var budget = 300;", script)
        # 250 ms at target scale is 750 ms at the CI ceiling.
        self.assertIn('"limit": 750', script)

    def test_a_method_and_path_pattern_matches_paths_and_a_name_matches_exactly(self):
        rule = perf.request_matcher("GET /index.php/apps/demo/api/search*")
        self.assertEqual(rule["method"], "GET")
        import re
        self.assertTrue(re.match(rule["path"], "/index.php/apps/demo/api/search/objects"))
        self.assertFalse(re.match(rule["path"], "/index.php/apps/demo/api/cases"))
        # The pattern runs in Newman's JavaScript sandbox, which has no inline flags.
        self.assertNotIn("(?", rule["path"])
        self.assertEqual(perf.request_matcher("List cases"), {"name": "List cases"})

    def test_expired_request_exceptions_are_not_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = Path(tmp) / "budget.json"
            stale = {**BUDGET["exceptions"][0], "expires": "2026-01-01"}
            budget.write_text(json.dumps({**BUDGET, "exceptions": [stale]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                live = perf._load_exceptions(str(budget), dt.date(2026, 11, 24))
        self.assertEqual(live, [])
        self.assertIn("expired on 2026-01-01", out.getvalue())


class ReportTest(unittest.TestCase):
    def test_the_table_lists_every_request_slowest_first_when_one_is_over(self):
        export = {"run": {"executions": [
            {"item": {"name": "fast"}, "request": {"method": "GET", "url": {"path": ["api", "a"]}},
             "response": {"code": 200, "responseTime": 40},
             "assertions": [{"assertion": "[budget] GET /api/a answers within 300 ms"}]},
            {"item": {"name": "slow"}, "request": {"method": "POST", "url": {"path": ["api", "b"]}},
             "response": {"code": 201, "responseTime": 812},
             "assertions": [{"assertion": "[budget] POST /api/b answers within 300 ms", "error": {"message": "x"}}]},
        ]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "1.json"
            path.write_text(json.dumps(export), encoding="utf-8")
            summary = Path(tmp) / "summary.md"
            os.environ["GITHUB_STEP_SUMMARY"] = str(summary)
            try:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    rc = perf.report([path], 300)
            finally:
                os.environ.pop("GITHUB_STEP_SUMMARY", None)
            text = out.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("2 request(s) timed against 300 ms; 1 over budget", text)
            self.assertLess(text.index("| 812 | OVER | 201 | POST /api/b | slow |"), text.index("| 40 | ok |"))
            self.assertIn("1 of 2 request(s) over 300 ms", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
