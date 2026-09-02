#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-55's cross-app widget rule in check_detail_page_discipline.py.

A widget reading ANOTHER app's OpenRegister register renders a value whether or
not that app is installed: the query 404s and an aggregation shows ``0``, which
is exactly what a real zero shows. dossiq's `case-kpis-hours` tile did this on
every install without humaniq and looked correct doing it, on every case, for
as long as it shipped. Declaring ``requiredApp`` makes the widget host render a
set-up state instead of asking.

WHAT THIS SUITE IS ACTUALLY GUARDING
------------------------------------
Not "does the rule fire" — that is the easy half. The three ways this rule goes
wrong in a direction nobody notices are:

  1. it stops firing (a refactor drops the check) and the class returns;
  2. it fires on the app's OWN registers, which would flag every widget in
     every app and get the whole rule reverted;
  3. it fires on an app that ships no register file, where "which registers are
     mine" is UNKNOWABLE — judging against an empty set flags everything.

So each is asserted separately, and the negative cases carry the weight.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "check_detail_page_discipline.py")


class CrossAppWidgetRule(unittest.TestCase):
    """gate-55 (g): a widget on another app's register must declare requiredApp."""

    def _app(self, root, widget, *, ships_register=True):
        """Write a minimal app tree with one detail page carrying *widget*."""
        os.makedirs(os.path.join(root, "src"), exist_ok=True)
        if ships_register:
            os.makedirs(os.path.join(root, "lib", "Settings"), exist_ok=True)
            with open(os.path.join(root, "lib", "Settings", "fx_register.json"),
                      "w", encoding="utf-8") as f:
                json.dump({"openapi": "3.0.0", "components": {
                    "registers": {"fxapp": {"title": "Fx"}}, "schemas": {}}}, f)
        manifest = {"version": "1.0.0", "pages": [{
            "id": "Detail", "route": "/x/:id", "type": "detail", "title": "D",
            "config": {"register": "fxapp", "schema": "thing",
                       "widgets": [widget],
                       "layout": [{"id": "1", "widgetId": widget["id"],
                                   "gridX": 0, "gridY": 0,
                                   "gridWidth": 4, "gridHeight": 2}]}}]}
        with open(os.path.join(root, "src", "manifest.json"), "w",
                  encoding="utf-8") as f:
            json.dump(manifest, f)

    def _findings(self, root):
        """Run the checker and return only this rule's findings."""
        log = os.path.join(root, "out.log")
        r = subprocess.run([sys.executable, TARGET, log, "src/manifest.json"],
                           capture_output=True, text=True, cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr)
        if not os.path.exists(log):
            return []
        with open(log, encoding="utf-8") as f:
            return [ln for ln in f.read().splitlines() if "requiredApp" in ln]

    # -- it fires -----------------------------------------------------------

    def test_a_foreign_register_without_requiredApp_is_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-hours", "type": "stats-block", "title": "Hours",
                          "content": {"entries": [{"register": "humaniq",
                                                   "schema": "TimeEntry",
                                                   "metric": "sum"}]}})
            found = self._findings(d)
            self.assertEqual(len(found), 1, found)
            self.assertIn("'humaniq'", found[0])
            self.assertIn("w-hours", found[0])

    def test_it_reads_the_single_source_shape_too_not_only_entries(self):
        # `content.register` and `content.entries[].register` are both live
        # shapes; covering only the one dossiq happened to use would let the
        # other half of the class through.
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-list", "type": "object-list", "title": "Decisions",
                          "content": {"register": "decidiq", "schema": "Decision"}})
            self.assertEqual(len(self._findings(d)), 1)

    # -- it does NOT fire ---------------------------------------------------

    def test_declaring_requiredApp_clears_it(self):
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-hours", "type": "stats-block", "title": "Hours",
                          "requiredApp": "humaniq",
                          "content": {"entries": [{"register": "humaniq",
                                                   "schema": "TimeEntry",
                                                   "metric": "sum"}]}})
            self.assertEqual(self._findings(d), [])

    def test_requiredApp_is_honoured_inside_content_as_well(self):
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-hours", "type": "stats-block", "title": "Hours",
                          "content": {"requiredApp": "humaniq",
                                      "entries": [{"register": "humaniq",
                                                   "schema": "TimeEntry",
                                                   "metric": "sum"}]}})
            self.assertEqual(self._findings(d), [])

    def test_the_apps_OWN_register_is_never_flagged(self):
        # If this regressed, every widget in every app becomes a finding and
        # the rule gets reverted wholesale rather than fixed.
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-own", "type": "object-list", "title": "Things",
                          "content": {"register": "fxapp", "schema": "thing"}})
            self.assertEqual(self._findings(d), [])

    def test_an_app_shipping_no_register_file_is_skipped_not_flagged(self):
        # "Which registers are mine" is unknowable here. An empty set would
        # make EVERY widget foreign — the rule must decline to judge instead.
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-any", "type": "object-list", "title": "Things",
                          "content": {"register": "anything", "schema": "thing"}},
                      ships_register=False)
            self.assertEqual(self._findings(d), [])

    def test_a_token_register_is_not_treated_as_an_app_name(self):
        # `@`-prefixed values are resolved at render time from the page context.
        with tempfile.TemporaryDirectory() as d:
            self._app(d, {"id": "w-tok", "type": "object-list", "title": "Things",
                          "content": {"register": "@config.register",
                                      "schema": "thing"}})
            self.assertEqual(self._findings(d), [])


if __name__ == "__main__":
    unittest.main()
