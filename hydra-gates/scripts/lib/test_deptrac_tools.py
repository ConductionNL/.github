#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for deptrac_areas.py, deptrac_summary.py and deptrac/layers.yaml.

    python3 scripts/lib/test_deptrac_tools.py

AreasTest pins how a components file becomes a deptrac config: one layer per area, include
patterns without the leading wildcard and anchored at the end, and a ruleset in which every area
may use only the shared area; --check reports a stale file. SummaryTest pins how a deptrac JSON
report is counted: occurrences per layer pair, and distinct class pairs. LayersTest keeps the
generic layering config in step with the roles of analyse_dependencies.py.
"""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_dependencies  # noqa: E402
import deptrac_areas  # noqa: E402
import deptrac_summary  # noqa: E402

COMPONENTS = """components:
  - name: Kernel
    include:
      - ".*/lib/Kernel/.*"
  - name: Processes
    include:
      - ".*/lib/Service/Flow/.*"
      - ".*/lib/Controller/Flow[^/]*[.]php"
  - name: Search
    include:
      - ".*/lib/Search/.*"
"""


class AreasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = self.tmp.name
        with open(os.path.join(self.app, "sigrid.components.yaml"), "w", encoding="utf-8") as fh:
            fh.write(COMPONENTS)
        self.definition = analyse_dependencies.read_components(os.path.join(self.app, "sigrid.components.yaml"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_area_may_use_only_the_shared_area(self):
        text = deptrac_areas.render(self.definition, "sigrid.components.yaml")
        ruleset = text.split("  ruleset:\n", 1)[1]
        self.assertIn("    Kernel: ~\n", ruleset)
        self.assertEqual(ruleset.count("      - Kernel\n"), 2)

    def test_patterns_drop_the_leading_wildcard_and_anchor_the_end(self):
        text = deptrac_areas.render(self.definition, "sigrid.components.yaml")
        self.assertIn("value: 'lib/Kernel/.*$'", text)
        self.assertIn("value: 'lib/Controller/Flow[^/]*[.]php$'", text)

    def test_the_shared_area_is_a_parameter(self):
        text = deptrac_areas.render(self.definition, "x", shared="Search")
        ruleset = text.split("  ruleset:\n", 1)[1]
        self.assertIn("    Search: ~\n", ruleset)
        self.assertEqual(ruleset.count("      - Search\n"), 2)

    def test_without_the_shared_area_no_area_may_use_another(self):
        text = deptrac_areas.render(self.definition, "x", shared="Base")
        ruleset = text.split("  ruleset:\n", 1)[1]
        self.assertEqual(ruleset, "    Kernel: ~\n    Processes: ~\n    Search: ~\n")

    def test_check_reports_a_stale_file(self):
        out = os.path.join(self.app, "areas.yaml")
        self.assertEqual(deptrac_areas.main([self.app, "--out", out]), 0)
        self.assertEqual(deptrac_areas.main([self.app, "--out", out, "--check"]), 0)
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("# edited\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deptrac_areas.main([self.app, "--out", out, "--check"]), 1)

    def test_an_app_without_components_is_refused(self):
        os.remove(os.path.join(self.app, "sigrid.components.yaml"))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deptrac_areas.main([self.app]), 2)


class SummaryTest(unittest.TestCase):
    REPORT = {
        "Report": {"Violations": 3, "Allowed": 10},
        "files": {
            "/tmp/x/lib/Db/A.php": {"messages": [
                {"message": "OCA\\X\\Db\\A must not depend on OCA\\X\\Service\\S (Persistence on Service)", "line": 3},
                {"message": "OCA\\X\\Db\\A must not depend on OCA\\X\\Service\\S (Persistence on Service)", "line": 9},
            ]},
            "/tmp/x/lib/Event/E.php": {"messages": [
                {"message": "OCA\\X\\Event\\E must not depend on OCA\\X\\Db\\A (SharedType on Persistence)", "line": 4},
            ]},
        },
    }

    def test_counts_occurrences_and_class_pairs(self):
        summary = deptrac_summary.summarise(self.REPORT)
        rows = {r["layers"]: (r["occurrences"], r["class_pairs"]) for r in summary["by_layers"]}
        self.assertEqual(rows, {"Persistence -> Service": (2, 1), "SharedType -> Persistence": (1, 1)})
        self.assertEqual(summary["class_pairs"], 2)
        self.assertNotIn("/tmp/", str(summary))


class LayersTest(unittest.TestCase):
    def test_layer_directories_are_the_roles_of_the_analysis(self):
        with open(os.path.join(HERE, "deptrac", "layers.yaml"), encoding="utf-8") as fh:
            text = fh.read()
        values = re.findall(r"value: '([^']+)'", text)
        self.assertEqual(len(values), 4)
        by_layer = {}
        for value in values:
            own = re.search(r"\)\?\(?([A-Za-z|]+)\)?/$", value).group(1).split("|")
            excluded = re.search(r"\?!\(([A-Za-z|]+)\)", value).group(1).split("|")
            self.assertEqual(sorted(set(excluded) - {"AppInfo"}), sorted(analyse_dependencies.ROLES))
            for name in own:
                by_layer[name] = analyse_dependencies.ROLES[name][1]
        self.assertEqual(sorted(by_layer), sorted(analyse_dependencies.ROLES))


if __name__ == "__main__":
    unittest.main()
