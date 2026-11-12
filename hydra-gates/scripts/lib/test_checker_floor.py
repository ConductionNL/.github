#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the checker floor (checker_floor.py).

The checker is replaced by a stub (CHECKER_HOME) whose scanner reports the
scan a tree carries in `scan.json`, so every verdict is driven by known
statuses on real git histories:

  1. RECORD: writes the floor; keeps the better status of an old floor; --reset
     writes the measurement; refuses an unmeasured criterion and writes nothing.
  2. COMPARE: holds is 0; a worse status or a lower score is 1; a better one is
     4; a floor criterion the scan did not measure is 2; the floor is the one
     committed at the merge base, not the base branch tip; a change that lowers
     or deletes the committed floor file is 1 even when the scan holds; no floor
     file anywhere is 3.
  3. NO RESULT: a scanner that fails, crashes or is missing is 2, never a pass.
  4. CACHE: a clean commit is scanned once; a dirty tree is never cached.

Run: python3 scripts/lib/test_checker_floor.py
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checker_floor  # noqa: E402

STUB = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
tree = args[1]
out = args[args.index("--out") + 1]
calls = os.environ.get("CHECKER_STUB_CALLS")
if calls:
    with open(calls, "a") as fh:
        fh.write(tree + "\n")
path = os.path.join(tree, "scan.json")
if not os.path.isfile(path):
    sys.stderr.write("scan-local: the scan crashed\n")
    sys.exit(2)
s = json.load(open(path))
if s.get("exit"):
    sys.exit(s["exit"])
doc = {"tool": "stub", "toolVersion": "0.0.1+stub", "scoringDigest": "d1", "score": s["score"],
       "commit": "x", "criteria": {k: {"status": v, "message": ""} for k, v in s["criteria"].items()},
       "unmeasured": s.get("unmeasured", [])}
