#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-123's five-star file floor (sig_file_floor.py, through
check_sig_floor.py check), on real git histories.

  1. RULES: a listed file passes at the 5-star bounds and fails on a unit
     over NLOC 15, McCabe 5 or 2 parameters, and on a 6+ line clone.
  2. CLONE LINES: shared `use` / `namespace` / import blocks and
     `}//end name()` markers do not make a clone; other lines still do.
  3. EXEMPTIONS (parameters only): a constructor that only wires its
     dependencies, and a method of an interface in the class's implements
     chain; size and complexity still apply to both.
  4. HONEST LIST: a listed file that is gone fails in both modes, and so does
     removing a path from the list while the file exists.
  5. MODES: diff mode judges only the listed files the change touches or adds
     to the list; full mode judges them all.
  6. VUE: while lizard <= 1.25.0 is pinned, findings in .vue / .js / .ts
     files are warnings and the run passes; a newer pin makes them fail.
  7. RE-RECORD: `write` raises the app floor to the current checks and keeps
     every check already floored.

Run: python3 scripts/lib/test_sig_file_floor.py
"""
import argparse
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
import sig_file_floor as files  # noqa: E402

LIZARD, WHY = sig.load_lizard()
if not LIZARD:
    print(f"FAIL: pinned tools unavailable: {WHY}")
    sys.exit(1)

HEADER = "<?php\n\nnamespace OCA\\Fx\\Service;\n\nuse OCP\\IConfig;\nuse OCP\\IL10N;\nuse OCP\\IUserSession;\n" \
         "use Psr\\Log\\LoggerInterface;\nuse OCP\\AppFramework\\Http;\nuse OCP\\IRequest;\n\n"


def method(name, statements=2, params="int $a", tag="x"):
    body = "".join(f"        $v{i} = {i} + strlen('{tag}{name}{i}');\n" for i in range(statements))
    return f"    public function {name}({params}): int\n    {{\n{body}        return 1;\n    }}//end {name}()\n\n"


def complex_method(name, branches):
    body = "".join(f"        if ($a === {i}) {{ return {i}; }}\n" for i in range(branches))
    return f"    public function {name}(int $a): int\n    {{\n{body}        return 0;\n    }}//end {name}()\n\n"


def php_class(name, members, head="", header=HEADER):
    return f"{header}class {name}{head}\n{{\n" + "".join(members) + "}//end class\n"


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = floor.main(list(argv))
    return rc, buf.getvalue()


class FileFloorCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="gate123-files-")
        self.git("init", "-q", ".")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.write("lib/Service/Good.php", php_class("Good", [method(f"m{i}", tag=f"g{i}") for i in range(3)]))
        self.write("lib/Service/Other.php", php_class("Other", [method(f"o{i}", tag=f"o{i}") for i in range(3)]))
        self.listing(["lib/Service/Good.php"])
        self.commit("app")
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "change")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True, text=True).stdout

    def write(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def listing(self, paths):
        self.write(files.LIST_PATH, "# five-star files\n\n" + "".join(f"{p}  # held\n" for p in paths))

    def commit(self, msg="change"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg)

    def full(self):
        self.commit()
        return run("check", self.dir)

    def diff(self):
        self.commit()
        return run("check", self.dir, "--base-ref", "base")

    def hold(self, rel, text):
        """Write `rel`, list it, and judge every listed file (full mode)."""
        self.write(rel, text)
        self.listing(["lib/Service/Good.php", rel])
        return self.full()


class Rules(FileFloorCase):
    def test_a_listed_file_at_the_bounds_passes_without_an_app_floor(self):
        rc, out = self.full()
        self.assertEqual(rc, 0, out)
        self.assertIn("[gate-123] sig-floor: PASS: 0 floored check(s) held", out)
        self.assertIn("five-star files (full mode): 1 of 1 listed file(s) judged, 0 failure(s)", out)
        self.assertIn(f"lizard {sig.LIZARD_VERSION}", out)

    def test_exactly_15_lines_5_branches_and_2_parameters_pass(self):
        rc, out = self.hold("lib/Service/Edge.php", php_class("Edge", [
            method("size", statements=11, tag="e"), complex_method("branchy", 4),
            method("wide", params="int $a, int $b", tag="w")]))
        self.assertEqual(rc, 0, out)

    def test_a_unit_over_15_lines_fails(self):
        rc, out = self.hold("lib/Service/Long.php", php_class("Long", [method("long", statements=12, tag="l")]))
        self.assertEqual(rc, 1, out)
        self.assertIn("  five-star file lib/Service/Long.php:", out)
        self.assertIn("Long::long: NLOC 16 > 15", out)
        self.assertIn("1 on five-star files", out)

    def test_a_unit_over_mccabe_5_fails(self):
        rc, out = self.hold("lib/Service/Branchy.php", php_class("Branchy", [complex_method("branchy", 5)]))
        self.assertEqual(rc, 1, out)
        self.assertIn("Branchy::branchy: McCabe 6 > 5", out)

    def test_a_unit_with_3_parameters_fails(self):
        rc, out = self.hold("lib/Service/Wide.php", php_class("Wide", [method("wide", params="int $a, int $b, int $c")]))
        self.assertEqual(rc, 1, out)
        self.assertIn("Wide::wide: 3 parameters > 2", out)

    def test_a_block_of_6_lines_copied_from_another_file_fails(self):
        rc, out = self.hold("lib/Service/Copy.php", php_class("Copy", [method("o0", tag="o0")]))
        self.assertEqual(rc, 1, out)
        self.assertIn("duplicated block of 6+ code lines, same as lib/Service/Other.php:", out)

    def test_a_block_repeated_inside_the_file_fails(self):
        block = "".join(f"        $r{i} = strtoupper('{i}');\n" for i in range(6))
        body = f"    public function a(): void\n    {{\n{block}    }}\n\n    public function b(): void\n    {{\n{block}    }}\n"
        rc, out = self.hold("lib/Service/Twice.php", php_class("Twice", [body]))
        self.assertEqual(rc, 1, out)
        self.assertIn("same as lib/Service/Twice.php:", out)


class CloneLines(FileFloorCase):
    def test_shared_use_blocks_and_end_markers_are_not_a_clone(self):
        # Good.php and Other.php share the header, the `}//end` markers and
        # the closing lines; on gate 122's lines alone they would be a clone.
        text = sig.read_text(os.path.join(self.dir, "lib/Service/Good.php"))
        self.assertGreater(len(sig.code_lines(text, "php")), len(files.floor_code_lines(text, "php")))
        rc, out = self.hold("lib/Service/Same.php", php_class("Same", [method("s", tag="s")]))
        self.assertEqual(rc, 0, out)

    def test_a_multi_line_import_block_is_left_out(self):
        text = "import {\n  a,\n  b,\n} from 'x'\nconst y = 1\n"
        self.assertEqual(files.floor_code_lines(text, "javascript"), {5})

    def test_a_bare_closing_brace_still_counts(self):
        self.assertIn(2, files.floor_code_lines("<?php\n}\n}//end x()\n", "php"))
        self.assertNotIn(3, files.floor_code_lines("<?php\n}\n}//end x()\n", "php"))


CTOR_PROMOTED = """    public function __construct(
        private readonly IConfig $config,
        private readonly IL10N $l10n,
        protected LoggerInterface $logger,
    ) {
    }

