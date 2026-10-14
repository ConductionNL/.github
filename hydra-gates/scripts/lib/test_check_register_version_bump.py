#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-120's checker (check_register_version_bump.py), rule by rule.

  1. A REGISTER VERSION RAISED WITHOUT AN APP VERSION FAILS: the portaliq #1549 shape.
  2. RAISED TOGETHER, IT PASSES.
  3. A register.d FRAGMENT'S info.version COUNTS LIKE THE BASE DOCUMENT'S.
  4. A MOCK DOES NOT COUNT: sample data is never imported by a repair step.
  5. A CHANGE THAT LEAVES info.version ALONE PASSES, whatever else it edits.
  6. AN ADDED DOCUMENT WITH A VERSION COUNTS; A DELETED ONE DOES NOT.
  7. NO BASE, OR NO appinfo/info.xml, IS NOT APPLICABLE (exit 4), never PASS.
  8. A DOCUMENT THAT IS NOT JSON IS exit 2, never a pass and never a finding.
  9. ONLY lib/Settings/*_register.json AND register.d/*.json ARE WATCHED.
 10. REF MODE AGREES WITH WORKING-TREE MODE.
 11. A REGISTER'S EFFECTIVE VERSION COUNTS: a new register.d fragment raising
     `components.registers.<slug>.version`, without any info.version, FAILS
     (the pipelinq #2471 shape); re-declaring the same version does not.

Run: python3 scripts/lib/test_check_register_version_bump.py
"""
import atexit
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_register_version_bump as crv  # noqa: E402


def git(d, *a):
    subprocess.run(["git", "-C", d, "-c", "user.email=f@x.invalid", "-c", "user.name=F", *a],
                   check=True, capture_output=True)


def info_xml(version):
    return "<?xml version=\"1.0\"?>\n<info>\n  <id>fixture</id>\n  <version>%s</version>\n</info>\n" % version


def register(version, mock=False, extra=None):
    doc = {"openapi": "3.0.0", "info": {"title": "Fixture", "version": version},
           "components": {"registers": {"fixture": {"slug": "fixture"}}}}
    if mock:
        doc["x-openregister"] = {"type": "mock"}
    if extra:
        doc["components"]["schemas"] = extra
    return json.dumps(doc)


def write(d, files):
    for path, body in files.items():
        full = os.path.join(d, path)
        if body is None:
            if os.path.exists(full):
                os.remove(full)
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)


def make_app(base_files, head_files):
    """A repo with a `base` commit and the change on top, in the working tree and committed as `head`."""
    d = tempfile.mkdtemp(prefix="gate120-")
    atexit.register(shutil.rmtree, d, True)
    git(d, "init", "-q")
    write(d, base_files)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    git(d, "branch", "base")
    write(d, head_files)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "change", "--allow-empty")
    git(d, "branch", "head")
    return d


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = crv.main(argv)
    return rc, out.getvalue()


BASE = {"appinfo/info.xml": info_xml("1.0.0"),
        "lib/Settings/fixture_register.json": register("0.96.0")}


class RegisterVersionBumpTest(unittest.TestCase):

    def test_register_raised_without_app_version_fails(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": register("0.97.0")})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(1, rc, out)
        self.assertIn("FAIL: 1 finding(s)", out)
        self.assertIn("lib/Settings/fixture_register.json: info.version 0.96.0 -> 0.97.0", out)
        self.assertIn("stays 1.0.0", out)

    def test_raised_together_passes(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": register("0.97.0"),
                            "appinfo/info.xml": info_xml("1.0.1")})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(0, rc, out)
        self.assertIn("checked 1 document(s), 1 version change(s)", out)

    def test_a_fragment_version_counts(self):
        base = dict(BASE, **{"lib/Settings/register.d/10-extra.json": json.dumps({"info": {"version": "1"}})})
        d = make_app(base, {"lib/Settings/register.d/10-extra.json": json.dumps({"info": {"version": "2"}})})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(1, rc, out)
        self.assertIn("register.d/10-extra.json: info.version 1 -> 2", out)

    def test_a_mock_does_not_count(self):
        base = dict(BASE, **{"lib/Settings/fixture_mock_register.json": register("0.27.0", mock=True)})
        d = make_app(base, {"lib/Settings/fixture_mock_register.json": register("0.28.0", mock=True)})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(0, rc, out)
        self.assertIn("0 version change(s)", out)

    def test_an_edit_that_keeps_the_version_passes(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": register("0.96.0", extra={"thing": {}})})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(0, rc, out)

    def test_an_added_document_counts_a_deleted_one_does_not(self):
        added = make_app(BASE, {"lib/Settings/other_register.json": register("1.0.0")})
        rc, out = run_main([added, "--base", "base"])
        self.assertEqual(1, rc, out)
        self.assertIn("other_register.json: info.version (none) -> 1.0.0", out)

        deleted = make_app(BASE, {"lib/Settings/fixture_register.json": None})
        rc, out = run_main([deleted, "--base", "base"])
        self.assertEqual(0, rc, out)

    def test_no_base_is_not_applicable(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": register("0.97.0")})
        rc, out = run_main([d])
        self.assertEqual(4, rc, out)
        self.assertIn("NOT APPLICABLE", out)

    def test_no_info_xml_is_not_applicable(self):
        d = make_app({"lib/Settings/fixture_register.json": register("0.96.0")},
                     {"lib/Settings/fixture_register.json": register("0.97.0")})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(4, rc, out)

    def test_a_document_that_is_not_json_cannot_be_judged(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": "{not json"})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(2, rc, out)
        self.assertNotIn("checked", out)

    def test_only_watched_paths_count(self):
        self.assertTrue(crv.is_register_document("lib/Settings/portaliq_register.json"))
        self.assertTrue(crv.is_register_document("lib/Settings/register.d/40-portal.json"))
        self.assertFalse(crv.is_register_document("lib/Settings/connections.json"))
        self.assertFalse(crv.is_register_document("lib/Settings/example-sets/a_register.json"))
        self.assertFalse(crv.is_register_document("lib/Settings/register.d/deep/x.json"))
        self.assertFalse(crv.is_register_document("tests/fixtures/x_register.json"))

    def test_ref_mode_agrees_with_working_tree_mode(self):
        d = make_app(BASE, {"lib/Settings/fixture_register.json": register("0.97.0")})
        work = run_main([d, "--base", "base"])
        ref = run_main([d, "--base", "base", "--ref", "head"])
        self.assertEqual(work, ref)

    def _registers_doc(self, versions, info=None):
        doc = {"components": {"registers": {slug: {"slug": slug, "version": v} for slug, v in versions.items()}}}
        if info is not None:
            doc["info"] = {"version": info}
        return json.dumps(doc)

    def test_a_new_fragment_raising_a_register_version_fails(self):
        base = {"appinfo/info.xml": info_xml("1.0.0"),
                "lib/Settings/pipelinq_register.json": self._registers_doc({"pipelinq": "1.0.0"}, info="1.11.0")}
        d = make_app(base, {"lib/Settings/register.d/99-zzz-access.json": self._registers_doc(
            {"pipelinq": "1.1.0", "sla": "1.1.0"})})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(1, rc, out)
        self.assertIn("register pipelinq: version 1.0.0 -> 1.1.0 (lib/Settings/register.d/99-zzz-access.json)", out)
        self.assertIn("register sla: version (none) -> 1.1.0", out)

    def test_a_fragment_redeclaring_the_same_register_version_passes(self):
        base = {"appinfo/info.xml": info_xml("1.0.0"),
                "lib/Settings/pipelinq_register.json": self._registers_doc({"pipelinq": "1.0.0"}, info="1.11.0")}
        d = make_app(base, {"lib/Settings/register.d/10-more.json": self._registers_doc({"pipelinq": "1.0.0"})})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(0, rc, out)

    def test_a_register_version_raised_in_the_base_document_fails(self):
        base = {"appinfo/info.xml": info_xml("1.0.0"),
                "lib/Settings/x_register.json": self._registers_doc({"x": "1.0.0"}, info="2.0.0")}
        d = make_app(base, {"lib/Settings/x_register.json": self._registers_doc({"x": "1.0.1"}, info="2.0.0")})
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(1, rc, out)
        self.assertIn("register x: version 1.0.0 -> 1.0.1", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
