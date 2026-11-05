#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-123's checker (check_sig_floor.py), on real git histories.

  1. WRITE: the floor lists exactly the 4-star checks gate 122's report meets,
     under gate 122's own check names.
  2. CHECK, against a committed floor:
       a planted regression that breaks a floored check FAILS and names it;
       a refactor that keeps every check PASSES;
       a check met at the merge base is guarded even when the committed file
       does not list it yet;
       a floored check development already misses is INHERITED while the
       change does not make it worse, and FAILS when it does;
       a change that removes a check from the floor file FAILS, and the floor
       is read from the base, so the change cannot lower its own;
       no floor file is exit 4, an unrelated base is exit 3;
       sigrid.yaml excludes are honoured, as in gate 122.
  3. FIVE STAR: a share between half the limit and the limit passes and is
     listed as a 5-star finding, never as a failure.
  4. RAISE: a head that meets checks the floor does not list writes the
     raised floor to --proposed, and writes nothing when it fails.
  5. READER BUMP: a floor recorded by an older unit reader (no `unit_reader`
     field is reader 1) may drop the checks the newer reader re-measures, in
     the change that re-records it; no other check may leave.
  6. CACHE: a cached run reads the same units as an uncached one and reads
     no file twice; a cache written by an older unit reader is not reused.

