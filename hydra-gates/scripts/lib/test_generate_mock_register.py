#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for generate_mock_register (gates 99/100). Run with:

    python3 scripts/lib/test_generate_mock_register.py

WHY THIS SUITE EXISTS
---------------------
The generator had no tests, and three defects in it were each SILENT — every
one produced a plausible, valid-looking result and exited 0.

1. DISCOVERY WAS NARROWER THAN COLLECTION. Schema definitions were swept only
   from files that also DECLARE a register. humaniq declares its register with
   a list of 54 schema names in one file and defines all 54 across thirty
   others that declare no register, so every name resolved to no definition
   and the tool announced "declares no schemas — nothing to generate". Three
   apps were written off on the strength of that sentence.

2. A SCHEMA SPLIT ACROSS FILES WAS TRUNCATED TO WHICHEVER SORTED FIRST.
   pipelinq ships a base `ticket` and a separate CTI overlay whose own comment
   says the overlay must land there "or OpenRegister's magic-table columns for
   these fields never exist". `setdefault` kept one half and discarded the
   other. Both halves are real schemas, so both outcomes generate objects that
   validate — nothing could notice.

3. THE APP ID CAME FROM THE CHECKOUT DIRECTORY. `x-openregister.app` is what
   the descriptor inventory resolves a register to an app by. Five of eight
   fleet apps already ship an `<id>` that differs from their directory name,
   so their descriptors named an app that does not exist. A cross-app id is a
   runtime lookup: it does not error, it finds nobody.

Every class below plants the defect's input and asserts the generator handles
it, AND asserts the property that would be wrong under the old behaviour. An
arm that only ever sees input both versions handle proves nothing.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_mock_register as gmr  # noqa: E402


def _schema(properties: dict, **extra) -> dict:
    """A minimal schema the generator can actually synthesise against."""
    return {"type": "object", "properties": properties, **extra}


def _write(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _app(root: Path, app_id: str | None = "widget") -> None:
    """Lay down appinfo/info.xml, or omit it when app_id is None."""
    if app_id is None:
        return
    path = root / "appinfo" / "info.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<info><id>{app_id}</id></info>", encoding="utf-8")


