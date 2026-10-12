#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-119's checker (check_procedure_code.py), rule by rule.

  1. A PROCEDURE TOKEN IN THE PATH COUNTS, for each token in the config.
  2. A PROCEDURE TOKEN IN A DECLARED CLASS NAME COUNTS, though the path is bland.
  3. SHORT TOKENS MATCH WHOLE WORDS ONLY. 'woo' is not 'Wood', 'dso' is not a
     word that merely contains it; camelCase, acronyms and kebab-case split.
  4. A NATIONAL-STANDARD ADAPTER IS EXCLUDED by word (zgw, stuf, dso-adapter) ...
  5. ... AND AN AMBIGUOUS TOKEN IS EXCUSED BY PATH: 'dso' under lib/Adapter is
     excluded, the same word elsewhere is counted.
  6. ONLY lib/ AND src/, ONLY php/js/ts/vue count. tests/ and .md do not.
  7. THE RATCHET: no baseline is exit 4 (never 0), equal is 0, above FAILS,
     below FAILS with the number to write, a raised baseline FAILS, a broken
     baseline FAILS.
  8. THE CONFIG IS THE ONLY LIST: a custom config changes what counts.
  9. REF MODE AGREES WITH WORKING-TREE MODE on a committed tree.

Run: python3 scripts/lib/test_check_procedure_code.py
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
import check_procedure_code as cpc  # noqa: E402

CFG = cpc.load_config(cpc.DEFAULT_CONFIG)


def cls(path, names=()):
    return cpc.classify(path, list(names), CFG)


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cpc.main(argv)
    return rc, out.getvalue()


def git(d, *a):
    subprocess.run(["git", "-C", d, "-c", "user.email=f@x.invalid", "-c", "user.name=F", *a],
                   check=True, capture_output=True)


def make_app(files, baseline=None):
    d = tempfile.mkdtemp(prefix="gate119-")
    atexit.register(shutil.rmtree, d, True)
    git(d, "init", "-q")
    for p, body in files.items():
        os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True)
        with open(os.path.join(d, p), "w") as fh:
            fh.write(body)
    if baseline is not None:
        with open(os.path.join(d, cpc.BASELINE_NAME), "w") as fh:
            fh.write(baseline if isinstance(baseline, str) else json.dumps({"count": baseline}))
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "base")
    return d


