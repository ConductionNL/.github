#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for write_gates_json.py, the runner's gates.json writer.

  1. Every declared gate is listed; one that emitted nothing is "not-run".
  2. A PASS has 0 findings; a FAIL or WARNING takes the count its reason
     states, ignoring numbers inside the log path; without one it counts the
     gate's findings log; a skip has no count.
  3. Every declared gate has a category, and only the matrix categories occur.
  4. The runner itself writes gates.json at full scope.

Run: python3 scripts/lib/test_write_gates_json.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import write_gates_json as w  # noqa: E402

RUNNER = os.path.join(os.path.dirname(HERE), "run-hydra-gates.sh")


def declared_of_runner():
    with open(RUNNER, encoding="utf-8") as fh:
        text = fh.read()
    return {int(n): name for n, name in re.findall(r'_(?:pass|fail|skip) ([0-9]+) "([^"]+)"', text)}


class Records(unittest.TestCase):
    def setUp(self):
        self.logs = tempfile.mkdtemp(prefix="gates-json-")

    def tearDown(self):
        shutil.rmtree(self.logs, ignore_errors=True)

    def build(self, lines, declared):
        return {g["gate"]: g for g in w.build(w.parse_records(io.StringIO("".join(lines))), declared,
                                              "full", self.logs)["gates"]}

    def test_a_declared_gate_without_a_verdict_is_not_run(self):
        gates = self.build(["1\tspdx-headers\tPASS\t\n"], {1: "spdx-headers", 2: "forbidden-patterns"})
        self.assertEqual(gates[1]["verdict"], "pass")
        self.assertEqual(gates[1]["findings"], 0)
        self.assertEqual(gates[2]["verdict"], "not-run")
        self.assertIsNone(gates[2]["findings"])

    def test_a_failure_takes_the_count_from_its_reason_not_from_the_log_path(self):
        gates = self.build(["60\ticon-vocabulary\tFAIL\t3 icon(s) outside the canonical vocabulary (ADR-077); "
                            "see /tmp/hydra-gates.7/hydra-gate-icon-vocabulary.log\n"], {60: "icon-vocabulary"})
        self.assertEqual((gates[60]["findings"], gates[60]["findings_from"]), (3, "verdict"))

    def test_a_count_with_a_thousands_separator(self):
        gates = self.build(["19\te2e-coverage\tWARNING\t1,187 scenario(s) missing @e2e\n"], {19: "e2e-coverage"})
        self.assertEqual(gates[19]["findings"], 1187)

    def test_a_failure_without_a_count_counts_its_log(self):
        with open(os.path.join(self.logs, "hydra-gate-composer-audit.log"), "w") as fh:
            fh.write("advisory one\n\nadvisory two\n")
        gates = self.build(["4\tcomposer-audit\tFAIL\tCVEs or advisories — see /x/hydra-gate-composer-audit.log\n"],
                           {4: "composer-audit"})
        self.assertEqual((gates[4]["findings"], gates[4]["findings_from"]), (2, "log"))

    def test_a_failure_with_neither_has_no_count(self):
        gates = self.build(["53\teffective-manifest-crossref\tFAIL\tajv not resolvable\n"],
                           {53: "effective-manifest-crossref"})
        self.assertIsNone(gates[53]["findings"])

    def test_skips_and_not_applicable_have_no_count(self):
        gates = self.build(["16\tspec-coverage\tNOT APPLICABLE\tno delta base, 0 methods\n",
                            "33\taxe-core\tSKIPPED\tstructural: 2 inputs missing\n"],
                           {16: "spec-coverage", 33: "axe-core"})
        self.assertEqual(gates[16]["verdict"], "not-applicable")
        self.assertEqual(gates[33]["verdict"], "skipped")
        self.assertIsNone(gates[16]["findings"])
        self.assertIsNone(gates[33]["findings"])

    def test_the_last_verdict_of_a_gate_wins(self):
        gates = self.build(["7\tno-admin-idor\tWARNING\t2 sub-findings\n", "7\tno-admin-idor\tFAIL\t5 methods\n"],
                           {7: "no-admin-idor"})
        self.assertEqual((gates[7]["verdict"], gates[7]["findings"]), ("fail", 5))


class Categories(unittest.TestCase):
    def test_every_declared_gate_has_a_matrix_category(self):
        declared = declared_of_runner()
        self.assertGreater(len(declared), 90)
        missing = sorted(set(declared) - set(w.CATEGORY))
        self.assertEqual(missing, [], "declared gates without a category")
        self.assertEqual(set(w.CATEGORY.values()), {"security", "accessibility", "architecture", "specs",
                                                    "licensing", "dependencies", "ui", "other"})


class Runner(unittest.TestCase):
    def test_the_runner_writes_gates_json(self):
        app = tempfile.mkdtemp(prefix="gates-json-app-")
        logs = tempfile.mkdtemp(prefix="gates-json-logs-")
        try:
            subprocess.run(["git", "init", "-q", app], check=True)
            os.makedirs(os.path.join(app, "lib"))
            with open(os.path.join(app, "lib", "A.php"), "w") as fh:
                fh.write("<?php\n/**\n * @license EUPL-1.2\n * @copyright 2026 Conduction\n */\nclass A {}\n")
            subprocess.run(["git", "-C", app, "add", "."], check=True)
            subprocess.run(["git", "-C", app, "-c", "user.email=f@example.invalid", "-c", "user.name=F",
                            "commit", "-qm", "a"], check=True)
            env = dict(os.environ, HYDRA_GATE_LOG_DIR=logs)
            subprocess.run(["bash", RUNNER, "--full", app], env=env, capture_output=True, text=True, timeout=1800)
            with open(os.path.join(logs, "gates.json")) as fh:
                doc = json.load(fh)
            self.assertEqual(doc["scope"], "full")
            self.assertEqual(len(doc["gates"]), len(declared_of_runner()))
            by_gate = {g["gate"]: g for g in doc["gates"]}
            self.assertEqual(by_gate[1]["name"], "spdx-headers")
            self.assertIn(by_gate[1]["verdict"], ("pass", "fail"))
            for g in doc["gates"]:
                self.assertEqual(set(g), {"gate", "name", "verdict", "findings", "findings_from", "scope",
                                          "category", "reason"})
        finally:
            shutil.rmtree(app, ignore_errors=True)
            shutil.rmtree(logs, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
