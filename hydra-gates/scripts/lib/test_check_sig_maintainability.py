#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-122's checker (check_sig_maintainability.py), rule by rule.

  1. UNITS: lizard's PHP parameter count is replaced by the unique $names;
     Python `self`/`cls` is not a parameter; a file lizard raises on is listed
     as skipped and the rest is still measured. A Vue file is read from its
     <script> blocks with the file's own line numbers, and get()/set() method
     shorthand no longer hides a file's units (fixtures in
     scripts/test-fixtures/sig-vue-units/).
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
  6. PROFILES: four-star is the v18.1 guidance; five-star is the derived
     5-star band, stricter than four-star on every check; a share between the
     two passes four-star and misses five-star; every report row carries the
     star level its share earns (5 to 1, "<4" for independence and
     entanglement below 4 stars); HYDRA_GATE_SIG_PROFILE picks
     the profile, --profile overrides it, four-star is the default, and an
     unknown profile is exit 2.
  7. RATING: the interpolation reproduces the worked example of Alves,
     Correia and Visser 2011 (ArgoUML, 2.68); p = 1 is the plain mean of the
     sub-characteristics and p = -1 is never higher; levers are ordered by
     their gain on a fixture; a language with no code, a single language,
     and a report without independence or entanglement are rated; a report
     carries the estimate.

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

    def test_code_lines_skip_licence_headers_and_comments(self):
        php = "<?php\n/**\n * SPDX-License-Identifier: EUPL-1.2\n */\n\ndeclare(strict_types=1);\n// note\n$a = 1; // end\n"
        self.assertEqual(sig.code_lines(php, "php"), {1, 6, 8})
        vue = ("<!--\n  SPDX-License-Identifier: EUPL-1.2\n  - copyright\n-->\n<template>\n"
               "\t<!-- one line -->\n\t<div />\n\t<!-- open\n\tclose --> <span />\n</template>\n")
        self.assertEqual(sig.code_lines(vue, "vue"), {5, 7, 9, 10})

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


VUE_FIXTURES = os.path.join(os.path.dirname(HERE), "test-fixtures", "sig-vue-units")