class Rules(unittest.TestCase):
    def test_1_every_token_counts_in_a_path(self):
        for tok in CFG["substringTokens"] + CFG["wordTokens"]:
            ok, hits, _ = cls("lib/Service/%sService.php" % tok.capitalize())
            self.assertTrue(ok, tok)
            self.assertIn(tok, hits)

    def test_1b_the_assigned_tokens_are_all_configured(self):
        want = ("woo bezwaar beschikking vth dso subsid termijn besluit leerplicht verlof melding klacht jeugd "
                "wmo bijstand leges omgevings").split()
        have = set(CFG["substringTokens"] + CFG["wordTokens"])
        self.assertEqual(set(want), have)

    def test_2_class_name_counts(self):
        ok, hits, _ = cls("lib/Service/Handler.php", ["BezwaarHandler"])
        self.assertTrue(ok)
        self.assertEqual(hits, ["bezwaar"])

    def test_2b_a_bland_file_does_not_count(self):
        self.assertFalse(cls("lib/Service/ObjectService.php", ["ObjectService"])[0])

    def test_3_short_tokens_are_whole_words(self):
        self.assertFalse(cls("lib/Service/WoodService.php")[0])
        self.assertFalse(cls("src/views/Dsonar.vue")[0])
        self.assertTrue(cls("lib/Service/WooPublication.php")[0])
        self.assertTrue(cls("src/views/woo-publication.vue")[0])
        self.assertTrue(cls("lib/Service/WOOPublication.php")[0])
        self.assertTrue(cls("lib/Service/Foo/WMO_Aanvraag.php")[0])

    def test_4_adapter_words_excluded(self):
        for path in ("lib/Service/ZgwBesluitMapper.php", "lib/Service/BeschikkingStufExport.php",
                     "lib/Service/DsoAdapter.php", "src/api/kvk-melding.js"):
            ok, hits, why = cls(path)
            self.assertFalse(ok, path)
            self.assertTrue(hits and why, path)

    def test_4b_dso_adapter_is_a_phrase_not_two_words(self):
        # 'dso' alone is ambiguous and counts; 'dso-adapter' as a phrase is excused.
        self.assertTrue(cls("lib/Service/DsoMelding.php")[0])
        self.assertFalse(cls("lib/Service/Dso/Adapter.php")[0])

    def test_5_ambiguous_token_is_excused_by_path(self):
        self.assertFalse(cls("lib/Adapter/DsoClient.php")[0])
        self.assertFalse(cls("lib/Service/Zgw/BesluitService.php")[0])
        self.assertTrue(cls("lib/Service/DsoClient.php")[0])
        self.assertTrue(cls("lib/Adapters/DsoClient.php")[0], "a sibling name is not the prefix")

    def test_6_scope(self):
        d = make_app({
            "lib/BezwaarService.php": "<?php class X {}",
            "src/BezwaarList.vue": "<template/>",
            "tests/BezwaarTest.php": "<?php",
            "docs/bezwaar.md": "x",
            "lib/bezwaar.md": "x",
            "lib/node_modules/bezwaar/index.js": "x",
            "other/BezwaarService.php": "x",
        }, baseline=2)
        files = cpc.collect_working(d, CFG)
        self.assertEqual(sorted(files), ["lib/BezwaarService.php", "src/BezwaarList.vue"])

    def test_7_ratchet(self):
        files = {"lib/BezwaarService.php": "<?php", "lib/WooService.php": "<?php", "lib/Plain.php": "<?php"}
        d = make_app(files)
        rc, out = run_main([d])
        self.assertEqual(rc, 4, out)
        d = make_app(files, baseline=2)
        rc, out = run_main([d])
        self.assertEqual(rc, 0, out)
        self.assertIn("counted 2 file(s), baseline 2", out)
        d = make_app(files, baseline=1)
        rc, out = run_main([d])
        self.assertEqual(rc, 1, out)
        self.assertIn("added 1", out)
        d = make_app(files, baseline=5)
        rc, out = run_main([d])
        self.assertEqual(rc, 1, out)
        self.assertIn('{"count": 2}', out)
        d = make_app(files, baseline="{not json")
        rc, out = run_main([d])
        self.assertEqual(rc, 1, out)
        self.assertIn("not a valid baseline", out)
        d = make_app(files, baseline='{"count": -1}')
        self.assertEqual(run_main([d])[0], 1)
        d = make_app(files, baseline='{"count": true}')
        self.assertEqual(run_main([d])[0], 1)

    def test_7b_raising_the_baseline_fails(self):
        d = make_app({"lib/BezwaarService.php": "<?php"}, baseline=1)
        git(d, "branch", "-M", "base")
        git(d, "checkout", "-q", "-b", "pr")
        with open(os.path.join(d, "lib/WooService.php"), "w") as fh:
            fh.write("<?php")
        with open(os.path.join(d, cpc.BASELINE_NAME), "w") as fh:
            fh.write('{"count": 2}')
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "grow and lift the ceiling")
        rc, out = run_main([d, "--base", "base"])
        self.assertEqual(rc, 1, out)
        self.assertIn("raised from 1 to 2", out)
        rc, out = run_main([d])
        self.assertEqual(rc, 0, "without a base the count alone is consistent")

    def test_7c_the_pr_that_adds_the_baseline_may_set_it(self):
        d = make_app({"lib/BezwaarService.php": "<?php"})
        git(d, "branch", "-M", "base")
        git(d, "checkout", "-q", "-b", "pr")
        with open(os.path.join(d, cpc.BASELINE_NAME), "w") as fh:
            fh.write('{"count": 1}')
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "add baseline")
        self.assertEqual(run_main([d, "--base", "base"])[0], 0)

    def test_8_config_is_the_only_list(self):
        d = make_app({"lib/PlanningService.php": "<?php", "lib/BezwaarService.php": "<?php"}, baseline=1)
        cfgp = os.path.join(d, "cfg.json")
        with open(cpc.DEFAULT_CONFIG) as fh:
            cfg = dict(json.load(fh))
        cfg["substringTokens"] = ["planning"]
        with open(cfgp, "w") as fh:
            json.dump(cfg, fh)
        rc, out = run_main([d, "--config", cfgp, "--list"])
        self.assertEqual(rc, 0, out)
        self.assertIn("counted lib/PlanningService.php", out)
        self.assertNotIn("counted lib/BezwaarService.php", out)

    def test_9_ref_mode_agrees_with_working_tree(self):
        d = make_app({
            "lib/Service/Handler.php": "<?php\nfinal class BezwaarHandler {}\n",
            "lib/Service/Bland.php": "<?php\n// class WooInComment\nclass Bland {}\n",
            "src/Termijn.vue": "<template/>",
            "src/store/s.js": "export default class VerlofStore {}\n",
            "lib/Service/Zgw/Besluit.php": "<?php",
        }, baseline=3)
        work, _ = cpc.count_tree(d, CFG)
        ref, _ = cpc.count_tree(d, CFG, "HEAD")
        self.assertEqual([p for p, _ in work], [p for p, _ in ref])
        self.assertEqual(len(work), 3)
        self.assertNotIn("lib/Service/Bland.php", [p for p, _ in work])

    def test_10_unreadable_config_is_exit_2_not_a_finding(self):
        d = make_app({"lib/A.php": "<?php"}, baseline=0)
        rc, out = run_main([d, "--config", os.path.join(d, "missing.json")])
        self.assertEqual(rc, 2)
        self.assertNotIn("FAIL:", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
