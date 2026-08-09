#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_autocomplete (gate-44). Run with:

    python3 scripts/lib/test_check_autocomplete.py

THE CONTROL THAT NAMED THE DEFECT
---------------------------------
`test_a_single_quoted_name_is_the_same_defect` is the fixture experiment run
as an assertion: the double-quoted form fired in both a .vue app and a
PHP-template app, and the byte-for-byte equivalent single-quoted form reported
PASS in both, because the value regex read out of double quotes only.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_autocomplete as cac  # noqa: E402


def rules(markup: str, fname: str = "Component.vue") -> list[str]:
    return [line.rsplit("rule=", 1)[1]
            for line in cac.scan_source(fname, markup)]


class ItCatchesTheTextbookCase(unittest.TestCase):
    def test_a_semantic_input_without_autocomplete(self):
        self.assertEqual(rules('<input id="e" type="text" name="email">'),
                         ["semantic-input-without-autocomplete"])

    def test_every_semantic_noun(self):
        for name in ("email", "telephone", "phone", "firstname", "lastname",
                     "address", "street", "city", "postcode", "country",
                     "password", "username", "organization", "birthday"):
            with self.subTest(name=name):
                self.assertEqual(rules(f'<input type="text" name="{name}">'),
                                 ["semantic-input-without-autocomplete"], name)

    def test_a_php_template_input_is_the_same_defect(self):
        self.assertEqual(
            rules('<div id="x"><input type="text" name="email"></div>',
                  "templates/settings/admin.php"),
            ["semantic-input-without-autocomplete"])

    def test_a_single_quoted_name_is_the_same_defect(self):
        # THE MEASURED BLIND SPOT. Identical rendered DOM, identical defect;
        # the pre-fix regex matched double quotes only and reported PASS.
        self.assertEqual(
            rules("<input id='b44-tel' type='text' name='telephone'>"),
            ["semantic-input-without-autocomplete"])

    def test_the_double_quoted_positive_control(self):
        # Absence is what a wrong lookup manufactures for free: the same
        # markup in the quoting style that already worked must still fire, or
        # the assertion above could be passing for the wrong reason.
        self.assertEqual(
            rules('<input id="b44-tel" type="text" name="telephone">'),
            ["semantic-input-without-autocomplete"])


class ItLeavesCorrectAndIrrelevantInputsAlone(unittest.TestCase):
    def test_autocomplete_present(self):
        self.assertEqual(
            rules('<input type="email" name="email" autocomplete="email">'), [])

    def test_a_bound_autocomplete_is_still_an_autocomplete(self):
        for attr in (':autocomplete="mode"', 'v-bind:autocomplete="mode"'):
            with self.subTest(attr=attr):
                self.assertEqual(
                    rules(f'<input type="text" name="email" {attr}>'), [], attr)

    def test_types_with_nothing_to_autofill(self):
        for t in ("hidden", "submit", "button", "reset", "image", "file",
                  "checkbox", "radio", "color", "range"):
            with self.subTest(t=t):
                self.assertEqual(rules(f'<input type="{t}" name="email">'), [], t)

    def test_a_non_semantic_name(self):
        self.assertEqual(rules('<input type="text" name="publicationTitle">'), [])

    def test_an_input_with_no_name_id_or_model(self):
        self.assertEqual(rules('<input type="text">'), [])


class ItReadsOnlyMarkupThatShips(unittest.TestCase):
    def test_a_commented_out_input_is_not_a_control(self):
        self.assertEqual(
            rules('<!-- <input type="text" name="email"> was the old field -->'),
            [])

    def test_an_input_in_a_script_string_is_not_a_control(self):
        self.assertEqual(
            rules('<script>el.innerHTML = \'<input type="text" name="email">\'</script>'),
            [])

    def test_the_positive_control_for_both(self):
        self.assertEqual(rules('<input type="text" name="email"> was the old field'),
                         ["semantic-input-without-autocomplete"])


class TheTagBoundaryIsQuoteAware(unittest.TestCase):
    def test_a_gt_inside_an_attribute_does_not_end_the_tag(self):
        # `[^>]*` ended the tag at the `>` in the expression, so `name=` fell
        # outside the attribute run and the input read as nameless — the
        # false-NEGATIVE half of #259.
        self.assertEqual(
            rules('<input type="text" :class="n > 5 ? \'a\' : \'b\'" name="email">'),
            ["semantic-input-without-autocomplete"])

    def test_and_an_autocomplete_past_that_gt_is_still_honoured(self):
        self.assertEqual(
            rules('<input type="text" :class="n > 5 ? \'a\' : \'b\'" '
                  'name="email" autocomplete="email">'),
            [])


class TheMutantIsTheWholePreFixChecker(unittest.TestCase):
    """The pre-fix heredoc, verbatim from run-hydra-gates.sh, replayed over
    the fixtures above. It must DISAGREE with the current checker on every one
    of them — otherwise the rewrite changed nothing."""

    PRE_FIX_INPUTS = [
        "<input id='b44-tel' type='text' name='telephone'>",
        '<!-- <input type="text" name="email"> was the old field -->',
        '<input type="text" :class="n > 5 ? \'a\' : \'b\'" name="email">',
        # first-name-like-attribute-wins: `id="e"` is not semantic, `name` is
        '<input id="e" type="text" name="email">',
    ]

    def _pre_fix(self, markup: str) -> int:
        import re
        txt = markup.replace('\n', ' ')
        sem = re.compile(
            r'(email|tel(?:ephone)?|phone|firstname|lastname|fullname|address'
            r'|street|city|postal|postcode|zip|country|password|username'
            r'|organization|birthday|dob)', re.IGNORECASE)
        n = 0
        for m in re.finditer(r'<input\b([^>]*)>', txt, re.IGNORECASE):
            attrs = m.group(1) or ''
            if re.search(r'(^|\s)type\s*=\s*"(hidden|submit|button|reset|image'
                         r'|file|checkbox|radio|color|range)"', attrs,
                         re.IGNORECASE):
                continue
            if re.search(r'(^|\s)(:?autocomplete|v-bind:autocomplete)\s*=', attrs):
                continue
            nm = re.search(r'(^|\s)(?:name|id|:name|:id|v-model)\s*=\s*"([^"]+)"',
                           attrs)
            if not nm:
                continue
            if sem.search(nm.group(2)):
                n += 1
        return n

    def test_the_pre_fix_checker_answers_differently(self):
        differed = 0
        for markup in self.PRE_FIX_INPUTS:
            if self._pre_fix(markup) != len(rules(markup)):
                differed += 1
        self.assertEqual(
            differed, len(self.PRE_FIX_INPUTS),
            "the pre-fix implementation agrees with the current one on every "
            "fixture — the rewrite is unverified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