class VueAndAccessorUnits(unittest.TestCase):
    """Each fixture holds one pattern that once made lizard read a file as
    zero units, or number its units from the <script> tag instead of the file.
    Expected: (name, start, end, McCabe, params) in the file's own line numbers."""

    def setUp(self):
        self.reader = sig.UnitReader(LIZARD)

    def units(self, name):
        lang = sig.LANG_OF_EXT[os.path.splitext(name)[1]]
        with open(os.path.join(VUE_FIXTURES, name), encoding="utf-8") as fh:
            src = fh.read()
        got = [(u["name"], u["start"], u["end"], u["ccn"], u["params"])
               for u in self.reader.units(name, lang, src)]
        self.assertEqual(self.reader.skipped, [])
        return got

    def test_plain_sfc_units_carry_the_file_line_numbers(self):
        self.assertEqual(self.units("control-plain.vue"),
                         [("label", 13, 18, 2, 2), ("reset", 19, 21, 1, 0)])

    def test_inline_arrow_handler_in_the_template(self):
        self.assertEqual(self.units("arrow-handler.vue"),
                         [("update", 18, 23, 2, 1), ("reset", 24, 26, 1, 0)])

    def test_apostrophe_in_a_template_comment(self):
        self.assertEqual(self.units("comment-apostrophe.vue"),
                         [("count", 16, 21, 2, 1), ("clear", 22, 24, 1, 0)])

    def test_quotes_and_backticks_in_the_header_comment(self):
        self.assertEqual(self.units("header-apostrophe.vue"),
                         [("status", 15, 20, 2, 1), ("refresh", 21, 23, 1, 0)])

    def test_computed_get_set_shorthand(self):
        self.assertEqual(self.units("computed-get-set.vue"),
                         [("get", 14, 16, 1, 0), ("set", 17, 22, 2, 1), ("after", 26, 28, 2, 1)])

    def test_script_setup_with_typescript_and_a_second_script_block(self):
        got = self.units("script-setup-ts.vue")
        self.assertIn(("shared", 14, 16, 1, 2), got)
        self.assertIn(("pick", 24, 29, 2, 2), got)
        self.assertFalse([u for u in got if u[1] < 14], "a unit was read from the template")

    def test_accessor_shorthand_in_plain_javascript(self):
        self.assertEqual(self.units("accessor-shorthand.js"),
                         [("get", 4, 6, 1, 0), ("set", 7, 11, 2, 1), ("after", 12, 14, 1, 1)])

    def test_style_and_template_are_not_script(self):
        text, _ext = sig.vue_script("<template>\n\t<p>a => b</p>\n</template>\n<script>\nconst a = 1\n</script>\n"
                                    "<style>\np > a { color: red; }\n</style>\n")
        self.assertEqual(text.splitlines(), ["", "", "", "", "const a = 1", "", "", "", ""])

    def test_script_end_tags_with_whitespace_attributes_or_capitals(self):
        for end in ("</script >", "</SCRIPT\n>", "</script\t\n bar>"):
            with self.subTest(end=end):
                src = f"<script>\nconst a = 1\n{end}\n<template>\n\t<p>a => b</p>\n</template>\n<script setup>\nconst b = 2\n</script>\n"
                text, _ext = sig.vue_script(src)
                self.assertEqual(text.count("\n"), src.count("\n"))
                self.assertEqual([line for line in text.splitlines() if line], ["const a = 1", "const b = 2"])


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

    def with_twin_on_base(self):
        """Base gains lib/Service/Twin.php, a clone of Legacy::copyOne's block."""
        self.repo.git("checkout", "-q", "base")
        self.repo.write("lib/Service/Twin.php", php_class("Twin", [
            php_method("copyTwo", lines=1, tag="y").replace("        return 0;", DUP_BLOCK + "        return 0;")]))
        self.repo.commit("base with an existing clone")
        self.repo.git("checkout", "-q", "-B", "change", "base")

    def move(self, old, new, namespace):
        os.makedirs(os.path.join(self.repo.dir, os.path.dirname(new)), exist_ok=True)
        self.repo.git("mv", old, new)
        self.edit("namespace OCA\\Fx\\Service;", f"namespace {namespace};", rel=new)

    def test_a_moved_file_adds_no_findings(self):
        # openregister#5519: 63 classes moved to lib/Search, and every line of
        # every moved file counted as added, so existing clones and long units
        # came back as 71 new findings.
        self.with_twin_on_base()
        self.move("lib/Service/Twin.php", "lib/Search/Twin.php", "OCA\\Fx\\Search")
        self.move("lib/Service/Legacy.php", "lib/Search/Legacy.php", "OCA\\Fx\\Search")
        rc, out = self.ratchet()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("duplicated fragment", out)
        self.assertIn("checked 0 changed unit(s) in 2 file(s), 0 finding(s)", out)

    def test_a_unit_made_worse_in_a_moved_file_is_new(self):
        self.move("lib/Service/Legacy.php", "lib/Search/Legacy.php", "OCA\\Fx\\Search")
        self.edit("$a5 = 5 + strlen('abig');", "$a5 = 5 + strlen('abig');\n        $grow = 1;",
                  rel="lib/Search/Legacy.php")
        rc, out = self.ratchet()
        self.assertEqual(rc, 1, out)
        self.assertIn(f"lib/Search/Legacy.php:6 Legacy::big: NLOC > 60: {nloc(71)} (was {nloc(70)})", out)
        self.assertIn("FAIL: 1 finding(s)", out)

    def test_a_clone_added_to_a_moved_file_is_new(self):
        self.move("lib/Service/Legacy.php", "lib/Search/Legacy.php", "OCA\\Fx\\Search")
        self.edit("class Legacy\n{\n", "class Legacy\n{\n" + php_method("copyThree", lines=1, tag="w").replace(
            "        return 0;", DUP_BLOCK + "        return 0;"), rel="lib/Search/Legacy.php")
        rc, out = self.ratchet()
        self.assertEqual(rc, 1, out)
        self.assertIn("duplicated fragment of 6+ lines", out)

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

    def test_duplication_counts_every_later_copy_of_six_code_lines(self):
        block = lambda tag: php_method("copy", lines=1, tag=tag).replace("        return 0;", DUP_BLOCK + "        return 0;")
        self.repo.write("lib/Service/A.php", php_class("A", [block("a")]))
        self.repo.write("lib/Service/B.php", php_class("B", [block("b")]))
        self.repo.write("lib/Service/C.php", php_class("C", [php_method("other", lines=9, tag="c")]))
        self.repo.commit("base")
        out_json = os.path.join(self.repo.dir, "..", os.path.basename(self.repo.dir) + "-dup.json")
        rc, out = run("report", self.repo.dir, "--json", out_json)
        self.assertEqual(rc, 0, out)
        with open(out_json) as fh:
            dup = json.load(fh)["languages"]["php"]
        os.unlink(out_json)
        # B repeats A's nine $shared lines plus the closing return, brace and class brace.
        self.assertGreaterEqual(dup["duplication"]["redundant_lines"], 9)
        self.assertLess(dup["duplication"]["redundant_lines"], 16)
        self.assertFalse(dup["duplication"]["ok"])
        self.assertIn("duplication_jscpd", dup)

    def test_no_measured_file_is_exit_4(self):
        self.repo.write("README.md", "x\n")
        self.repo.commit("base")
        rc, out = run("report", self.repo.dir)
        self.assertEqual(rc, 4, out)


