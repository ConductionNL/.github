#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_newman_reach (gate-112). Run with:

    python3 scripts/lib/test_check_newman_reach.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_newman_reach as cnr  # noqa: E402


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _collection(requests, description: str = "", with_tests: bool = True) -> str:
    """Build a minimal but structurally real Postman v2.1 collection."""
    items = []
    for i, url in enumerate(requests):
        item = {"name": f"req-{i}", "request": {"method": "GET", "url": url}}
        if with_tests:
            item["event"] = [{
                "listen": "test",
                "script": {"exec": ["pm.test('ok', function () {",
                                    "  pm.response.to.have.status(200);", "});"]},
            }]
        items.append(item)
    return json.dumps({
        "info": {"name": "c", "description": description,
                 "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": items,
    })


_CALLER_ON = """\
jobs:
  quality:
    uses: ConductionNL/.github/.github/workflows/quality.yml@main
    with:
      app-name: demo
      enable-newman: true
"""

_CALLER_OFF = _CALLER_ON.replace("enable-newman: true", "enable-newman: false")
_CALLER_ON_CUSTOM = _CALLER_ON + '      newman-collection-path: "tests/newman"\n'


class NewmanReachTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _codes(self) -> list[str]:
        return [f["code"] for f in cnr.analyse(self.root)["findings"]]

    # -- caller config ------------------------------------------------------

    def test_reads_enable_and_path_from_the_caller(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON_CUSTOM)
        enabled, path, wf = cnr.read_caller_config(self.root)
        self.assertTrue(enabled)
        self.assertEqual(path, "tests/newman")
        self.assertEqual(wf, ".github/workflows/code-quality.yml")

    def test_an_unset_path_falls_back_to_the_workflow_default(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _enabled, path, _wf = cnr.read_caller_config(self.root)
        self.assertEqual(path, "tests/integration")

    # -- findings -----------------------------------------------------------

    def test_no_collections_is_not_applicable(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        self.assertEqual(cnr.main(["x", str(self.root)]), cnr.EXIT_NOT_APPLICABLE)

    def test_a_reachable_asserting_collection_passes(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), [])
        self.assertEqual(cnr.main(["x", str(self.root)]), cnr.EXIT_PASS)

    def test_V1_newman_switched_off_with_collections_committed(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), ["V1"])

    def test_V1_fires_once_for_the_whole_repo_not_once_per_collection(self):
        # The finding is "this repo runs no API tests", said once. Repeating it
        # per file would bury the single decision that fixes all of them.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        for n in "abc":
            _write(self.root, f"tests/integration/{n}.postman_collection.json",
                   _collection(["{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), ["V1"])

    def test_V2_a_collection_outside_the_configured_path(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/newman/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), ["V2"])

    def test_a_subdirectory_of_the_configured_path_is_reachable(self):
        # quality.yml recurses under the configured path as of 2026-09-08, so
        # buildiq's tests/integration/quarantine/ is reached and is not a V2.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/quarantine/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), [])

    def test_V3_a_collection_that_asserts_nothing(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"], with_tests=False))
        self.assertEqual(self._codes(), ["V3"])

    def test_V4_the_unedited_scaffold(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/app-template.postman_collection.json",
               _collection(["{{base_url}}/status.php"]))
        self.assertEqual(self._codes(), ["V4"])

    def test_a_real_suite_that_also_pings_status_php_is_not_the_scaffold(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/status.php", "{{base_url}}/api/things"]))
        self.assertEqual(self._codes(), [])

    # -- exclusions ---------------------------------------------------------

    def test_a_reason_bearing_exclusion_silences_the_finding(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/newman/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="@newman exclude vendor ZGW conformance "
                                       "suite, run by the supplier not by us"))
        self.assertEqual(self._codes(), [])

    def test_a_bare_exclusion_is_itself_a_finding(self):
        # Same rule as gate-16 and gate-19: an exclusion with no reason cannot
        # be reviewed and cannot expire.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/newman/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="@newman exclude"))
        self.assertEqual(self._codes(), ["V2", "V5"])

    def test_V1_does_not_count_a_collection_that_recorded_why_it_does_not_run(self):
        # 🔴 THE DEFECT IN #757. V1 was raised from every committed collection
        # whenever Newman was off, so a repo that had given each one a reason
        # was still told it carried unrun work, and the Fix line printed
        # underneath offered exactly the exclusion that could not help.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="@newman exclude the ZGW API is still in "
                                       "progress, this suite fails at 95 percent"))
        self.assertEqual(self._codes(), [])

    def test_V1_still_counts_the_collections_that_recorded_nothing(self):
        # The half that must not be lost: one reason does not excuse the rest,
        # and V1 names only the ones still unaccounted for.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/excused.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="@newman exclude owned by the supplier"))
        _write(self.root, "tests/integration/silent.postman_collection.json",
               _collection(["{{base_url}}/api/other"]))

        findings = cnr.analyse(self.root)["findings"]
        self.assertEqual([f["code"] for f in findings], ["V1"])
        self.assertEqual(findings[0]["paths"],
                         ["tests/integration/silent.postman_collection.json"])
        self.assertIn("1 collection(s)", findings[0]["detail"])

    def test_V1_still_counts_a_bare_exclusion_and_V5_still_names_it(self):
        # An exclusion with no reason is not a reason. It stays counted, and
        # keeps its own finding.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="@newman exclude"))
        self.assertEqual(self._codes(), ["V1", "V5"])

    def test_an_exclusion_on_its_own_line_of_a_longer_description_is_found(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/newman/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"],
                           description="Supplier conformance suite.\n"
                                       "@newman exclude owned by the ZGW vendor, "
                                       "we do not host the fixtures\nSee README."))
        self.assertEqual(self._codes(), [])

    # -- discovery ----------------------------------------------------------

    def test_vendor_and_node_modules_are_not_this_repos_responsibility(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "node_modules/x/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        _write(self.root, "vendor/y/b.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(cnr.analyse(self.root)["totals"]["collections"], 0)

    def test_a_shipped_app_scaffold_is_a_template_not_a_suite(self):
        # buildiq ships lib/Resources/template/tests/integration/… for the apps
        # it GENERATES. Reporting it would ask buildiq to run another app's
        # tests.
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root,
               "lib/Resources/template/tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/status.php"]))
        self.assertEqual(cnr.analyse(self.root)["totals"]["collections"], 0)

    def test_an_unreadable_collection_is_not_silently_dropped(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/broken.postman_collection.json",
               "{ this is not json")
        rows = cnr.analyse(self.root)["collections"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["unreadable"])

    # -- totals -------------------------------------------------------------

    def test_totals_separate_committed_from_executed(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/runs.postman_collection.json",
               _collection(["{{base_url}}/a", "{{base_url}}/b"]))
        _write(self.root, "tests/newman/orphan.postman_collection.json",
               _collection(["{{base_url}}/c"]))
        t = cnr.analyse(self.root)["totals"]
        self.assertEqual(t["requests"], 3)
        self.assertEqual(t["requests_that_run"], 2)

    def test_report_mode_always_exits_zero(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(
            cnr.main(["x", str(self.root), "--mode", "report"]), cnr.EXIT_PASS
        )

    def test_gate_mode_fails_on_a_finding(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        self.assertEqual(cnr.main(["x", str(self.root)]), cnr.EXIT_FAIL)

    def test_a_missing_directory_is_an_error_not_a_pass(self):
        self.assertEqual(
            cnr.main(["x", str(self.root / "nope")]), cnr.EXIT_ERROR
        )

    # -- the verdict word belongs to the runner (.github#729) ---------------
    #
    # This gate is report-only until an app sets
    # HYDRA_GATE_NEWMAN_REACH_BLOCKING=1, and that switch lives in
    # run-hydra-gates.sh. A helper that prints FAIL is asserting an outcome it
    # cannot know: the runner then emits WARNING for the same gate, 45 lines
    # apart, and the reader who was told to "count the named FAIL lines" counts
    # a failure that did not happen. Both arms below run the REAL main(), so
    # they fail if the word comes back in either direction.

    def _stdout_of(self, argv):
        import contextlib
        import io as _io
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cnr.main(argv)
        return rc, buf.getvalue()

    def test_the_finding_verdict_states_a_count_and_no_verdict_word(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_OFF)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        rc, out = self._stdout_of(["x", str(self.root)])
        self.assertEqual(rc, cnr.EXIT_FAIL)
        verdict = [ln for ln in out.splitlines() if ln.startswith("[gate-112]")]
        self.assertTrue(verdict, "the helper printed no [gate-112] line at all")
        for word in ("FAIL", "PASS", "WARNING"):
            for ln in verdict:
                self.assertNotIn(
                    word, ln,
                    f"the helper printed the verdict word {word!r} on {ln!r}; "
                    "only run-hydra-gates.sh knows whether this blocks",
                )
        self.assertIn("1 finding(s)", out)

    def test_the_clean_verdict_states_a_count_and_no_verdict_word(self):
        _write(self.root, ".github/workflows/code-quality.yml", _CALLER_ON)
        _write(self.root, "tests/integration/a.postman_collection.json",
               _collection(["{{base_url}}/api/things"]))
        rc, out = self._stdout_of(["x", str(self.root)])
        self.assertEqual(rc, cnr.EXIT_PASS)
        for ln in out.splitlines():
            if ln.startswith("[gate-112]"):
                for word in ("FAIL", "PASS", "WARNING"):
                    self.assertNotIn(word, ln)
        self.assertIn("0 finding(s)", out)


if __name__ == "__main__":
    unittest.main()
