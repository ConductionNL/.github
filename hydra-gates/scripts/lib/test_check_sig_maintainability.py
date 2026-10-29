#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-122's checker (check_sig_maintainability.py), rule by rule.

  1. UNITS: lizard's PHP parameter count is replaced by the unique $names;
     Python `self`/`cls` is not a parameter; a file lizard raises on is listed
     as skipped and the rest is still measured.
  2. SCOPE: tests, vendor, Sigrid's default excludes, Nextcloud js/ and l10n/
     are not measured; sigrid.yaml excludes are honoured.
  3. RATCHET on a real git history:
       a new unit over each bound is NEW, and names file, line and unit;
       a legacy unit touched but not made worse is INHERITED;
       a legacy unit made worse is NEW;
       an untouched oversize unit is INHERITED;
       a new copy of a 6+ line fragment is NEW, an edit inside an existing
       clone is not;
       a change with no measured source file is exit 4;
       a base with no merge base is exit 3.
  4. REPORT: the shares are code-weighted and compared with the 4-star limits.
  5. STRUCTURE: PHP and Python dependencies, the component root, and the
     violation degree on the examples in SIG's Guidance for Producers.

Run: python3 scripts/lib/test_check_sig_maintainability.py
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
import check_sig_maintainability as sig  # noqa: E402

LIZARD, WHY = sig.load_lizard()
JSCPD, WHY_JSCPD = sig.find_jscpd() if LIZARD else (None, WHY)
if not LIZARD or not JSCPD:
    # A suite that cannot load its tools must not report green.
    print(f"FAIL: pinned tools unavailable: {WHY or WHY_JSCPD}")
    sys.exit(1)


def php_method(name, lines=3, params=1, branches=0, tag="x"):
    ps = ", ".join(f"${'p'}{i}" for i in range(params))
    body = "".join(f"        if ($p0 === {i}) {{ return strlen('{tag}{i}'); }}\n" for i in range(branches))
    body += "".join(f"        ${tag}{i} = {i} + strlen('{tag}{name}');\n" for i in range(lines))
    return f"    public function {name}({ps}): int\n    {{\n{body}        return 0;\n    }}\n"


def nloc(lines, branches=0):
    """lizard's NLOC for php_method(): signature, braces and return add four."""
    return lines + branches + 4


def php_class(name, methods):
    return f"<?php\nnamespace OCA\\Fx\\Service;\n\nclass {name}\n{{\n" + "".join(methods) + "}\n"