class Profiles(unittest.TestCase):
    """A fixture whose PHP has 44 of 242 unit lines (18.2%) in a unit over 30
    lines: inside the 4-star limit (24.2%), outside the 5-star one (17.0%)."""

    def setUp(self):
        self.repo = Repo()
        methods = [php_method("long", lines=40, tag="a")]
        methods += [php_method(f"s{i}", lines=5, tag=f"b{i}") for i in range(22)]
        self.repo.write("lib/Service/A.php", php_class("A", methods))
        self.repo.commit("base")
        self.saved_env = os.environ.pop("HYDRA_GATE_SIG_PROFILE", None)

    def tearDown(self):
        os.environ.pop("HYDRA_GATE_SIG_PROFILE", None)
        if self.saved_env is not None:
            os.environ["HYDRA_GATE_SIG_PROFILE"] = self.saved_env
        self.repo.close()

    def report(self, *extra):
        out_json = os.path.join(self.repo.dir, "..", os.path.basename(self.repo.dir) + "-profile.json")
        rc, out = run("report", self.repo.dir, "--json", out_json, *extra)
        self.assertEqual(rc, 0, out)
        with open(out_json) as fh:
            report = json.load(fh)
        os.unlink(out_json)
        return report, out

    def above_30(self, report):
        return {r["above"]: r for r in report["languages"]["php"]["unit_size"]}[30]

    def test_four_star_is_the_v18_1_guidance(self):
        four = sig.PROFILES["four-star"]
        self.assertEqual(four["limits"], {
            "unit_size": [(15, .480), (30, .242), (60, .091)],
            "unit_complexity": [(5, .207), (10, .075), (25, .011)],
            "unit_interfacing": [(2, .154), (4, .034), (6, .009)],
            "module_coupling": [(10, .097), (20, .053), (50, .018)],
        })
        self.assertEqual((four["duplication"], four["independence_min"], four["entanglement"]), (.058, .945, .075))
        self.assertIn("v18.1", four["source"])

    def test_every_band_is_stricter_than_the_one_below_it(self):
        for prop, bands in sig.STAR_BANDS.items():
            for hi, lo in ((5, 4), (4, 3), (3, 2)):
                for a, b in zip(*(bands[x] if isinstance(bands[x], tuple) else (bands[x],) for x in (hi, lo))):
                    self.assertLess(a, b, f"{prop} {hi} vs {lo}")
        five = sig.PROFILES["five-star"]
        self.assertEqual(five["limits"]["unit_size"], [(15, .360), (30, .170), (60, .055)])
        self.assertEqual((five["duplication"], five["independence_min"], five["entanglement"]), (.035, .973, .0375))

    def test_stars_of_each_band_edge(self):
        for share, want in ((.360, 5), (.3601, 4), (.480, 4), (.4801, 3), (.630, 3), (.847, 2), (.8471, 1)):
            self.assertEqual(sig.stars_of("unit_size", share, 0), want, share)
        self.assertEqual(sig.stars_of("unit_complexity", .006, 2), 4)
        self.assertEqual(sig.stars_of("unit_complexity", .012, 2), 3)
        for share, want in ((.035, 5), (.058, 4), (.116, 3), (.230, 2), (.231, 1)):
            self.assertEqual(sig.stars_of("duplication", share), want, share)

    def test_independence_and_entanglement_have_no_band_under_four(self):
        self.assertEqual(sig.stars_of("component_independence", .973), 5)
        self.assertEqual(sig.stars_of("component_independence", .945), 4)
        self.assertEqual(sig.stars_of("component_independence", .10), "<4")
        self.assertEqual(sig.stars_of("component_entanglement", .0375), 5)
        self.assertEqual(sig.stars_of("component_entanglement", .075), 4)
        self.assertEqual(sig.stars_of("component_entanglement", .9), "<4")

    def test_report_rows_carry_their_stars(self):
        report, out = self.report()
        php = report["languages"]["php"]
        self.assertEqual(self.above_30(report)["stars"], 4)
        self.assertEqual(php["duplication"]["stars"], 5)
        self.assertIn(php["unit_size"][0]["stars"], (1, 2, 3, 4, 5))
        self.assertEqual(php["unit_size"][1]["loc"], 44)
        rating = report["rating"]
        self.assertLessEqual(rating["overall"]["range"][0], rating["overall"]["range"][1])
        self.assertIn("Estimated SIG maintainability rating", out)
        self.assertIn("4★", out)

    def test_default_is_four_star(self):
        report, out = self.report()
        self.assertEqual(report["profile"], "four-star")
        row = self.above_30(report)
        self.assertAlmostEqual(row["share"], round(nloc(40) / (nloc(40) + 22 * nloc(5)), 4))
        self.assertEqual(row["limit"], .242)
        self.assertTrue(row["ok"])
        self.assertEqual(report["languages"]["php"]["duplication"]["limit"], .058)
        self.assertIn("4-star checks met", out)

    def test_five_star_flag_holds_the_same_code_to_the_five_star_band(self):
        report, out = self.report("--profile", "five-star")
        self.assertEqual(report["profile"], "five-star")
        row = self.above_30(report)
        self.assertEqual(row["limit"], .170)
        self.assertFalse(row["ok"])
        self.assertEqual(report["languages"]["php"]["duplication"]["limit"], .035)
        self.assertEqual(report["structure"]["php"]["component_independence"]["limit_min"], .973)
        self.assertEqual(report["structure"]["php"]["component_entanglement"]["limit"], .0375)
        self.assertIn("5-star checks met; missed: ", out)
        self.assertIn("php unit_size >30", out)
        self.assertIn("against the 5-star limit", out)

    def test_env_var_selects_the_profile_and_the_flag_overrides_it(self):
        os.environ["HYDRA_GATE_SIG_PROFILE"] = "five-star"
        report, _out = self.report()
        self.assertEqual(report["profile"], "five-star")
        report, _out = self.report("--profile", "four-star")
        self.assertEqual(report["profile"], "four-star")

    def test_unknown_profile_is_exit_2(self):
        rc, out = run("report", self.repo.dir, "--profile", "six-star")
        self.assertEqual(rc, 2, out)
        self.assertIn("unknown profile 'six-star'", out)

    def test_the_ratchet_ignores_the_profile(self):
        os.environ["HYDRA_GATE_SIG_PROFILE"] = "six-star"
        self.repo.write("lib/Service/B.php", php_class("B", [php_method("small", lines=3)]))
        self.repo.commit("head")
        rc, out = run("ratchet", self.repo.dir, "--base-ref", "HEAD~1")
        self.assertEqual(rc, 0, out)
        self.assertIn("0 finding(s)", out)


