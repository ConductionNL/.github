#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-55's ICON_REGISTRY mirror in check_detail_page_discipline.py.

The mirror is a hardcoded copy of nextcloud-vue's
``src/components/CnWidgetGrid/widgetIcons.js``. Nothing enforces the copy, so
it is a silent expiry date — and when it drifts, the gate is wrong in a
direction nobody notices: a widget icon is either rejected while it renders
fine, or accepted while it renders the "?" fallback.

THE DERIVATION IS THE PART THAT GOES WRONG
------------------------------------------
``CnIcon`` resolves a name by KEY lookup::

    _registry[name] || DASHBOARD_ICONS[name] || ... || HelpCircleOutline

so the mirror must hold the object KEYS of ``DASHBOARD_ICONS``. Two keys
deliberately differ from the file they import::

    ClipboardList: ClipboardListIcon  <- '…/ClipboardListOutline.vue'
    Map:           MapIcon            <- '…/MapOutline.vue'

Deriving the set from the ``import`` statements instead — which is what
.github#304 did — yields ``ClipboardListOutline`` / ``MapOutline``, names that
are NOT registry keys and DO render "?", while dropping the two that work. That
report concluded the mirror had drifted on ``ClipboardList``; the mirror was
right and the measurement was wrong, and applying its suggested swap would have
made the gate reject the only working name.

This suite pins both halves so neither can regress:

  1. the working KEYS are present (``Map`` was the one genuine omission —
     nextcloud-vue added it with the Map dashboard widget, and without it the
     gate rejected a valid icon);
  2. the filename-derived spellings are ABSENT, so a future "resync" done by
     grepping imports fails here instead of silently inverting the gate.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "check_detail_page_discipline.py")


def _load():
    spec = importlib.util.spec_from_file_location("_dpd", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class IconRegistryMirrorTest(unittest.TestCase):

    def setUp(self):
        self.registry = _load().ICON_REGISTRY

    def test_keys_whose_import_filename_differs_are_present(self):
        """The two entries whose key != imported file must be the KEY."""
        for key in ("ClipboardList", "Map"):
            self.assertIn(
                key, self.registry,
                f"{key!r} is a DASHBOARD_ICONS key; without it the gate rejects "
                f"an icon that renders correctly",
            )

    def test_filename_derived_spellings_are_absent(self):
        """Guards against a resync done by grepping the import statements.

        These names are not registry keys, so an app that used one would render
        the '?' fallback — accepting them is the failure mode .github#304
        described, and (by its own suggested fix) would have introduced.
        """
        for name in ("ClipboardListOutline", "MapOutline"):
            self.assertNotIn(
                name, self.registry,
                f"{name!r} is an import FILENAME, not a registry key — it "
                f"renders the '?' fallback",
            )

    def test_positive_control_unknown_name_is_not_accepted(self):
        """A name that was never in the registry must not be in the mirror.

        Without this, a mirror that had accidentally become "everything" would
        satisfy both tests above while checking nothing.
        """
        self.assertNotIn("LedgerOutline", self.registry)
        self.assertNotIn("NotAnIconAtAll", self.registry)


if __name__ == "__main__":
    unittest.main()