"""
CTOR_ASSIGNED = """    public function __construct(IConfig $config, IL10N $l10n, IRequest $request, string $appName)
    {
        parent::__construct($appName, $request);
        // wiring only
        $this->config = $config;
        $this->l10n   = $l10n;
    }//end __construct()

"""
CTOR_LOGIC = """    public function __construct(IConfig $config, IL10N $l10n, LoggerInterface $logger)
    {
        $this->config = $config;
        $this->l10n = $l10n;
        $this->logger = $logger;
        $this->name = $config->getSystemValue('x');
    }

"""


class Exemptions(FileFloorCase):
    def test_a_constructor_with_promoted_properties_is_exempt(self):
        rc, out = self.hold("lib/Service/Promoted.php", php_class("Promoted", [CTOR_PROMOTED]))
        self.assertEqual(rc, 0, out)

    def test_a_constructor_that_assigns_and_forwards_its_dependencies_is_exempt(self):
        rc, out = self.hold("lib/Service/Wired.php", php_class("Wired", [CTOR_ASSIGNED], " extends Base"))
        self.assertEqual(rc, 0, out)

    def test_a_constructor_that_does_more_than_wire_is_not_exempt(self):
        rc, out = self.hold("lib/Service/Busy.php", php_class("Busy", [CTOR_LOGIC]))
        self.assertEqual(rc, 1, out)
        self.assertIn("Busy::__construct: 3 parameters > 2", out)

    def test_named_forwarding_and_an_unpacked_services_object_are_wiring(self):
        src = ("<?php\nclass C extends B {\n    public function __construct(string $appName, IRequest $request, S $services)\n"
               "    {\n        parent::__construct(appName: $appName, request: $request);\n"
               "        $this->links = $services->domain->links;\n    }\n}\n")
        unit = {"name": "C::__construct", "start": 3, "end": 7}
        self.assertTrue(files.is_wiring_constructor(unit, src, "php"))
        self.assertFalse(files.is_wiring_constructor(unit, src.replace("->links;", "->links();"), "php"))

    def test_the_exemption_is_detected_in_typescript_and_python(self):
        ts = {"name": "constructor", "start": 2, "end": 5}
        src = "export class S {\n  constructor(private readonly a: A, b: B, c: C) {\n    this.b = b\n    this.c = c;\n  }\n}\n"
        self.assertTrue(files.is_wiring_constructor(ts, src, "typescript"))
        py = {"name": "__init__", "start": 2, "end": 4}
        src = "class P:\n    def __init__(self, a, b, c):\n        self.a = a\n        super().__init__(b, c)\n"
        self.assertTrue(files.is_wiring_constructor(py, src, "python"))
        self.assertFalse(files.is_wiring_constructor(py, src.replace("self.a = a", "self.a = a + 1"), "python"))

    def test_an_exempt_constructor_still_has_the_size_rule(self):
        assigns = "".join(f"        $this->p{i} = $p{i};\n" for i in range(15))
        params = ", ".join(f"int $p{i}" for i in range(15))
        ctor = f"    public function __construct({params})\n    {{\n{assigns}    }}\n\n"
        rc, out = self.hold("lib/Service/Many.php", php_class("Many", [ctor]))
        self.assertEqual(rc, 1, out)
        self.assertIn("Many::__construct: NLOC", out)
        self.assertNotIn("parameters > 2", out)

    def interface_repo(self):
        self.write("lib/Contract/Reader.php", "<?php\nnamespace OCA\\Fx\\Contract;\n\ninterface Reader\n{\n"
                   "    public function read(int $a, int $b, int $c): int;\n}\n")
        self.write("lib/Contract/Store.php", "<?php\nnamespace OCA\\Fx\\Contract;\n\ninterface Store extends Reader\n{\n"
                   "    public function store(int $a, int $b, int $c): int;\n}\n")
        self.write("lib/Service/AbstractStore.php", "<?php\nnamespace OCA\\Fx\\Service;\n\nuse OCA\\Fx\\Contract\\Store;\n\n"
                   "abstract class AbstractStore implements Store\n{\n}\n")

    def test_a_method_of_an_interface_through_an_abstract_parent_is_exempt(self):
        self.interface_repo()
        rc, out = self.hold("lib/Service/Impl.php", php_class("Impl", [
            method("read", params="int $a, int $b, int $c", tag="r"),
            method("store", params="int $a, int $b, int $c", tag="s")], " extends AbstractStore"))
        self.assertEqual(rc, 0, out)

    def test_a_method_the_interfaces_do_not_declare_is_not_exempt(self):
        self.interface_repo()
        rc, out = self.hold("lib/Service/Impl.php", php_class("Impl", [
            method("extra", params="int $a, int $b, int $c", tag="x")], " extends AbstractStore"))
        self.assertEqual(rc, 1, out)
        self.assertIn("Impl::extra: 3 parameters > 2", out)

    def test_an_interface_method_still_has_the_complexity_rule(self):
        self.interface_repo()
        branchy = complex_method("read", 5).replace("(int $a)", "(int $a, int $b, int $c)")
        rc, out = self.hold("lib/Service/Impl.php", php_class("Impl", [branchy], " extends AbstractStore"))
        self.assertEqual(rc, 1, out)
        self.assertIn("Impl::read: McCabe 6 > 5", out)
        self.assertNotIn("parameters > 2", out)

    def test_an_unreadable_interface_counts_for_a_method_marked_inheritdoc(self):
        marked = "    /**\n     * {@inheritDoc}\n     */\n" + method("handle", params="int $a, int $b, int $c", tag="h")
        rc, out = self.hold("lib/Service/Ext.php", php_class("Ext", [marked], " implements \\OCP\\External\\IHandler"))
        self.assertEqual(rc, 0, out)
        rc, out = self.hold("lib/Service/Ext.php", php_class("Ext", [
            method("handle", params="int $a, int $b, int $c", tag="h")], " implements \\OCP\\External\\IHandler"))
        self.assertEqual(rc, 1, out)

    def test_an_interface_composer_maps_into_vendor_is_read(self):
        self.write("vendor/composer/autoload_psr4.php", "<?php\nreturn array(\n"
                   "    'OCP\\\\' => array($vendorDir . '/nextcloud/ocp/OCP'),\n);\n")
        self.write("vendor/nextcloud/ocp/OCP/External/IHandler.php", "<?php\nnamespace OCP\\External;\n\n"
                   "interface IHandler\n{\n    public function handle(int $a, int $b, int $c): int;\n}\n")
        self.write(".gitignore", "vendor/\n")
        rc, out = self.hold("lib/Service/Ext.php", php_class("Ext", [
            method("handle", params="int $a, int $b, int $c", tag="h")], " implements \\OCP\\External\\IHandler"))
        self.assertEqual(rc, 0, out)
        rc, out = self.hold("lib/Service/Ext.php", php_class("Ext", [
            method("other", params="int $a, int $b, int $c", tag="h")], " implements \\OCP\\External\\IHandler"))
        self.assertEqual(rc, 1, out)


class HonestList(FileFloorCase):
    def test_a_listed_file_that_is_gone_fails_in_full_mode(self):
        self.listing(["lib/Service/Good.php", "lib/Service/Gone.php"])
        rc, out = self.full()
        self.assertEqual(rc, 1, out)
        self.assertIn("lib/Service/Gone.php: listed in .sig/five-star-files.txt but does not exist", out)

    def test_a_listed_file_deleted_by_the_change_fails_in_diff_mode(self):
        self.git("rm", "-q", "lib/Service/Good.php")
        rc, out = self.diff()
        self.assertEqual(rc, 1, out)
        self.assertIn("lib/Service/Good.php: listed in .sig/five-star-files.txt but does not exist", out)

    def test_removing_a_path_while_the_file_exists_fails(self):
        self.listing([])
        rc, out = self.diff()
        self.assertEqual(rc, 1, out)
        self.assertIn("lib/Service/Good.php: removed from .sig/five-star-files.txt while the file still exists", out)

    def test_a_listed_file_that_is_not_source_fails(self):
        self.write("css/app.css", "a { color: red; }\n")
        self.listing(["lib/Service/Good.php", "css/app.css"])
        rc, out = self.full()
        self.assertEqual(rc, 1, out)
        self.assertIn("css/app.css: listed in .sig/five-star-files.txt but not a measured source file", out)


class Modes(FileFloorCase):
    def setUp(self):
        super().setUp()
        self.git("checkout", "-q", "base")
        self.write("lib/Service/Wide.php", php_class("Wide", [method("wide", params="int $a, int $b, int $c")]))
        self.listing(["lib/Service/Good.php", "lib/Service/Wide.php"])
        self.commit("development holds a broken listed file")
        self.git("checkout", "-q", "-B", "change")

    def test_diff_mode_judges_only_the_listed_files_the_change_touches(self):
        self.write("lib/Service/Good.php", php_class("Good", [method("m0", tag="g0"), method("n", tag="n")]))
        rc, out = self.diff()
        self.assertEqual(rc, 0, out)
        self.assertIn("five-star files (diff mode): 1 of 2 listed file(s) judged", out)

    def test_diff_mode_judges_a_listed_file_the_change_touches(self):
        self.write("lib/Service/Wide.php", php_class("Wide", [method("wide", params="int $a, int $b, int $c", tag="t")]))
        rc, out = self.diff()
        self.assertEqual(rc, 1, out)
        self.assertIn("Wide::wide: 3 parameters > 2", out)

    def test_diff_mode_judges_a_path_the_change_adds_to_the_list(self):
        self.git("checkout", "-q", "base")
        self.write("lib/Service/Other.php", php_class("Other", [method("o", params="int $a, int $b, int $c")]))
        self.commit("an unlisted wide file")
        self.git("checkout", "-q", "-B", "change")
        self.listing(["lib/Service/Good.php", "lib/Service/Wide.php", "lib/Service/Other.php"])
        rc, out = self.diff()
        self.assertEqual(rc, 1, out)
        self.assertIn("Other::o: 3 parameters > 2", out)
        self.assertNotIn("Wide::wide", out)

    def test_full_mode_judges_every_listed_file(self):
        rc, out = self.full()
        self.assertEqual(rc, 1, out)
        self.assertIn("Wide::wide: 3 parameters > 2", out)
        self.assertIn("five-star files (full mode): 2 of 2 listed file(s) judged", out)


VUE = """<template>
  <div>{{ total }}</div>
