#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""A CHECKER'S OWN PATTERN MUST MATCH THE SHAPES IT CLAIMS TO RECOGNISE.

WHY THIS FILE EXISTS
--------------------
Six defects in this package on 2026-08-16 were the same defect. Every one of
them was a pattern-matching instrument failing toward "no match", and every one
of them was invisible because a regex that matches nothing prints nothing, and
printing nothing is what a clean run looks like:

  1. `\\b` does not match after `_` — a rename codemod missed every
     `snake_case` occurrence and reported success.
  2. `\\b` does not match before the `I` in `ObjectServiceInterface` — gate-7's
     `_OR_IMPORT_RE` stopped recognising OpenRegister delegation the moment a
     repo adopted ADR-084. **decidesk went 5 -> 12 findings with no controller
     edit.**
  3. A quoted-token rename could not see a bare identifier key.
  4. `[a-z-]` dropped the digit in `e2e-coverage`.
  5. gate-48's `MUTATING_METHOD` matched only a QUOTED literal, so
     `const method = isNew ? 'POST' : 'PUT'` was invisible — **15 call sites
     reported where 27 were unprotected.**
  6. gate-7's `_OR_FACADE_CALL_RE` required the facade to be the receiver of
     the next `->`, so `$svc = $this->settingsService->getObjectService()` did
     not count as reaching the facade.

None of them was caught by a unit test, because the unit tests were written
from the same reading of the shape as the regex. What catches this class is a
registry that states, IN THE TEST, the spellings each pattern is responsible
for — including the ones nobody thought of when the pattern was written — and
asserts both directions.

HOW TO USE IT
-------------
When you widen or narrow a checker's pattern, add the spelling you were
widening FOR to `MUST_MATCH`, and the shape you must not start matching to
`MUST_NOT_MATCH`. The second half is not optional: a pattern with no negative
control is a pattern that can be satisfied by `.*`.

Run with::

    python3 scripts/lib/test_checker_patterns_match_documented_shapes.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_csrf_callers as csrf_callers  # noqa: E402
import check_no_admin_idor as idor  # noqa: E402


# ---------------------------------------------------------------------------
# The registry: (module, attribute, must-match, must-not-match)
# ---------------------------------------------------------------------------
#
# `attribute` is looked up BY NAME and the test fails if it is missing — a
# renamed or deleted pattern must break this file loudly rather than quietly
# stop being covered. (`.github` has already shipped a "12 passed / 0 failed"
# suite that compared over a set no longer containing the thing it was about.)
REGISTRY = [
    (
        idor, "_OR_IMPORT_RE",
        # Every way a PHP file can name OpenRegister's ObjectService.
        [
            "use OCA\\OpenRegister\\Service\\ObjectService;",
            # ADR-084's published contract. `ObjectService\\b` cannot match
            # this: `\\b` needs a non-word character and `I` is a word
            # character. This is defect (2) above.
            "use OCA\\OpenRegister\\Contract\\ObjectServiceInterface;",
            # The container form — the MAJORITY shape in the fleet.
            "$this->container->get('OCA\\OpenRegister\\Service\\ObjectService')",
            "$c->get(id: 'OCA\\\\OpenRegister\\\\Service\\\\ObjectService')",
            # Type position, no import at all — zaakafhandelapp's ZGW services.
            "private \\OCA\\OpenRegister\\Service\\ObjectService $objectService;",
            "private readonly \\OCA\\OpenRegister\\Contract\\ObjectServiceInterface $svc,",
            "$c->get(\\OCA\\OpenRegister\\Contract\\ObjectServiceInterface::class)",
        ],
        [
            # A leaf app's OWN ObjectService is that app's storage and carries
            # no OpenRegister authorisation. The `OCA\\OpenRegister\\` anchor
            # is the whole safety of this pattern.
            "use OCA\\ZaakAfhandelApp\\Service\\ObjectService;",
            "use OCA\\Procest\\Service\\ObjectService;",
            # Longer identifiers that merely START with the name.
            "use OCA\\OpenRegister\\Service\\ObjectServiceHelper;",
            "use OCA\\OpenRegister\\Contract\\ObjectServiceInterfaceFactory;",
            "use OCA\\OpenRegister\\Service\\SearchService;",
        ],
    ),
    (
        idor, "_OR_FACADE_CALL_RE",
        [
            "return $this->objectService->find($id);",
            "$objectService->searchObjects($query);",
            # Accessor, chained.
            "$this->getObjectService()->find($id);",
            # Accessor, ASSIGNED then used — defect (6) above.
            "$objectService = $this->settingsService->getObjectService();",
            "$orService = $this->mapperService->getOpenRegisters();",
            "return $this->getOpenRegisters();",
            # The container resolution IS obtaining the facade.
            "return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');",
        ],
        [
            # A NAME is not a call. These must keep needing the arrow.
            "$this->objectService;",
            "if ($objectService === null) {",
            # A leaf app's own mapper is its own storage (Pattern 2's line).
            "$this->invoiceMapper->findAll();",
            # An unrelated getter.
            "$this->getObjectStore()->read($id);",
        ],
    ),
    (
        idor, "_IDENTITY_INTO_ARRAY_RE",
        [
            "$options['participants'] = [$orgUuid];",
            "$filters['owner'] = $userId;",
            "$q['scope']['org'] = $orgUuid;",
        ],
        [
            # A whole-variable assignment is the OTHER rule's business.
            "$options = $this->request->getParams();",
            # A comparison is not an assignment.
            "if ($options['owner'] == $userId) {",
        ],
    ),
    (
        csrf_callers, "MUTATING_METHOD",
        [
            "method: 'POST'",
            'method: "put"',
            "method: `PATCH`",
            "method: 'DELETE',",
        ],
        [
            "method: 'GET'",
            # ⚠️ THESE ARE THE DEFECT (5) SHAPES, AND THEY BELONG HERE RATHER
            # THAN IN MUST_MATCH: this regex is a LITERAL matcher and is not
            # being asked to resolve a computed verb. What must handle them is
            # `_fetch_is_mutating`, pinned by `ComputedVerbsAreMutating` below.
            # Saying so in the registry is the point — a shape has to be
            # SOMEBODY's responsibility, named.
            "method,",
            "method: isNew ? 'POST' : 'PUT'",
        ],
    ),
]