class Structure(unittest.TestCase):
    def test_connected_pairs_counts_a_two_way_pair_once(self):
        with tempfile.TemporaryDirectory() as app:
            names = ("lib/A/a.php", "lib/B/b.php", "lib/C/c.php")
            for name in names:
                os.makedirs(os.path.dirname(os.path.join(app, name)), exist_ok=True)
                with open(os.path.join(app, name), "w") as fh:
                    fh.write("<?php\nclass X {}\n")
            deps = {names[0]: {names[1]}, names[1]: {names[0]}, names[2]: {names[1]}}
            e = sig.structure(app, {n: "php" for n in names}, deps)["component_entanglement"]
        self.assertEqual((e["communication_lines"], e["connected_pairs"], e["connected_components"]), (3, 2, 3))

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

    def test_components_from_scope_reads_top_level_directories(self):
        with tempfile.TemporaryDirectory() as app:
            with open(os.path.join(app, "sigrid.yaml"), "w") as fh:
                fh.write('component_base_dirs: [""]\n')
            self.assertTrue(sig.sigrid_yaml_top_level_components(app))
            with open(os.path.join(app, "sigrid.yaml"), "w") as fh:
                fh.write("component_base_dirs: [lib]\n")
            self.assertFalse(sig.sigrid_yaml_top_level_components(app))
        self.assertEqual(sig.top_level_component_of("lib/Service/A.php"), "lib")
        self.assertEqual(sig.top_level_component_of("index.php"), "Root files")

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

            repo.write("lib/Db/Mapper.php", "<?php\nnamespace OCA\\Fx\\Db;\nclass Mapper {}\n")
            repo.write("lib/Db/Mapper/Handler.php", "<?php\nnamespace OCA\\Fx\\Db\\Mapper;\nclass Handler {}\n")
            repo.write("lib/Db/Mapper/Caller.php", "<?php\nnamespace OCA\\Fx\\Db\\Mapper;\nclass Caller { public function f(\\OCA\\Fx\\Db\\Mapper $m): void {} }\n")
            sub = ["lib/Db/Mapper.php", "lib/Db/Mapper/Handler.php", "lib/Db/Mapper/Caller.php"]
            deps = sig.php_dependencies(repo.dir, sub)
            self.assertEqual(deps["lib/Db/Mapper/Handler.php"], set())
            self.assertEqual(deps["lib/Db/Mapper/Caller.php"], {"lib/Db/Mapper.php"})

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


