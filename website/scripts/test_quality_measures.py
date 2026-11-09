#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the measures in quality_measures.py that the SIG matrix publishes."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quality_measures as qm  # noqa: E402

REAL_RUN = subprocess.run
CLOVER = ('<?xml version="1.0"?><coverage generated="1"><project timestamp="1">'
          '<file name="a.php"><metrics statements="3" coveredstatements="1"/></file>'
          '<metrics statements="207165" coveredstatements="164994" methods="9"/></project></coverage>')


def bundle(xml=CLOVER, name="clover.xml"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(name, xml)
    return buf.getvalue()


def artifact(art_id, branch, created="2026-11-08T19:07:00Z", expired=False, head_repo=1):
    return {"id": art_id, "expired": expired, "created_at": created,
            "workflow_run": {"head_branch": branch, "head_sha": "f7f23ef5b3aa", "repository_id": 1,
                             "head_repository_id": head_repo}}


def fake_gh(listing, archives=None, fail=False):
    """A subprocess.run that answers `gh api` from `listing` and leaves every other command real."""
    calls = []

    def run(cmd, *args, **kwargs):
        if cmd[0] != "gh":
            return REAL_RUN(cmd, *args, **kwargs)
        calls.append(cmd[2])
        if fail:
            raise subprocess.CalledProcessError(1, cmd)
        if "/artifacts?" in cmd[2]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"artifacts": listing}).encode(), b"")
        art_id = int(cmd[2].split("/artifacts/")[1].split("/")[0])
        return subprocess.CompletedProcess(cmd, 0, (archives or {}).get(art_id, bundle()), b"")

    run.calls = calls
    return run


