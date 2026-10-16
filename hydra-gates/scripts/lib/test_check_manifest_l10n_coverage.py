#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Self-test for check_manifest_l10n_coverage.py (gate-102).

Pins that a field path inside a data-binding block (`source`, `bind`) is not
read as copy, while a real label next to it, and a `label` that is plain copy,
are still reported. The toggle-table shape is taken from shillinq's
required-fields admin tab, where `source.label: "title"` names the row field.
A string made only of `{field}` tokens is a row template, not copy.

Run: python3 scripts/lib/test_check_manifest_l10n_coverage.py   (exit 0 = green)
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_manifest_l10n_coverage import main  # noqa: E402

_FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS - {name}")
    else:
        print(f"FAIL - {name}{(': ' + detail) if detail else ''}")
        _FAILED.append(name)


def run(manifest: dict, keys: list[str], fragments: dict | None = None) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "src", "manifest.d"))
        os.makedirs(os.path.join(root, "l10n"))
        with open(os.path.join(root, "src", "manifest.json"), "w") as fh:
            json.dump(manifest, fh)
        for name, body in (fragments or {}).items():
            with open(os.path.join(root, "src", "manifest.d", name), "w") as fh:
                json.dump(body, fh)
        with open(os.path.join(root, "l10n", "nl.json"), "w") as fh:
            json.dump({"translations": {k: k for k in keys}}, fh)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["check", root])
        return rc, out.getvalue()


TOGGLE_TABLE = {
    "adminTab": {
        "id": "required-fields",
        "widget": {
            "type": "toggle-table",
            "content": {
                "source": {
                    "url": "/apps/shillinq/api/field-requirements",
                    "path": "rows",
                    "key": "id",
                    "label": "title",
                },
                "bind": {
                    "mode": "each",
                    "field": "enabled",
                    "label": "enabled",
                },
                "emptyText": "No required fields yet.",
            },
        },
    },
}

# --- the false positive -----------------------------------------------------
rc, out = run({"menu": []}, ["No required fields yet."], {"required.json": TOGGLE_TABLE})
check("source.label field path is not reported", "FAIL no nl.json key: title" not in out, out)
check("bind.label field path is not reported", "FAIL no nl.json key: enabled" not in out, out)
check("toggle-table with covered copy passes", rc == 0, f"rc={rc}\n{out}")
check("only the real copy is counted", "checked 1 manifest string(s)" in out, out)

# --- real copy next to the field path is still checked ----------------------
rc, out = run({"menu": []}, [], {"required.json": TOGGLE_TABLE})
check("emptyText beside a source block is still reported", "FAIL no nl.json key: No required fields yet." in out, out)
check("uncovered copy fails the gate", rc == 1, f"rc={rc}")

# --- an ordinary label is still copy ----------------------------------------
manifest = {
    "menu": [{"id": "Flows", "label": "Flow", "route": "Flows"}],
    "pages": [
        {
            "id": "Invoices",
            "type": "index",
            "title": "Invoices",
            "config": {"columns": [{"key": "state", "label": "Status"}]},
        },
    ],
}
rc, out = run(manifest, ["Invoices"])
check("menu label is reported", "FAIL no nl.json key: Flow" in out, out)
check("column label is reported", "FAIL no nl.json key: Status" in out, out)
check("covered title is not reported", "FAIL no nl.json key: Invoices" not in out, out)
check("uncovered labels fail the gate", rc == 1, f"rc={rc}")

# --- a scalar `source` (a URL prop) does not hide its siblings --------------
manifest = {
    "pages": [
        {
            "id": "Audit",
            "title": "Audit trail",
            "props": {"source": "/index.php/apps/openregister/api/audit-trails"},
        },
    ],
}
rc, out = run(manifest, [])
check("title beside a scalar source is reported", "FAIL no nl.json key: Audit trail" in out, out)

# --- pure field templates are filled from the row, not translated -----------
RECORD_LIST = {
    "pages": [
        {
            "id": "Customer",
            "type": "detail",
            "widgets": [
                {
                    "type": "record-list",
                    "title": "Open invoices",
                    "content": {
                        "title": "{invoiceNumber}",
                        "subtitle": "{amount|currency:EUR} · {dueDate|date}",
                        "description": "Factuur {invoiceNumber}",
                        "label": "{total}",
                    },
                },
            ],
        },
    ],
}
rc, out = run(RECORD_LIST, ["Open invoices"])
check("a pure {field} title is not reported", "FAIL no nl.json key: {invoiceNumber}" not in out, out)
check("tokens with formats and punctuation are not reported", "{amount|currency:EUR}" not in out, out)
check("a lone {total} label is not reported", "FAIL no nl.json key: {total}" not in out, out)
check("a template with words is still reported", "FAIL no nl.json key: Factuur {invoiceNumber}" in out, out)
check("only the worded strings are counted", "checked 2 manifest string(s)" in out, out)
check("the worded template fails the gate", rc == 1, f"rc={rc}")

rc, out = run(RECORD_LIST, ["Open invoices", "Factuur {invoiceNumber}"])
check("covering the worded template passes", rc == 0, f"rc={rc}\n{out}")

if _FAILED:
    print(f"\n{len(_FAILED)} assertion(s) failed")
    sys.exit(1)
print("\nall assertions passed")
