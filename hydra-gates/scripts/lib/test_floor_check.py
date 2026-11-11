#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the maintainability floor comparator (floor_check.py).

The estimator is replaced by a stub (MAINTAINABILITY_FLOOR_ESTIMATOR) that
reports the ratings a tree carries in `ratings.json`, so every verdict is
driven by known numbers on real git histories:

  1. COMPARE: a drop of more than the tolerance FAILS and names the value; a
     drop of exactly the tolerance and a rise PASS; a value the base rates and
     the head no longer rates FAILS; --base-ref measures the merge base, not
     the base branch tip; a change that lowers or deletes the committed floor
     file FAILS even when the measurement holds.
  2. AGAINST-FLOOR: below the floor FAILS, at the floor PASSES, no floor file
     is exit 4.
  3. RAISE: no floor writes the first one; every value higher or equal with
     one higher rewrites it; one lower value refuses and writes nothing;
     all equal is exit 3 and writes nothing.
  4. CACHE: a clean commit is measured once; a dirty tree is never cached.
  5. TOOLING: the estimator's exit 4 and 5 pass through as 4 and 5.

Run: python3 scripts/lib/test_floor_check.py
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
import floor_check  # noqa: E402

STUB = r'''
import json, os, sys
args = sys.argv[1:]
app = args[1]
out = args[args.index("--json") + 1]
calls = os.environ.get("FLOOR_STUB_CALLS")
if calls:
    with open(calls, "a") as fh:
        fh.write(app + "\n")
path = os.path.join(app, "ratings.json")
if not os.path.isfile(path):
    sys.exit(4)
r = json.load(open(path))
if r.get("exit"):
    sys.exit(r["exit"])
props = {k: {"rating": v} for k, v in r["properties"].items()}
json.dump({"rating": {"overall": {"range": r["range"]}, "properties": props}}, open(out, "w"))
'''

BASE = {"range": [3.50, 3.70], "properties": {"duplication": 3.40, "unit_size": 3.20,
        "unit_complexity": 3.10, "unit_interfacing": 2.90, "module_coupling": 4.00,
        "component_independence": 5.50, "component_entanglement": 5.50}}


def ratings(**changes):
    r = json.loads(json.dumps(BASE))
    for k, v in changes.items():
        if k == "overall":
            r["range"][0] = v
        elif v is None:
            r["properties"].pop(k, None)
        else:
            r["properties"][k] = v
    return r


def read(path):
    with open(path) as fh:
        return fh.read()


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = floor_check.main(list(argv))
    return rc, buf.getvalue()


class FloorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        stub = os.path.join(self.root, "stub.py")
        with open(stub, "w") as fh:
            fh.write(STUB)
        self.calls = os.path.join(self.root, "calls.txt")
        self.env = {"MAINTAINABILITY_FLOOR_ESTIMATOR": stub,
                    "HYDRA_GATE_FLOOR_CACHE": os.path.join(self.root, "cache"),
                    "FLOOR_STUB_CALLS": self.calls}
        self.saved = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def git(self, repo, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                       check=True, capture_output=True)

    def repo(self, name, r):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        self.git(path, "init", "-q", "-b", "development")
        self.write(path, r)
        self.git(path, "add", "-A")
        self.git(path, "commit", "-q", "-m", "base")
        return path

    def write(self, path, r, floor=None):
        with open(os.path.join(path, "ratings.json"), "w") as fh:
            json.dump(r, fh)
        if floor is not None:
            with open(os.path.join(path, floor_check.FLOOR_FILE), "w") as fh:
                json.dump(floor, fh)

    def commit(self, path, r, msg="change", floor=None):
        self.write(path, r, floor)
        self.git(path, "add", "-A")
        self.git(path, "commit", "-q", "-m", msg)

    def json_tree(self, name, r):
        path = os.path.join(self.root, name + ".json")
        props = {k: {"rating": v} for k, v in r["properties"].items()}
        with open(path, "w") as fh:
            json.dump({"rating": {"overall": {"range": r["range"]}, "properties": props}}, fh)
        return path

    # 1. compare
    def test_drop_beyond_tolerance_fails_and_names_it(self):
        rc, out = run("compare", self.json_tree("b", BASE), self.json_tree("h", ratings(unit_size=3.18)))
        self.assertEqual(rc, 1)
        self.assertIn("unit_size 3.20 -> 3.18", out)

    def test_drop_of_exactly_the_tolerance_passes(self):
        rc, _ = run("compare", self.json_tree("b", BASE), self.json_tree("h", ratings(unit_size=3.19, overall=3.49)))
        self.assertEqual(rc, 0)

    def test_rise_passes(self):
        rc, out = run("compare", self.json_tree("b", BASE), self.json_tree("h", ratings(duplication=4.0)))
        self.assertEqual(rc, 0, out)

    def test_overall_drop_fails(self):
        rc, out = run("compare", self.json_tree("b", BASE), self.json_tree("h", ratings(overall=3.40)))
        self.assertEqual(rc, 1)
        self.assertIn("overall 3.50 -> 3.40", out)

    def test_value_that_leaves_the_scope_fails(self):
        rc, out = run("compare", self.json_tree("b", BASE), self.json_tree("h", ratings(module_coupling=None)))
        self.assertEqual(rc, 1)
        self.assertIn("module_coupling 4.00 -> none", out)

    def test_base_ref_measures_the_merge_base(self):
        repo = self.repo("app", BASE)
        self.git(repo, "checkout", "-q", "-b", "feature")
        self.commit(repo, ratings(unit_complexity=2.50))
        self.git(repo, "checkout", "-q", "development")
        self.commit(repo, ratings(unit_complexity=2.00), "development moves on")
        self.git(repo, "checkout", "-q", "feature")
        rc, out = run("compare", repo, "--base-ref", "development")
        self.assertEqual(rc, 1, out)
        self.assertIn("unit_complexity 3.10 -> 2.50", out)

    def test_working_tree_is_the_head(self):
        repo = self.repo("app", BASE)
        self.write(repo, ratings(duplication=3.0))
        rc, out = run("compare", repo, "--base-ref", "HEAD")
        self.assertEqual(rc, 1, out)

    def test_lowering_the_committed_floor_fails(self):
        base = self.repo("base", BASE)
        head = self.repo("head", BASE)
        floor = {"overall": 3.5, "properties": {"unit_size": 3.2}}
        self.commit(base, BASE, floor=floor)
        self.commit(head, BASE, floor={"overall": 3.5, "properties": {"unit_size": 3.0}})
        rc, out = run("compare", base, head)
        self.assertEqual(rc, 1)
        self.assertIn("lowers unit_size", out)

    def test_deleting_the_committed_floor_fails(self):
        base = self.repo("base", BASE)
        head = self.repo("head", BASE)
        self.commit(base, BASE, floor={"overall": 3.5, "properties": {}})
        rc, out = run("compare", base, head)
        self.assertEqual(rc, 1)
        self.assertIn("deletes", out)

    # 2. against-floor
    def test_below_the_floor_fails(self):
        repo = self.repo("app", BASE)
        self.commit(repo, ratings(unit_interfacing=2.80), floor={"overall": 3.5, "properties": {"unit_interfacing": 2.9}})
        rc, out = run("against-floor", repo)
        self.assertEqual(rc, 1, out)

    def test_at_the_floor_passes(self):
        repo = self.repo("app", BASE)
        self.commit(repo, BASE, floor={"overall": 3.5, "properties": {"unit_interfacing": 2.9}})
        rc, out = run("against-floor", repo)
        self.assertEqual(rc, 0, out)

    def test_no_floor_is_not_applicable(self):
        rc, _ = run("against-floor", self.repo("app", BASE))
        self.assertEqual(rc, 4)

    # 3. raise
    def test_raise_writes_the_first_floor(self):
        repo = self.repo("app", BASE)
        rc, _ = run("raise", repo)
        self.assertEqual(rc, 0)
        floor = json.loads(read(os.path.join(repo, floor_check.FLOOR_FILE)))
        self.assertEqual(floor["overall"], 3.5)
        self.assertEqual(floor["overall_range"], [3.5, 3.7])
        self.assertEqual(floor["properties"]["unit_size"], 3.2)
        self.assertIsNone(floor["properties"]["volume"])
        self.assertEqual(floor["tolerance"], 0.01)
        self.assertTrue(floor["commit"])
        self.assertIn("profile five-star", floor["tool_version"])

    def test_raise_rewrites_when_one_value_rose(self):
        repo = self.repo("app", BASE)
        run("raise", repo)
        self.commit(repo, ratings(duplication=3.60), floor=json.loads(read(os.path.join(repo, floor_check.FLOOR_FILE))))
        rc, out = run("raise", repo)
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(read(os.path.join(repo, floor_check.FLOOR_FILE)))["properties"]["duplication"], 3.6)

    def test_raise_refuses_when_one_value_fell(self):
        repo = self.repo("app", BASE)
        run("raise", repo)
        before = read(os.path.join(repo, floor_check.FLOOR_FILE))
        self.write(repo, ratings(duplication=3.90, unit_size=3.19))
        rc, out = run("raise", repo)
        self.assertEqual(rc, 1, out)
        self.assertEqual(read(os.path.join(repo, floor_check.FLOOR_FILE)), before)

    def test_raise_with_nothing_higher_writes_nothing(self):
        repo = self.repo("app", BASE)
        run("raise", repo)
        before = read(os.path.join(repo, floor_check.FLOOR_FILE))
        rc, _ = run("raise", repo)
        self.assertEqual(rc, 3)
        self.assertEqual(read(os.path.join(repo, floor_check.FLOOR_FILE)), before)

    # 4. cache
    def calls_made(self):
        return len(read(self.calls).splitlines()) if os.path.isfile(self.calls) else 0

    def test_clean_commit_is_measured_once(self):
        repo = self.repo("app", BASE)
        run("measure", repo)
        run("measure", repo)
        self.assertEqual(self.calls_made(), 1)

    def test_dirty_tree_is_not_cached(self):
        repo = self.repo("app", BASE)
        run("measure", repo)
        self.write(repo, ratings(duplication=2.0))
        rc, out = run("measure", repo)
        self.assertEqual(self.calls_made(), 2)
        self.assertIn('"duplication": 2.0', out)

    # 5. tooling
    def test_estimator_exit_codes_pass_through(self):
        repo = self.repo("app", dict(BASE, exit=5))
        self.assertEqual(run("measure", repo)[0], 5)
        empty = os.path.join(self.root, "empty")
        os.makedirs(empty)
        subprocess.run(["git", "init", "-q", empty], check=True)
        self.assertEqual(run("measure", empty)[0], 4)


if __name__ == "__main__":
    unittest.main()