Run: python3 scripts/lib/test_check_sig_floor.py
"""
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
import check_sig_floor as floor  # noqa: E402
import check_sig_maintainability as sig  # noqa: E402

LIZARD, WHY = sig.load_lizard()
if not LIZARD:
    # A suite that cannot load its tools must not report green.
    print(f"FAIL: pinned tools unavailable: {WHY}")
    sys.exit(1)


def php_method(name, lines=3, tag="x"):
    body = "".join(f"        ${tag}{i} = {i} + strlen('{tag}{name}');\n" for i in range(lines))
    return f"    public function {name}(int $p0): int\n    {{\n{body}        return $p0;\n    }}\n"


def php_class(name, methods):
    return f"<?php\nnamespace OCA\\Fx\\Service;\n\nclass {name}\n{{\n" + "".join(methods) + "}\n"


SMALL = [php_method(f"m{i}", lines=3, tag=f"s{i}") for i in range(12)]


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = floor.main(list(argv))
    return rc, buf.getvalue()


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="gate123-")
        self.git("init", "-q", ".")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True, text=True).stdout

    def write(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def remove(self, rel):
        os.remove(os.path.join(self.dir, rel))

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def floor_file(self):
        with open(os.path.join(self.dir, floor.FLOOR_PATH)) as fh:
            return json.load(fh)

    def set_floor(self, checks):
        doc = self.floor_file()
        doc["checks"] = sorted(checks)
        self.write(floor.FLOOR_PATH, json.dumps(doc, indent=1) + "\n")

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class FloorCase(unittest.TestCase):
    """A clean app at `base` with the floor written from it."""

    def setUp(self):
        self.repo = Repo()
        self.repo.write("lib/Service/Small.php", php_class("Small", SMALL))
        self.repo.commit("app")
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.repo.commit("floor")
        self.repo.git("branch", "base")
        self.repo.git("checkout", "-q", "-b", "change")

    def tearDown(self):
        self.repo.close()

    def check(self, *extra):
        self.repo.commit("change")
        return run("check", self.repo.dir, "--base-ref", "base", *extra)


class Write(FloorCase):
    def test_the_floor_is_the_met_four_star_checks_under_gate_122_names(self):
        report = floor.measure(self.repo.dir, LIZARD, sig.UnitReader(LIZARD))
        met = sorted(label for label, ok in sig.checks_of(report) if ok)
        self.assertEqual(self.repo.floor_file()["checks"], met)
        self.assertIn("php unit_size >60", met)
        self.assertEqual(self.repo.floor_file()["profile"], "four-star")
        self.assertIn("v18.1", self.repo.floor_file()["limits"])

    def test_re_recording_never_lowers_the_floor_and_names_the_missed_check(self):
        # A check floored under older limits that the current limits miss stays.
        wide = [m.replace("(int $p0)", "(int $p0, int $q, int $r)") for m in SMALL[:3]]
        self.repo.write("lib/Service/Small.php", php_class("Small", wide + SMALL[3:]))
        self.repo.commit("three wide units")
        before = self.repo.floor_file()["checks"]
        self.assertIn("php unit_interfacing >2", before)
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.repo.floor_file()["checks"], before)
        self.assertIn("floored but missed at the current limits, kept in the floor: php unit_interfacing >2", out)
        self.assertIn("(1 floored but missed)", out)

    def test_re_recording_drops_a_check_that_left_the_measured_scope(self):
        self.repo.set_floor(self.repo.floor_file()["checks"] + ["python duplication"])
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("python duplication", self.repo.floor_file()["checks"])

    def test_check_rows_agree_with_gate_122_checks(self):
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        report = floor.measure(self.repo.dir, LIZARD, sig.UnitReader(LIZARD))
        rows = floor.check_rows(report, "four-star")
        self.assertEqual({k: r["ok"] for k, r in rows.items()}, dict(sig.checks_of(report)))


class Check(FloorCase):
    def test_a_planted_regression_fails_and_names_the_check(self):
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("  php unit_size >60: ", out)
        self.assertIn("met at the base (0.0%)", out)
        self.assertIn("[gate-123] sig-floor: FAIL: ", out)

    def test_a_refactor_that_keeps_every_check_passes(self):
        methods = SMALL[:10] + [php_method("merged", lines=4, tag="mm")]
        self.repo.write("lib/Service/Small.php", php_class("Small", methods))
        self.repo.write("lib/Service/Split.php", php_class("Split", [php_method("moved", lines=2, tag="mv")]))
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("[gate-123] sig-floor: PASS: ", out)

    def test_a_check_met_at_the_base_is_guarded_before_the_file_lists_it(self):
        self.repo.git("checkout", "-q", "base")
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c != "php unit_size >60"])
        self.repo.commit("floor without the check")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("  php unit_size >60: ", out)

    def test_a_check_development_already_misses_is_inherited_until_made_worse(self):
        self.repo.git("checkout", "-q", "base")
        checks = self.repo.floor_file()["checks"]
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        self.repo.commit("development broke it")
        self.assertIn("php unit_size >60", checks)

        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("lib/Service/More.php", php_class("More", [php_method("tiny", lines=2, tag="t")]))
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("inherited, not counted: php unit_size >60", out)

        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=90, tag="h")]))
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("already missed at the base", out)
        self.assertIn("makes it worse", out)

    def test_an_equal_share_on_an_inherited_breach_is_not_worse(self):
        self.repo.git("checkout", "-q", "base")
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        self.repo.commit("development broke it")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("README.md", "docs only\n")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("inherited, not counted: php unit_size >60", out)

    def test_removing_a_check_from_the_floor_file_fails(self):
        checks = self.repo.floor_file()["checks"]
        self.repo.set_floor([c for c in checks if c != "php unit_size >60"])
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: php unit_size >60", out)

    def test_the_floor_is_read_from_the_base_so_a_change_cannot_lower_its_own(self):
        self.repo.git("checkout", "-q", "base")
        checks = self.repo.floor_file()["checks"]
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        self.repo.commit("development broke it")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.set_floor([c for c in checks if c != "php unit_size >60"])
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=90, tag="h")]))
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("  php unit_size >60: ", out)
        self.assertIn("makes it worse", out)

    def test_no_floor_file_is_exit_4(self):
        self.repo.remove(floor.FLOOR_PATH)
        self.repo.commit("drop")
        rc, out = run("check", self.repo.dir)
        self.assertEqual(rc, 4, out)
        self.assertIn("check_sig_floor.py write", out)

    def test_an_unrelated_base_is_exit_3(self):
        self.repo.git("checkout", "-q", "--orphan", "other")
        self.repo.write("README.md", "x\n")
        self.repo.commit("unrelated")
        self.repo.git("checkout", "-q", "change")
        rc, out = run("check", self.repo.dir, "--base-ref", "other")
        self.assertEqual(rc, 3, out)

    def test_sigrid_yaml_excludes_are_honoured(self):
        self.repo.write("sigrid.yaml", "exclude:\n  - \".*/lib/Generated/.*\"\n")
        self.repo.write("lib/Generated/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        rc, out = self.check()
        self.assertEqual(rc, 0, out)


class FiveStar(FloorCase):
    def test_a_five_star_miss_is_reported_and_never_blocks(self):
        # One of seven equal units takes three parameters: 14.3% of the code,
        # above the 5-star 12.5% and below the 4-star 15.4%.
        wide = [SMALL[0].replace("(int $p0)", "(int $p0, int $q, int $r)")]
        self.repo.write("lib/Service/Small.php", php_class("Small", wide + SMALL[1:7]))
        md = os.path.join(self.repo.dir, "..", os.path.basename(self.repo.dir) + ".md")
        rc, out = self.check("--md", md)
        try:
            self.assertEqual(rc, 0, out)
            self.assertIn("5-star finding(s), not blocking", out)
            with open(md) as fh:
                text = fh.read()
            self.assertIn("5-star findings (not blocking)", text)
            self.assertIn("php unit_interfacing >2", text.split("5-star findings (not blocking)")[1])
        finally:
            if os.path.exists(md):
                os.remove(md)


class Raise(FloorCase):
    def setUp(self):
        super().setUp()
        self.proposed = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.proposed):
            os.remove(self.proposed)
        super().tearDown()

    def test_a_head_that_meets_more_checks_proposes_the_raised_floor(self):
        self.repo.git("checkout", "-q", "base")
        checks = self.repo.floor_file()["checks"]
        self.repo.set_floor([c for c in checks if c != "php unit_size >60"])
        self.repo.commit("lower floor")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("README.md", "docs\n")
        rc, out = self.check("--proposed", self.proposed)
        self.assertEqual(rc, 0, out)
        self.assertIn("1 check(s) above the committed floor", out)
        with open(self.proposed) as fh:
            self.assertEqual(json.load(fh)["checks"], checks)

    def test_the_proposal_keeps_committed_checks_the_head_misses(self):
        self.repo.git("checkout", "-q", "base")
        checks = self.repo.floor_file()["checks"]
        self.repo.set_floor([c for c in checks if c != "php unit_interfacing >6"])
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        self.repo.commit("development broke a floored check and the file misses another")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("README.md", "docs\n")
        rc, out = self.check("--proposed", self.proposed)
        self.assertEqual(rc, 0, out)
        with open(self.proposed) as fh:
            proposed = json.load(fh)["checks"]
        self.assertIn("php unit_size >60", proposed)
        self.assertIn("php unit_interfacing >6", proposed)

    def test_a_failing_change_proposes_nothing(self):
        self.repo.git("checkout", "-q", "base")
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c != "php unit_interfacing >6"])
        self.repo.commit("floor below what the app meets")
        self.repo.git("checkout", "-q", "-B", "change")
        self.repo.write("lib/Service/Big.php", php_class("Big", [php_method("huge", lines=70, tag="h")]))
        rc, out = self.check("--proposed", self.proposed)
        self.assertEqual(rc, 1, out)
        self.assertIn("1 check(s) above the committed floor", out)
        self.assertFalse(os.path.exists(self.proposed))


class FloorFirst(FloorCase):
    def test_no_floor_is_not_applicable_before_any_tool_or_base(self):
        self.repo.remove(floor.FLOOR_PATH)
        self.repo.commit("drop")
        real = sig.load_lizard
        sig.load_lizard = lambda: (None, "tools must not be loaded without a floor")
        try:
            rc, out = run("check", self.repo.dir)
            self.assertEqual(rc, 4, out)
            rc, out = run("check", self.repo.dir, "--base-ref", "no-such-ref")
            self.assertEqual(rc, 4, out)
            self.assertNotIn("tooling", out)
        finally:
            sig.load_lizard = real

    def test_with_a_floor_missing_tools_are_wiring(self):
        real = sig.load_lizard
        sig.load_lizard = lambda: (None, "no lizard")
        try:
            rc, out = run("check", self.repo.dir, "--base-ref", "base")
            self.assertEqual(rc, 5, out)
        finally:
            sig.load_lizard = real


class Boundaries(unittest.TestCase):
    def report(self, size, dup, coupling, hidden):
        rows = lambda prop: [{"above": b, "share": size if i == 0 else 0.0}
                             for i, (b, _cap) in enumerate(sig.LIMITS[prop])]
        return {"languages": {"php": {"unit_size": rows("unit_size"), "unit_complexity": rows("unit_complexity"),
                                      "unit_interfacing": rows("unit_interfacing"),
                                      "duplication": {"share": dup}}},
                "structure": {"php": {"module_coupling": [{"above": 10, "share": coupling},
                                                          {"above": 20, "share": 0.0}, {"above": 50, "share": 0.0}],
                                      "component_independence": {"hidden_share": hidden}}}}

    def test_a_share_equal_to_the_limit_meets_it(self):
        rows = floor.check_rows(self.report(.480, .058, .097, .945), "four-star")
        for label in ("php unit_size >15", "php duplication", "php module_coupling >10",
                      "php component_independence"):
            self.assertTrue(rows[label]["ok"], label)

    def test_an_equal_share_is_not_worse_in_either_direction(self):
        for better_high in (False, True):
            row = {"share": .5, "higher_is_better": better_high}
            self.assertFalse(floor.worse(row, dict(row)))
            self.assertTrue(floor.worse(row, dict(row, share=.6 if better_high else .4)))

    def test_just_past_the_limit_misses_it(self):
        rows = floor.check_rows(self.report(.4801, .0581, .0971, .9449), "four-star")
        for label in ("php unit_size >15", "php duplication", "php module_coupling >10",
                      "php component_independence"):
            self.assertFalse(rows[label]["ok"], label)


class Scope(FloorCase):
    def setUp(self):
        super().setUp()
        self.repo.git("checkout", "-q", "base")
        self.repo.write("src/a.js", "export function f(a) {\n  if (a) { return 1 }\n  return 2\n}\n")
        self.repo.commit("a js file")
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.repo.commit("floor with javascript")
        self.assertIn("javascript unit_size >15", self.repo.floor_file()["checks"])
        self.repo.git("checkout", "-q", "-B", "change")

    def test_a_language_that_leaves_without_a_scope_change_fails(self):
        self.repo.remove("src/a.js")
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("javascript unit_size >15: no longer measured", out)

    def test_a_sigrid_yaml_exclude_takes_the_checks_out_of_the_floor(self):
        self.repo.write("sigrid.yaml", "exclude:\n  - \".*/src/.*\"\n")
        js = [c for c in self.repo.floor_file()["checks"] if c.startswith("javascript")]
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c not in js])
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("left the measured scope through sigrid.yaml", out)

        # The next change, on a base that already excludes it, is not judged on it again.
        self.repo.git("branch", "-f", "base", "HEAD")
        self.repo.write("README.md", "next\n")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("javascript", out.split("[gate-123]")[0])

    def test_a_check_the_base_no_longer_measures_is_not_judged_again(self):
        self.repo.write("sigrid.yaml", "exclude:\n  - \".*/src/.*\"\n")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("javascript unit_size >15", self.repo.floor_file()["checks"])
        self.repo.git("branch", "-f", "base", "HEAD")
        self.repo.write("README.md", "next\n")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("inherited, not counted: javascript unit_size >15", out)

    def test_removing_a_still_measured_check_fails_even_with_a_sigrid_change(self):
        self.repo.write("sigrid.yaml", "exclude:\n  - \".*/docs/.*\"\n")
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c != "javascript unit_size >15"])
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: javascript unit_size >15", out)


VUE_COMPONENT = ("<template>\n\t<input @input=\"(v) => pick(v)\">\n</template>\n\n<script>\nexport default {\n"
                 "\tmethods: {\n\t\tpick(v) {\n\t\t\tif (v) {\n\t\t\t\treturn 1\n\t\t\t}\n\t\t\treturn 2\n\t\t},\n"
                 "\t},\n}\n</script>\n")


class ReaderBump(FloorCase):
    """A unit reader change re-measures some checks, so the floor recorded
    under the older reader may be re-recorded: a check whose measurement the
    new reader changed may leave the floor file, any other check may not."""

    def setUp(self):
        super().setUp()
        self.repo.git("checkout", "-q", "base")
        self.repo.write("src/components/Pick.vue", VUE_COMPONENT)
        self.repo.commit("a vue component")
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.assertIn("vue unit_size >15", self.repo.floor_file()["checks"])
        self.assertEqual(self.repo.floor_file()["unit_reader"], sig.UNIT_READER_VERSION)

    def recorded_under(self, version):
        """Commit the base floor as recorded by reader `version` (None: no field)."""
        doc = self.repo.floor_file()
        doc.pop("unit_reader", None)
        if version is not None:
            doc["unit_reader"] = version
        self.repo.write(floor.FLOOR_PATH, json.dumps(doc, indent=1) + "\n")
        self.repo.commit("floor")
        self.repo.git("checkout", "-q", "-B", "change")

    def rerecord_without(self, label):
        rc, out = run("write", self.repo.dir)
        self.assertEqual(rc, 0, out)
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c != label])

    def test_a_floor_without_the_field_was_recorded_by_reader_1(self):
        self.assertEqual(floor.unit_reader_of({"checks": []}), 1)
        self.assertEqual(floor.unit_reader_of({"checks": [], "unit_reader": 2}), 2)

    def test_a_reader_bump_lets_a_vue_unit_check_leave_the_floor(self):
        self.recorded_under(None)
        self.rerecord_without("vue unit_size >15")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("vue unit_size >15", out)
        self.assertIn("re-measured by unit reader", out)

    def test_a_reader_bump_does_not_let_a_php_check_leave(self):
        self.recorded_under(None)
        self.rerecord_without("php unit_size >60")
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: php unit_size >60", out)

    def test_a_reader_bump_does_not_let_vue_duplication_leave(self):
        self.recorded_under(None)
        self.rerecord_without("vue duplication")
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: vue duplication", out)

    def test_a_floor_recorded_by_the_current_reader_keeps_its_vue_checks(self):
        self.recorded_under(sig.UNIT_READER_VERSION)
        self.rerecord_without("vue unit_size >15")
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: vue unit_size >15", out)

    def test_the_bump_counts_only_when_the_head_floor_is_re_recorded(self):
        self.recorded_under(None)
        self.repo.set_floor([c for c in self.repo.floor_file()["checks"] if c != "vue unit_size >15"])
        rc, out = self.check()
        self.assertEqual(rc, 1, out)
        self.assertIn("removes 1 check(s) from the committed floor: vue unit_size >15", out)


class Cache(unittest.TestCase):
    def test_a_cached_run_reads_the_same_units_and_no_file_twice(self):
        repo = Repo()
        try:
            repo.write("lib/Service/Small.php", php_class("Small", SMALL))
            repo.write("src/a.js", "export function f(a, b, c) {\n  if (a) { return b }\n  return c\n}\n")
            repo.commit("app")
            cache = {}
            first = floor.CachedUnitReader(LIZARD, cache)
            r1 = floor.measure(repo.dir, LIZARD, first)
            self.assertEqual((first.hits, first.misses), (0, 2))
            second = floor.CachedUnitReader(LIZARD, cache)
            r2 = floor.measure(repo.dir, LIZARD, second)
            self.assertEqual((second.hits, second.misses), (2, 0))
            self.assertEqual(r1["languages"], r2["languages"])
            plain = floor.measure(repo.dir, LIZARD, sig.UnitReader(LIZARD))
            self.assertEqual(plain["languages"], r2["languages"])

            path = os.path.join(repo.dir, "..", os.path.basename(repo.dir) + "-cache.json")
            floor.save_cache(path, cache, second.used)
            try:
                self.assertEqual(floor.load_cache(path), cache)
            finally:
                os.remove(path)
        finally:
            repo.close()

    def test_a_cache_written_by_an_older_unit_reader_is_not_reused(self):
        fd, path = tempfile.mkstemp(prefix="gate123-cache-", suffix=".json")
        os.close(fd)
        try:
            with open(path, "w") as fh:
                json.dump({"lizard": sig.LIZARD_VERSION, "files": {"k": {"units": []}}}, fh)
            self.assertEqual(floor.load_cache(path), {})
            with open(path, "w") as fh:
                json.dump({"lizard": sig.LIZARD_VERSION, "reader": sig.UNIT_READER_VERSION,
                           "files": {"k": {"units": []}}}, fh)
            self.assertEqual(floor.load_cache(path), {"k": {"units": []}})
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main(verbosity=1)