def rated_report(langs, structure=None):
    """A report with the fields rating_inputs() reads. `langs` maps a language
    to (unit_loc, size, complexity, interfacing, (code_lines, redundant)),
    each property a triple of cumulative shares."""
    out = {"languages": {}, "structure": {}}
    for lang, (loc, size, ccn, params, dup) in langs.items():
        out["languages"][lang] = {
            "unit_loc": loc,
            "unit_size": [{"share": x} for x in size],
            "unit_complexity": [{"share": x} for x in ccn],
            "unit_interfacing": [{"share": x} for x in params],
            "duplication": {"code_lines": dup[0], "redundant_lines": dup[1]},
        }
    for lang, (loc, coupling, hidden, degree) in (structure or {}).items():
        out["structure"][lang] = {"module_loc": loc, "module_coupling": [{"share": x} for x in coupling],
                                  "component_independence": {"hidden_share": hidden},
                                  "component_entanglement": {"violation_degree": degree}}
    return out


GOOD = (10000, (.30, .10, .02), (.10, .03, .0), (.10, .02, .0), (10000, 200))


def crossing_sfc(name):
    """A Vue file that shares with its twins only the lines around the
    script/style boundary: 3 code lines before it, 3 after."""
    return (f"<script>\nconst {name} = 1\nexport const {name}2 = {name}\n"
            "shared.first()\nshared.second()\nshared.third()\n</script>\n\n"
            "<style scoped>\n.same-one { color: red; }\n.same-two { color: red; }\n.same-three { color: red; }\n"
            f".{name} {{ color: blue; }}\n</style>\n")