class DefinitionsAcrossFiles(unittest.TestCase):
    """Defect 1: a schema defined in a file that declares no register."""

    def _modular_app(self, root: Path) -> None:
        # The register names its schemas but defines none of them — exactly
        # humaniq's shape.
        _write(
            root,
            "lib/Settings/widget_register.json",
            {
                "x-openregister": {"type": "application", "app": "widget"},
                "components": {
                    "registers": {"widget": {"schemas": ["Employee", "Payslip"]}},
                    "schemas": {},
                },
            },
        )
        # Definitions live elsewhere, in files declaring NO register.
        _write(
            root,
            "lib/Settings/schemas/employee.json",
            {"components": {"schemas": {"Employee": _schema({"name": {"type": "string"}})}}},
        )
        _write(
            root,
            "lib/Settings/schemas/payslip.json",
            {"components": {"schemas": {"Payslip": _schema({"gross": {"type": "number"}})}}},
        )

    def test_a_schema_defined_away_from_its_register_is_still_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._modular_app(root)

            _registers, owns, definitions = gmr._register_schema_map(str(root))

            # 🔴 THE ASSERTION THAT FAILS UNDER THE OLD BEHAVIOUR. Sweeping
            # definitions only from register-declaring files left `definitions`
            # empty, so `owns['widget']` filtered down to [] and the generator
            # reported the app as carrying no schemas.
            self.assertEqual(sorted(definitions), ["Employee", "Payslip"])
            self.assertEqual(owns["widget"], ["Employee", "Payslip"])

    def test_it_generates_objects_for_those_schemas_rather_than_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._modular_app(root)

            built = gmr.build(str(root), "widget", 3, None)
            objects = built["components"]["objects"]

            self.assertEqual(len(objects), 6, "3 objects for each of 2 schemas")
            self.assertEqual(
                {o["@self"]["schema"] for o in objects}, {"Employee", "Payslip"}
            )

    def test_a_name_with_no_definition_anywhere_is_still_dropped(self):
        """The widening must not turn undefined names into phantom schemas.

        A register may legitimately list a schema whose definition ships in an
        app this one does not have. Those must stay out — otherwise the fix to
        defect 1 invents objects for schemas that do not exist.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            _write(
                root,
                "lib/Settings/widget_register.json",
                {
                    "components": {
                        "registers": {"widget": {"schemas": ["Employee", "FromAnotherApp"]}},
                        "schemas": {},
                    }
                },
            )
            _write(
                root,
                "lib/Settings/schemas/employee.json",
                {"components": {"schemas": {"Employee": _schema({"name": {"type": "string"}})}}},
            )

            _registers, owns, _definitions = gmr._register_schema_map(str(root))

            self.assertEqual(owns["widget"], ["Employee"])


class SchemaSplitAcrossFiles(unittest.TestCase):
    """Defect 2: a base definition plus an overlay that extends it."""

    def _overlaid_app(self, root: Path) -> None:
        _write(
            root,
            "lib/Settings/a_base.json",
            {
                "components": {
                    "registers": {"widget": {"schemas": ["ticket"]}},
                    "schemas": {
                        "ticket": _schema(
                            {"title": {"type": "string"}, "status": {"type": "string"}},
                            required=["title"],
                        )
                    },
                }
            },
        )
        # Sorts AFTER a_base.json, so first-wins discarded it.
        _write(
            root,
            "lib/Settings/z_overlay.json",
            {
                "components": {
                    "schemas": {
                        "ticket": _schema(
                            {"telephony_platform": {"type": "string"}},
                            required=["telephony_platform"],
                        )
                    }
                }
            },
        )

    def test_both_halves_of_a_split_schema_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._overlaid_app(root)

            _registers, _owns, definitions = gmr._register_schema_map(str(root))
            properties = definitions["ticket"]["properties"]

            # 🔴 UNDER first-wins ONLY `title`/`status` SURVIVED, and the demo
            # data satisfied half a schema while looking entirely valid.
            self.assertIn("title", properties)
            self.assertIn("status", properties)
            self.assertIn("telephony_platform", properties)
            self.assertEqual(
                sorted(definitions["ticket"]["required"]),
                ["telephony_platform", "title"],
                "`required` is unioned too, or the overlay's mandatory fields "
                "are generated as optional and may be omitted",
            )

    def test_the_overlay_reaches_the_generated_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._overlaid_app(root)

            built = gmr.build(str(root), "widget", 1, None)
            obj = built["components"]["objects"][0]

            self.assertIn("telephony_platform", obj)
            self.assertIn("title", obj)

    def test_a_property_defined_in_both_files_keeps_one_definition(self):
        """Merging must not produce a property that is two things at once."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            _write(
                root,
                "lib/Settings/a_base.json",
                {
                    "components": {
                        "registers": {"widget": {"schemas": ["ticket"]}},
                        "schemas": {"ticket": _schema({"title": {"type": "string"}})},
                    }
                },
            )
            _write(
                root,
                "lib/Settings/z_overlay.json",
                {"components": {"schemas": {"ticket": _schema({"title": {"type": "number"}})}}},
            )

            _registers, _owns, definitions = gmr._register_schema_map(str(root))

            self.assertEqual(definitions["ticket"]["properties"]["title"], {"type": "string"})


