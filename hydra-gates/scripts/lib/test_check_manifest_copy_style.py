#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-96's checker (check_manifest_copy_style.py).

Focus: the App Store scope added 2026-09-09, and the boundary between what
BLOCKS and what only WARNS.

The gate read `src/manifest.json` and nothing else, so `appinfo/info.xml` was
never checked even though it IS the App Store description. Measured over the
21 core apps at `development`, their info.xml files carry 204 em-dashes inside
`<description>` / `<summary>`, spread over 20 of the 21. So the new scope ships
ADVISORY: it prints, it does not fail.

That is a claim about an exit code, and an exit code is the one thing a reader
of the output cannot see. Hence arm 2, which is the whole suite:

  1. THE MANIFEST SCOPE STILL BLOCKS. Unchanged behaviour, pinned so that
     widening the checker cannot quietly soften the half that was already
     green fleet-wide.
  2. THE APP STORE SCOPE DOES NOT BLOCK. An info.xml violation with a clean
     manifest exits 0 while printing WARN. Wire `store_hits` into the return
     value and this arm goes red immediately. That is deliberate: when the
     fleet's 204 are cleared and the scope is promoted to blocking, this test
     is the thing that has to be edited, so the promotion cannot happen by
     accident.
  3. BOTH TOGETHER STILL BLOCK, and both are reported. A checker that stopped
     at the first finding, or that let the advisory mask the failure, fails
     here.
  4. THE ELEMENT SCOPE IS `<description>` AND `<summary>`, NOT THE FILE.
     273 of the fleet's 477 info.xml em-dashes sit in XML comments, which are
     developer prose. Flagging them would hand 20 apps a chore that changes
     nothing a user reads.
  5. THE NUMERIC-RANGE EXCEPTION SURVIVES INTO THE NEW SCOPE. voice.md §8
     permits an en-dash between digits. A checker that banned every dash
     outright would pass arms 1 to 4 and be wrong.

Run: python3 scripts/lib/test_check_manifest_copy_style.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_manifest_copy_style.py")

CLEAN_MANIFEST = {"pages": [{"id": "cases", "title": "Cases", "body": "Your open cases."}]}
DIRTY_MANIFEST = {"pages": [{"id": "cases", "title": "Cases — all of them"}]}

CLEAN_INFO = """<?xml version="1.0"?>
<info>
    <id>probe</id>
    <summary lang="en">Case handling for Nextcloud</summary>
    <description lang="en"><![CDATA[Probe does one thing well.

Reporting covers 2020-2024.
    ]]></description>
</info>
"""

DIRTY_INFO = CLEAN_INFO.replace(
    "Probe does one thing well.",
    "Probe does one thing well — and it says so twice.",
)


def _tree(root, manifest=None, info=None):
    """
    Write a throwaway repository tree.

    :param root: directory to populate.
    :param manifest: dict written to src/manifest.json, or None to omit it.
    :param info: string written to appinfo/info.xml, or None to omit it.
    :return: None
    """
    if manifest is not None:
        os.makedirs(os.path.join(root, "src"), exist_ok=True)
        with open(os.path.join(root, "src", "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
    if info is not None:
        os.makedirs(os.path.join(root, "appinfo"), exist_ok=True)
        with open(os.path.join(root, "appinfo", "info.xml"), "w", encoding="utf-8") as fh:
            fh.write(info)


class ManifestCopyStyleTest(unittest.TestCase):
    """Arms for the blocking / advisory boundary."""

    def run_check(self, manifest=None, info=None):
        """
        Run the checker over a throwaway tree.

        :param manifest: dict for src/manifest.json, or None.
        :param info: string for appinfo/info.xml, or None.
        :return: (returncode, stdout)
        """
        with tempfile.TemporaryDirectory() as root:
            _tree(root, manifest, info)
            proc = subprocess.run(
                [sys.executable, CHECKER, root],
                capture_output=True, text=True,
            )
            return proc.returncode, proc.stdout

    def test_a_manifest_em_dash_still_fails_the_gate(self):
        """Arm 1: the half that was already green fleet-wide stays blocking."""
        rc, out = self.run_check(manifest=DIRTY_MANIFEST, info=CLEAN_INFO)
        self.assertEqual(rc, 1, f"manifest copy must block, got rc={rc}\n{out}")
        self.assertIn("FAIL", out)

    def test_an_app_store_em_dash_warns_and_does_not_fail(self):
        """Arm 2: THE point of this change. Advisory means exit 0.

        If this arm goes red, someone wired the App Store findings into the
        return value. That promotion is intended one day, and it is intended
        deliberately: edit this test in the same commit, and only once the
        fleet's 204 findings are cleared.
        """
        rc, out = self.run_check(manifest=CLEAN_MANIFEST, info=DIRTY_INFO)
        self.assertIn("WARN", out, f"the finding must be reported\n{out}")
        self.assertIn("ADVISORY", out, f"and reported AS advisory\n{out}")
        self.assertEqual(rc, 0, f"the App Store scope must not block yet, got rc={rc}\n{out}")

    def test_both_scopes_dirty_blocks_and_reports_both(self):
        """Arm 3: the advisory must not mask the failure, nor be swallowed by it."""
        rc, out = self.run_check(manifest=DIRTY_MANIFEST, info=DIRTY_INFO)
        self.assertEqual(rc, 1, f"a manifest finding still blocks, got rc={rc}\n{out}")
        self.assertIn("FAIL", out)
        self.assertIn("WARN", out, f"the advisory must survive a failing run\n{out}")

    def test_an_xml_comment_is_not_app_store_copy(self):
        """Arm 4: 273 of the fleet's 477 sit in comments, and are not copy."""
        commented = CLEAN_INFO.replace(
            "<id>probe</id>",
            "<id>probe</id>\n    <!-- a note for the next developer — not user copy -->",
        )
        rc, out = self.run_check(manifest=CLEAN_MANIFEST, info=commented)
        self.assertEqual(rc, 0, f"a comment must not produce a verdict\n{out}")
        self.assertNotIn("WARN", out, f"nor an advisory finding\n{out}")

    def test_a_numeric_range_en_dash_is_still_allowed(self):
        """Arm 5: voice.md §8's one exception reaches the new scope too."""
        ranged = CLEAN_INFO.replace("2020-2024", "2020–2024")
        rc, out = self.run_check(manifest=CLEAN_MANIFEST, info=ranged)
        self.assertEqual(rc, 0, f"a numeric range is not a finding\n{out}")
        self.assertNotIn("WARN", out, out)

    def test_an_app_store_string_is_counted_even_when_clean(self):
        """A count of zero and a clean read must not print the same thing.

        Same rule the runner already applies to `checked N manifest string(s)`:
        an empty scope is not a pass.
        """
        _, out = self.run_check(manifest=CLEAN_MANIFEST, info=CLEAN_INFO)
        self.assertIn("warned 2 app-store string(s)", out, out)
        _, out = self.run_check(manifest=CLEAN_MANIFEST, info=None)
        self.assertIn("warned 0 app-store string(s)", out, out)


if __name__ == "__main__":
    unittest.main()
