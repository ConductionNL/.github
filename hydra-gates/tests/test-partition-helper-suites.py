#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the helper-suite sharding: the partition and the aggregate check.

The partition must put every suite on exactly one shard, whatever the timings
table says, and the aggregate must refuse each way a sharded run can lose a
verdict. Each refusal has its own case, so a check that stopped refusing is
seen here first.

Run: python3 hydra-gates/tests/test-partition-helper-suites.py   (exit 0 = green)
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(file_name: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(HERE, file_name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


part = _load("partition_helper_suites.py", "_part")
agg = _load("check-helper-shard-reports.py", "_agg")
LIB = os.path.join(HERE, "..", "scripts", "lib")
TIMINGS = os.path.join(HERE, "helper-suite-timings.tsv")


class PartitionTest(unittest.TestCase):

    def test_every_real_suite_is_on_exactly_one_shard(self):
        names = sorted(agg.discover(LIB))
        rows = part.partition(names, part.read_weights(TIMINGS), 6)
        self.assertEqual(sorted(n for _s, n in rows), names)
        self.assertTrue(all(0 <= s < 6 for s, _n in rows))

    def test_a_suite_missing_from_the_table_still_runs(self):
        rows = part.partition(["test_a.sh", "test_new.sh"], {"test_a.sh": 100}, 2)
        self.assertEqual(sorted(n for _s, n in rows), ["test_a.sh", "test_new.sh"])

    def test_the_split_is_deterministic(self):
        names = [f"test_{i}.sh" for i in range(40)]
        weights = {n: (i * 7) % 13 + 1 for i, n in enumerate(names)}
        first = part.partition(names, weights, 5)
        self.assertEqual(first, part.partition(list(reversed(names)), weights, 5))

    def test_heavy_suites_go_to_different_shards(self):
        rows = dict((n, s) for s, n in part.partition(
            ["test_a.sh", "test_b.sh", "test_c.sh", "test_d.sh"],
            {"test_a.sh": 300, "test_b.sh": 290, "test_c.sh": 5, "test_d.sh": 5}, 2))
        self.assertNotEqual(rows["test_a.sh"], rows["test_b.sh"])

    def test_the_measured_table_balances_the_real_suites(self):
        weights = part.read_weights(TIMINGS)
        names = sorted(agg.discover(LIB))
        load = [0] * 6
        for shard, name in part.partition(names, weights, 6):
            load[shard] += weights.get(name, part.DEFAULT_WEIGHT)
        self.assertLess(max(load), 1.25 * sum(load) / 6, load)


class AggregateTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.lib = os.path.join(self._tmp.name, "lib")
        self.rep = os.path.join(self._tmp.name, "rep")
        os.makedirs(self.lib)
        os.makedirs(self.rep)
        for name in ("test_a.sh", "test_b.py", "test_c.js"):
            open(os.path.join(self.lib, name), "w").close()

    def tearDown(self):
        self._tmp.cleanup()

    def _report(self, shard, rows):
        with open(os.path.join(self.rep, f"helper-suites-shard-{shard}.tsv"), "w") as fh:
            for verdict, name in rows:
                fh.write(f"{verdict}\t{name}\n")

    def _check(self, result="success"):
        return agg.problems(self.lib, self.rep, 2, result)

    def test_a_complete_green_run_passes(self):
        self._report(0, [("PASS", "test_a.sh"), ("QUARANTINED", "test_c.js")])
        self._report(1, [("PASS", "test_b.py")])
        self.assertEqual(self._check(), [])

    def test_a_suite_on_no_shard_fails(self):
        self._report(0, [("PASS", "test_a.sh")])
        self._report(1, [("PASS", "test_b.py")])
        self.assertEqual(self._check(), ["test_c.js ran on no shard"])

    def test_a_suite_on_two_shards_fails(self):
        self._report(0, [("PASS", "test_a.sh"), ("PASS", "test_c.js")])
        self._report(1, [("PASS", "test_b.py"), ("PASS", "test_c.js")])
        self.assertEqual(len(self._check()), 1)
        self.assertIn("test_c.js ran 2 times", self._check()[0])

    def test_a_failed_suite_fails(self):
        self._report(0, [("PASS", "test_a.sh"), ("FAIL", "test_c.js")])
        self._report(1, [("PASS", "test_b.py")])
        self.assertEqual(self._check(), ["test_c.js: FAIL on shard 0"])

    def test_a_shard_without_a_report_fails(self):
        self._report(0, [("PASS", "test_a.sh"), ("PASS", "test_b.py"), ("PASS", "test_c.js")])
        found = self._check()
        self.assertEqual(len(found), 1)
        self.assertIn("shard 1 left no report", found[0])

    def test_an_unknown_suite_in_a_report_fails(self):
        self._report(0, [("PASS", "test_a.sh"), ("PASS", "test_c.js"), ("PASS", "test_gone.sh")])
        self._report(1, [("PASS", "test_b.py")])
        self.assertEqual(self._check(), ["test_gone.sh was reported but is not a discovered suite"])

    def test_a_matrix_that_did_not_succeed_fails(self):
        self._report(0, [("PASS", "test_a.sh"), ("PASS", "test_c.js")])
        self._report(1, [("PASS", "test_b.py")])
        self.assertEqual(self._check("cancelled"), ["the shard matrix ended 'cancelled', not 'success'"])


if __name__ == "__main__":
    unittest.main()
