#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-114's checker (check_header_action_budget.py).

Every arm below was watched fail before it was watched pass. A guard test
that has never been red is a guard test nobody has evidence for.

  1. THE CENSUS READS THE FRAGMENTS. src/manifest.d/*.json is merged over the
     base manifest at runtime (ADR-037), and eight fleet apps use it. A
     checker that opens only src/manifest.json passes every other arm here
     and is blind to whatever the fragments add.
  2. GROWTH IS A FINDING, per page.
  3. A FLAT BAR AND A SHRINKING BAR ARE NOT. The second matters more than it
     looks: a ratchet that fired on any delta would make every removal a
     finding, and nobody would remove anything.
  4. THE FINDING DOES NOT BLOCK. Exit stays 0 while WARN is printed. This is
     the arm that pins the warning-first decision, and it is the one to edit
     on purpose when the fleet's bars are worked down and gate-114 is
     promoted to blocking. Wire findings into the return value and this arm
     goes red immediately, which is the point.
  5. NO BASE MEANS NO RATCHET, AND NO `base=` LINE. The runner decides
     whether to print "the RATCHET half was NOT computed" by the absence of
     that line, so a checker that printed base=0 without a base would make
     the runner claim a ratchet that never ran.
  6. A PAGE THAT IS NEW AT HEAD RAISES NO FINDING. It has nothing to compare
     against. It still appears in the census, so a bar that arrives long is
     visible in the output.
  7. AN EMPTY SCOPE IS NOT A PASS. No manifest, or a manifest with no pages,
     exits 4 so the gate can skip rather than report a clean read of nothing.
  8. THE BASE CENSUS RE-RESOLVES ITS OWN FILE LIST. A fragment ADDED by the
     change does not exist at the base. Reading head's file list against the
     base would count that fragment's pages as base pages and hide exactly
     the growth this gate is for.

Run: python3 scripts/lib/test_check_header_action_budget.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_header_action_budget.py")


def _page(pid, n_actions, ptype="detail"):
    """
    One manifest page declaring n header actions.

    :param pid: page id.
    :param n_actions: how many entries config.headerActions carries.
    :param ptype: the page type.
    :return: the page dict.
    """
    return {
        "id": pid,
        "route": f"/{pid.lower()}",
        "type": ptype,
        "title": pid,
        "config": {
            "headerActions": [
                {"id": f"{pid.lower()}-a{i}", "type": "open-modal",
                 "label": f"Action {i}", "target": "SomeDialog"}
                for i in range(n_actions)
            ],
        },
    }


class HeaderActionBudget(unittest.TestCase):
    """The checker runs inside a throwaway git repository with a `base` branch."""

    def _git(self, *args):
        """
        Run git in the fixture repository.

        :param args: git arguments.
        :return: None
        """
        subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def setUp(self):
        """
        Build a fixture repository whose base ref carries a known census.

        :return: None
        """
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        os.makedirs(os.path.join(self.repo, "src", "manifest.d"))
        self._write_manifest([_page("CaseDetail", 3), _page("Cases", 0, "index")])
        self._write_fragment("50-extra.json", [_page("TaskDetail", 1)])
        self._git("init", "-q")
        self._git("config", "user.email", "t@t.tld")
        self._git("config", "user.name", "t")
        self._git("add", ".")
        self._git("commit", "-qm", "base")
        self._git("branch", "base")

    def tearDown(self):
        """
        Remove the fixture repository.

        :return: None
        """
        self.tmp.cleanup()

    def _write_manifest(self, pages):
        """
        Replace src/manifest.json with these pages.

        :param pages: list of page dicts.
        :return: None
        """
        path = os.path.join(self.repo, "src", "manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": "1.0.0", "pages": pages}, fh, indent=2)

    def _write_fragment(self, name, pages):
        """
        Write one src/manifest.d fragment.

        :param name: file name inside src/manifest.d.
        :param pages: list of page dicts.
        :return: None
        """
        path = os.path.join(self.repo, "src", "manifest.d", name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"pages": pages}, fh, indent=2)

    def _run(self, base="base"):
        """
        Run the checker over the fixture.

        :param base: value for HYDRA_GATE_BASE_REF, or None to omit it.
        :return: the CompletedProcess.
        """
        env = dict(os.environ)
        env.pop("HYDRA_GATE_BASE_REF", None)
        if base is not None:
            env["HYDRA_GATE_BASE_REF"] = base
        return subprocess.run(
            [sys.executable, CHECKER, self.repo],
            capture_output=True, text=True, check=False, env=env,
        )

    def _findings(self, out):
        """
        The findings count the checker reported.

        :param out: the checker's stdout.
        :return: the integer count.
        """
        for line in reversed(out.splitlines()):
            if line.startswith("[header-action-budget] findings="):
                return int(line.rsplit("=", 1)[1])
        self.fail(f"no findings= line in output:\n{out}")
        return -1

    # 1 ---------------------------------------------------------------------
    def test_census_counts_fragments_too(self):
        """A fragment's pages are part of the effective manifest."""
        res = self._run()
        self.assertIn("[header-action-budget] CaseDetail: 3", res.stdout)
        self.assertIn("[header-action-budget] TaskDetail: 1", res.stdout)
        self.assertIn("pages=3 with-actions=2 total=4", res.stdout)
        self.assertIn("checked 3 page(s) in the effective manifest", res.stdout)

    # 2 ---------------------------------------------------------------------
    def test_growth_is_a_finding(self):
        """One more button on an existing page is reported, and named."""
        self._write_manifest([_page("CaseDetail", 5), _page("Cases", 0, "index")])
        res = self._run()
        self.assertEqual(self._findings(res.stdout), 1)
        self.assertIn("base=4 head=6 delta=+2", res.stdout)
        self.assertIn("WARN CaseDetail: header actions went 3 to 5 (+2)", res.stdout)

    # 3 ---------------------------------------------------------------------
    def test_flat_and_shrinking_are_clean(self):
        """A bar that did not grow is not a finding, and neither is one that shrank."""
        self.assertEqual(self._findings(self._run().stdout), 0)
        self._write_manifest([_page("CaseDetail", 1), _page("Cases", 0, "index")])
        res = self._run()
        self.assertEqual(self._findings(res.stdout), 0)
        self.assertIn("delta=-2", res.stdout)

    # 4 ---------------------------------------------------------------------
    def test_a_finding_does_not_block(self):
        """
        Warning first. The exit code stays 0 while the finding is printed.

        EDIT THIS ARM ON PURPOSE to promote gate-114 to blocking, and not
        before the fleet's header bars have been measured and worked down.
        This package resolves at @main for all 21 core apps, so a blocking
        gate fails every repository carrying inherited debt the minute it
        merges.
        """
        self._write_manifest([_page("CaseDetail", 9), _page("Cases", 0, "index")])
        res = self._run()
        self.assertEqual(self._findings(res.stdout), 1)
        self.assertEqual(res.returncode, 0, "gate-114 ships advisory; see the docstring")

    # 5 ---------------------------------------------------------------------
    def test_without_a_base_the_ratchet_does_not_run(self):
        """No base ref means no base/head/delta line for the runner to read."""
        self._write_manifest([_page("CaseDetail", 9), _page("Cases", 0, "index")])
        res = self._run(base=None)
        self.assertNotIn("base=", res.stdout)
        self.assertEqual(self._findings(res.stdout), 0)
        self.assertIn("pages=3", res.stdout)

    # 6 ---------------------------------------------------------------------
    def test_a_new_page_is_censused_but_not_ratcheted(self):
        """A page absent at the base has nothing to have grown against."""
        self._write_manifest([
            _page("CaseDetail", 3), _page("Cases", 0, "index"), _page("BezwaarDetail", 7),
        ])
        res = self._run()
        self.assertEqual(self._findings(res.stdout), 0)
        self.assertIn("[header-action-budget] BezwaarDetail: 7", res.stdout)
        self.assertIn("max=7 on BezwaarDetail", res.stdout)

    # 7 ---------------------------------------------------------------------
    def test_empty_scope_exits_four(self):
        """Nothing to judge is not a clean read."""
        os.remove(os.path.join(self.repo, "src", "manifest.json"))
        os.remove(os.path.join(self.repo, "src", "manifest.d", "50-extra.json"))
        res = self._run()
        self.assertEqual(res.returncode, 4)
        self.assertIn("checked 0 page(s)", res.stdout)

        self._write_manifest([])
        res = self._run()
        self.assertEqual(res.returncode, 4)

    # 8 ---------------------------------------------------------------------
    def test_a_fragment_added_by_the_change_is_not_a_base_file(self):
        """
        The base census re-resolves its file list at the base ref.

        A checker that read head's file list against the base would find no
        blob for the new fragment, count its pages as zero on BOTH sides, and
        report the new page as new rather than as growth. That is the right
        answer here by accident. The arm that matters is the total: the base
        total must not include the fragment's actions.
        """
        self._write_fragment("60-new.json", [_page("AdviceDetail", 4)])
        res = self._run()
        self.assertIn("base=4 head=8 delta=+4", res.stdout)
        self.assertEqual(self._findings(res.stdout), 0, "a new page is not growth")


if __name__ == "__main__":
    unittest.main(verbosity=2)
