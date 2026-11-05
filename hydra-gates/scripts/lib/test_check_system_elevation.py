#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate 97: elevation from a forbidden caller, including component directories."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_system_elevation as cse  # noqa: E402

ELEVATING = "<?php\nclass X\n{\n    public function go(): void\n    {\n        $this->ctx->runAsSystem(fn () => 1);\n    }\n}\n"


class ForbiddenCallers(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gate97-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_on(self, rel):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(ELEVATING)
        buf = io.StringIO()
        argv = sys.argv
        sys.argv = ["x", self.root]
        try:
            with contextlib.redirect_stdout(buf):
                rc = cse.main()
        finally:
            sys.argv = argv
        return rc, buf.getvalue()

    def test_a_controller_in_lib_controller_fails(self):
        rc, out = self.run_on("lib/Controller/ThingController.php")
        self.assertEqual(rc, 1, out)

    def test_a_controller_in_a_component_directory_fails(self):
        rc, out = self.run_on("lib/Search/Controller/ThingController.php")
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL  lib/Search/Controller/ThingController.php:6", out)

    def test_a_flow_node_in_a_component_directory_fails(self):
        rc, out = self.run_on("lib/Workflow/Service/Flow/Nodes/SendNode.php")
        self.assertEqual(rc, 1, out)

    def test_a_background_job_in_a_component_directory_may_elevate(self):
        rc, out = self.run_on("lib/Search/BackgroundJob/ReindexJob.php")
        self.assertEqual(rc, 0, out)

    def test_a_controller_directory_two_levels_down_is_not_a_component(self):
        rc, out = self.run_on("lib/Service/Thing/Controller/Helper.php")
        self.assertEqual(rc, 0, out)

    def test_a_layer_directory_is_not_read_as_a_component(self):
        rc, out = self.run_on("lib/Service/Flow/Engine/Runner.php")
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
