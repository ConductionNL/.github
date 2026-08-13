#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""Tests for check_notification_dialect (gate-18).

WHY THIS FILE DID NOT EXIST UNTIL #424
--------------------------------------
Gate-18 shipped with no helper suite. Its only coverage was the acceptance
bundle under scripts/test-fixtures/gate-acceptance/register-dialect/, whose
expect.conf pins exactly two rows — one per code path — so three of the four
substring tokens and the whole prose axis were unexercised.

WHAT WRITING IT FOUND
---------------------
The four substring tokens were matched against `json.dumps(rule)`: keys,
machine values and human documentation flattened into one haystack. A rule
whose own `description` WARNED AGAINST the legacy dialect was therefore
reported as the legacy dialect, twice over — the "the better the docs, the
redder the repo" shape recorded for gate-58 in source_scope's header.

Every arm below is labelled EVIDENCE or CONTROL by MEASUREMENT, against the
pre-#424 implementation restored as `_blob_scan` at the bottom of this file:

  EVIDENCE (red on the pre-#424 scan)
    test_a_description_warning_against_the_dialect_is_not_the_dialect
    test_a_subject_template_mentioning_at_self_is_not_a_recipient
  CONTROL (green both ways — they prove the fix kept the gate able to fail)
    every arm in LegacyDialectStillDetectedTest

Run: python3 scripts/lib/test_check_notification_dialect.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_notification_dialect as gate  # noqa: E402


def _register(rule: dict) -> dict:
    return {
        "components": {
            "schemas": {
                "Thing": {
                    "type": "object",
                    "x-openregister-notifications": {"onIntakeClosed": rule},
                }
            }
        }
    }


def _scan(rule: dict) -> list[str]:
    fd, path = tempfile.mkstemp(suffix=".register.json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(_register(rule), fh)
        return [line.split("token=", 1)[1] for line in gate.scan_file(path)]
    finally:
        os.unlink(path)


CANONICAL = {
    "trigger": {"type": "lifecycle", "state": "closed"},
    "channels": ["mail"],
    "recipients": ["owner"],
    "subject": {"en": "Intake closed"},
}


class LegacyDialectStillDetectedTest(unittest.TestCase):
    """CONTROL. The gate must be able to fail before anything else counts."""

    def test_a_clean_canonical_rule_is_clean(self):
        self.assertEqual(_scan(dict(CANONICAL)), [])

    def test_legacy_trigger_key_is_reported(self):
        rule = dict(CANONICAL, trigger={"lifecycleEnter": "closed"})
        self.assertIn("lifecycleEnter", _scan(rule))

    def test_legacy_side_channel_flag_is_reported(self):
        self.assertIn("alsoDispatchLifecycle",
                      _scan(dict(CANONICAL, alsoDispatchLifecycle=True)))

    def test_legacy_dedupe_field_is_reported(self):
        self.assertIn("idempotencyKey",
                      _scan(dict(CANONICAL, idempotencyKey="a-b-c")))

    def test_legacy_self_recipient_VALUE_is_reported(self):
        rule = dict(CANONICAL, recipients=["@self.owner"])
        self.assertIn("@self.", _scan(rule))

    def test_singular_channel_is_reported(self):
        rule = {k: v for k, v in CANONICAL.items() if k != "channels"}
        rule["channel"] = "mail"
        self.assertIn("channel", _scan(rule))

    def test_singular_recipient_is_reported(self):
        rule = {k: v for k, v in CANONICAL.items() if k != "recipients"}
        rule["recipient"] = "owner"
        self.assertIn("recipient", _scan(rule))

    def test_legacy_calculated_trigger_key_is_reported(self):
        rule = dict(CANONICAL, trigger={"calculated": "score"})
        self.assertIn("trigger.calculated", _scan(rule))


class ProseIsNotDialectTest(unittest.TestCase):
    """#424 — documentation ABOUT the dialect is not the dialect."""

    def test_a_description_warning_against_the_dialect_is_not_the_dialect(self):
        """EVIDENCE."""
        rule = dict(
            CANONICAL,
            description=(
                "Canonical dialect. Do NOT use the legacy lifecycleEnter "
                "trigger or alsoDispatchLifecycle; both were removed in "
                "ADR-031, and idempotencyKey with them."
            ),
        )
        self.assertEqual(_scan(rule), [])

    def test_a_subject_template_mentioning_at_self_is_not_a_recipient(self):
        """EVIDENCE. `subject` is the CANONICAL per-locale message map."""
        rule = dict(CANONICAL, subject={"en": "Closed — see @self.owner below"})
        self.assertEqual(_scan(rule), [])

    def test_documented_AND_defective_is_still_reported(self):
        """CONTROL, and the one that matters: excusing prose must not excuse
        the rule the prose sits on."""
        rule = dict(
            CANONICAL,
            description="We must stop using lifecycleEnter.",
            trigger={"lifecycleEnter": "closed"},
        )
        self.assertIn("lifecycleEnter", _scan(rule))


class MutationTest(unittest.TestCase):
    """The pre-#424 scan, restored, so the labels above are measured rather
    than asserted. If this ever agrees with the current one, the EVIDENCE arms
    are inert and this suite proves nothing."""

    _SUBSTRING_TOKENS = (
        "lifecycleEnter", "alsoDispatchLifecycle", "idempotencyKey", "@self.",
    )

    def _blob_scan(self, rule: dict) -> list[str]:
        blob = json.dumps(rule)
        return [t for t in self._SUBSTRING_TOKENS if t in blob]

    def test_the_old_blob_scan_fails_the_description_fixture(self):
        rule = dict(
            CANONICAL,
            description=(
                "Canonical dialect. Do NOT use the legacy lifecycleEnter "
                "trigger or alsoDispatchLifecycle; both were removed in "
                "ADR-031, and idempotencyKey with them."
            ),
        )
        self.assertEqual(
            self._blob_scan(rule),
            ["lifecycleEnter", "alsoDispatchLifecycle", "idempotencyKey"],
        )
        self.assertEqual(_scan(rule), [])

    def test_the_old_blob_scan_fails_the_subject_fixture(self):
        rule = dict(CANONICAL, subject={"en": "Closed — see @self.owner below"})
        self.assertEqual(self._blob_scan(rule), ["@self."])
        self.assertEqual(_scan(rule), [])

    def test_the_two_scans_AGREE_on_every_real_defect(self):
        """If they agreed everywhere the fix would be a no-op; if they
        disagreed everywhere it would be a deletion. They must differ on prose
        and agree on defects."""
        for rule in (
            dict(CANONICAL, trigger={"lifecycleEnter": "closed"}),
            dict(CANONICAL, alsoDispatchLifecycle=True),
            dict(CANONICAL, idempotencyKey="a-b-c"),
            dict(CANONICAL, recipients=["@self.owner"]),
        ):
            old = set(self._blob_scan(rule))
            new = set(_scan(rule))
            self.assertTrue(old and old.issubset(new), (old, new))


if __name__ == "__main__":
    unittest.main()
