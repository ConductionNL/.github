#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for php_attributes and for every docblock walk that uses it.

Each walker below goes up from a method declaration to its docblock, and each
used to stop on the closing line of a multi-line attribute (dossiq#5151).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import php_attributes as pa  # noqa: E402
import check_spec_coverage as csc  # noqa: E402
import check_orphan_auth as coa  # noqa: E402
import check_contract_coverage as ccc  # noqa: E402
import check_listener_placement as clp  # noqa: E402
import check_orphaned_write_capability as cowc  # noqa: E402
import check_caller_identity_exempt as ccie  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "detect_redundant_controllers", os.path.join(HERE, "detect-redundant-controllers.py")
)
drc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drc)


MULTI = [
    "    #[McpTool(",
    "        name: 'createTask',",
    "        description: 'a task (for the handler)'",
    "            . ' or \"me\".',",
    "    )]",
]
STRING_CLOSE = [
    "    #[Route(",
    "        path: '/odd)]/path',",
    "        note: \"])\",",
    "    )]",
]
STACKED = [
    "    #[NoAdminRequired]",
    "    #[McpTool(",
    "        tags: ['x', ['y']],",
    "    )]",
    "    #[RateLimit(",
    "        limit: 5,",
    "    )] #[NoCSRFRequired]",
]
COMMENTED = [
    "    #[McpTool( // registered by the scanner",
    "        name: 'a', /* ) ] */",
    "        # a hash comment )]",
    "    )] // trailing note",
    "    #[NoAdminRequired] /* note */",
]
SHAPES = {"multi-line": MULTI, "string with )]": STRING_CLOSE, "stacked": STACKED, "comments": COMMENTED}


class AttributeBlockStartTest(unittest.TestCase):

    def _walk(self, lines: list[str]) -> int:
        """Index the walk reaches after stepping over every attribute block."""
        i = len(lines) - 1
        while i >= 0:
            start = pa.attribute_block_start(lines, i)
            if start is None:
                break
            i = start - 1
        return i

    def test_every_shape_is_stepped_over_to_the_line_above(self):
        for name, attr in SHAPES.items():
            with self.subTest(name):
                self.assertEqual(self._walk(["    /** doc */"] + attr), 0)

    def test_one_line_attribute(self):
        self.assertEqual(pa.attribute_block_start(["#[A]"], 0), 0)

    def test_CONTROL_array_close_is_not_an_attribute(self):
        lines = ["    #[Single]", "    const ITEMS = [", "        'a',", "    ]"]
        self.assertIsNone(pa.attribute_block_start(lines, 3))

    def test_CONTROL_unclosed_attribute_is_not_an_attribute(self):
        lines = ["    #[A(", "        x: ']',", "    ]"]
        self.assertIsNone(pa.attribute_block_start(lines, 2))

    def test_CONTROL_one_line_docblock_below_an_attribute_is_not_part_of_it(self):
        lines = ["    #[A]", "    /** @var int[] */"]
        self.assertIsNone(pa.attribute_block_start(lines, 1))

    def test_CONTROL_code_after_the_close_is_not_an_attribute(self):
        lines = ["    #[A(", "        x: 1,", "    )] $y = [1];"]
        self.assertIsNone(pa.attribute_block_start(lines, 2))


class WalkersStepOverAttributesTest(unittest.TestCase):
    """Every docblock walk reaches the docblock above each attribute shape, and
    still finds nothing when there is no docblock."""

    DOC = [
        "    /**",
        "     * Create a task.",
        "     *",
        "     * @spec openspec/specs/x/spec.md#req",
        "     * @orphan-auth exclude kept for the planned approval step",
        "     * @orphaned-write-capability exclude kept for the planned approval step",
        "     */",
    ]
    DECL = "    public function createTask(string $id): array {"

    def _cases(self):
        for name, attr in SHAPES.items():
            yield name, self.DOC + attr + [self.DECL], True
            yield name + " (no docblock)", ["    }", ""] + attr + [self.DECL], False

    def _assert_all(self, found) -> None:
        for name, lines, has_doc in self._cases():
            with self.subTest(name):
                self.assertEqual(bool(found(lines, len(lines) - 1)), has_doc)

    def test_check_spec_coverage(self):
        self._assert_all(csc._docblock_block)

    def test_check_orphan_auth(self):
        self._assert_all(lambda lines, i: coa._is_excluded("\n".join(lines), i + 1))

    def test_check_contract_coverage_docblock(self):
        self._assert_all(ccc._docblock_block)

    def test_check_contract_coverage_preamble_reads_a_public_page_above(self):
        lines = ["    /** doc */", "    #[PublicPage]"] + MULTI + [self.DECL]
        self.assertTrue(ccc._method_is_public_endpoint(lines, len(lines) - 1))

    def test_detect_redundant_controllers(self):
        self._assert_all(lambda lines, i: drc._method_docblock(lines, i + 1))

    def test_check_listener_placement(self):
        self._assert_all(clp._docblock_above)

    def test_check_orphaned_write_capability(self):
        self._assert_all(cowc._preceding_docblock_has_exclude)

    def test_check_caller_identity_exempt(self):
        self._assert_all(ccie.docblock_above)


if __name__ == "__main__":
    unittest.main()