class PatternMatchesDocumentedShapes(unittest.TestCase):
    """Every registered pattern matches what it claims and nothing it disclaims."""

    def test_every_registered_attribute_still_exists(self):
        """A renamed pattern must FAIL here, not silently stop being covered."""
        for module, name, _match, _no_match in REGISTRY:
            with self.subTest(pattern=f"{module.__name__}.{name}"):
                self.assertTrue(
                    hasattr(module, name),
                    f"{module.__name__}.{name} no longer exists — this "
                    f"registry is now covering nothing under that name.",
                )

    def test_documented_shapes_match(self):
        for module, name, must_match, _no_match in REGISTRY:
            pattern = getattr(module, name)
            self.assertTrue(must_match, f"{name} has no documented shapes")
            for shape in must_match:
                with self.subTest(pattern=name, shape=shape):
                    self.assertIsNotNone(
                        pattern.search(shape),
                        f"{module.__name__}.{name} does NOT match a spelling "
                        f"it is responsible for: {shape!r}. A pattern that "
                        f"fails to match prints nothing, and nothing reads as "
                        f"clean.",
                    )

    def test_disclaimed_shapes_do_not_match(self):
        for module, name, _match, must_not_match in REGISTRY:
            pattern = getattr(module, name)
            self.assertTrue(must_not_match,
                            f"{name} has no negative control — a pattern with "
                            f"no negative control can be satisfied by '.*'")
            for shape in must_not_match:
                with self.subTest(pattern=name, shape=shape):
                    self.assertIsNone(
                        pattern.search(shape),
                        f"{module.__name__}.{name} matches a shape it "
                        f"disclaims: {shape!r}",
                    )


class WordBoundaryAgainstIdentifierFragments(unittest.TestCase):
    """The specific trap, stated as a property rather than as four examples.

    `\\b` between two word characters never matches. So any pattern that ends
    an IDENTIFIER FRAGMENT with `\\b` is asserting that no longer identifier
    starts with that fragment — which is a claim about a codebase, not about a
    regex, and it has been wrong three times in this fleet.
    """

    def test_b_does_not_separate_ObjectService_from_Interface(self):
        import re
        narrow = re.compile(r"ObjectService\b")
        self.assertIsNone(
            narrow.search("ObjectServiceInterface"),
            "If this ever passes, Python's \\b has changed and the whole "
            "premise of this file is different.",
        )
        self.assertIsNotNone(narrow.search("ObjectService;"))

    def test_the_shipped_pattern_does_separate_them(self):
        self.assertIsNotNone(
            idor._OR_IMPORT_RE.search(
                "use OCA\\OpenRegister\\Contract\\ObjectServiceInterface;"))
        self.assertIsNone(
            idor._OR_IMPORT_RE.search(
                "use OCA\\OpenRegister\\Contract\\ObjectServiceInterfaceFactory;"))


class ComputedVerbsAreMutating(unittest.TestCase):
    """gate-48: a `method` value that cannot be PROVEN safe counts as mutating.

    The registry above records that `MUTATING_METHOD` is a literal matcher.
    This is where the shapes it cannot see are made somebody's responsibility.
    """

    SAFE = "const method = 'GET'\nfetch('/x', { method })"
    TERNARY_BINDING = "const method = isNew ? 'POST' : 'PUT'\nfetch('/x', { method })"
    TERNARY_INLINE = "fetch('/x', { method: isNew ? 'POST' : 'PUT' })"
    UNRESOLVABLE = "fetch('/x', { method: m })"
    NO_METHOD_KEY = "fetch('/x')"
    SAFE_LITERAL = "fetch('/x', { method: 'GET' })"

    def _verdict(self, text: str):
        at = text.index("fetch(")
        call = csrf_callers._call_text(text, text.index("(", at))
        return csrf_callers._fetch_is_mutating(call, text, at)[0]

    def test_a_ternary_binding_is_mutating(self):
        self.assertIs(self._verdict(self.TERNARY_BINDING), True)

    def test_an_inline_ternary_is_mutating(self):
        self.assertIs(self._verdict(self.TERNARY_INLINE), True)

    def test_an_unresolvable_value_is_mutating(self):
        """Fail closed: an unreadable verb is not a pass."""
        self.assertIs(self._verdict(self.UNRESOLVABLE), True)

    def test_a_proven_safe_binding_is_not_mutating(self):
        """The negative control — without it, every fetch() would report."""
        self.assertIs(self._verdict(self.SAFE), False)

    def test_a_literal_safe_verb_is_not_mutating(self):
        self.assertIs(self._verdict(self.SAFE_LITERAL), False)

    def test_no_method_key_is_a_GET(self):
        self.assertIsNone(self._verdict(self.NO_METHOD_KEY))


if __name__ == "__main__":
    unittest.main(verbosity=2)