class AppIdentity(unittest.TestCase):
    """Defect 3: `x-openregister.app` took the directory name."""

    def test_the_app_id_comes_from_info_xml_not_the_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hrmq"
            root.mkdir()
            _app(root, "humaniq")

            # 🔴 THE DIRECTORY IS `hrmq`; THE SHIPPED ID IS `humaniq`. Five of
            # eight fleet apps are in exactly this state.
            self.assertEqual(gmr._app_id(str(root)), "humaniq")

    def test_it_falls_back_to_the_directory_when_there_is_no_info_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "somedir"
            root.mkdir()

            self.assertEqual(gmr._app_id(str(root)), "somedir")

    def test_a_relative_dot_does_not_become_the_app_id(self):
        """`basename(".")` is `"."` — a nonsense id, and the gate always passes
        a relative dot."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myapp"
            root.mkdir()
            try:
                os.chdir(root)
                self.assertEqual(gmr._app_id("."), "myapp")
            finally:
                os.chdir(cwd)

    def test_main_uses_the_app_id_for_the_descriptor_and_the_filename(self):
        """🔴 THE CALL SITE, NOT JUST THE HELPER.

        The three tests above call `_app_id()` directly, so they all stayed
        GREEN when the fix was reverted — reverting it changes only which
        expression `main()` assigns to `app_id`, and a test that never runs
        `main()` cannot see that. Caught by reverting each defect in turn and
        noticing this class did not fail.

        This arm drives the whole generator over a directory whose name is not
        its id, and asserts on what actually lands on disk.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hrmq"
            root.mkdir()
            _app(root, "humaniq")
            _write(
                root,
                "lib/Settings/widget_register.json",
                {
                    "components": {
                        "registers": {"humaniq": {"schemas": ["Employee"]}},
                        "schemas": {"Employee": _schema({"name": {"type": "string"}})},
                    }
                },
            )

            rc = gmr.main(["generate_mock_register.py", str(root)])
            self.assertEqual(rc, 0)

            written = sorted((root / "lib" / "Settings").glob("*_mock_register.json"))
            self.assertEqual(
                [p.name for p in written],
                ["humaniq_mock_register.json"],
                "the descriptor is named for the app id, not the directory",
            )
            payload = json.loads(written[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["x-openregister"]["app"], "humaniq")

    def test_info_xml_wins_over_the_directory_in_the_written_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hrmq"
            root.mkdir()
            _app(root, "humaniq")
            _write(
                root,
                "lib/Settings/widget_register.json",
                {
                    "components": {
                        "registers": {"humaniq": {"schemas": ["Employee"]}},
                        "schemas": {"Employee": _schema({"name": {"type": "string"}})},
                    }
                },
            )

            built = gmr.build(str(root), gmr._app_id(str(root)), 1, None)

            self.assertEqual(built["x-openregister"]["app"], "humaniq")
            # The `--app=` hint the descriptor prints must resolve too.
            self.assertIn("--app=humaniq", built["x-openregister"]["description"])


class UnusualComponentShapes(unittest.TestCase):
    """A crashed checker is not a finding.

    `components.registers` is not always a slug-keyed map: openregister's
    `avg-bundle.json` and `report-bundle.json` ship a LIST of register
    objects. The old discovery required a dict, so those files never reached
    the code that reads `.keys()`. Widening discovery to schema-defining files
    let them through and `--check` died with

        AttributeError: 'list' object has no attribute 'keys'

    on the app that owns the gate.
    """

    def _app_with_a_list_shaped_register(self, root: Path) -> None:
        _write(
            root,
            "lib/Settings/widget_register.json",
            {
                "components": {
                    "registers": {"widget": {"schemas": ["Employee"]}},
                    "schemas": {"Employee": _schema({"name": {"type": "string"}})},
                }
            },
        )
        _write(
            root,
            "lib/Resources/avg-bundle.json",
            {
                "components": {
                    "registers": [{"title": "AVG", "slug": "avg"}],
                    "schemas": {"Consent": _schema({"granted": {"type": "boolean"}})},
                }
            },
        )

    def test_check_does_not_crash_on_a_list_shaped_registers_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._app_with_a_list_shaped_register(root)
            gmr.main(["generate_mock_register.py", str(root)])

            rc = gmr.main(["generate_mock_register.py", str(root), "--check"])

            self.assertEqual(rc, 0, "a list-shaped registers block must not crash --check")

    def test_the_map_still_resolves_the_dict_shaped_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            self._app_with_a_list_shaped_register(root)

            _registers, owns, definitions = gmr._register_schema_map(str(root))

            # The bundle contributes its DEFINITIONS but no register slug —
            # this suite does not teach the generator the list dialect, it only
            # stops it dying on one.
            self.assertEqual(owns["widget"], ["Employee"])
            self.assertIn("Consent", definitions)
            self.assertNotIn("avg", owns)


class MockDescriptorsAreNotInput(unittest.TestCase):
    """The generator's own output must never be read back as a source.

    Widening discovery to any file with a `components` block brings the
    generated mock register itself into range — it has one. Feeding it back
    would let demo objects define schemas.
    """

    def test_a_mock_marked_file_is_skipped_by_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _app(root)
            _write(
                root,
                "lib/Settings/widget_register.json",
                {
                    "components": {
                        "registers": {"widget": {"schemas": ["Employee"]}},
                        "schemas": {"Employee": _schema({"name": {"type": "string"}})},
                    }
                },
            )
            _write(
                root,
                "lib/Settings/widget_mock_register.json",
                {
                    "x-openregister": {"type": "mock", "app": "widget"},
                    "components": {"schemas": {"GhostSchema": _schema({})}, "objects": []},
                },
            )

            _registers, _owns, definitions = gmr._register_schema_map(str(root))

            self.assertIn("Employee", definitions)
            self.assertNotIn("GhostSchema", definitions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
