#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Unit tests for controller_resolver.py: route controller names to files."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import controller_resolver as cr  # noqa: E402


class Resolve(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ctrl-resolver-")
        self.write("composer.json", json.dumps({"autoload": {"psr-4": {"OCA\\Fx\\": "lib/"}}}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def ctrl(self, rel, ns, cls):
        self.write(rel, f"<?php\nnamespace {ns};\n\nclass {cls} extends Controller\n{{\n}}\n")

    def resolve(self, name):
        return cr.Resolver(self.root, "OCA\\Fx").resolve(name)

    def test_plain_and_snake_case_names_resolve_under_lib_controller(self):
        self.ctrl("lib/Controller/MyThingController.php", "OCA\\Fx\\Controller", "MyThingController")
        self.assertEqual(self.resolve("my_thing"), "lib/Controller/MyThingController.php")
        self.assertEqual(self.resolve("myThing"), "lib/Controller/MyThingController.php")

    def test_a_moved_controller_resolves_through_its_class_alias(self):
        self.ctrl("lib/Search/Controller/WidgetController.php", "OCA\\Fx\\Search\\Controller", "WidgetController")
        self.write("appinfo/class-aliases.json", json.dumps({"aliases": {
            "OCA\\Fx\\Controller\\WidgetController": {"class": "OCA\\Fx\\Search\\Controller\\WidgetController"}}}))
        self.assertEqual(self.resolve("widget"), "lib/Search/Controller/WidgetController.php")

    def test_a_moved_controller_without_an_alias_does_not_resolve(self):
        self.ctrl("lib/Search/Controller/WidgetController.php", "OCA\\Fx\\Search\\Controller", "WidgetController")
        self.assertIsNone(self.resolve("widget"))

    def test_namespaced_and_fully_qualified_names(self):
        self.ctrl("lib/AppHost/Controller/GenericHealthController.php", "OCA\\Fx\\AppHost\\Controller",
                  "GenericHealthController")
        self.assertEqual(self.resolve("AppHost\\Controller\\GenericHealth"),
                         "lib/AppHost/Controller/GenericHealthController.php")
        self.assertEqual(self.resolve("OCA\\Fx\\AppHost\\Controller\\GenericHealth"),
                         "lib/AppHost/Controller/GenericHealthController.php")

    def test_a_class_off_its_psr4_path_is_found_by_its_declaration(self):
        self.ctrl("lib/Legacy/odd_file.php", "OCA\\Fx\\Controller", "OddController")
        self.assertEqual(self.resolve("odd"), "lib/Legacy/odd_file.php")

    def test_main_prints_one_line_per_name_and_a_census(self):
        self.ctrl("lib/Controller/AController.php", "OCA\\Fx\\Controller", "AController")
        import contextlib
        import io
        buf = io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("a\nmissing\n")
        try:
            with contextlib.redirect_stdout(buf):
                rc = cr.main(["x", self.root, "OCA\\Fx"])
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().splitlines(),
                         ["a\tlib/Controller/AController.php", "missing\t", "# resolved 1 of 2"])


if __name__ == "__main__":
    unittest.main()