DUP_BLOCK = "".join(f"        $shared{i} = $p0 * {i} + {i * 7};\n" for i in range(9))


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sig.main(list(argv))
    return rc, buf.getvalue()


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="gate122-")
        self.git("init", "-q", ".")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True)

    def write(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class Units(unittest.TestCase):
    def setUp(self):
        self.reader = sig.UnitReader(LIZARD)

    def test_php_params_are_the_unique_dollar_names(self):
        src = "<?php\nclass A {\n    public function w(int $a, ?string $b = null, array $c = [], $d = 1, \\Foo $e = null): int { return 1; }\n}\n"
        (u,) = self.reader.units("A.php", "php", src)
        self.assertEqual(u["params"], 5)

    def test_python_self_and_cls_are_not_parameters(self):
        src = "class K:\n    def m(self, x, y):\n        return x\n\n    @classmethod\n    def c(cls, x):\n        return x\n\ndef f(self_like, b):\n    return b\n"
        got = {u["name"]: u["params"] for u in self.reader.units("k.py", "python", src)}
        self.assertEqual(got, {"m": 2, "c": 1, "f": 2})

    def test_a_file_lizard_raises_on_is_skipped_and_named(self):
        class Boom:
            def analyze_source_code(self, *_a):
                raise IndexError("planted")
        self.reader.analyzer = Boom()
        self.assertEqual(self.reader.units("src/X.vue", "vue", "<template/>"), [])
        self.assertEqual(self.reader.skipped[0]["file"], "src/X.vue")
        self.assertIn("IndexError", self.reader.skipped[0]["reason"])


class ScopeRules(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def test_measured_and_excluded_paths(self):
        s = sig.Scope(self.repo.dir)
        self.assertEqual(s.language("lib/Service/A.php"), "php")
        self.assertEqual(s.language("src/views/A.vue"), "vue")
        self.assertEqual(s.language("src/store/a.ts"), "typescript")
        self.assertEqual(s.language("src/api/main.py"), "python")
        for rel in ("tests/Unit/ATest.php", "src/a.spec.js", "src/tests/test_x.py", "vendor/x/A.php",
                    "js/app.js", "l10n/nl.js", "lib/Migration/Version1.php", "webpack.config.js",
                    "src/__mocks__/a.js", "lib/Service/MockService.php", "docs/a.js", "README.md"):
            self.assertIsNone(s.language(rel), rel)

    def test_sigrid_yaml_excludes_are_honoured(self):
        self.repo.write("sigrid.yaml", "default_excludes: true\nexclude:\n  - \".*/phpmetrics/.*\"\n  - .*/generated[.]php\nlanguages:\n  - php\n")
        s = sig.Scope(self.repo.dir)
        self.assertIsNone(s.language("phpmetrics/html/js/d3.v3.js"))
        self.assertIsNone(s.language("lib/generated.php"))
        self.assertEqual(s.language("lib/languages.php"), "php")


class Ratchet(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("lib/Service/Legacy.php", php_class("Legacy", [
            php_method("big", lines=70, tag="a"),
            php_method("bigToo", lines=70, tag="b"),
            php_method("copyOne", lines=1, tag="c").replace("        return 0;", DUP_BLOCK + "        return 0;"),
            php_method("small", lines=3, tag="d"),
        ]))
        self.repo.write("README.md", "fixture\n")
        self.repo.commit("base")
        self.repo.git("branch", "-M", "base")
        self.repo.git("checkout", "-q", "-b", "change")

    def tearDown(self):
        self.repo.close()

    def edit(self, old, new, rel="lib/Service/Legacy.php"):
        path = os.path.join(self.repo.dir, rel)
        with open(path) as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(path, "w") as fh:
            fh.write(text.replace(old, new, 1))

    def ratchet(self):
        self.repo.commit("change")
        return run("ratchet", self.repo.dir, "--base-ref", "base")

    def add_class(self, methods):
        self.repo.write("lib/Service/Fresh.php", php_class("Fresh", methods))

    def test_new_units_over_each_bound_are_new_findings(self):
        self.add_class([php_method("long", lines=62, tag="e"), php_method("wide", params=5, tag="f"),
                        php_method("branchy", branches=11, tag="g"), php_method("fine", params=4, branches=9, tag="h")])
        rc, out = self.ratchet()
        self.assertEqual(rc, 1, out)
        self.assertIn(f"lib/Service/Fresh.php:6 Fresh::long: NLOC > 60: {nloc(62)}", out)
        self.assertIn("Fresh::wide: 5 or more parameters: 5", out)
        self.assertIn("Fresh::branchy: McCabe > 10: 12", out)
        self.assertNotIn("Fresh::fine", out)
        self.assertIn("[gate-122] sig-maintainability: FAIL: 3 finding(s)", out)

    def test_bounds_are_exclusive(self):
        self.add_class([php_method("edge", lines=47, params=4, branches=9, tag="e")])
        self.assertEqual(nloc(47, 9), 60)
        rc, out = self.ratchet()
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 1 changed unit(s) in 1 file(s), 0 finding(s)", out)

    def test_touched_legacy_unit_not_made_worse_is_inherited(self):
        self.edit("$a5 = 5 + strlen('abig');", "$a5 = 6 + strlen('abig');")
        rc, out = self.ratchet()
        self.assertEqual(rc, 0, out)
        self.assertIn("inherited, not counted", out)
        self.assertIn(f"Legacy::big: NLOC > 60: {nloc(70)}", out)

    def test_legacy_unit_made_worse_is_new(self):
        self.edit("$a5 = 5 + strlen('abig');", "$a5 = 5 + strlen('abig');\n        $grow = 1;")
        rc, out = self.ratchet()
        self.assertEqual(rc, 1, out)
        self.assertIn(f"Legacy::big: NLOC > 60: {nloc(71)} (was {nloc(70)})", out)
        self.assertNotIn("Legacy::bigToo: NLOC", out.split("inherited")[0])

    def test_new_copy_of_a_fragment_is_new_and_names_the_original(self):
        self.add_class([php_method("copyTwo", lines=1, tag="z").replace("        return 0;", DUP_BLOCK + "        return 0;")])
        rc, out = self.ratchet()
        self.assertEqual(rc, 1, out)
        self.assertIn("duplicated fragment of 6+ lines", out)
        self.assertIn("same as lib/Service/Legacy.php:", out)

    def test_a_clone_of_mostly_comment_lines_is_not_six_lines_of_code(self):
        # The openregister #5008 shape: jscpd's weak mode matches across a
        # docblock, so a long "fragment" can hold three lines of code.
        tail = ("        $this->addType(fieldName: 'linkedBy', type: 'string', nullable: true, default: null);\n    }\n\n"
                "    /**\n" + "".join(f"     * Line {i} of a long explanation of the method below.\n" for i in range(9))
                + "     */\n")
        self.repo.git("checkout", "-q", "base")
        self.repo.write("lib/Service/First.php", php_class("First", ["    public function __construct()\n    {\n" + tail
                                                                     + php_method("one", lines=2, tag="o")]))
        self.repo.commit("base with the first copy")
        self.repo.git("checkout", "-q", "-B", "change", "base")
        self.repo.write("lib/Service/Second.php", php_class("Second", ["    public function __construct()\n    {\n" + tail
                                                                       + php_method("two", lines=2, tag="t")]))
        rc, out = self.ratchet()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("duplicated fragment", out)
        # Five equal code lines are not a SIG clone, so the report counts no redundant code either.
        clones = sig.run_jscpd(self.repo.dir, JSCPD, ["lib/Service/First.php", "lib/Service/Second.php"])
        self.assertEqual(clones, [])

    def test_edit_inside_an_existing_clone_is_not_new(self):
        self.repo.git("checkout", "-q", "base")
        self.repo.write("lib/Service/Twin.php", php_class("Twin", [
            php_method("copyTwo", lines=1, tag="y").replace("        return 0;", DUP_BLOCK + "        return 0;")]))
        self.repo.commit("base with an existing clone")
        self.repo.git("checkout", "-q", "-B", "change", "base")
        # Re-indent two lines inside the clone (still a clone in jscpd's weak
        # mode) and add an unrelated method, so the clone search does run.
        self.edit("        $shared4 = $p0 * 4 + 28;\n        $shared5", "          $shared4 = $p0 * 4 + 28;\n          $shared5",
                  rel="lib/Service/Twin.php")
        self.edit("class Twin\n{\n", "class Twin\n{\n" + php_method("unrelated", lines=8, tag="u"), rel="lib/Service/Twin.php")
        rc, out = self.ratchet()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("duplicated fragment", out)

    def test_a_change_with_no_measured_source_is_not_applicable(self):
        self.repo.write("README.md", "changed\n")
        self.repo.write("tests/Unit/FreshTest.php", php_class("FreshTest", [php_method("t", lines=80)]))
        rc, out = self.ratchet()
        self.assertEqual(rc, 4, out)
        self.assertIn("touches no measured source file", out)

    def test_an_unrelated_base_is_exit_3(self):
        self.repo.git("checkout", "-q", "--orphan", "other")
        self.repo.write("lib/Other.php", "<?php\n")
        self.repo.commit("unrelated")
        self.repo.git("checkout", "-q", "change")
        self.add_class([php_method("fine")])
        self.repo.commit("change")
        rc, out = run("ratchet", self.repo.dir, "--base-ref", "other")
        self.assertEqual(rc, 3, out)


class Report(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def test_profile_is_code_weighted_against_the_limits(self):
        self.repo.write("lib/Service/A.php", php_class("A", [php_method("long", lines=40, tag="a"),
                                                          php_method("short", lines=5, tag="b")]))
        self.repo.write("tests/Unit/ATest.php", php_class("ATest", [php_method("huge", lines=200)]))
        self.repo.commit("base")
        out_json = os.path.join(self.repo.dir, "..", os.path.basename(self.repo.dir) + ".json")
        rc, out = run("report", self.repo.dir, "--json", out_json)
        self.assertEqual(rc, 0, out)
        with open(out_json) as fh:
            report = json.load(fh)
        os.unlink(out_json)
        php = report["languages"]["php"]
        self.assertEqual(php["units"], 2)
        total = php["unit_loc"]
        size = {r["above"]: r for r in php["unit_size"]}
        self.assertEqual(total, nloc(40) + nloc(5))
        self.assertAlmostEqual(size[30]["share"], round(nloc(40) / total, 4))
        self.assertFalse(size[30]["ok"])
        self.assertEqual(size[60]["share"], 0)
        self.assertIn("[gate-122] sig-maintainability: report: 2 unit(s) in 1 file(s), languages php", out)
        self.assertIn("| php | 2 |", out)

    def test_no_measured_file_is_exit_4(self):
        self.repo.write("README.md", "x\n")
        self.repo.commit("base")
        rc, out = run("report", self.repo.dir)
        self.assertEqual(rc, 4, out)


class Structure(unittest.TestCase):
    def test_violation_degree_direct_cycle_takes_the_lighter_line(self):
        degree, kinds, _ex = sig.violation_degree({("A", "B"): 1, ("B", "A"): 10})
        self.assertEqual(kinds, {"cyclic": 1})
        self.assertAlmostEqual(degree, round(1 / 11, 4))

    def test_violation_degree_indirect_cycle(self):
        # Guidance figure 10: A->B 10, B->C 8, C->D 3, D->A 15, no direct pair.
        degree, kinds, examples = sig.violation_degree({("A", "B"): 10, ("B", "C"): 8, ("C", "D"): 3, ("D", "A"): 15})
        self.assertEqual(kinds, {"indirect-cyclic": 1})
        self.assertIn("C -> D (indirect-cyclic)", examples)

    def test_violation_degree_transitive(self):
        # Guidance figure 11 shape: B->C->D and a lighter direct B->D; D has an outgoing line.
        lines = {("B", "C"): 10, ("C", "D"): 14, ("B", "D"): 1, ("D", "E"): 18}
        degree, kinds, examples = sig.violation_degree(lines)
        self.assertEqual(kinds, {"transitive": 1})
        self.assertIn("B -> D (transitive)", examples)
        # Heavier than the path it bypasses: not a violation.
        _d, kinds, _e = sig.violation_degree({**lines, ("B", "D"): 50})
        self.assertEqual(kinds, {})

    def test_component_root_descends_into_the_dominant_directory(self):
        # lib/Service holding 71% of lib/ (filinq) must not become the root.
        files = [f"lib/Service/X{i}.php" for i in range(71)] + [f"lib/Db/X{i}.php" for i in range(28)] + ["lib/AppInfo.php"]
        root, comp = sig.component_of_factory(files)
        self.assertEqual(root, "lib")
        self.assertEqual(comp("lib/Service/X1.php"), "Service")
        self.assertEqual(comp("lib/AppInfo.php"), "(root)")

    def test_component_root_in_a_python_service_and_modules_outside_it(self):
        files = ["src/__init__.py", "src/api/main.py", "src/api/routers/a.py", "src/api/routers/b.py",
                 "src/api/utils/c.py", "src/api/utils/d.py", "src/api/utils/e.py", "src/api/utils/f.py",
                 "src/api/services/g.py", "src/api/services/h.py", "scripts/run.py", "api.py"]
        root, comp = sig.component_of_factory(files)
        self.assertEqual(root, "src/api")
        self.assertEqual(comp("src/api/routers/a.py"), "routers")
        self.assertEqual(comp("src/api/main.py"), "(root)")
        self.assertEqual(comp("scripts/run.py"), "scripts")
        self.assertEqual(comp("api.py"), "(top)")
        self.assertEqual(comp("src/__init__.py"), "src")

    def test_php_and_python_dependencies(self):
        repo = Repo()
        try:
            repo.write("lib/Service/A.php", "<?php\nnamespace OCA\\Fx\\Service;\nuse OCA\\Fx\\Db\\{Thing, Other as O};\nclass A { public function f(B $b): Thing { return new Thing(); } }\n")
            repo.write("lib/Service/B.php", "<?php\nnamespace OCA\\Fx\\Service;\nclass B {}\n")
            repo.write("lib/Db/Thing.php", "<?php\nnamespace OCA\\Fx\\Db;\nclass Thing {}\n")
            repo.write("lib/Db/Other.php", "<?php\nnamespace OCA\\Fx\\Db;\n// mentions \\OCA\\Fx\\Service\\A in a comment only\nclass Other {}\n")
            files = ["lib/Service/A.php", "lib/Service/B.php", "lib/Db/Thing.php", "lib/Db/Other.php"]
            deps = sig.php_dependencies(repo.dir, files)
            self.assertEqual(deps["lib/Service/A.php"], {"lib/Service/B.php", "lib/Db/Thing.php", "lib/Db/Other.php"})
            self.assertEqual(deps["lib/Db/Other.php"], set())

            repo.write("src/api/__init__.py", "")
            repo.write("src/api/main.py", "from .routers import documents\nfrom src.api.utils.crypto import encrypt\nimport os\n")
            repo.write("src/api/routers/__init__.py", "")
            repo.write("src/api/routers/documents.py", "from ..utils import crypto\n")
            repo.write("src/api/utils/__init__.py", "")
            repo.write("src/api/utils/crypto.py", "def encrypt(x):\n    return x\n")
            py = ["src/api/__init__.py", "src/api/main.py", "src/api/routers/__init__.py", "src/api/routers/documents.py",
                  "src/api/utils/__init__.py", "src/api/utils/crypto.py"]
            deps = sig.python_dependencies(repo.dir, py)
            self.assertEqual(deps["src/api/main.py"], {"src/api/routers/documents.py", "src/api/utils/crypto.py"})
            self.assertEqual(deps["src/api/routers/documents.py"], {"src/api/utils/crypto.py"})
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