</template>

<script>
export default {
  methods: {
    total(a, b, c) {
      return a + b + c
    },
  },
}
</script>
"""


class Vue(FileFloorCase):
    def test_a_vue_finding_is_a_warning_while_lizard_is_1_25_0_or_older(self):
        self.assertFalse(files.js_reliable("1.24.3"))
        self.assertFalse(files.js_reliable("1.25.0"))
        rc, out = self.hold("src/views/Total.vue", VUE)
        self.assertEqual(rc, 0, out)
        self.assertIn("  warning: five-star file src/views/Total.vue:8 total: 3 parameters > 2", out)
        self.assertIn("reads vue, js and ts unreliably up to 1.25.0 (terryyin/lizard#549)", out)
        self.assertIn("0 failure(s), 1 warning(s)", out)

    def test_a_newer_pinned_lizard_makes_vue_findings_fail(self):
        self.assertTrue(files.js_reliable("1.26.0"))
        pinned = sig.LIZARD_VERSION
        self.write("src/views/Total.vue", VUE)
        self.listing(["src/views/Total.vue"])
        self.commit()
        try:
            sig.LIZARD_VERSION = "1.26.0"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = floor.cmd_check(argparse.Namespace(
                    app=self.dir, base_ref=None, floor=floor.FLOOR_PATH, cache=None,
                    md=None, json=None, proposed=None), LIZARD)
        finally:
            sig.LIZARD_VERSION = pinned
        self.assertEqual(rc, 1, buf.getvalue())
        self.assertIn("  five-star file src/views/Total.vue:8 total: 3 parameters > 2", buf.getvalue())


class ReRecord(FileFloorCase):
    def test_write_re_records_the_app_floor_upwards(self):
        rc, out = run("write", self.dir)
        self.assertEqual(rc, 0, out)
        path = os.path.join(self.dir, floor.FLOOR_PATH)
        with open(path) as fh:
            doc = json.load(fh)
        self.assertIn("php unit_size >60", doc["checks"])
        doc["checks"] = [c for c in doc["checks"] if c != "php unit_size >60"]
        with open(path, "w") as fh:
            json.dump(doc, fh)
        rc, out = run("write", self.dir)
        self.assertEqual(rc, 0, out)
        with open(path) as fh:
            self.assertIn("php unit_size >60", json.load(fh)["checks"])


if __name__ == "__main__":
    unittest.main()
