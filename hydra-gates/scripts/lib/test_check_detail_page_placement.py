#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-55's widgets <-> layout check (ADR-062 rule 8).

Rule 8 says every widget in ``config.widgets`` is placed exactly once. The
check used to know one placement, a ``config.layout`` grid cell, and later
learned two containers (``tabs``, ``container``). A detail page in the v2
shape has more places than that:

  * ``config.sideColumn``: a column of cards beside the body. A string entry
    is the id of a page widget, which CnDetailPage renders there.
  * a ``sections`` widget: ``content.sections[].widgetId`` names the page
    widget each section shows.
  * a ``tabs`` entry with ``widgetIds``: a stack of cards in one tab.

On 2026-10-12 portaliq's ``development`` carried 18 findings of the form
"widget 'x' maps to 0 layout cell(s)" on five detail pages. Every one of those
widgets was placed, in a side column or in a section, and rendered.

THE CONTROL IS HALF OF THIS SUITE. A check that stops reporting placed
widgets must keep reporting an unplaced one, or the fix is only a silence.
So each new placement has a pass case, and the suite also pins that a widget
with no placement at all still fails, that a grid cell next to a side column
placement is reported as a double render, and that a side column entry naming no widget is reported.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "check_detail_page_discipline.py")


def _load():
    spec = importlib.util.spec_from_file_location("_dpd_placement", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cell(widget_id, y=0):
    return {"widgetId": widget_id, "gridX": 0, "gridY": y, "gridWidth": 12, "gridHeight": 2}


def _page(widgets, layout, **config):
    cfg = {"widgets": widgets, "layout": layout}
    cfg.update(config)
    return {"id": "ThingDetail", "type": "detail", "config": cfg}


def _findings(page):
    found = []
    _load().check_page("src/manifest.json", page, {"ThingDetail"}, found)
    return found


class SideColumnPlacementTest(unittest.TestCase):

    def test_a_widget_named_by_the_side_column_is_placed(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}, {"id": "thing-history", "type": "audit-trail"}],
            [_cell("thing-data")],
            sideColumn=["thing-history"],
        )
        self.assertEqual(_findings(page), [])

    def test_an_inline_side_column_card_needs_no_declared_widget(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}],
            [_cell("thing-data")],
            sideColumn=[{"type": "audit-trail", "title": "History"}],
        )
        self.assertEqual(_findings(page), [])

    def test_control_a_widget_with_no_placement_still_fails(self):
        page = _page(
            [
                {"id": "thing-data", "type": "data"},
                {"id": "thing-history", "type": "audit-trail"},
                {"id": "thing-lost", "type": "related"},
            ],
            [_cell("thing-data")],
            sideColumn=["thing-history"],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("widget 'thing-lost' maps to 0 layout cell(s)", found[0])

    def test_control_without_a_side_column_the_old_finding_stands(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}, {"id": "thing-history", "type": "audit-trail"}],
            [_cell("thing-data")],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("widget 'thing-history' maps to 0 layout cell(s)", found[0])

    def test_side_column_and_a_grid_cell_is_a_double_render(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}, {"id": "thing-history", "type": "audit-trail"}],
            [_cell("thing-data"), _cell("thing-history", 2)],
            sideColumn=["thing-history"],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("config.sideColumn AND has 1 layout cell(s)", found[0])

    def test_side_column_and_a_tab_is_left_to_the_designer(self):
        # pipelinq ContactDetail and shillinq CustomerDetail ship exactly this:
        # a History card beside the body and a History tab.
        page = _page(
            [
                {"id": "thing-data", "type": "data"},
                {"id": "thing-history", "type": "audit-trail"},
                {
                    "id": "thing-tabs",
                    "type": "tabs",
                    "content": {"tabs": [{"widgetId": "thing-data"}, {"widgetId": "thing-history"}]},
                },
            ],
            [_cell("thing-tabs")],
            sideColumn=["thing-history"],
        )
        self.assertEqual(_findings(page), [])

    def test_the_same_id_twice_in_the_side_column_is_reported(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}, {"id": "thing-history", "type": "audit-trail"}],
            [_cell("thing-data")],
            sideColumn=["thing-history", "thing-history"],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("named 2 times in config.sideColumn", found[0])

    def test_a_side_column_id_that_names_no_widget_is_reported(self):
        page = _page(
            [{"id": "thing-data", "type": "data"}],
            [_cell("thing-data")],
            sideColumn=["thing-histroy"],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("config.sideColumn names widget 'thing-histroy'", found[0])


class ContainerPlacementTest(unittest.TestCase):

    def _sections_page(self, sections, extra_layout=()):
        return _page(
            [
                {"id": "thing-settings", "type": "sections", "content": {"sections": sections}},
                {"id": "thing-details", "type": "ThingDetailsForm"},
                {"id": "thing-theme", "type": "ThingTheme"},
            ],
            [_cell("thing-settings")] + list(extra_layout),
        )

    def test_a_widget_shown_by_a_section_is_placed(self):
        page = self._sections_page(
            [
                {"key": "details", "title": "Details", "widgetId": "thing-details"},
                {"key": "theme", "title": "Theme", "widgetId": "thing-theme"},
            ]
        )
        self.assertEqual(_findings(page), [])

    def test_control_a_widget_no_section_names_still_fails(self):
        page = self._sections_page([{"key": "details", "title": "Details", "widgetId": "thing-details"}])
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("widget 'thing-theme' maps to 0 layout cell(s)", found[0])

    def test_a_section_widget_with_a_grid_cell_is_a_double_render(self):
        page = self._sections_page(
            [
                {"key": "details", "widgetId": "thing-details"},
                {"key": "theme", "widgetId": "thing-theme"},
            ],
            extra_layout=[_cell("thing-theme", 2)],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("held by a container widget AND has 1 layout cell(s)", found[0])

    def test_a_section_with_an_inline_widget_contributes_nothing(self):
        page = self._sections_page(
            [
                {"key": "details", "widgetId": "thing-details"},
                {"key": "theme", "widgetId": "thing-theme"},
                {"key": "note", "widget": {"type": "text", "content": {"text": "x"}}},
            ]
        )
        self.assertEqual(_findings(page), [])

    def test_a_tab_stack_places_every_widget_it_names(self):
        page = _page(
            [
                {"id": "thing-data", "type": "data"},
                {"id": "thing-history", "type": "audit-trail"},
                {
                    "id": "thing-tabs",
                    "type": "tabs",
                    "content": {"tabs": [{"label": "All", "widgetIds": ["thing-data", "thing-history"]}]},
                },
            ],
            [_cell("thing-tabs")],
        )
        self.assertEqual(_findings(page), [])

    def test_control_a_tab_stack_does_not_place_what_it_does_not_name(self):
        page = _page(
            [
                {"id": "thing-data", "type": "data"},
                {"id": "thing-history", "type": "audit-trail"},
                {
                    "id": "thing-tabs",
                    "type": "tabs",
                    "content": {"tabs": [{"label": "All", "widgetIds": ["thing-data"]}]},
                },
            ],
            [_cell("thing-tabs")],
        )
        found = _findings(page)
        self.assertEqual(len(found), 1, found)
        self.assertIn("widget 'thing-history' maps to 0 layout cell(s)", found[0])


if __name__ == "__main__":
    unittest.main()
