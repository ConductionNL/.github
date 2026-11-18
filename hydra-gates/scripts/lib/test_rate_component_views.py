#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for rate_component_views.py.

    python3 scripts/lib/test_rate_component_views.py

They pin the two transformations the script applies before it rates (merging components into the
foundation, and dropping the foundation's references to other components), and run the five views
on a small app: with a components file all five are rated, without one only A and B.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_dependencies as analysis  # noqa: E402
import rate_component_views as views  # noqa: E402

COMPONENTS = """components:
  - name: Kernel
    include:
      - ".*/lib/Contract/[^/]*"
  - name: Core
    include:
      - ".*/lib/Db/MagicMapper[.]php"
  - name: Processes
    include:
      - ".*/lib/Service/Flow/[^/]*"
"""


def parsed(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "components.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return analysis.read_components(path)


class FoundationMergeTest(unittest.TestCase):
    def test_core_is_renamed_to_the_foundation(self):
        out = views.merge_into_foundation(parsed(COMPONENTS))
        self.assertEqual([c["name"] for c in out["components"]], ["Kernel", "Kernel", "Processes"])

    def test_patterns_and_the_original_are_kept(self):
        definition = parsed(COMPONENTS)
        out = views.merge_into_foundation(definition)
        self.assertEqual(out["components"][1]["include"][0].pattern, ".*/lib/Db/MagicMapper[.]php")
        self.assertEqual(definition["components"][1]["name"], "Core")

    def test_foundation_and_merge_are_parameters(self):
        out = views.merge_into_foundation(parsed(COMPONENTS), "Base", ("Kernel", "Core"))
        self.assertEqual([c["name"] for c in out["components"]], ["Base", "Base", "Processes"])
        self.assertTrue(views.has_component(out, "Base"))
        self.assertFalse(views.has_component(out, "Kernel"))


class BackrefsTest(unittest.TestCase):
    def test_only_foundation_to_other_edges_are_dropped(self):
        comp = {"lib/Db/MagicMapper.php": "Kernel", "lib/Contract/X.php": "Kernel",
                "lib/Service/Flow/FlowService.php": "Processes"}.get
        deps = {
            "lib/Db/MagicMapper.php": {"lib/Contract/X.php", "lib/Service/Flow/FlowService.php"},
            "lib/Service/Flow/FlowService.php": {"lib/Db/MagicMapper.php"},
            "lib/Contract/X.php": set(),
        }
        out = views.without_foundation_backrefs(deps, comp)
        self.assertEqual(out["lib/Db/MagicMapper.php"], {"lib/Contract/X.php"})
        self.assertEqual(out["lib/Service/Flow/FlowService.php"], {"lib/Db/MagicMapper.php"})

    def test_foundation_backrefs_are_counted_per_component(self):
        comp = {"a": "Kernel", "b": "Kernel", "c": "Processes", "d": "Compliance"}.get
        deps = {"a": {"b", "c", "d"}, "b": {"c"}, "c": {"a"}, "d": set()}
        self.assertEqual(views.foundation_backrefs(deps, comp), {"Processes": 2, "Compliance": 1})

    def test_a_foundation_name_other_than_kernel_is_honoured(self):
        comp = {"a": "Base", "b": "Processes"}.get
        deps = {"a": {"b"}, "b": {"a"}}
        self.assertEqual(views.without_foundation_backrefs(deps, comp, "Base"), {"a": set(), "b": {"a"}})
        self.assertEqual(views.foundation_backrefs(deps, comp, "Base"), {"Processes": 1})

    def test_one_component_covers_lib(self):
        [comp] = views.one_component()["components"]
        self.assertTrue(comp["include"][0].fullmatch("/lib/Db/X.php"))


class KindTest(unittest.TestCase):
    def test_declarations_decide_the_kind(self):
        cases = {
            ("lib/Contract/X.php", "<?php\ninterface X {}"): "interface",
            ("lib/Db/T.php", "<?php\ntrait T {}"): "trait",
            ("lib/Exception/NopeException.php", "<?php\nclass NopeException {}"): "exception",
            ("lib/Event/DoneEvent.php", "<?php\nclass DoneEvent {}"): "event",
            ("lib/Db/Task.php", "<?php\nclass Task extends Entity {}"): "entity",
            ("lib/Db/TaskMapper.php", "<?php\nclass TaskMapper extends QBMapper {}"): "mapper",
            ("lib/Service/TaskService.php", "<?php\nclass TaskService {}"): "concrete class",
        }
        for (rel, text), kind in cases.items():
            self.assertEqual(views.kind_of(rel, text), kind, rel)


class TargetsTest(unittest.TestCase):
    def test_top_of_the_scale_needs_nothing_exposed(self):
        self.assertEqual(views.targets()["5.5"], {"exposed_share": 0.0, "violation_degree": 0.0})

    def test_half_a_star_above_four_is_the_five_star_band_limit(self):
        self.assertAlmostEqual(views.targets()["4.5"]["exposed_share"], 0.0275, places=4)
        self.assertAlmostEqual(views.targets()["4.5"]["violation_degree"], 0.0375, places=4)


NS = "OCA\\Demo"
APP_FILES = {
    "lib/Kernel/Value.php": f"namespace {NS}\\Kernel;\nclass Value {{}}\n",
    "lib/Db/ObjectMapper.php": f"namespace {NS}\\Db;\nuse {NS}\\Kernel\\Value;\nuse {NS}\\Service\\FlowService;\n"
                               "class ObjectMapper { public function x(Value $v, FlowService $f) {} }\n",
    "lib/Service/FlowService.php": f"namespace {NS}\\Service;\nuse {NS}\\Db\\ObjectMapper;\n"
                                   "class FlowService { public function __construct(ObjectMapper $m) {} }\n",
    "lib/Controller/FlowController.php": f"namespace {NS}\\Controller;\nuse {NS}\\Service\\FlowService;\n"
                                         "class FlowController { public function __construct(FlowService $s) {} }\n",
}
APP_COMPONENTS = """components:
  - name: Kernel
    include:
      - ".*/lib/Kernel/.*"
  - name: Core
    include:
      - ".*/lib/Db/.*"
  - name: Processes
    include:
      - ".*/lib/(Service|Controller)/Flow[^/]*"
"""


class ViewsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = self.tmp.name
        for rel, src in APP_FILES.items():
            os.makedirs(os.path.dirname(os.path.join(self.app, rel)), exist_ok=True)
            with open(os.path.join(self.app, rel), "w", encoding="utf-8") as fh:
                fh.write("<?php\n" + src)
        self.report = {"languages": {}, "structure": {}}

    def tearDown(self):
        self.tmp.cleanup()

    def write_components(self, text=APP_COMPONENTS):
        with open(os.path.join(self.app, "sigrid.components.yaml"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_without_a_components_file_only_a_and_b_are_rated(self):
        out = views.views(self.report, self.app)
        self.assertEqual(sorted(k for k in out if k != "skipped"), ["A", "B"])
        self.assertEqual(sorted(out["skipped"]), ["C", "D", "E"])
        self.assertIn("no `components:` block", out["skipped"]["C"])
        # B: the directory rule puts Controller, Db, Kernel and Service in four components.
        self.assertEqual(out["B"]["components"], 4)

    def test_a_is_one_component_and_left_unrated(self):
        out = views.views(self.report, self.app)
        self.assertEqual(out["A"]["components"], 1)
        self.assertIsNone(out["A"]["independence"])
        self.assertIn("one component", out["A"]["warning"])

    def test_with_a_components_file_all_five_views_are_rated(self):
        self.write_components()
        out = views.views(self.report, self.app)
        self.assertNotIn("skipped", out)
        self.assertEqual(out["C"]["components"], 3)
        self.assertEqual(out["D"]["components"], 2)
        # The mapper (in Core, so in the foundation for D) calls back into FlowService. The two
        # directions weigh the same, so both lines of the pair count as cyclic.
        self.assertEqual(out["D"]["foundation_backrefs"], {"Processes": 1})
        self.assertEqual(out["D"]["violations"], {"cyclic": 2})
        self.assertEqual(out["E"]["violations"], {})
        self.assertLess(out["E"]["violation_degree"], out["D"]["violation_degree"])
        self.assertGreater(out["C"]["exposed_by_component"]["Processes"]["exposed_loc"], 0)

    def test_d_and_e_are_skipped_without_the_foundation(self):
        self.write_components()
        out = views.views(self.report, self.app, foundation="Base", merge=())
        self.assertIn("C", out)
        self.assertEqual(sorted(out["skipped"]), ["D", "E"])
        self.assertIn("no component named Base", out["skipped"]["D"])

    def test_main_takes_the_app_and_the_merge_list(self):
        self.write_components()
        report = os.path.join(self.app, "report.json")
        with open(report, "w", encoding="utf-8") as fh:
            json.dump(self.report, fh)
        out = os.path.join(self.app, "views.json")
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            rc = views.main([self.app, "--report", report, "--foundation", "Base", "--merge", "Kernel,Core",
                             "--json", out])
        self.assertEqual(rc, 0)
        with open(out, encoding="utf-8") as fh:
            result = json.load(fh)
        self.assertEqual(result["D"]["foundation_backrefs"], {"Processes": 1})
        self.assertIn("targets", result)
        self.assertIn("E: 2 components", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