class PhpCoverage(unittest.TestCase):
    def measure(self, listing, archives=None, fail=False):
        """The php_coverage cell of a clone whose committed floor is 58.88."""
        with tempfile.TemporaryDirectory() as clone:
            with open(os.path.join(clone, ".coverage-baseline"), "w") as fh:
                fh.write("58.88\n")
            git = ["git", "-C", clone, "-c", "user.name=t", "-c", "user.email=t@example.org"]
            REAL_RUN(["git", "init", "-q", clone], check=True)
            REAL_RUN(git + ["add", "-A"], check=True)
            REAL_RUN(git + ["commit", "-q", "--no-gpg-sign", "-m", "x"], check=True)
            with mock.patch("subprocess.run", fake_gh(listing, archives, fail)), \
                    mock.patch.object(qm, "spec_coverage", return_value=(None, "")), \
                    mock.patch.object(qm, "e2e_coverage", return_value=(None, "")):
                return qm.measure("openregister", clone, {"languages": {}}, None)["php_coverage"]

    def test_reads_the_ci_clover_not_the_committed_floor(self):
        cell = self.measure([artifact(7, "development")])
        self.assertEqual(cell["value"], 79.64)
        self.assertEqual(cell["stars"], 3)
        self.assertIn("164994 of 207165 statements", cell["detail"])
        self.assertIn("development at f7f23ef5, 2026-11-08", cell["detail"])

    def test_development_wins_over_a_newer_branch_run(self):
        other = bundle(CLOVER.replace('coveredstatements="164994"', 'coveredstatements="1000"'))
        cell = self.measure([artifact(1, "feature/x", "2026-11-08T20:00:00Z"), artifact(2, "development")], {1: other})
        self.assertEqual(cell["value"], 79.64)

    def test_newest_other_branch_when_development_has_none(self):
        newest = bundle(CLOVER.replace('coveredstatements="164994"', 'coveredstatements="165000"'))
        cell = self.measure([artifact(1, "feature/x"), artifact(2, "feature/y", "2026-11-01T00:00:00Z")], {1: newest})
        self.assertEqual(cell["value"], 79.65)
        self.assertIn("feature/x", cell["detail"])

    def assertStaleFloor(self, cell):
        today = REAL_RUN(["date", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(cell["value"], 58.88)
        self.assertEqual(cell["stale"], today)
        self.assertTrue(cell["detail"].startswith("STALE: "))
        self.assertIn(f".coverage-baseline, last changed {today}", cell["detail"])

    def test_expired_and_fork_reports_are_skipped(self):
        cell = self.measure([artifact(1, "development", expired=True), artifact(2, "development", head_repo=9)])
        self.assertStaleFloor(cell)

    def test_no_report_falls_back_to_the_floor_marked_stale(self):
        cell = self.measure([])
        self.assertStaleFloor(cell)
        self.assertIn("no coverage report kept by CI", cell["detail"])

    def test_a_fresh_report_carries_no_stale_mark(self):
        self.assertNotIn("stale", self.measure([artifact(7, "development")]))

    def test_no_report_and_no_floor_shows_nothing(self):
        with tempfile.TemporaryDirectory() as clone, \
                mock.patch("subprocess.run", fake_gh([])):
            cell = qm.php_coverage("openregister", clone)
        self.assertIsNone(cell["value"])
        self.assertNotIn("stale", cell)

    def test_unreadable_reports_fall_back_to_the_stale_floor(self):
        for label, kwargs in (("gh failure", {"fail": True}),
                              ("bad xml", {"archives": {1: bundle("not xml")}}),
                              ("no clover", {"archives": {1: bundle(name="other.xml")}}),
                              ("no metrics", {"archives": {1: bundle("<coverage><project/></coverage>")}})):
            with self.subTest(label):
                cell = self.measure([artifact(1, "development")], **kwargs)
                self.assertStaleFloor(cell)
                self.assertIn("CI coverage report unreadable", cell["detail"])

    def test_clover_without_statements_has_no_percentage(self):
        xml = '<coverage><project><metrics statements="0" coveredstatements="0"/></project></coverage>'
        self.assertEqual(qm.clover_coverage(xml), (None, 0, 0))

    def test_every_page_is_read_for_a_development_report(self):
        full = [artifact(i, "feature/x") for i in range(1, 101)]

        def run(cmd, *args, **kwargs):
            if "/artifacts?" in cmd[2]:
                body = [artifact(200, "development")] if "page=2" in cmd[2] else full
                return subprocess.CompletedProcess(cmd, 0, json.dumps({"artifacts": body}).encode(), b"")
            return subprocess.CompletedProcess(cmd, 0, bundle(), b"")

        with mock.patch("subprocess.run", run):
            self.assertIn("development", qm.ci_coverage("openregister")[1])


class StaleCellText(unittest.TestCase):
    def test_the_matrix_cell_says_stale_and_when(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_sig_matrix", os.path.join(HERE, "build-sig-matrix.py"))
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        fresh = {"value": 79.64, "stars": 3, "detail": "ci"}
        stale = {"value": 58.88, "stars": 2, "detail": "STALE: x", "stale": "2026-08-07"}
        rows = {r["id"]: r for g in build.own_measures({"a": {"php_coverage": fresh}, "b": {"php_coverage": stale}})
                for r in g["rows"]}
        cells = rows["own.php_coverage"]["cells"]
        self.assertNotIn("stale", cells["a"]["text"])
        self.assertTrue(cells["b"]["text"].endswith(" stale 2026-08-07"))


class ComposerSeverity(unittest.TestCase):
    def audit(self, advisories):
        output = json.dumps({"advisories": advisories})

        def run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, output, "")

        with tempfile.TemporaryDirectory() as clone:
            open(os.path.join(clone, "composer.lock"), "w").close()
            with mock.patch("subprocess.run", run):
                return qm.audits(clone)

    def test_blank_severity_counts_as_high(self):
        for label, advisory in (("empty", {"severity": ""}), ("null", {"severity": None}),
                                ("missing", {}), ("spaces", {"severity": "  "})):
            with self.subTest(label):
                value, detail = self.audit({"acme/lib": [advisory]})
                self.assertEqual(value, 1)
                self.assertEqual(detail, "composer 1 high, 0 critical (1 without a severity, counted as high)")

    def test_keyed_advisories_are_read_too(self):
        self.assertEqual(self.audit({"acme/lib": {"0": {"severity": ""}}})[0], 1)

    def test_a_package_is_counted_once_at_its_worst_known_level(self):
        value, detail = self.audit({"acme/lib": [{"severity": ""}, {"severity": "critical"}],
                                    "acme/two": [{"severity": ""}, {"severity": "high"}]})
        self.assertEqual(value, 2)
        self.assertEqual(detail, "composer 1 high, 1 critical")

    def test_a_blank_next_to_a_low_rating_is_still_counted(self):
        self.assertEqual(self.audit({"acme/lib": [{"severity": "low"}, {"severity": ""}]})[0], 1)

    def test_rated_below_high_stays_uncounted(self):
        value, detail = self.audit({"acme/lib": [{"severity": "medium"}], "acme/two": [{"severity": "low"}]})
        self.assertEqual(value, 0)
        self.assertEqual(detail, "composer 0 high, 0 critical")

    def test_no_advisories(self):
        self.assertEqual(self.audit([])[0], 0)


class Adjacency(unittest.TestCase):
    MEASURES = {"audit": {"value": 0, "detail": ""}, "unmanaged": {"value": 0, "detail": ""}}

    def other(self, report):
        with tempfile.TemporaryDirectory() as clone:
            return qm.sig_other(clone, report, self.MEASURES)

    def test_a_two_way_pair_is_one_neighbour_on_each_side(self):
        with tempfile.TemporaryDirectory() as app:
            names = ("lib/A/a.php", "lib/B/b.php", "lib/C/c.php")
            for name in names:
                os.makedirs(os.path.dirname(os.path.join(app, name)), exist_ok=True)
                with open(os.path.join(app, name), "w") as fh:
                    fh.write("<?php\nclass X {}\n")
            deps = {names[0]: {names[1]}, names[1]: {names[0]}, names[2]: {names[1]}}
            structure = qm.sig.structure(app, {n: "php" for n in names}, deps)
        cell = self.other({"structure": {"php": structure}})["arch_adjacency"]
        self.assertEqual(cell["value"], 1.3)
        self.assertEqual(cell["stars"], 4)
        self.assertEqual(cell["detail"], "2 connected pairs between 3 components (estimate)")

    def test_the_four_star_limit_stays_on_six_neighbours(self):
        def stars(pairs):
            return self.other({"structure": {"php": {"component_entanglement": {
                "communication_lines": 99, "connected_pairs": pairs, "connected_components": 10}}}})["arch_adjacency"]["stars"]
        self.assertEqual(stars(30), 4)
        self.assertEqual(stars(31), "<4")

    def test_a_report_without_the_pair_count_gives_no_cell(self):
        report = {"structure": {"php": {"component_entanglement": {"communication_lines": 4, "connected_components": 2}}}}
        self.assertNotIn("arch_adjacency", self.other(report))


if __name__ == "__main__":
    unittest.main()