json.dump(doc, open(out, "w"))
'''

BASE = {"score": 80, "criteria": {"license": "pass", "maintainability": "warn", "secretscanning": "fail"}}


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


class CheckerFloorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.home = os.path.join(root, "checker")
        os.makedirs(os.path.join(self.home, "scripts"))
        os.makedirs(os.path.join(self.home, "node_modules", ".bin"))
        open(os.path.join(self.home, "scripts", "scan-local.ts"), "w").close()
        tsx = os.path.join(self.home, "node_modules", ".bin", "tsx")
        with open(tsx, "w") as fh:
            fh.write(STUB)
        os.chmod(tsx, 0o755)
        run(["git", "init", "-q"], self.home)
        run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "c"], self.home)
        self.calls = os.path.join(root, "calls.txt")
        self.env = {"CHECKER_HOME": self.home, "HYDRA_GATE_FLOOR_CACHE": os.path.join(root, "cache"),
                    "CHECKER_STUB_CALLS": self.calls}
        self.old_env = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        self.app = os.path.join(root, "app")
        os.makedirs(self.app)
        run(["git", "init", "-q", "-b", "development"], self.app)
        self.commit(BASE, "base")

    def tearDown(self):
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def write_scan(self, scan):
        with open(os.path.join(self.app, "scan.json"), "w") as fh:
            json.dump(scan, fh)

    def commit(self, scan, msg):
        if scan is not None:
            self.write_scan(scan)
        run(["git", "add", "-A"], self.app)
        run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", msg], self.app)

    def main(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = checker_floor.main(list(argv))
        return rc, buf.getvalue()

    def floor(self):
        with open(os.path.join(self.app, checker_floor.FLOOR_FILE)) as fh:
            return json.load(fh)

    def record_base(self):
        rc, out = self.main("record", self.app)
        self.assertEqual(rc, 0, out)
        self.commit(None, "floor")
        run(["git", "checkout", "-q", "-b", "feature"], self.app)

    # 1. record
    def test_record_writes_the_floor(self):
        rc, out = self.main("record", self.app)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.floor()["criteria"], BASE["criteria"])
        self.assertEqual(self.floor()["score"], 80)

    def test_record_keeps_the_better_status_of_the_old_floor(self):
        self.main("record", self.app)
        self.write_scan({"score": 70, "criteria": {"license": "warn", "maintainability": "pass", "secretscanning": "fail"}})
        rc, out = self.main("record", self.app)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.floor()["criteria"], {"license": "pass", "maintainability": "pass", "secretscanning": "fail"})
        self.assertEqual(self.floor()["score"], 80)

    def test_record_reset_writes_the_measurement(self):
        self.main("record", self.app)
        self.write_scan({"score": 70, "criteria": {"license": "warn"}})
        rc, _ = self.main("record", self.app, "--reset")
        self.assertEqual(rc, 0)
        self.assertEqual(self.floor()["criteria"], {"license": "warn"})
        self.assertEqual(self.floor()["score"], 70)

    def test_record_refuses_an_unmeasured_criterion(self):
        self.write_scan(dict(BASE, unmeasured=["secretscanning"]))
        rc, out = self.main("record", self.app)
        self.assertEqual(rc, 2, out)
        self.assertFalse(os.path.exists(os.path.join(self.app, checker_floor.FLOOR_FILE)))

    # 2. compare
    def test_compare_holds(self):
        self.record_base()
        self.commit({"score": 80, "criteria": dict(BASE["criteria"])}, "same")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS", out.splitlines()[-1])

    def test_compare_fails_on_a_worse_status(self):
        self.record_base()
        self.commit({"score": 80, "criteria": dict(BASE["criteria"], license="warn")}, "worse")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 1, out)
        self.assertIn("WORSE license: pass -> warn", out)

    def test_compare_fails_on_a_lower_score(self):
        self.record_base()
        self.commit({"score": 79, "criteria": dict(BASE["criteria"])}, "lower")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 1, out)
        self.assertIn("WORSE score: 80 -> 79", out)

    def test_compare_fails_when_a_criterion_disappears(self):
        self.record_base()
        crit = dict(BASE["criteria"])
        del crit["license"]
        self.commit({"score": 80, "criteria": crit}, "gone")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 1, out)

    def test_compare_reports_an_improvement_as_4(self):
        self.record_base()
        self.commit({"score": 85, "criteria": dict(BASE["criteria"], secretscanning="pass")}, "better")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 4, out)
        self.assertIn("record", out.splitlines()[-1])

    def test_compare_unmeasured_floor_criterion_is_no_result(self):
        self.record_base()
        self.commit(dict(BASE, unmeasured=["maintainability"]), "unmeasured")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 2, out)
        self.assertIn("not a pass", out.splitlines()[-1])

    def test_compare_uses_the_floor_at_the_merge_base(self):
        self.record_base()
        run(["git", "checkout", "-q", "development"], self.app)
        self.write_scan({"score": 99, "criteria": dict(BASE["criteria"], maintainability="pass")})
        self.main("record", self.app)
        self.commit(None, "development raises its floor after the branch point")
        run(["git", "checkout", "-q", "feature"], self.app)
        self.commit({"score": 80, "criteria": dict(BASE["criteria"])}, "same")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 0, out)

    def test_compare_fails_when_the_change_lowers_the_floor_file(self):
        self.record_base()
        self.commit({"score": 70, "criteria": dict(BASE["criteria"], license="warn")}, "scan")
        self.main("record", self.app, "--reset")
        self.commit(None, "lower the floor")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 1, out)
        self.assertIn(f"the change lowers license in {checker_floor.FLOOR_FILE}", out)

    def test_compare_fails_when_the_change_deletes_the_floor_file(self):
        self.record_base()
        os.remove(os.path.join(self.app, checker_floor.FLOOR_FILE))
        self.commit(None, "delete the floor")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 1, out)
        self.assertIn("deletes", out)

    def test_compare_without_any_floor_is_not_applicable(self):
        run(["git", "checkout", "-q", "-b", "feature"], self.app)
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 3, out)

    def test_compare_needs_a_base_ref(self):
        rc, _ = self.main("compare", self.app)
        self.assertEqual(rc, 2)

    def test_compare_reads_a_given_scan(self):
        self.record_base()
        os.remove(self.calls)
        scan = os.path.join(self.tmp.name, "given.json")
        with open(scan, "w") as fh:
            json.dump({"score": 80, "criteria": {k: {"status": v} for k, v in dict(BASE["criteria"], license="fail").items()}}, fh)
        rc, out = self.main("compare", self.app, "--base-ref", "development", "--scan", scan)
        self.assertEqual(rc, 1, out)
        self.assertFalse(os.path.exists(self.calls))

    # 3. no result
    def test_a_crashing_scanner_is_no_result(self):
        self.record_base()
        os.remove(os.path.join(self.app, "scan.json"))
        self.commit(None, "no scan")
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 2, out)
        self.assertIn("NO RESULT", out.splitlines()[-1])

    def test_a_scanner_exit_2_is_no_result(self):
        self.record_base()
        self.commit(dict(BASE, exit=2), "scanner refuses")
        rc, _ = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 2)

    def test_a_missing_scanner_is_no_result(self):
        self.record_base()
        os.remove(os.path.join(self.home, "node_modules", ".bin", "tsx"))
        rc, out = self.main("compare", self.app, "--base-ref", "development")
        self.assertEqual(rc, 2, out)

    # 4. cache
    def test_a_clean_commit_is_scanned_once(self):
        self.main("measure", self.app)
        self.main("measure", self.app)
        with open(self.calls) as fh:
            self.assertEqual(len(fh.read().splitlines()), 1)

    def test_a_dirty_tree_is_never_cached(self):
        with open(os.path.join(self.app, "dirty.txt"), "w") as fh:
            fh.write("x")
        self.main("measure", self.app)
        self.main("measure", self.app)
        with open(self.calls) as fh:
            self.assertEqual(len(fh.read().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