class VuePieces(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="gate122-vue-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def profile(self, texts):
        for rel, text in texts.items():
            with open(os.path.join(self.dir, rel), "w") as fh:
                fh.write(text)
        return sig.duplication_profile(self.dir, [], {rel: "vue" for rel in texts})["vue"][0]

    def pieces(self, text):
        lines = text.splitlines()
        return [[lines[n - 1].strip() for n in piece]
                for piece in sig.sfc_pieces(lines, sig.code_lines(text, "vue"))]

    def test_a_window_does_not_span_script_and_style(self):
        row = self.profile({"A.vue": crossing_sfc("a"), "B.vue": crossing_sfc("b")})
        self.assertEqual(row["redundant_lines"], 0)

    def test_the_same_lines_are_a_clone_when_no_block_boundary_separates_them(self):
        # Control: the shared lines of crossing_sfc() in one block, so the fixture bites.
        shared = ("shared.first()\nshared.second()\nshared.third()\n"
                  ".same-one { color: red; }\n.same-two { color: red; }\n.same-three { color: red; }\n")
        row = self.profile({"A.vue": f"<script>\nconst a = 1\n{shared}</script>\n",
                            "B.vue": f"<script>\nconst b = 2\n{shared}</script>\n"})
        self.assertEqual(row["redundant_lines"], 6)

    def test_a_clone_inside_one_block_still_counts(self):
        body = "".join(f"  step{i}()\n" for i in range(6))
        row = self.profile({"A.vue": f"<script>\nconst a = 1\n{body}</script>\n",
                            "B.vue": f"<script>\nconst b = 2\n{body}</script>\n"})
        self.assertEqual(row["redundant_lines"], 6)

    def test_a_window_does_not_span_template_and_script(self):
        tail = "".join(f"  <p>{i}</p>\n" for i in range(3))
        head = "".join(f"step{i}()\n" for i in range(3))
        row = self.profile({"A.vue": f"<template>\n  <a />\n{tail}</template>\n<script>\n{head}a()\n</script>\n",
                            "B.vue": f"<template>\n  <b />\n{tail}</template>\n<script>\n{head}b()\n</script>\n"})
        self.assertEqual(row["redundant_lines"], 0)

    def test_blocks_are_pieces_and_their_tags_belong_to_none(self):
        text = ("<template>\n  <div>\n    <template #x>\n      <a />\n    </template>\n  </div>\n</template>\n"
                "<script setup>\nconst a = 1\n</script>\n<style src=\"./a.css\"></style>\n"
                "<style lang=\"scss\" scoped>\n.a { top: 0; }\n</style>\n")
        self.assertEqual(self.pieces(text), [
            ["<div>", "<template #x>", "<a />", "</template>", "</div>"], ["const a = 1"], [".a { top: 0; }"]])

    def test_boundaries_hold_when_the_code_lines_leave_the_tags_out(self):
        lines = ["<script>", "a()", "</script>", "<style>", ".a { top: 0; }", "</style>"]
        self.assertEqual(sig.sfc_pieces(lines, {2, 5}), [[2], [5]])

    def test_other_languages_keep_one_piece(self):
        lines = [f"$a{i} = {i};" for i in range(8)]
        self.assertEqual(len(list(sig.dup_windows(lines, set(range(1, 9)), "php"))), 3)

    def test_the_denominator_keeps_every_code_line(self):
        row = self.profile({"A.vue": crossing_sfc("a")})
        self.assertEqual(row["code_lines"], len(sig.code_lines(crossing_sfc("a"), "vue")))


class VueAssumption(unittest.TestCase):
    def report(self, rel, text):
        repo = Repo()
        self.addCleanup(repo.close)
        repo.write(rel, text)
        repo.commit("app")
        return sig.build_report(repo.dir, LIZARD, None)

    def test_a_report_with_vue_states_the_assumption(self):
        report = self.report("src/A.vue", crossing_sfc("a"))
        self.assertEqual(report["assumptions"], [sig.VUE_PIECES_ASSUMPTION])
        self.assertIn(f"Assumption: {sig.VUE_PIECES_ASSUMPTION}", sig.markdown(report))
        self.assertIn("until a real Sigrid scan confirms it", sig.VUE_PIECES_ASSUMPTION)

    def test_a_report_without_vue_states_none(self):
        report = self.report("lib/A.php", php_class("A", [php_method("a")]))
        self.assertEqual(report["assumptions"], [])
        self.assertNotIn("Assumption:", sig.markdown(report))


class Rating(unittest.TestCase):
    def test_interpolation_reproduces_alves_2011_argouml(self):
        # Table III (b), McCabe: cumulative caps for moderate / high / very high.
        table = {5: (.179, .099, .033), 4: (.234, .169, .067), 3: (.313, .238, .106), 2: (.391, .298, .167)}
        profile = (.258, .187, .099)
        ratings = [sig.interpolate(v, {lvl: table[lvl][i] for lvl in table}) for i, v in enumerate(profile)]
        self.assertAlmostEqual(min(ratings), 2.68, places=2)
        self.assertEqual(ratings.index(min(ratings)), 2)

    def test_interpolation_edges(self):
        caps = sig.rating_caps("duplication")
        self.assertEqual(sig.interpolate(0, caps), 5.5)
        self.assertAlmostEqual(sig.interpolate(caps[4], caps), 3.5)
        self.assertAlmostEqual(sig.interpolate(caps[2], caps), 1.5)
        self.assertAlmostEqual(sig.interpolate(1.0, caps), 0.5)
        self.assertAlmostEqual(sig.interpolate((caps[2] + 1) / 2, caps), 1.0)
        values = [sig.interpolate(x / 1000, caps) for x in range(1001)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_p1_is_the_plain_mean_and_harmonic_is_never_higher(self):
        self.assertAlmostEqual(sig.power_mean([1.0, 2.0, 4.5], 1), 2.5)
        self.assertAlmostEqual(sig.power_mean([1.0, 2.0, 4.0], -1), 3 / (1 + .5 + .25))
        report = rated_report({"php": GOOD, "vue": (2000, (.6, .4, .2), (.3, .2, .05), (.3, .1, .03), (3000, 900))},
                              {"php": (8000, (.05, .02, .01), .80, .10)})
        rated = sig.rate_inputs(sig.rating_inputs(report))
        subs = list(rated["subcharacteristics"].values())
        self.assertAlmostEqual(rated["overall"][1], sum(subs) / len(subs))
        self.assertLessEqual(rated["overall"][-1], rated["overall"][1])
        modifiability = [rated["properties"][p]["rating"] for p in ("duplication", "unit_complexity", "module_coupling")]
        self.assertAlmostEqual(rated["subcharacteristics"]["modifiability"], sum(modifiability) / 3)

    def test_languages_are_weighted_by_their_code(self):
        report = rated_report({"php": GOOD, "vue": (2000, (.6, .4, .2), (.3, .2, .05), (.3, .1, .03), (3000, 900))})
        prop = sig.rate_inputs(sig.rating_inputs(report))["properties"]["unit_size"]
        php, vue = prop["languages"]["php"]["rating"], prop["languages"]["vue"]["rating"]
        self.assertAlmostEqual(prop["rating"], (php * 10000 + vue * 2000) / 12000)

    def test_a_language_without_code_carries_no_weight(self):
        alone = sig.rate_inputs(sig.rating_inputs(rated_report({"php": GOOD})))
        empty = (0, (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0))
        both = sig.rate_inputs(sig.rating_inputs(rated_report({"php": GOOD, "typescript": empty})))
        self.assertEqual(alone["overall"], both["overall"])
        self.assertNotIn("typescript", both["properties"]["unit_size"]["languages"])

    def test_a_single_language_is_its_own_property_rating(self):
        rated = sig.rate_inputs(sig.rating_inputs(rated_report({"php": GOOD})))
        for prop in ("unit_size", "unit_complexity", "unit_interfacing", "duplication"):
            self.assertEqual(rated["properties"][prop]["rating"], rated["properties"][prop]["languages"]["php"]["rating"])

    def test_no_structure_leaves_independence_and_entanglement_out(self):
        rated = sig.rate_inputs(sig.rating_inputs(rated_report({"php": GOOD})))
        for prop in ("module_coupling", "component_independence", "component_entanglement"):
            self.assertIsNone(rated["properties"][prop]["rating"])
        self.assertIsNone(rated["subcharacteristics"]["modularity"])
        self.assertEqual(rated["subcharacteristics"]["testability"], rated["properties"]["unit_complexity"]["rating"])
        self.assertIsNotNone(rated["overall"][-1])

    def test_independence_and_entanglement_are_rated_below_four(self):
        report = rated_report({"php": GOOD}, {"php": (10000, (0, 0, 0), .50, .20)})
        self.assertEqual(sig.stars_of("component_independence", .50), "<4")
        props = sig.rate_inputs(sig.rating_inputs(report))["properties"]
        self.assertLess(props["component_independence"]["rating"], 1.5)
        self.assertGreater(props["component_independence"]["rating"], 0.5)
        self.assertLess(props["component_entanglement"]["rating"], 2.5)
        self.assertGreater(props["component_entanglement"]["rating"], 1.5)

    def test_levers_are_ordered_by_their_gain(self):
        # php duplication is the worst property (30% redundant, 1 star), but on
        # the flat 1-star slope 1,000 lines move it little; vue unit size and
        # php unit complexity sit on steeper slopes and lead under both exponents.
        bad_dup = (10000, (.30, .10, .02), (.10, .03, .0), (.10, .02, .0), (10000, 3000))
        report = rated_report({"php": bad_dup, "vue": (1500, (.6, .4, .2), (.1, .03, 0), (.1, .02, 0), (1500, 0))},
                              {"php": (10000, (0, 0, 0), 1.0, .05)})
        inputs = sig.rating_inputs(report)
        self.assertLess(sig.rate_inputs(inputs)["properties"]["duplication"]["rating"], 2)
        levers = sig.levers(inputs)
        order = [(lv["property"], lv["language"]) for lv in levers]
        self.assertEqual(set(order[:2]), {("unit_size", "vue"), ("unit_complexity", "php")})
        self.assertEqual(order[4], ("duplication", "php"))
        self.assertTrue(levers[0]["sure"] and levers[1]["sure"])
        self.assertFalse(levers[4]["sure"])
        for p in sig.EXPONENTS:
            gains = [lv["gain_per_kloc"][p] for lv in sorted(levers, key=lambda lv: lv["rank"][p])]
            self.assertEqual(gains, sorted(gains, reverse=True))
            self.assertTrue(all(g > 0 for g in gains))
        for lv in levers:
            self.assertEqual(lv["sure"], max(lv["rank"].values()) <= sig.SURE_TOP)
        vue = next(lv for lv in levers if order[levers.index(lv)] == ("unit_size", "vue"))
        self.assertEqual(vue["fixed_loc"], 900)
        self.assertNotIn("component_entanglement", {p for p, _l in order})

    def test_loc_for_half_star_is_the_fewest_lines(self):
        report = rated_report({"php": (10000, (.30, .10, .02), (.10, .03, .0), (.10, .02, .0), (10000, 1500))})
        inputs = sig.rating_inputs(report)
        before = sig.rate_inputs(inputs)["properties"]["duplication"]["rating"]
        n = sig.loc_for_half_star(inputs, "duplication", "php", before)
        self.assertIsNotNone(n)

        def after(k):
            fixed = sig.with_entry(inputs, "duplication", "php", sig.fix_loc("duplication", inputs["duplication"]["php"], k))
            return sig.rate_inputs(fixed)["properties"]["duplication"]["rating"]
        self.assertGreaterEqual(after(n), before + 0.5 - 1e-9)
        self.assertLess(after(n - 1), before + 0.5 - 1e-9)

    def test_fixing_takes_the_worst_band_first(self):
        entry = {"loc": 1000, "above": [500, 300, 100]}
        self.assertEqual(sig.fix_loc("unit_size", entry, 150), {"loc": 1000, "above": [350, 150, 0]})
        self.assertEqual(sig.fix_loc("duplication", {"loc": 1000, "above": [100]}, 40), {"loc": 960, "above": [60]})


if __name__ == "__main__":
    unittest.main(verbosity=1)
