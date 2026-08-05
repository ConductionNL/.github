#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_spec_anchors (gate-46). Run with:

    python3 scripts/lib/test_check_spec_anchors.py

or via pytest:

    python3 -m pytest scripts/lib/test_check_spec_anchors.py

BOTH WAYS, EVERY TIME
---------------------
Gate-46 was measured at 1,995 findings across 21 repos, 54% of them false.
Every relaxation below was written to clear a specific false-positive shape,
and every one of them ships PAIRED with a case that must still FAIL. A gate
that stops flagging is not a fixed gate, it is a dead one — and a dead gate
is indistinguishable from a passing repository, which is the defect this
whole package has spent a week fighting.

So each ``...Relaxed`` test class has a sibling assertion in the same class:

  * the false-positive input now resolves, AND
  * an input that differs only in the part the gate is supposed to check
    still does not resolve.

The fixtures are copied from real fleet specs (pipelinq's
``pos-payment-provider-adapter``, zaakafhandelapp's ``zgw-zaak-management``,
pipelinq's ``bi-export-and-data-warehouse-sink``) rather than written to
mirror the implementation's own regexes back at it.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_spec_anchors as csa  # noqa: E402


def _anchor(md: str, fragment: str) -> bool:
    """Write *md* to a throwaway file and ask whether *fragment* resolves."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "spec.md"
        p.write_text(md, encoding="utf-8")
        return csa.has_anchor(str(p), fragment)


def _scan(tree: dict[str, str], source_rel: str, source_src: str) -> list[str]:
    """Materialise an openspec tree plus one annotated source file and scan."""
    with tempfile.TemporaryDirectory() as root:
        for rel, body in tree.items():
            p = Path(root) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        src = Path(root) / source_rel
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(source_src, encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(root)
            return csa.scan_files([source_rel], root=root)
        finally:
            os.chdir(cwd)


# --------------------------------------------------------------------------
# Mode 1 — the `:`-tail rule accepted only EQUALITY where the full-heading
# rule accepted a PREFIX. 351 fleet findings.
# --------------------------------------------------------------------------
ZGW = """# ZGW Zaak Management

## Requirements

### Requirement: REQ-001: List and search zaken

### Requirement: REQ-005: Manage case-bound sub-resources
"""


class ColonTailPrefixParity(unittest.TestCase):
    def test_fp_the_id_before_the_second_colon_now_resolves(self):
        self.assertTrue(_anchor(ZGW, "REQ-001"))
        self.assertTrue(_anchor(ZGW, "REQ-005"))

    def test_tp_an_id_that_is_in_no_heading_still_fails(self):
        # REQ-002/3/4 exist in the real file; this fixture stops at 005.
        self.assertFalse(_anchor(ZGW, "REQ-002"))
        self.assertFalse(_anchor(ZGW, "REQ-999"))

    def test_tp_the_prefix_rule_still_respects_the_dash_boundary(self):
        # `#REQ-00` must not resolve against `REQ-001`: prefix matching is
        # only allowed to consume WHOLE dash-delimited segments.
        self.assertFalse(_anchor(ZGW, "REQ-00"))

    def test_regression_the_long_tail_still_resolves_by_prefix(self):
        head = "### Task 8 — implement the retry ladder\n"
        self.assertTrue(_anchor(head, "task-8"))
        self.assertFalse(_anchor(head, "task-89"))


# --------------------------------------------------------------------------
# Mode 2 — a requirement id in trailing parentheses. 944 fleet findings.
# --------------------------------------------------------------------------
POS_PAYMENT = """# POS Pluggable Payment Provider Specification

## ADDED Requirements

### Requirement: Payment Provider Adapter Interface (REQ-PAY-001)

#### Scenario: MollieAdapter implements PaymentProviderInterface

### Requirement: Provider Credential Storage & Encryption (REQ-PAY-002)

### Requirement: Refund and capture flows [REQ-PAY-003, REQ-PAY-004]
"""


class ParenthesisedRequirementIds(unittest.TestCase):
    def test_fp_a_parenthesised_id_now_resolves(self):
        self.assertTrue(_anchor(POS_PAYMENT, "REQ-PAY-001"))
        self.assertTrue(_anchor(POS_PAYMENT, "REQ-PAY-002"))

    def test_fp_a_bracketed_comma_list_resolves_each_member(self):
        self.assertTrue(_anchor(POS_PAYMENT, "REQ-PAY-003"))
        self.assertTrue(_anchor(POS_PAYMENT, "REQ-PAY-004"))

    def test_tp_an_id_no_heading_declares_still_fails(self):
        self.assertFalse(_anchor(POS_PAYMENT, "REQ-PAY-005"))
        self.assertFalse(_anchor(POS_PAYMENT, "REQ-CARD-001"))

    def test_tp_a_short_id_is_matched_by_equality_not_prefix(self):
        # This is the anti-blindness assertion for mode 2. If lifted tokens
        # were prefix-matched like full headings, `#REQ` would resolve
        # against REQ-PAY-001 and the gate would accept any tag beginning
        # with a live id's first segment.
        self.assertFalse(_anchor(POS_PAYMENT, "REQ"))
        self.assertFalse(_anchor(POS_PAYMENT, "REQ-PAY"))

    def test_regression_the_full_github_anchor_still_resolves(self):
        self.assertTrue(_anchor(
            POS_PAYMENT,
            "requirement-payment-provider-adapter-interface-req-pay-001",
        ))


# --------------------------------------------------------------------------
# Mode 3 — `- [~]` / `- [-]` checkboxes were invisible, which ALSO shifted
# every positional `#task-N` after them. 28 fleet findings, plus a silent
# mis-resolution class that produced no finding at all.
# --------------------------------------------------------------------------
TASKS = """# Tasks

- [x] 1.1 Write the mapper
- [~] 1.2 Wire the controller
- [ ] 1.3 Add the route
- [-] 1.4 Dropped: the legacy shim
"""


class PartialAndDroppedCheckboxes(unittest.TestCase):
    def test_fp_a_partial_item_id_now_resolves(self):
        self.assertTrue(_anchor(TASKS, "task-1.2"))

    def test_fp_a_dropped_item_id_now_resolves(self):
        self.assertTrue(_anchor(TASKS, "task-1.4"))

    def test_positional_resolution_counts_every_checkbox(self):
        # The important half: `#task-3` must land on 1.3, the THIRD item.
        # With `[~]` invisible the counter never incremented for 1.2, so
        # `#task-3` silently resolved to 1.4 — a wrong answer that reported
        # PASS, which is worse than the missing anchor it replaced.
        #
        # Proved by deleting the third item: `#task-3` must then fail.
        self.assertTrue(_anchor(TASKS, "task-3"))
        three_items = "\n".join(
            ln for ln in TASKS.splitlines() if "1.3" not in ln and "1.4" not in ln
        )
        self.assertFalse(_anchor(three_items, "task-3"))

    def test_tp_a_task_number_past_the_end_still_fails(self):
        self.assertFalse(_anchor(TASKS, "task-5"))
        self.assertFalse(_anchor(TASKS, "task-9.9"))


# --------------------------------------------------------------------------
# Mode 4 — apostrophes and slashes. GitHub DROPS them; the fleet's retrofit
# tooling turns them into `-`. Both spellings name the same heading, and an
# anchor built by dropping the character misses by exactly one and looks
# identical to a dangling reference.
# --------------------------------------------------------------------------
PUNCT = "## A subscription's retry/backoff policy\n"


class SlugPunctuation(unittest.TestCase):
    def test_fp_github_spelling_resolves(self):
        self.assertTrue(_anchor(PUNCT, "a-subscriptions-retrybackoff-policy"))

    def test_fp_kebab_spelling_resolves(self):
        self.assertTrue(_anchor(PUNCT, "a-subscription-s-retry-backoff-policy"))

    def test_tp_a_heading_that_does_not_exist_still_fails(self):
        self.assertFalse(_anchor(PUNCT, "a-subscriptions-retry-policy"))
        self.assertFalse(_anchor(PUNCT, "a-subscriptions-backoff-policy"))

    def test_slugify_turns_punctuation_into_a_separator(self):
        self.assertEqual(csa.slugify("A subscription's retry/backoff policy"),
                         "a-subscription-s-retry-backoff-policy")

    def test_gh_slugify_drops_punctuation_inside_a_word(self):
        self.assertEqual(csa.gh_slugify("A subscription's retry/backoff policy"),
                         "a-subscriptions-retrybackoff-policy")


# --------------------------------------------------------------------------
# Mode 5 — the flat/directory spec path shapes.
# --------------------------------------------------------------------------
SRC_TAG = """<?php
/**
 * @spec openspec/specs/task-collaboration.md#requirement-assign-a-task
 */
class Foo {}
"""
SRC_TAG_MISSING = """<?php
/**
 * @spec openspec/specs/no-such-capability.md#requirement-assign-a-task
 */
class Foo {}
"""
COLLAB = "# Task collaboration\n\n### Requirement: Assign a task\n"


class SpecPathShapes(unittest.TestCase):
    def test_fp_flat_tag_resolves_against_the_directory_form(self):
        findings = _scan(
            {"openspec/specs/task-collaboration/spec.md": COLLAB},
            "lib/Service/Foo.php", SRC_TAG,
        )
        self.assertEqual(findings, [])

    def test_fp_directory_tag_resolves_against_the_flat_form(self):
        src = SRC_TAG.replace("task-collaboration.md",
                              "task-collaboration/spec.md")
        findings = _scan(
            {"openspec/specs/task-collaboration.md": COLLAB},
            "lib/Service/Foo.php", src,
        )
        self.assertEqual(findings, [])

    def test_tp_a_spec_that_exists_in_neither_shape_still_fails(self):
        findings = _scan(
            {"openspec/specs/task-collaboration/spec.md": COLLAB},
            "lib/Service/Foo.php", SRC_TAG_MISSING,
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("target file not found", findings[0])

    def test_tp_the_shape_fallback_does_not_excuse_a_bad_anchor(self):
        # The file is found via the other shape; the fragment still has to
        # exist in it.
        src = SRC_TAG.replace("requirement-assign-a-task",
                              "requirement-delete-a-task")
        findings = _scan(
            {"openspec/specs/task-collaboration/spec.md": COLLAB},
            "lib/Service/Foo.php", src,
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("anchor not found", findings[0])


# --------------------------------------------------------------------------
# The id-like-token rule — `#### Scenario REQ-BIE-004-01: Cron triggers …`
# puts the id BEFORE the colon, as its own token.
# --------------------------------------------------------------------------
BI_EXPORT = """# BI export

#### Scenario REQ-BIE-004-01: Cron triggers export run creation

#### Scenario REQ-BIE-004-02: Worker picks up pending runs within 60 seconds

## BlastService (Task 2.3 of giant)
"""


class IdLikeTokensInHeadings(unittest.TestCase):
    def test_fp_a_pre_colon_id_token_resolves(self):
        self.assertTrue(_anchor(BI_EXPORT, "REQ-BIE-004-01"))
        self.assertTrue(_anchor(BI_EXPORT, "REQ-BIE-004-02"))

    def test_fp_an_id_inside_prose_parentheses_resolves(self):
        self.assertTrue(_anchor(BI_EXPORT, "task-2.3"))

    def test_tp_an_id_absent_from_every_heading_still_fails(self):
        self.assertFalse(_anchor(BI_EXPORT, "REQ-BIE-004-03"))
        self.assertFalse(_anchor(BI_EXPORT, "REQ-BIE-005-01"))
        self.assertFalse(_anchor(BI_EXPORT, "task-2.4"))

    def test_tp_prose_words_are_not_lifted_as_ids(self):
        # The anti-blindness assertion for this rule. Without the
        # digit requirement, every word of every heading before a colon
        # would become an anchor and the gate would resolve anything.
        self.assertFalse(_anchor(BI_EXPORT, "scenario"))
        self.assertFalse(_anchor(BI_EXPORT, "requirement"))
        self.assertFalse(_anchor(BI_EXPORT, "cron"))
        # `#blastservice` DOES resolve — `## BlastService (Task 2.3 of
        # giant)` is a real topic heading whose bracket carries provenance,
        # not title. That is the same class as `#webhooks` below.
        self.assertTrue(_anchor(BI_EXPORT, "blastservice"))
        self.assertFalse(_anchor(BI_EXPORT, "giant"))
        # ...but a fragment that names a real TOPIC heading still resolves:
        # `#webhooks` against `## Webhooks (Task 2.9 of giant)` is a working
        # anchor, so the structural-keyword exclusion is a keyword list and
        # not a ban on short fragments.
        self.assertTrue(_anchor("## Webhooks (Task 2.9 of giant)\n", "webhooks"))
        self.assertFalse(_anchor("### The retry and backoff policy: details\n",
                                 "retry"))
        self.assertFalse(_anchor("### The retry and backoff policy: details\n",
                                 "backoff"))

    def test_idlike_tokens_directly(self):
        self.assertEqual(csa._idlike_tokens("Scenario REQ-BIE-004-01"),
                         {"req-bie-004-01"})
        self.assertEqual(csa._idlike_tokens("Task 2.3 of giant"), {"2-3"})
        self.assertEqual(csa._idlike_tokens("The retry and backoff policy"),
                         set())


# --------------------------------------------------------------------------
# Behaviour that must survive every relaxation above.
# --------------------------------------------------------------------------
class PreservedBehaviour(unittest.TestCase):
    def test_a_missing_target_file_is_reported(self):
        findings = _scan(
            {"openspec/specs/other/spec.md": "# Other\n"},
            "lib/Foo.php",
            "<?php\n/** @spec openspec/specs/ghost/spec.md */\n",
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("target file not found", findings[0])

    def test_an_archived_change_still_resolves(self):
        findings = _scan(
            {
                "openspec/changes/archive/2026-06-14-pos-payment-provider-adapter"
                "/specs/pos-payment-provider-adapter/spec.md": POS_PAYMENT,
            },
            "lib/Foo.php",
            "<?php\n/** @spec openspec/changes/pos-payment-provider-adapter"
            "/specs/pos-payment-provider-adapter/spec.md#REQ-PAY-001 */\n",
        )
        self.assertEqual(findings, [])

    def test_a_tag_with_no_fragment_only_needs_the_file(self):
        findings = _scan(
            {"openspec/specs/thing/spec.md": "# Thing\n"},
            "lib/Foo.php",
            "<?php\n/** @spec openspec/specs/thing/spec.md */\n",
        )
        self.assertEqual(findings, [])

    def test_spec_exclude_is_not_a_target(self):
        findings = _scan(
            {"openspec/specs/thing/spec.md": "# Thing\n"},
            "lib/Foo.php",
            "<?php\n/** @spec exclude pure DTO, no behaviour */\n",
        )
        self.assertEqual(findings, [])

    def test_a_wholly_invented_fragment_is_still_reported(self):
        findings = _scan(
            {"openspec/specs/thing/spec.md": ZGW},
            "lib/Foo.php",
            "<?php\n/** @spec openspec/specs/thing/spec.md"
            "#requirement-teleport-the-zaak */\n",
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("anchor not found", findings[0])


class GateIsNotBlind(unittest.TestCase):
    """One consolidated demonstration that the gate still has teeth.

    If a future relaxation makes ``has_anchor`` return True unconditionally,
    every ``assertFalse`` above goes green individually only if someone
    deletes them. This test asserts the property directly: a spec file with
    real content must reject a fragment built from words that appear
    nowhere in it.
    """

    def test_random_fragments_do_not_resolve_against_a_real_spec(self):
        for frag in (
            "requirement-nonexistent",
            "REQ-ZZZ-999",
            "task-12345",
            "scenario-the-server-catches-fire",
            "zzzz",
            "",
        ):
            with self.subTest(frag=frag):
                self.assertFalse(_anchor(POS_PAYMENT, frag))
                self.assertFalse(_anchor(ZGW, frag))
                self.assertFalse(_anchor(BI_EXPORT, frag))


if __name__ == "__main__":
    unittest.main(verbosity=2)
