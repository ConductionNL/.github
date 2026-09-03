#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Unit cover for check_shipped_object_properties.py.

The acceptance suite (`test_gate108_shipped_object_properties_scope.sh`) drives
the gate through the REAL wrapper over a real git history, and is the authority
on scope. This file covers the axes a two-commit fixture cannot cheaply reach:
the container shapes one at a time, the envelope rule key by key, and the
resolution order between a definition key and a slug.

Run: python3 scripts/lib/test_check_shipped_object_properties.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "check_sop", os.path.join(_HERE, "check_shipped_object_properties.py")
)
assert _SPEC is not None and _SPEC.loader is not None
sop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sop)

_fail = 0
_pass = 0


def ok(msg: str) -> None:
    global _pass
    _pass += 1
    print(f"  ok   — {msg}")


def bad(msg: str) -> None:
    global _fail
    _fail += 1
    print(f"  FAIL — {msg}")


def _run(files: dict[str, dict], changed: set[str] | None = None) -> tuple[int, str]:
    """Write a throwaway app, run the checker over it, return (rc, stdout)."""
    with tempfile.TemporaryDirectory() as app:
        os.makedirs(os.path.join(app, "appinfo"), exist_ok=True)
        with open(os.path.join(app, "appinfo", "info.xml"), "w", encoding="utf-8") as fh:
            fh.write("<info><id>fixture</id></info>")
        for rel, doc in files.items():
            path = os.path.join(app, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = sop.run(app, changed)
        return rc, buf.getvalue()


_SCHEMA_FILE = {
    "openapi": "3.0.0",
    "x-openregister": {"type": "application", "app": "fixture"},
    "components": {
        "registers": {"fixture": {"slug": "fixture", "schemas": ["Thing"]}},
        "schemas": {"Thing": {"type": "object", "slug": "thing",
                              "properties": {"declared": {"type": "string"}}}},
    },
}


def _obj(**extra: object) -> dict:
    base = {"@self": {"register": "fixture", "schema": "thing", "slug": "o-1"}, "declared": "x"}
    base.update(extra)
    return base


print("== the four container shapes are all read ==")
for name, doc in [
    ("components.objects as a LIST",
     {"components": {"objects": [_obj(orphan="v")]}}),
    ("top-level objects as a LIST",
     {"objects": [_obj(orphan="v")]}),
    ("components.objects as a DICT keyed by slug",
     {"components": {"objects": {"o-1": _obj(orphan="v")}}}),
    ("x-openregister.seedData.objects, schema -> list",
     {"x-openregister": {"seedData": {"objects": {"thing": [_obj(orphan="v")]}}}}),
]:
    rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE, "lib/Settings/objs.json": doc})
    if rc == 1 and "orphan" in out:
        ok(f"{name} — the undeclared key is found")
    else:
        bad(f"{name} — rc={rc}, output: {out.strip()[:200]}")

print("== the envelope rule, key by key (openregister's own list) ==")
for key in ("id", "uuid", "@self", "@anything", "_note", "_meta"):
    rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE,
                    "lib/Settings/objs.json": {"components": {"objects": [_obj(**{key: "v"})]}}})
    if rc == 0:
        ok(f"'{key}' is envelope, not a finding")
    else:
        bad(f"'{key}' was reported: {out.strip()[:200]}")

print("== metadata-bearing display keys are a DELIBERATE blind spot ==")
for key in ("name", "title", "description", "summary", "slug", "image", "naam", "omschrijving"):
    rc, _out = _run({"lib/Settings/base.json": _SCHEMA_FILE,
                     "lib/Settings/objs.json": {"components": {"objects": [_obj(**{key: "v"})]}}})
    if rc == 0:
        ok(f"'{key}' reaches a metadata column regardless, so it is not reported")
    else:
        bad(f"'{key}' was reported — it would drown every real finding")

print("== keys openregister does NOT handle at top level ARE reported ==")
for key in ("version", "folder", "schema", "register", "catalog", "bronEntiteit"):
    rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE,
                    "lib/Settings/objs.json": {"components": {"objects": [_obj(**{key: "v"})]}}})
    if rc == 1 and key in out:
        ok(f"'{key}' is ordinary payload and is reported")
    else:
        bad(f"'{key}' was NOT reported — it is only read from @self, so at top level it is dropped")

print("== schema resolution: slug first, definition key as fallback ==")
rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE,
                "lib/Settings/objs.json": {"components": {"objects": [
                    {"@self": {"register": "fixture", "schema": "Thing"}, "orphan": "v"}]}}})
if rc == 1 and "orphan" in out:
    ok("an object referencing the DEFINITION KEY still resolves")
else:
    bad(f"the definition-key fallback did not resolve: {out.strip()[:200]}")

rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE,
                "lib/Settings/objs.json": {"components": {"objects": [
                    {"@self": {"register": "fixture", "schema": "nobody-defines-this"}, "orphan": "v"}]}}})
if rc == 0 and "NOTE" in out and "NOT judged" in out:
    ok("an unresolvable schema is NOTED and counted, never reported as a finding")
else:
    bad(f"an unresolvable schema was mishandled: rc={rc}, {out.strip()[:200]}")

print("== a schema EXTENDED by a later fragment contributes its properties ==")
rc, out = _run({
    "lib/Settings/base.json": _SCHEMA_FILE,
    "lib/Settings/register.d/10-extends.json":
        {"components": {"schemas": {"Thing": {"properties": {"added": {"type": "string"}}}}}},
    "lib/Settings/objs.json": {"components": {"objects": [_obj(added="v")]}},
})
if rc == 0:
    ok("a property declared only by an extending fragment is not reported")
else:
    bad(f"the union across fragments was not taken: {out.strip()[:200]}")

print("== an unreadable file IN SCOPE is a finding; out of scope it is not ==")
with tempfile.TemporaryDirectory() as app:
    os.makedirs(os.path.join(app, "lib", "Settings"), exist_ok=True)
    with open(os.path.join(app, "lib", "Settings", "broken.json"), "w", encoding="utf-8") as fh:
        fh.write("{ not json")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc_in = sop.run(app, {"lib/Settings/broken.json"})
    out_in = buf.getvalue()
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc_out = sop.run(app, {"lib/Settings/something-else.json"})
    if rc_in == 1 and "not valid JSON" in out_in:
        ok("an unreadable file the run was asked to judge fails closed")
    else:
        bad(f"an in-scope unreadable file did not fail: rc={rc_in}, {out_in.strip()[:200]}")
    if rc_out == 0:
        ok("an unreadable file NOT in scope is somebody else's problem")
    else:
        bad("an out-of-scope unreadable file was reported")

print("== the terminal summary line is always printed ==")
_rc, out = _run({"lib/Settings/base.json": _SCHEMA_FILE})
if any(line.startswith("checked ") and line.endswith("object(s)") for line in out.splitlines()):
    ok("'checked N object(s)' is printed — the runner's did-it-finish sentinel")
else:
    bad("the terminal summary is missing; the runner would report this run as a crash")

print()
if _fail == 0:
    print(f"test_check_shipped_object_properties.py: ALL PASS ({_pass} assertions)")
    sys.exit(0)
print(f"test_check_shipped_object_properties.py: {_fail} FAILURE(S) of {_fail + _pass}")
sys.exit(1)
