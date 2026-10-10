#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-118's checker (check_spec_screens.py).

The gate asks whether every OpenSpec change and spec directory a PR touches
names its boards in screens.md. Every arm runs offline against a local copy of
the design-system layout (HYDRA_GATE_SCREENS_SOURCE), so no arm depends on the
network or on what design-system main holds today.

  1. A CLEAN DIRECTORY PASSES: a board in the published index, a board only in
     the app's own registration file, a board another app owns, and a real
     no-screen reason.
  2. A MISSING screens.md FAILS, and so does one with no `- ` line.
  3. A BOARD NOBODY DREW FAILS, named by board and line.
  4. `No board found yet` FAILS in a directory the change touches.
  5. A PLACEHOLDER REASON FAILS: every shape in design-system's own list, plus
     a bare and a too-short reason. The control arm keeps a real reason that
     happens to contain the word "design" green.
  6. SCOPE: only touched directories are judged; a deleted or moved-away
     directory is not judged at its old path; archive/ is judged when touched
     and skipped by --full-tree.
  7. NO VERDICT WITHOUT THE BOARD LIST: an unreachable design-system is exit 2,
     never a pass and never a finding. A finding that needs no network still
     fails.
  8. THE DESIGN BACKLOG PASSES (decision 157): `- Design backlog: <proposed
     board>` marks real UI whose board is not drawn yet. It passes, beside an
     unknown board, a placeholder reason and `No board found yet`, which still
     fail in the same file. A backlog line naming nothing fails.
  9. BOARD NAMES ARE VALIDATED, NOT URL TEXT: a real board with a link whose
     id points elsewhere passes; an unknown board with a real board's link fails.
 10. NOTHING TO JUDGE is exit 3 (empty scope) or 4 (no openspec), never 0.

Run: python3 scripts/lib/test_check_spec_screens.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_spec_screens.py")

INDEX = {
    "boards": {
        "DqZaak": {"id": "dossiq/DqZaak", "app": "dossiq"},
        "LpStart": {"id": "werkplek/LpStart", "app": "werkplek"},
        "wilgenboom-Artikel": {"id": "wilgenboom/Artikel", "app": "wilgenboom"},
    }
}
APP_FILE = {
    "rows": [["rowFixture", "fixture", [["DqNieuw.dc.html"]]]],
    "boards": {"DqZaaktypen.dc.html": {"title": "zaaktypen"}},
}

CLEAN = """# Screens

- DqZaak https://identity.conduction.nl/screens/board?id=dossiq/DqZaak
- DqZaaktypen https://identity.conduction.nl/screens/board?id=dossiq/DqZaaktypen
- DqNieuw
- LpStart https://identity.conduction.nl/screens/board?id=werkplek/LpStart
- No screen: a nightly job that mails reminders, no page changes
"""


class SpecScreensTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ds = os.path.join(self.root, "ds")
        self.app = os.path.join(self.root, "dossiq")
        self.write(self.ds, "preview/screens/screens.json", json.dumps(INDEX))
        self.write(self.ds, "screens-src/zuiddrecht/apps/dossiq.json", json.dumps(APP_FILE))
        self.write(self.app, "appinfo/info.xml", "<info><id>procest</id></info>\n")
        os.makedirs(os.path.join(self.app, "openspec/specs"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def write(base, rel, text):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def run_check(self, changed, *, full=False, source=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("HYDRA_GATE_SCREENS")}
        env.pop("GITHUB_REPOSITORY", None)
        env["HYDRA_GATE_SCREENS_SOURCE"] = self.ds if source is None else source
        args = [sys.executable, CHECKER, self.app, "--full-tree" if full else "--changed-stdin"]
        proc = subprocess.run(args, input="\n".join(changed) + "\n", capture_output=True,
                              text=True, timeout=60, env=env)
        return proc.returncode, proc.stdout + proc.stderr

    # -- 1 ---------------------------------------------------------------

    def test_clean_directory_passes(self):
        self.write(self.app, "openspec/changes/add-x/proposal.md", "x\n")
        self.write(self.app, "openspec/changes/add-x/screens.md", CLEAN)
        rc, out = self.run_check(["openspec/changes/add-x/proposal.md"])
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 1 dir(s), 4 board line(s), 1 no-screen line(s), 0 design-backlog line(s), 0 finding(s)", out)

    # -- 2 ---------------------------------------------------------------

    def test_missing_screens_md_fails(self):
        self.write(self.app, "openspec/specs/cases/spec.md", "x\n")
        rc, out = self.run_check(["openspec/specs/cases/spec.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("openspec/specs/cases/: no screens.md", out)

    def test_screens_md_without_a_line_fails(self):
        self.write(self.app, "openspec/specs/cases/screens.md", "# Screens\n\nTo do.\n")
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("has no `- ` line", out)

    # -- 3 ---------------------------------------------------------------

    def test_unknown_board_fails_by_name(self):
        self.write(self.app, "openspec/specs/cases/screens.md", "# Screens\n\n- DqZaak\n- DqNope https://x/?id=dossiq/DqNope\n")
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("screens.md:4: board 'DqNope' is not on design-system main", out)
        self.assertNotIn("'DqZaak'", out)

    # -- 4 ---------------------------------------------------------------

    def test_no_board_found_yet_fails(self):
        self.write(self.app, "openspec/specs/cases/screens.md", "# Screens\n\n- No board found yet (decision 150)\n")
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("`No board found yet`", out)

    # -- 5 ---------------------------------------------------------------

    def test_placeholder_reasons_fail(self):
        reasons = [
            "not designed yet", "not yet designed", "not drawn", "no board for this",
            "see missing-boards", "waiting for the design session", "decision 96 applies",
            "nog niet ontworpen", "niet getekend", "geen bord", "no design yet",
            "no screen drawn",
        ]
        body = "# Screens\n\n" + "".join(f"- No screen: {r}\n" for r in reasons)
        self.write(self.app, "openspec/specs/cases/screens.md", body)
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn(f"{len(reasons)} finding(s)", out)

    def test_bare_and_short_reasons_fail(self):
        self.write(self.app, "openspec/specs/cases/screens.md", "# Screens\n\n- No screen:\n- No screen: n/a\n")
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(out.count("without a real reason"), 2, out)

    def test_real_reason_mentioning_design_passes(self):
        self.write(self.app, "openspec/specs/cases/screens.md",
                   "# Screens\n\n- No screen: the API design for webhook delivery, no page\n")
        rc, out = self.run_check(["openspec/specs/cases/screens.md"])
        self.assertEqual(rc, 0, out)

    # -- 6 ---------------------------------------------------------------

    def test_only_touched_directories_are_judged(self):
        self.write(self.app, "openspec/specs/untouched/spec.md", "x\n")
        self.write(self.app, "openspec/specs/cases/screens.md", CLEAN)
        rc, out = self.run_check(["openspec/specs/cases/screens.md", "README.md", "lib/X.php"])
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 1 dir(s)", out)

    def test_a_directory_gone_from_head_is_not_judged(self):
        # A change being archived leaves its old path in the diff's history.
        self.write(self.app, "openspec/changes/archive/2026-10-10-add-x/screens.md", CLEAN)
        rc, out = self.run_check([
            "openspec/changes/add-x/proposal.md",
            "openspec/changes/archive/2026-10-10-add-x/screens.md",
        ])
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 1 dir(s)", out)

    def test_touched_archive_directory_is_judged(self):
        self.write(self.app, "openspec/changes/archive/2026-10-10-add-x/proposal.md", "x\n")
        rc, out = self.run_check(["openspec/changes/archive/2026-10-10-add-x/proposal.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("openspec/changes/archive/2026-10-10-add-x/: no screens.md", out)

    def test_full_tree_skips_archive(self):
        self.write(self.app, "openspec/changes/archive/2026-01-01-old/proposal.md", "x\n")
        self.write(self.app, "openspec/changes/live/screens.md", CLEAN)
        self.write(self.app, "openspec/specs/cases/screens.md", CLEAN)
        rc, out = self.run_check([], full=True)
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 2 dir(s)", out)

    # -- 7 ---------------------------------------------------------------

    def test_unreachable_design_system_is_no_verdict(self):
        self.write(self.app, "openspec/specs/cases/screens.md", CLEAN)
        env = {k: v for k, v in os.environ.items() if not k.startswith("HYDRA_GATE_SCREENS")}
        env["HYDRA_GATE_SCREENS_REPO_URL"] = "http://127.0.0.1:9"
        proc = subprocess.run([sys.executable, CHECKER, self.app, "--changed-stdin"],
                              input="openspec/specs/cases/screens.md\n", capture_output=True,
                              text=True, timeout=120, env=env)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("UNVERIFIED", proc.stdout)

    def test_a_finding_without_network_still_fails_when_unreachable(self):
        self.write(self.app, "openspec/specs/cases/screens.md", CLEAN)
        self.write(self.app, "openspec/specs/other/spec.md", "x\n")
        empty = os.path.join(self.root, "empty-ds")
        os.makedirs(empty)
        rc, out = self.run_check(["openspec/specs/cases/screens.md", "openspec/specs/other/spec.md"],
                                 source=empty)
        self.assertEqual(rc, 1, out)
        self.assertIn("openspec/specs/other/: no screens.md", out)

    # -- 8 ---------------------------------------------------------------

    def test_design_backlog_marker_passes(self):
        self.write(self.app, "openspec/changes/add-x/screens.md",
                   "# Screens\n\n- DqZaak\n- Design backlog: DqZaakTermijnen (decision 157)\n")
        rc, out = self.run_check(["openspec/changes/add-x/screens.md"])
        self.assertEqual(rc, 0, out)
        self.assertIn("1 design-backlog line(s), 0 finding(s)", out)

    def test_design_backlog_does_not_excuse_the_other_failures(self):
        self.write(self.app, "openspec/changes/add-x/screens.md",
                   "# Screens\n\n- Design backlog: DqZaakTermijnen (decision 157)\n"
                   "- DqNope\n- No screen: not designed yet\n- No board found yet (decision 150)\n")
        self.write(self.app, "openspec/specs/bare/spec.md", "x\n")
        rc, out = self.run_check(["openspec/changes/add-x/screens.md", "openspec/specs/bare/spec.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("4 finding(s)", out)
        self.assertIn("board 'DqNope'", out)
        self.assertIn("only says the design is not there yet", out)
        self.assertIn("`No board found yet`", out)
        self.assertIn("openspec/specs/bare/: no screens.md", out)
        self.assertNotIn("DqZaakTermijnen", out)

    def test_design_backlog_naming_nothing_fails(self):
        self.write(self.app, "openspec/changes/add-x/screens.md",
                   "# Screens\n\n- Design backlog: (decision 157)\n")
        rc, out = self.run_check(["openspec/changes/add-x/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("without the board it proposes", out)

    # -- 9 ---------------------------------------------------------------

    def test_board_name_is_validated_not_the_url(self):
        self.write(self.app, "openspec/specs/a/screens.md",
                   "# Screens\n\n- DqZaak https://identity.conduction.nl/screens/board?id=other/Whatever\n")
        self.write(self.app, "openspec/specs/b/screens.md",
                   "# Screens\n\n- DqGone https://identity.conduction.nl/screens/board?id=dossiq/DqZaak\n")
        rc, out = self.run_check(["openspec/specs/a/screens.md", "openspec/specs/b/screens.md"])
        self.assertEqual(rc, 1, out)
        self.assertIn("1 finding(s)", out)
        self.assertIn("openspec/specs/b/screens.md:3: board 'DqGone'", out)

    def test_a_school_set_board_is_found_by_its_id(self):
        # screens.json keys it `wilgenboom-Artikel`; its id is `wilgenboom/Artikel`.
        self.write(self.app, "openspec/specs/a/screens.md",
                   "# Screens\n\n- wilgenboom/Artikel https://identity.conduction.nl/screens/board?id=wilgenboom/Artikel\n")
        rc, out = self.run_check(["openspec/specs/a/screens.md"])
        self.assertEqual(rc, 0, out)

    def test_a_board_file_on_main_counts_before_the_index_is_rebuilt(self):
        self.write(self.ds, "screens-src/zuiddrecht/DqVers.dc.html", "<html></html>\n")
        self.write(self.app, "openspec/specs/a/screens.md", "# Screens\n\n- DqVers\n")
        rc, out = self.run_check(["openspec/specs/a/screens.md"])
        self.assertEqual(rc, 0, out)

    # -- 10 --------------------------------------------------------------

    def test_empty_scope_is_not_a_pass(self):
        rc, out = self.run_check(["README.md"])
        self.assertEqual(rc, 3, out)

    def test_no_openspec_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as bare:
            proc = subprocess.run([sys.executable, CHECKER, bare, "--changed-stdin"], input="",
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 4, proc.stdout)


if __name__ == "__main__":
    unittest.main()
