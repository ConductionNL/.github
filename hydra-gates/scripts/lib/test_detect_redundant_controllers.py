#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for detect-redundant-controllers (gate-17). Run with:

    python3 scripts/lib/test_detect_redundant_controllers.py

or via pytest:

    python3 -m pytest scripts/lib/test_detect_redundant_controllers.py

WHY THIS FILE DID NOT EXIST UNTIL #422
--------------------------------------
gate-17 shipped with no suite of its own, so nothing had ever asked it to
fail. That is the same gap gate-25 was in when it was found carrying gate-19's
defect verbatim (#425): a gate whose only evidence of correctness is that
nobody has complained about it has no evidence of correctness.

The module is imported by path because its filename is hyphenated and is
therefore not a legal Python module name — the gate is invoked as a script.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "detect_redundant_controllers", os.path.join(_HERE, "detect-redundant-controllers.py")
)
drc = importlib.util.module_from_spec(_SPEC)
sys.modules["detect_redundant_controllers"] = drc
_SPEC.loader.exec_module(drc)


def _scan(controller_src: str) -> list[str]:
    """Materialise a throwaway app root holding one controller, scan it."""
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "lib" / "Controller" / "ThingController.php"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(controller_src, encoding="utf-8")
        return drc.scan_files([(path, path.relative_to(root))])


_PASS_THROUGH = """\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
%s	public function index() {
%s		return $this->objectService->findAll('thing');
	}
}
"""


# ---------------------------------------------------------------------------
# A comment is not domain logic (#415 class, #422).
#
# Reverted against origin/main, arms 2 and 3 FLIP (no finding -> finding), as
# does the blank-line arm in the class below. Arms 1, 3b, 4, 5, 6 and 7 pass
# either way and are CONTROLS.
# ---------------------------------------------------------------------------
class CommentIsNotDomainLogic(unittest.TestCase):
    """`WRAPPER_NOISE_PATTERNS` recognised a comment by its LINE PREFIX, which
    covers the three ways a comment line can BEGIN and misses the one way it
    can continue. An unprefixed interior line of a `/* … */` block survived as
    "significant code", and a one-call pass-through carrying an explanatory
    block comment read as a method with real logic — so the gate went quiet on
    exactly the wrapper whose author had documented it."""

    def test_1_positive_control_a_bare_pass_through_is_flagged(self):
        """CONTROL. Without this firing, arms 2-3 measure nothing."""
        out = _scan(_PASS_THROUGH % ("", ""))
        self.assertEqual(len(out), 1, out)
        self.assertIn("rule=pass-through-to-ObjectService", out[0])

    def test_2_an_unprefixed_block_comment_interior_line_is_not_logic(self):
        out = _scan(_PASS_THROUGH % ("", """\
		/*
		TODO: this should also apply the tenant filter before delegating.
		Not done yet.
		*/
"""))
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=index", out[0])

    def test_3_a_rescue_phrase_inside_a_block_comment_is_not_a_guard(self):
        """The second direction of the same hole, and the worse one: an
        unprefixed block-comment line reaches RESCUE_PATTERNS, so prose saying
        the authorization happens ELSEWHERE reads as authorization happening
        HERE and the method escapes the gate entirely."""
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	public function index() {
		/*
		requireAdmin() is handled by the middleware, not by this method.
		*/
		return $this->objectService->findAll('thing');
	}
}
""")
        self.assertEqual(len(out), 1, out)

    def test_3b_CONTROL_a_trailing_comment_on_the_call_statement(self):
        """CONTROL — the near-miss, and saying so is the point. The same
        sentence three characters further along never reaches the question:
        `_is_redundant_body` tests for the ObjectService call FIRST and
        `continue`s, so a rescue phrase trailing the call statement is skipped
        before RESCUE_PATTERNS is consulted. This arm passes before and after.
        An arm that cannot fail is not proof that the gate cannot."""
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	public function index() {
		return $this->objectService->findAll('thing'); // requireAdmin() is middleware's
	}
}
""")
        self.assertEqual(len(out), 1, out)

    def test_4_real_domain_logic_is_still_not_a_pass_through(self):
        """CONTROL (anti-widening). Passes before and after — the mask must
        not turn a method that does something into a wrapper."""
        out = _scan(_PASS_THROUGH % ("", "		$this->tenantService->scope($this->userId);\n"))
        self.assertEqual(out, [])

    def test_5_a_reason_bearing_spec_exclude_still_exempts(self):
        """CONTROL (anti-widening), AND THE ARM THAT CAUGHT THE FIX
        OVER-APPLYING. The docblock is read from the ORIGINAL text — `@spec
        exclude` lives in a comment BY DESIGN — but the first cut of this
        change also let `METHOD_HEADER_RE`'s `^\\s*` slide the reported line up
        through the blanked docblock's now-blank lines, so `_method_docblock`
        walked from the wrong place, found no `*/`, and this escape hatch
        silently stopped working. Closing a false negative by breaking an
        author's only correct remedy is worse than the false negative."""
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	/**
	 * @spec exclude deliberate ObjectServiceMapperAdapter facade, ADR-022
	 */
	public function index() {
		return $this->objectService->findAll('thing');
	}
}
""")
        self.assertEqual(out, [])

    def test_6_a_bare_spec_exclude_still_does_NOT_exempt(self):
        """CONTROL. `#412`: a marker with no usable reason must not waive a
        gate that gate-16 would refuse for the identical keystrokes."""
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	/**
	 * @spec exclude
	 */
	public function index() {
		return $this->objectService->findAll('thing');
	}
}
""")
        self.assertEqual(len(out), 1, out)

    def test_7_a_non_CRUD_method_name_is_still_never_flagged(self):
        """CONTROL. The name filter is the gate's main defence against
        flagging domain actions, and the mask must not reach past it."""
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	public function publishThing() {
		return $this->objectService->saveObject('thing', []);
	}
}
""")
        self.assertEqual(out, [])


class ReportedLineIsTheDeclarationLine(unittest.TestCase):
    """`METHOD_HEADER_RE` used `^\\s*`, and in MULTILINE mode `\\s` matches
    `\\n` — so the match could begin at the start of any run of BLANK LINES
    above the declaration and the reported line number was the blank line.
    Pre-existing (measured on origin/main: true line 6, reported 5); it became
    load-bearing once the body was comment-masked, because a blanked docblock
    IS a run of blank lines."""

    def test_a_method_preceded_by_a_blank_line_reports_its_own_line(self):
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {

	public function index() {
		return $this->objectService->findAll('thing');
	}
}
""")
        self.assertEqual(len(out), 1, out)
        self.assertIn(":6 ", out[0] + " ")

    def test_a_method_preceded_by_a_docblock_reports_its_own_line(self):
        out = _scan("""\
<?php
namespace OCA\\Fixture\\Controller;

class ThingController {
	/**
	 * Lists things.
	 */
	public function index() {
		return $this->objectService->findAll('thing');
	}
}
""")
        self.assertEqual(len(out), 1, out)
        self.assertIn(":8 ", out[0] + " ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
